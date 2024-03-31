import asyncio
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Tuple

import discord
import pandas as pd
import pytz
from discord.ext import commands

# from cli.main import database as db
from src.types import BotConstants, WalkArgs
from src.commands import leaderboard


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
    walk_time_in_seconds = timedelta(minutes=WalkArgs.LENGTH_OF_WALK_IN_MINUTES).total_seconds()
    duration_points = (users_durations.dt.total_seconds() / walk_time_in_seconds) * 50
    duration_points.loc[duration_points > WalkArgs.MAX_DURATION_POINTS] = WalkArgs.MAX_DURATION_POINTS
    late_time = (users_df.groupby('id').apply(
        lambda user: user['time'].min() - user['time'].min().replace(hour=WalkArgs.START_HOUR, minute=0, second=0,
                                                                     microsecond=0)))
    on_time_points = WalkArgs.MAX_DURATION_POINTS - (late_time.dt.total_seconds()
                                                           / (walk_time_in_seconds / 2)) * 50
    on_time_points.loc[on_time_points < 0] = 0
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
    points_df.to_sql('points', db.connection, if_exists='append', index=False)
    return points_df


def log_and_upload(member, event_time, joining):
    if verbose:
        log_data(member, event_time, joining)
    upload()


def log_data(member, event_time, joining):
    leaving_str = "leaving " if not joining else ""
    print(f'Logged user {member.name} {leaving_str}at {event_time}...')
    print(pd.read_sql_query("SELECT * FROM voice_log", db.connection).tail())


def append_to_database(member, event, event_time, joined):
    db.cursor.execute("INSERT INTO voice_log VALUES (?, ?, ?, ?, ?)",
              (member.name, member.id, event_time, event.channel.name, joined))
    db.connection.commit()


def _get_current_time() -> Tuple[str, datetime]:
    utc_now = datetime.now(pytz.utc)

    # Convert to Pacific time
    pacific_tz = pytz.timezone('US/Pacific')
    pacific_time = utc_now.astimezone(pacific_tz)

    # Format the time
    join_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    print(pacific_time)
    return join_time, pacific_time


# def connect_to_database():
#     # Connect to the SQLite database
#     database = sqlite3.connect(bot_constants.DB_FILE)
#     c = conn.cursor()
#
#     # Create table if it doesn't exist
#     c.execute('''CREATE TABLE IF NOT EXISTS voice_log
#                 (name text, id text, time datetime, channel text, user_joined boolean)''')
#
#     # Create table if it doesn't exist
#     c.execute('''CREATE TABLE IF NOT EXISTS points
#                 (name text, id text, points_awarded float, day datetime, type text)''')



@commands.command()
async def copy_database(ctx, new_db_file: str):
    shutil.copyfile(BotConstants.DB_FILE, new_db_file)
    BotConstants.DB_FILE = new_db_file
    await ctx.send(f'Database file set to {BotConstants.DB_FILE}')
    # connect_to_database()
    upload()


async def determine_winner(db, *args):
    # Select all rows from the points table
    leaderboard_query = f"""SELECT name, MIN(time) as 'time'
                            FROM (
                                SELECT name, id, time
                                FROM voice_log
                                WHERE time >= "{datetime.now().date()}"
                            )  
                            GROUP BY id"""
    print(leaderboard_query)
    leaderboard_df = pd.read_sql_query(leaderboard_query, db.connection)
    print(leaderboard_df)
    leaderboard_df['time'] = leaderboard_df['time'].astype('datetime64[ns]')
    winner = leaderboard_df.sort_values(by='time', ascending=True).iloc[0]
    print(winner)
    return winner


async def play_song(voice_client, file_path: str, duration: int = 16, start_second: int = 15,
                    disconnect_after_song: bool = True):
    print(file_path)
    dropbox.download_file(file_path)
    voice_client.play(discord.FFmpegPCMAudio(file_path, options=f'-ss {start_second}'))
    await asyncio.sleep(duration)
    voice_client.stop()
    if disconnect_after_song:
        await voice_client.disconnect()


def upload():
    dropbox.upload_file(bot_constants.DB_FILE)


async def update_points(ctx, current_time):
    # Groupby name and id, extract day from date and groupby day, subtract max and min time to get duration
    # Divide duration by walk duration to get points
    voice_log_df = pd.read_sql_query("""
                            SELECT * 
                            FROM voice_log""", db.connection)
    voice_log_df['time'] = voice_log_df['time'].astype('datetime64[ns]')
    voice_log_df['day'] = voice_log_df['time'].dt.date
    current_day = datetime.now(pytz.timezone('US/Pacific')).date()
    latest_voice_log_day = voice_log_df['day'].max()
    if current_day != latest_voice_log_day or args.test:
        await ctx.send(f'No one has joined the walk today. Bad !end_walk command registered. 500 social credit will '
                       f'be deducted from `{ctx.author.name}`.')
        return
    await ctx.send(f'Walk ended at {current_time}! Getting weekly leaderboard...')

    daily_voice_log_df = voice_log_df.loc[voice_log_df['day'] == current_day]
    users_durations = daily_voice_log_df.groupby(['id']).apply(lambda user: user['time'].max() - user['time'].min())
    calculate_points(daily_voice_log_df, users_durations)
    print(pd.read_sql_query("""SELECT * FROM points""", db.connection).tail())
    await leaderboard(ctx, 'WEEKLY')
    await ctx.send('Getting Today\'s On Time Leaderboard')
    await leaderboard(ctx, 'on time today')
    upload()


def download(backend_client):
    print(BotConstants.DB_FILE)
    backend_client.download_file(BotConstants.DB_FILE)