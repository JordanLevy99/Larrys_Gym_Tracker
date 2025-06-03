import asyncio
from datetime import datetime, timedelta
from typing import Tuple

import discord
import pandas as pd
import pytz
from mutagen.mp3 import MP3

from src.types import BotConstants, WalkArgs


def _process_query(query, type_filter=''):
    query = query.strip().upper()
    timezone = pytz.timezone('US/Pacific')
    if query == '':
        current_month = datetime.now(tz=timezone).month
        start_month = ((current_month - 1) // 3) * 3 + 1
        return 'season', f"""WHERE strftime('%m', day) >= "{start_month:02}" """, type_filter
    elif query == 'SLEEP':
        return 'sleep', '', ''  # Add this line to handle the 'sleep' query
    elif 'ON TIME' in query:
        return _process_query(query.replace('ON TIME', ''), type_filter="""WHERE type = "ON TIME" """)
    elif 'DURATION' in query:
        return _process_query(query.replace('DURATION', ''), type_filter="""WHERE type = "DURATION" """)
    elif 'EXERCISE' in query:
        return _process_query(query.replace('EXERCISE', ''), type_filter="""WHERE type = "EXERCISE" """)
    elif 'TODAY' in query:
        return 'daily', f"""WHERE day = "{datetime.now(tz=timezone).date()}" """, type_filter
    elif 'WEEK' in query:
        last_monday = datetime.now(tz=timezone).date() - timedelta(days=datetime.now(tz=timezone).weekday())
        return 'weekly', f"""WHERE day >= "{last_monday}" """, type_filter
    elif 'MONTH' in query:
        return 'monthly', f"""WHERE day >= "{datetime.now(tz=timezone).date().replace(day=1)}" """, type_filter
    elif 'YEAR' in query:
        return 'yearly', f"""WHERE day >= "{datetime.now(tz=timezone).date().replace(month=1, day=1)}" """, type_filter
    elif 'ALL' in query:
        return 'all', '', type_filter
    else:
        return 'all', '', type_filter  # Default case to handle unexpected queries


def calculate_points(database, users_df, users_durations, length_of_walk_in_minutes, max_duration_points, start_hour, stock_db=None):
    # TODO: move this function to a class that contains our walk constants
    print(users_durations)
    walk_time_in_seconds = timedelta(minutes=length_of_walk_in_minutes).total_seconds()
    duration_points = (users_durations.dt.total_seconds() / walk_time_in_seconds) * 50
    duration_points.loc[duration_points > max_duration_points] = max_duration_points
    late_time = (users_df.groupby('id').apply(
        lambda user: user['time'].min() - user['time'].min().replace(hour=start_hour, minute=0, second=0,
                                                                     microsecond=0)))
    on_time_points = WalkArgs.MAX_ON_TIME_POINTS - (late_time.dt.total_seconds()
                                                     / (walk_time_in_seconds / 2)) * 50
    on_time_points.loc[on_time_points < 0] = 0
    # print('User Durations:',users_durations)
    day = users_df['day'].max()
    users_df = users_df[['name', 'id', 'day']].drop_duplicates()
    on_time_points = process_points_df(database, users_df, on_time_points, 'ON TIME', day)
    duration_points = process_points_df(database, users_df, duration_points, 'DURATION', day)
    try:
        for idx, user in on_time_points.iterrows():
            _update_stock_balance(stock_db, user)
        for idx, user in duration_points.iterrows():
            _update_stock_balance(stock_db, user)
        stock_db.connection.commit()
    except Exception as e:
        print('Error updating stock balance:', e)

def get_mp3_duration(file_path):
        audio = MP3(file_path)
        return audio.info.length


def _update_stock_balance(stock_db, user):
    current_balance = stock_db.get_user_balance(user['id'])
    print(f'Current balance for {user["name"]}: {current_balance}')
    current_balance += user['points_awarded']
    stock_db.update_user_balance(user['id'], current_balance)


def process_points_df(database, users_df, points_df, points_type, day):
    points_df.name = 'points_awarded'
    points_df = points_df.to_frame()
    points_df['type'] = points_type
    points_df['day'] = day
    print(f'{points_type} points df before merge: \n', points_df)
    points_df = points_df.merge(users_df[['name', 'id']], left_on='id', right_on='id', how='left').drop_duplicates()
    print(f'{points_type} points df after merge: \n', points_df)
    points_df = points_df[['name', 'id', 'points_awarded', 'day', 'type']]
    points_df.to_sql('points', database.connection, if_exists='append', index=False)
    return points_df


def log_data(database, member, event_time, joining):
    leaving_str = "leaving " if not joining else ""
    print(f'Logged user {member.name} {leaving_str}at {event_time}...')
    print(pd.read_sql_query("SELECT * FROM voice_log", database.connection).tail())


def append_to_database(database, member, event, event_time, joined):
    database.cursor.execute("INSERT INTO voice_log VALUES (?, ?, ?, ?, ?)",
                            (member.name, member.id, event_time, event.channel.name, joined))
    database.connection.commit()


def append_mute_event(database, member, event_time, channel_name, muted):
    database.cursor.execute(
        "INSERT INTO mute_log VALUES (?, ?, ?, ?, ?)",
        (member.name, member.id, event_time, channel_name, muted)
    )
    database.connection.commit()


def _get_current_time() -> Tuple[str, datetime]:
    utc_now = datetime.now(pytz.utc)

    # Convert to Pacific time
    pacific_tz = pytz.timezone('US/Pacific')
    pacific_time = utc_now.astimezone(pacific_tz)

    # Format the time
    join_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    print(pacific_time)
    return join_time, pacific_time


async def determine_winner(db, *args):
    # Select all rows from the points table
    leaderboard_query = f"""SELECT name, MIN(time) as 'time'
                            FROM (
                                SELECT name, id, time
                                FROM voice_log
                                WHERE time >= "{datetime.now(tz=pytz.timezone('US/Pacific')).date()}"
                            )  
                            GROUP BY id"""
    print(leaderboard_query)
    leaderboard_df = pd.read_sql_query(leaderboard_query, db.connection)
    print(leaderboard_df)
    leaderboard_df['time'] = leaderboard_df['time'].astype('datetime64[ns]')
    winner = leaderboard_df.sort_values(by='time', ascending=True).iloc[0]
    print(winner)
    return winner


async def play_audio(voice_client, file_path: str, backend_client, duration: int = 16, start_second: int = 15,
                     disconnect_after_played: bool = True, download=True):
    print(file_path)
    if download:
        backend_client.download_file(file_path)
    voice_client.play(discord.FFmpegPCMAudio(file_path, options=f'-ss {start_second}'))
    await asyncio.sleep(duration)
    voice_client.stop()
    if disconnect_after_played:
        await voice_client.disconnect()


def upload(backend_client, db_file: str = BotConstants.DB_FILE):
    backend_client.upload_file(db_file)


def download(backend_client, db_file: str = BotConstants.DB_FILE):
    print(f'Downloading {db_file}...')
    backend_client.download_file(db_file)
