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
from tabulate import tabulate
from discord import Embed

# Constants
db_file = 'dinksters_database.db'
text_channel = 'Larry\'s Gym Tracker'
current_text_channel = lambda member: discord.utils.get(member.guild.threads, name=text_channel)
voice_channel = 'Larry\'s Gym'
verbose = True

# Walking constants
global start_hour, end_hour

start_hour = 7
end_hour =  9
length_of_walk_in_minutes = 45
max_on_time_points = 50
max_duration_points = 50
walk_ended = False

# Load the .env file
load_dotenv()

# permissions = Permissions(0x00000400 | 0x00000800 | 0x00800000)
# Get the bot token
bot_token = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix='!', intents=intents)

def connect_to_database():
    global conn, c
    # Connect to the SQLite database
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS voice_log
                (name text, id text, time datetime, channel text, user_joined boolean)''')

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS points
                (name text, id text, points_awarded float, day datetime, type text)''')

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

connect_to_database()
download()

@bot.command()
async def start_time(ctx, start_time: int):
    global start_hour, end_hour
    start_hour = start_time
    end_hour = start_time + 2
    await ctx.send(f'Walk start time set to {start_hour}:00 Pacific time for today...')


@bot.command()
async def database(ctx, new_db_file: str):
    global db_file
    db_file = new_db_file
    await ctx.send(f'Database file set to {db_file}')
    connect_to_database()

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

def upload():
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

@bot.command()
async def end_walk(ctx):
    global walk_ended
    if not walk_ended:
        await ctx.send(f'Walk ended at {_get_current_time()}! Calculating points...')
        await update_points(ctx)
        walk_ended = True


@bot.command()
async def drop_points(ctx):
    c.execute("DROP TABLE points")
    conn.commit()
    upload()

@bot.command()
async def delete_all_points(ctx):
    c.execute("DELETE FROM points")
    conn.commit()
    upload()
    # await ctx.send(f'Dropped points table...')

async def update_points(ctx):
    # Groupby name and id, extract day from date and groupby day, subtract max and min time to get duration
    # Divide duration by walk duration to get points
    users_df = pd.read_sql_query("""
                            SELECT * 
                            FROM voice_log""", conn)
    print('users df at first:\n',users_df)
    users_df['time'] = users_df['time'].astype('datetime64[ns]')
    users_df['day'] = users_df['time'].dt.date
    current_day = users_df['day'].max()
    users_df = users_df.loc[users_df['day'] == current_day]
    print('users df after filtering:\n',users_df)
    users_durations = users_df.groupby(['id']).apply(lambda user: user['time'].max() - user['time'].min())
    calculate_points(users_df, users_durations)
    print(pd.read_sql_query("""SELECT * FROM points""", conn).tail())
    await leaderboard(ctx, 'WEEKLY')
    upload()

@bot.command()
async def download_db(ctx):
    download()
    # await ctx.send(f'Downloaded {db_file} from Google Drive!')

@bot.command()
async def upload_db(ctx):
    upload()
    # await ctx.send(f'Uploaded {db_file} to Google Drive!')

@bot.command()

async def leaderboard(ctx, *args):
    query = ' '.join(args)
    role = discord.utils.get(ctx.guild.roles, name='Walker')
    # Select all rows from the points table
    unit_of_time, time_filter = _process_query(query)
    
    points_column = f'{unit_of_time}' if unit_of_time else 'total'
    leaderboard_query = f"""SELECT name, SUM(points_awarded) as '{points_column}'
                                       FROM points 
                                       WHERE id IN ({','.join([f'"{member.id}"' for member in role.members])}) 
                                       {time_filter}
                                       GROUP BY id"""
    leaderboard_df = pd.read_sql_query(leaderboard_query, conn)
    print(leaderboard_df)
    if leaderboard_df.empty:
        # Find all users in the text_channel and output 0 for their points
        leaderboard_series = pd.Series(dict(zip([member.name for member in role.members], [0] * len(role.members))))
        leaderboard_series.name = points_column
        leaderboard_df = leaderboard_series.to_frame()
    leaderboard_df[points_column] = leaderboard_df[points_column].round(2) 
    # Convert the leaderboard to a table with borders
    leaderboard_table = tabulate(leaderboard_df.sort_values(by=points_column, ascending=False).reset_index(drop=True), 
                                 headers='keys', 
                                 showindex=False, 
                                 tablefmt='simple_grid')
    print(f'{unit_of_time.capitalize()} Leaderboard:\n',leaderboard_df)
    
    await ctx.send(f'```{leaderboard_table}```')    

def _process_query(query):
    query = query.strip().upper()
    if '' == query:
        return 'total', ''
    elif 'ON TIME' in query or 'DURATION' in query:
        return query, f"""AND type = "{query}" """
    elif 'TODAY' in query:
        return 'daily', f"""AND day = "{datetime.now().date()}" """
    elif 'WEEK' in query:
        last_monday = datetime.now().date() - timedelta(days=datetime.now().weekday())
        return 'weekly', f"""AND day >= "{last_monday}" """
    elif 'MONTH' in query:
        return 'monthly', f"""AND day >= "{datetime.now().date().replace(day=1)}" """
    elif 'YEAR' in query:
        return 'yearly', f"""AND day >= "{datetime.now().date().replace(month=1, day=1)}" """

def calculate_points(users_df, users_durations):
    print(users_durations)
    walk_time_in_seconds = timedelta(minutes=length_of_walk_in_minutes).total_seconds()
    duration_points = (users_durations.dt.total_seconds() / walk_time_in_seconds) * 50
    duration_points.loc[duration_points>max_duration_points] = max_duration_points
    late_time = (users_df.groupby('id').apply(lambda user: user['time'].min() - user['time'].min().replace(hour=start_hour, minute=0, second=0)))
    on_time_points = max_on_time_points - (late_time.dt.total_seconds() / (walk_time_in_seconds / 2)) * 50
    on_time_points.loc[on_time_points<0] = 0
    # print('User Durations:',users_durations)
    day = users_df['day'].max()
    users_df = users_df[['name', 'id', 'day']].drop_duplicates()
    process_points_df(users_df, on_time_points, 'ON TIME', day)
    process_points_df(users_df, duration_points, 'DURATION', day)    

def process_points_df(users_df, points_df, points_type, day):
    points_df.name = 'points_awarded'
    points_df = points_df.to_frame()
    points_df['type'] = points_type
    points_df['day'] = day
    print(f'{points_type} points df before merge: \n', points_df)
    points_df = points_df.merge(users_df[['name', 'id']], left_on='id', right_on='id', how='left').drop_duplicates()
    print(f'{points_type} points df after merge: \n', points_df)
    points_df = points_df[['name', 'id', 'points_awarded', 'day', 'type']]
    points_df.to_sql('points', conn, if_exists='append', index=False)
    return points_df

@bot.event
async def on_voice_state_update(member, before, after):
    global walk_ended
    current_time = _get_current_time()
    pacific_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
    walk_hour_condition = pacific_time.hour >= start_hour and pacific_time.hour < end_hour


    if walk_ended:
        points = pd.read_sql('SELECT day FROM points ORDER BY day DESC LIMIT 1', conn)
        current_day = str(pacific_time.date())
        walk_day = str(points.values[0][0])
        if current_day != walk_day and walk_hour_condition:
            walk_ended = False
            print('New walk starting')
            download()
        else:
            print('Walk already ended')
            return

    # Check if the time is between 7am and 9am in Pacific timezone
    if walk_hour_condition:
        if after.channel is not None and after.channel.name == voice_channel:
            # Get current time in UTC
            join_time = _get_current_time()
            append_to_database(member, after, join_time, joined=True)
            log_and_upload(member, join_time, True)

        if before.channel is not None and before.channel.name == voice_channel:
            leave_time = _get_current_time()
            
            append_to_database(member, before, leave_time, joined=False)
            log_and_upload(member, leave_time, False)

def log_and_upload(member, event_time, joining):
    if verbose:
        log_data(member, event_time, joining)
    upload()

def log_data(member, event_time, joining):
    leaving_str = "leaving " if not joining else ""
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
