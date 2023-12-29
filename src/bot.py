import discord
from discord.ext import commands
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

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
             (name text, id text, join_time text)''')

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello, world!')

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None:
        if after.channel.name == 'General':
            # Get current time
            join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Insert values into the database
            c.execute("INSERT INTO voice_log VALUES (?, ?, ?, ?)", (member.name, member.id, join_time, after.channel.name))
            # Commit the changes
            conn.commit()
            print(f'Logged user {member.name} at {join_time}...')

bot.run(bot_token)

# Close the connection to the database
conn.close()
