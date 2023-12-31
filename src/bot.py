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
import pandas as pd
import requests


if __name__ == '__main__':
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

    # Authenticate with Google Drive
    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()

    # Create a Google Drive instance
    drive = GoogleDrive(gauth)

    # Check if the file exists in Google Drive
    file_list = drive.ListFile({'q': "title='voice_log.csv'"}).GetList()
    print(file_list)
    if file_list:
        # Download the file
        file = file_list[0]
        file.GetContentFile('voice_log.csv')
        # print(file)

        # URL of the file in Google Drive
        file_id = file['id']

        # Extract the file ID from the URL

        # Construct the download link
        download_link = f'https://drive.google.com/uc?id={file_id}'
        print(download_link)
        requests.get(download_link)
        # Read the file into a pandas DataFrame
        df = pd.read_csv('voice_log.csv')

        # Print the DataFrame
        print(df)
        # df = pd.read_csv(file)
        df.to_sql('voice_log.db', conn, if_exists='append', index=False)
        print('Downloaded voice_log.csv from Google Drive!')
    else:
        print('voice_log.csv does not exist in Google Drive.')

    bot.run(bot_token)

    # Close the connection to the database
    conn.close()


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello, world!')

def upload():
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
        file.SetContentFile(csv_file)
        file.Upload()
        print(f'Updated {csv_file} in Google Drive!')
    else:
        # Upload the CSV file to Google Drive
        file = drive.CreateFile({'title': csv_file})
        file.SetContentFile(csv_file)
        file.Upload()
        print(f'Uploaded {csv_file} to Google Drive!')

@bot.event()
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
            upload()

    if before.channel is not None:
        if before.channel.name == 'General':
            # Get current time in UTC
            utc_now = datetime.now(pytz.utc)
            
            # Convert to Pacific time
            pacific_tz = pytz.timezone('US/Pacific')
            pacific_time = utc_now.astimezone(pacific_tz)
            
            # Format the time
            leave_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Insert values into the database
            c.execute("INSERT INTO voice_log VALUES (?, ?, ?, ?)", (member.name, member.id, leave_time, before.channel.name))
            # Commit the changes
            conn.commit()
            print(f'Logged user {member.name} leaving at {leave_time}...')
            print(pd.read_sql_query("SELECT * FROM voice_log", conn))
            upload()
            