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
from discord import Permissions
from datetime import timedelta

# Constants
db_file = 'dinksters_database.db'
text_channel = 'larrys-gym-planner-name-subject-to-change'
current_text_channel = lambda member: discord.utils.get(member.guild.text_channels, name=text_channel)
voice_channel = 'Larry\'s Gym'
verbose = False

# Walking constants
global start_hour, end_hour

start_hour = 7
end_hour =  9
length_of_walk_in_minutes = 45
max_on_time_points = 50
max_duration_points = 50

# Load the .env file
load_dotenv()

# permissions = Permissions(0x00000400 | 0x00000800 | 0x00800000)
# Get the bot token
bot_token = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix='!', intents=intents)

# Connect to the SQLite database
conn = sqlite3.connect(db_file)
c = conn.cursor()

# Create table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS voice_log
            (name text, id text, time datetime, channel text, user_joined boolean)''')

# Create table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS points
            (name text, id text, points_awarded float, time datetime, type text)''')

def download():
    global conn, c, drive
    # Authenticate with Google Drive
    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()

    # Create a Google Drive instance
    drive = GoogleDrive(gauth)

    # Check if the file exists in Google Drive
    file_list = drive.ListFile({'q': f"title='{db_file}'"}).GetList()
    if file_list:
        # Download the file
        file = file_list[0]
        file.GetContentFile(db_file)

        # URL of the file in Google Drive
        file_id = file['id']

        # Construct the download link
        download_link = f'https://drive.google.com/uc?id={file_id}'
        print(download_link)
        requests.get(download_link)
        # Read the file into a pandas DataFrame
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        df = pd.read_sql_query("SELECT * FROM voice_log", conn)

        # Print the last five entries of the DataFrame
        print(df.tail())
        df.to_sql(db_file, conn, if_exists='replace', index=False)
        print(f'Downloaded {db_file} from Google Drive!')
    else:
        print(f'{db_file} does not exist in Google Drive.')
    # return conn, c, drive

download()

@bot.command()
async def start_time(ctx, start_time: int):
    global start_hour, end_hour
    start_hour = start_time
    end_hour = start_time + 2

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

async def upload(channel):
    # Query the voice_log table    
    # Check if the file already exists in Google Drive
    file_list = drive.ListFile({'q': f"title='{db_file}'"}).GetList()
    if file_list:
        # Update the existing file
        file = file_list[0]
        file.SetContentFile(db_file)
        file.Upload()
        print(f'Updated {db_file} in Google Drive!')
    else:
        # Upload the CSV file to Google Drive
        file = drive.CreateFile({'title': db_file})
        file.SetContentFile(db_file)
        file.Upload()
        print(f'Uploaded {db_file} to Google Drive!')

async def add_points(text_channel):
    print('Points query results:')
    users_df = pd.read_sql_query("""
                            SELECT name, id, time 
                            FROM voice_log
                            GROUP BY time, id
                            ORDER BY time DESC 
                            LIMIT 2""", conn)
    users_df['time'] = users_df['time'].astype('datetime64[ns]')
    users_durations = users_df.groupby('id').apply(lambda user: user['time'].max() - user['time'].min())
    await calculate_points(text_channel, users_df, users_durations)
    print(pd.read_sql_query("""SELECT * FROM points""", conn).tail())

@bot.command()
async def leaderboard(ctx):
    print(ctx.guild.roles)
    role = discord.utils.get(ctx.guild.roles, name='Walker')
    if role:
        for member in role.members:
            print(member.name)
    # Select all rows from the points table
    leaderboard_series = pd.read_sql_query(f"""SELECT name, SUM(points_awarded) as total_points 
                                       FROM points 
                                       WHERE id IN ({','.join([f'"{member.id}"' for member in role.members])}) 
                                       GROUP BY id""", conn)
    print(leaderboard_series)
    if leaderboard_series.empty:
        print(role.members)
        # Find all users in the text_channel and output 0 for their points
        leaderboard_series = pd.Series(dict(zip([member.name for member in role.members], [0] * len(role.members))))
        leaderboard_series.name = 'Total Points'
        # leaderboard_df = pd.DataFrame(data=dict(zip([member.name for member in role.members], [0] * len(role.members))))

    # Send the leaderboard as a message in the text_channel
    # await ctx.send(f"Leaderboard:\n{leaderboard_df.to_string(index=False)}")
    await ctx.send(f"Leaderboard:\n{leaderboard_series.to_string(index=True)}")

async def calculate_points(text_channel, users_df, users_durations):
    walk_time_in_seconds = timedelta(minutes=length_of_walk_in_minutes).total_seconds()
    duration_points = (users_durations.dt.total_seconds() / walk_time_in_seconds) * 50
    duration_points.loc[duration_points>max_duration_points] = max_duration_points
    late_time = (users_df.groupby('id').apply(lambda user: user['time'].min() - user['time'].min().replace(hour=start_hour, minute=0, second=0)))
    on_time_points = max_on_time_points - (late_time.dt.total_seconds() / (walk_time_in_seconds / 2)) * 50
    on_time_points.loc[on_time_points<0] = 0

    await process_points_df(text_channel, users_df, on_time_points, 'ON TIME')
    await process_points_df(text_channel, users_df, duration_points, 'DURATION')    

async def process_points_df(text_channel, users_df, points_df, points_type):
    points_df.name = 'points_awarded'
    points_df = points_df.to_frame()
    points_df['type'] = points_type
    points_df = points_df.merge(users_df.loc[users_df['time'] == users_df['time'].max(), ['name', 'id', 'time']], how='left', left_on='id', right_on='id')
    points_df = points_df[['name', 'id', 'points_awarded', 'time', 'type']]
    if len(points_df) == 1:
        await text_channel.send(f"Awarded {points_df['points_awarded'].values[0]} points to {points_df['name'].values[0]} for {points_df['type'].values[0]}")
    points_df.to_sql('points', conn, if_exists='append', index=False)
    return points_df

@bot.event
async def on_voice_state_update(member, before, after):
    
    # Get current time in Pacific timezone
    current_time = _get_current_time()
    pacific_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")


    # Check if the time is between 7am and 9am in Pacific timezone
    if pacific_time.hour >= start_hour and pacific_time.hour < end_hour:
        if after.channel is not None and after.channel.name == voice_channel:
            # Get current time in UTC
            join_time = _get_current_time()
            append_to_database(member, after, join_time, joined=True)
            
            # Send a message in the general text channel
            await log_and_upload(member, join_time, True)

        if before.channel is not None and before.channel.name == voice_channel:
            leave_time = _get_current_time()
            
            append_to_database(member, before, leave_time, joined=False)
            await add_points(current_text_channel(member))
            await log_and_upload(member, leave_time, False)

async def log_and_upload(member, event_time, joining):
    logging_channel = current_text_channel(member)
    if verbose:
        await log_data(logging_channel, member, event_time, joining)
    await upload(logging_channel)

async def log_data(channel, member, event_time, joining):
    leaving_str = "leaving " if not joining else ""
    # await channel.send(f'Logged user {member.name} {leaving_str}at {event_time}...')
    print(f'Logged user {member.name} {leaving_str}at {event_time}...')
    print(pd.read_sql_query("SELECT * FROM voice_log", conn).tail())

def append_to_database(member, event, event_time, joined):
    c.execute("INSERT INTO voice_log VALUES (?, ?, ?, ?, ?)", (member.name, member.id, event_time, event.channel.name, joined))
    conn.commit()

def _get_current_time():
    utc_now = datetime.now(pytz.utc)
        
    # Convert to Pacific time
    pacific_tz = pytz.timezone('US/Pacific')
    pacific_time = utc_now.astimezone(pacific_tz)
        
    # Format the time
    join_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S")
    return join_time

bot.run(bot_token)

# # either 5:55am pacific or 6:55am pacific in UTC standard time, depending on daylight savings time
# schedule.every().day.at("13:55").do(download)
# schedule.every().day.at("14:55").do(download)


# schedule.every().day.at("00:11").do(download)

# while True:
#     schedule.run_pending()
    # time.sleep(1)

# # Close the connection to the database

# bot.run(bot_token)

# # Close the connection to the database
# conn.close()
