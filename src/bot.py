from datetime import datetime
import os
from pathlib import Path
import time
from typing import Tuple
from dotenv import load_dotenv
import pandas as pd
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pytz
import pandas as pd
from discord import Permissions
from datetime import timedelta
from tabulate import tabulate
from discord import Embed
from discord.ext import tasks, commands
import discord
import sqlite3


from backend import Dropbox
import shutil
import asyncio
import random
# Constants
db_file = 'larrys_database.db'
# db_file = 'test.db'
text_channel = 'larrys-gym-logger'
text_channel_id = 1193971930794045544
voice_channel_id = 1143972564616626209
### TODO: uncomment below two lines to test on test server ###
# text_channel_id = 1193977937955913879
# voice_channel_id = 1191159993861414922
current_text_channel = lambda member: discord.utils.get(member.guild.threads, name=text_channel)
voice_channel = 'Larry\'s Gym'
verbose = True

# Walking constants
# global start_hour, end_hour

start_hour = 7
end_hour = 9
length_of_walk_in_minutes = 45
max_on_time_points = 50
max_duration_points = 50
walk_ended = False

winner_hour = start_hour
winner_minute = 8

# TODO: integrate birthday_args into determine_daily_winner
birthday_args = {
    # (month, day): (name, link)
    (1, 19): ('james', 'https://www.youtube.com/watch?v=jcZRsApNZwk'),
    (9, 27): ('jordan', 'https://www.youtube.com/watch?v=E8Jx5jOXM9Y'),
    (4, 5): ('kyle', 'https://www.youtube.com/watch?v=bujfHuKO-Vc'),
    (1, 21): ('ben', 'https://www.youtube.com/watch?v=t5r1qIY0g2g'),
    (4, 12): ('peter', 'https://www.youtube.com/watch?v=SsoIMucoHa4'),
    (1, 27): ('mikal', 'https://www.youtube.com/watch?v=Hz8-5D2dmus'),
}


winner_songs = {
    # Provides the song name, duration, and start second
    'jam4bears': [('rocky_balboa.mp3', 15, 0),
                  ('walk_it_talk_it.mp3', 45, 40)],
    'bemno': [('wanna_be_free.mp3', 40, 0)],
    'dinkstar': [('chug_jug_with_you.mp3', 16, 1),
                 ('jesus_forgive_me_i_am_a_thot.mp3', 23, 122),
                 ('thot_tactics.mp3', 17, 109),
                 ('jump_out_the_house.mp3', 12, 7)],
    'Larry\'s Gym Bot': [('larrys_song.mp3', 26, 0)],
    'kyboydigital': [('shenanigans.mp3', 15, 13)],
    'shmeg.': [('chum_drum_bedrum.mp3', 67, 26),
               ('whats_new_scooby_doo.mp3', 64, 0),
               ('tnt_dynamite.mp3', 64, 18),
               ('HEYYEYAAEYAAAEYAEYAA.mp3', 84, 0),
               ('hyrule_field.mp3', 50, 175),
               ('tunak_tunak.mp3', 76, 26),
               ('vinland_saga.mp3', 75, 14),
               ('german_soldiers_song.mp3', 37, 0),
               ('BED_INTRUDER_SONG.mp3', 76, 0),
               ('Medal_Of_Honor_European_Assault.mp3', 75, 77),
               ('Klendathu_Drop.mp3', 80, 0),
               ('The_Black_Pearl.mp3', 64, 30),
               ('Rohan_and_Gondor_Themes.mp3', 62, 222),
               ('The_Ecstasy_of_Gold.mp3', 107, 0),
               ('Fergie_sings_the_national_anthem.mp3', 62, 77)],
    'shamupete': [('Bloopin.mp3', 81, 0),
                  ('chocolate_rain.mp3', 60, 0)]
}
# Load the .env file
load_dotenv()

# permissions = Permissions(0x00000400 | 0x00000800 | 0x00800000)
# Get the bot token
bot_token = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

dropbox = Dropbox()


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
    global conn, c
    print(db_file)
    dropbox.download_file(db_file)

    # Read the file into a pandas DataFrame
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    df = pd.read_sql_query("SELECT * FROM voice_log", conn)

    # Print the last five entries of the DataFrame
    print(df.tail())
    df.to_sql(db_file, conn, if_exists='replace', index=False)

connect_to_database()
download()

@bot.command()
async def start_time(ctx, start_time: int):
    global start_hour, end_hour, winner_hour
    start_hour = start_time
    winner_hour = start_time
    end_hour = start_time + 2
    await ctx.send(f'Walk start time set to {start_hour}:00 Pacific time for today...')


@bot.command()
async def copy_database(ctx, new_db_file: str):
    global db_file
    shutil.copyfile(db_file, new_db_file)
    db_file = new_db_file
    await ctx.send(f'Database file set to {db_file}')
    connect_to_database()
    upload()


@tasks.loop(hours=24)
async def determine_daily_winner():
    voice_channel = bot.get_channel(voice_channel_id)

    if voice_channel and len(voice_channel.members) >= 1:
        try:
            voice_client = await voice_channel.connect()
        except discord.errors.ClientException:
            print(
                f'Already connected to a voice channel.')
        
        voice_client = bot.voice_clients[0]
        winner = await determine_winner()
        if winner.empty:
            print('No winner found')
            await voice_channel.connect()
            return
        winner_args = winner_songs[winner['name']]
        random_winner_args = random.choice(winner_args)
        _, pacific_time = _get_current_time()
        current_date = pacific_time.date()
        # TODO: get these values from the `birthday_args` dictionary
        try:
            current_birthday = birthday_args[(current_date.month, current_date.day)]
            birthday_name, birthday_link = current_birthday
            duration = 73
            if birthday_name == 'ben':
                duration = 49
            text_channel = bot.get_channel(text_channel_id)
            await text_channel.send(f'Happy Birthday {birthday_name.capitalize()}!\n{birthday_link}')
            await play_song(voice_client, f'data/songs/happy_birthday_{birthday_name}.mp3',
                            duration, 0, disconnect_after_song=False)
            
            time.sleep(2)
        except KeyError:
            pass
        await play_song(voice_client, f'data/songs/{random_winner_args[0]}', random_winner_args[1], random_winner_args[2])
    else:
        print('not enough people in the vc')


@bot.command()
async def determine_daily_winner_backup(ctx):
    await determine_daily_winner()


@bot.command()
async def disconnect(ctx):
    voice_client = bot.voice_clients[0]
    await voice_client.disconnect(force=True)


async def determine_winner(*args):
    # Select all rows from the points table
    leaderboard_query = f"""SELECT name, MIN(time) as 'time'
                            FROM (
                                SELECT name, id, time
                                FROM voice_log
                                WHERE time >= "{datetime.now().date()}"
                            )  
                            GROUP BY id"""
    print(leaderboard_query)
    leaderboard_df = pd.read_sql_query(leaderboard_query, conn)
    print(leaderboard_df)
    leaderboard_df['time'] = leaderboard_df['time'].astype('datetime64[ns]')
    winner = leaderboard_df.sort_values(by='time', ascending=True).iloc[0]
    print(winner)
    return winner


async def play_song(voice_client, file_path: str, duration: int = 16, start_second: int = 15, disconnect_after_song: bool = True):
    print(file_path)
    dropbox.download_file(file_path)
    voice_client.play(discord.FFmpegPCMAudio(file_path,  options=f'-ss {start_second}'))
    await asyncio.sleep(duration)
    voice_client.stop()
    if disconnect_after_song:
        await voice_client.disconnect()


@determine_daily_winner.before_loop
async def before_determine_daily_winner():
    now = datetime.now()
    now = now.astimezone(pytz.timezone('US/Pacific'))
    target_time = datetime.replace(now, hour=winner_hour, minute=winner_minute, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)
    print('Waiting until', target_time)
    print(f'wait time: {(target_time - now).total_seconds()}')
    await asyncio.sleep((target_time - now).total_seconds())


@bot.command()
async def get_id(ctx):
    # await ctx.send(
    channel = discord.utils.get(ctx.guild.channels, name=text_channel)
    channel_id = channel.id
    print(f'The channel id for {text_channel} is {channel_id}')
    channel = discord.utils.get(ctx.guild.channels, name=voice_channel)
    channel_id = channel.id
    print(f'The channel id for {voice_channel} is {channel_id}')

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    determine_daily_winner.start()

def upload():
    dropbox.upload_file(db_file)


@bot.command()
async def end_walk(ctx):
    global walk_ended
    if not walk_ended:
        current_time, _ = _get_current_time()
        await ctx.send(f'Walk ended at {current_time}! Getting weekly leaderboard...')
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
    await ctx.send('Getting Today\'s On Time Leaderboard')
    await leaderboard(ctx, 'on time today')
    upload()






@bot.command()
async def download_db(ctx):
    download()
    # await ctx.send(f'Downloaded {db_file} from Google Drive!')

@bot.command()
async def upload_db(ctx):
    upload()
    print(f'Uploaded {db_file} to Dropbox!')
    # await ctx.send(f'Uploaded {db_file} to Google Drive!')



@bot.command()
async def leaderboard(ctx, *args):
    query = ' '.join(args)
    role = discord.utils.get(ctx.guild.roles, name='Walker')
    # Select all rows from the points table
    points_column, time_filter, type_filter = _process_query(query)
    
    points_column = f'{points_column}' if points_column else 'total'
    print(points_column, time_filter, type_filter)
    leaderboard_query = f"""SELECT name, SUM(points_awarded) as '{points_column}'
                            FROM (
                                SELECT name, id, points_awarded, day, type
                                FROM points
                                {type_filter}
                            )  
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
    print(f'{points_column.capitalize()} Leaderboard:\n',leaderboard_df)
    
    await ctx.send(f'```{leaderboard_table}```')    

def _process_query(query, type_filter=''):
    query = query.strip().upper()
    print(query)
    if '' == query:
        return 'total', '', type_filter
    elif 'ON TIME' in query:
        return _process_query(query.replace('ON TIME', ''), type_filter="""WHERE type = "ON TIME" """)
    elif 'DURATION' in query:
        return _process_query(query.replace('DURATION', ''), type_filter="""WHERE type = "DURATION" """)
    elif 'TODAY' in query:
        return 'daily', f"""WHERE day = "{datetime.now().date()}" """, type_filter
    elif 'WEEK' in query:
        last_monday = datetime.now().date() - timedelta(days=datetime.now().weekday())
        return 'weekly', f"""WHERE day >= "{last_monday}" """, type_filter
    elif 'MONTH' in query:
        return 'monthly', f"""WHERE day >= "{datetime.now().date().replace(day=1)}" """, type_filter
    elif 'YEAR' in query:
        return 'yearly', f"""WHERE day >= "{datetime.now().date().replace(month=1, day=1)}" """, type_filter

def calculate_points(users_df, users_durations):
    print(users_durations)
    walk_time_in_seconds = timedelta(minutes=length_of_walk_in_minutes).total_seconds()
    duration_points = (users_durations.dt.total_seconds() / walk_time_in_seconds) * 50
    duration_points.loc[duration_points>max_duration_points] = max_duration_points
    late_time = (users_df.groupby('id').apply(lambda user: user['time'].min() - user['time'].min().replace(hour=start_hour, minute=0, second=0, microsecond=0)))
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
    global walk_ended, length_of_walk_in_minutes, max_on_time_points, max_duration_points, start_hour, end_hour

    # if member.voice is not None and member.voice.self_mute:
    #     print(f'{member.name} is muted')
    #     return
    current_time, pacific_time = _get_current_time()
    # pacific_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S.%f")
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
            join_time, _ = _get_current_time()
            append_to_database(member, after, join_time, joined=True)
            log_and_upload(member, join_time, True)
            await member.send(f"Welcome to The Walk™. You joined Larry\'s Gym within the proper time frame.")
            # join_time = datetime.strptime(join_time, "%Y-%m-%d %H:%M:%S.%f")
            # late_time =  (join_time - join_time.replace(hour=start_hour, minute=0, second=0, microsecond=0))
            # walk_time_in_seconds = timedelta(minutes=length_of_walk_in_minutes).total_seconds()
            # calculated_points = max(max_on_time_points - (late_time.total_seconds() / (walk_time_in_seconds / 2)) * 50, 0)
            # await member.send(f"You will earn {calculated_points} points. {'Congrats!' if calculated_points > 49 else 'Better luck next time!'}")
        if before.channel is not None and before.channel.name == voice_channel:
            leave_time, _ = _get_current_time()
            
            append_to_database(member, before, leave_time, joined=False)
            log_and_upload(member, leave_time, False)
    elif after.channel is not None and after.channel.name == voice_channel:
        await member.send(f"Sorry buckaroo, you joined Larry\'s Gym at {current_time}. The Walk™ is only between {start_hour}:00 and {end_hour}:00 Pacific time.")

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

def _get_current_time() -> Tuple[str, datetime]:
    utc_now = datetime.now(pytz.utc)
        
    # Convert to Pacific time
    pacific_tz = pytz.timezone('US/Pacific')
    pacific_time = utc_now.astimezone(pacific_tz)
        
    # Format the time
    join_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    print(pacific_time)
    return join_time, pacific_time

bot.run(bot_token)
