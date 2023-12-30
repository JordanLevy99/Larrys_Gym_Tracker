import discord
from discord.ext import commands
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pytz

# Load the .env file
load_dotenv()

# Get the bot token
bot_token = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Connect to the SQLite database
conn = sqlite3.connect('voice_log.db')
c = conn.cursor()
 
# Create table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS voice_log
             (name text, id text, join_time text, channel text)''')

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello, world!')

@bot.command()
async def upload(ctx):
    # Query the voice_log table
    df = pd.read_sql_query("SELECT * FROM voice_log", conn)
    
    # Save the table as a CSV file
    csv_file = 'voice_log.csv'
    df.to_csv(csv_file, index=False)
    
    # Authenticate with Google Drive
    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()
    
    # Create a Google Drive instance
    drive = GoogleDrive(gauth)
    
    # Check if the file already exists in Google Drive
    file_list = drive.ListFile({'q': f"title='{csv_file}'"}).GetList()
    if file_list:
        # Update the existing file
        file = file_list[0]
        print(file_list)
        file.SetContentFile(csv_file)
        file.Upload()
        await ctx.send(f'Updated {csv_file} in Google Drive!')
    else:
        # Upload the CSV file to Google Drive
        file = drive.CreateFile({'title': csv_file})
        file.SetContentFile(csv_file)
        file.Upload()
        await ctx.send(f'Uploaded {csv_file} to Google Drive!')

@bot.event

async def on_voice_state_update(member, before, after):
    if after.channel is not None:
        if after.channel.name == 'General':
            # Get current time in UTC
            utc_now = datetime.now(pytz.utc)
            
            # Convert to Pacific time
            pacific_tz = pytz.timezone('US/Pacific')
            pacific_time = utc_now.astimezone(pacific_tz)
            
            # Format the time
            join_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Insert values into the database
            c.execute("INSERT INTO voice_log VALUES (?, ?, ?, ?)", (member.name, member.id, join_time, after.channel.name))
            # Commit the changes
            conn.commit()
            print(f'Logged user {member.name} at {join_time}...')
            print(pd.read_sql_query("SELECT * FROM voice_log", conn))

bot.run(bot_token)

# Close the connection to the database
conn.close()

