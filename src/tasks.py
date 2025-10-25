import asyncio
import random
import re
import time
from datetime import timedelta
import datetime
from pathlib import Path

import discord
import pandas as pd
import pytz
from discord.ext import commands, tasks
from discord.utils import get

from src.openai import OpenAICog
from src.types import ROOT_PATH
from src.util import _get_current_time, play_audio, determine_winner, get_mp3_duration


class LarrysTasks(commands.Cog):

    def __init__(self, bot: 'LarrysBot'):
        self.bot = bot
        self.tz = pytz.timezone('US/Pacific')

    def _seconds_until_next_run(self, minute: int, hour_offset: int = 0, second: int = 0) -> float:
        """Calculate seconds until the next run based on the configured start time."""
        now = datetime.datetime.now(self.tz)
        start_hour_today = self.bot.walk_constants.get_start_hour(now) + hour_offset
        target = now.replace(hour=start_hour_today, minute=minute, second=second, microsecond=0)
        if now >= target:
            next_day = now + timedelta(days=1)
            start_hour_next = self.bot.walk_constants.get_start_hour(next_day) + hour_offset
            target = next_day.replace(hour=start_hour_next, minute=minute, second=second, microsecond=0)
        return (target - now).total_seconds()

    @tasks.loop(hours=24)
    async def determine_monthly_winner(self):
        _, pacific_time = _get_current_time()
        if pacific_time.day == 1:
            voice_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.VOICE_CHANNEL_ID)

            if voice_channel and len(voice_channel.members) >= 1:
                try:
                    voice_client = await voice_channel.connect()
                except discord.errors.ClientException:
                    print(
                        f'Already connected to a voice channel.')

                voice_client = self.bot.discord_client.voice_clients[0]
                leaderboard_query = """
                        SELECT name, SUM(points_awarded) AS total_points
                        FROM points
                        WHERE day >= date('now', '-1 month')
                        GROUP BY name
                        ORDER BY total_points DESC
                        LIMIT 1
                    """
                leaderboard_df = pd.read_sql_query(leaderboard_query, self.bot.database.connection)
                winner = leaderboard_df.iloc[0]
                if winner.empty:
                    print('No winner found')
                    await voice_channel.disconnect()
                    return
                # winner_args = winner_songs[winner['name']]
                text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
                previous_month  = pacific_time.month - 1
                previous_month_name = datetime.date(1900, previous_month, 1).strftime('%B')
                winner_message = f"Congrats to {winner['name']} for winning the month of {previous_month_name} with {round(winner['total_points'])} points!"
                await text_channel.send(
                    f"{winner_message}\nhttps://www.youtube.com/watch?v=veb4_RB01iQ&ab_channel=KB8")

                remote_speech_file_path = Path('data') / f"{previous_month_name}_winner_{pacific_time.year}.wav'"
                local_speech_file_path = ROOT_PATH / remote_speech_file_path
                OpenAICog.produce_tts_audio(self.bot.openai_client, winner_message, local_speech_file_path)
                await play_audio(voice_client, str(remote_speech_file_path), self.bot.backend_client, get_mp3_duration(local_speech_file_path), 0, False)
                await play_audio(voice_client, f'data/songs/first_of_the_month.mp3', self.bot.backend_client, 21, 41, True)

        # schedule next run for the monthly winner task
        next_interval = self._seconds_until_next_run(self.bot.walk_constants.WINNER_MINUTE - 2, second=50)
        self.determine_monthly_winner.change_interval(seconds=next_interval)

    @tasks.loop(hours=24)
    async def determine_daily_winner(self):
        voice_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.VOICE_CHANNEL_ID)

        if voice_channel and len(voice_channel.members) >= 1:
            try:
                voice_client = await voice_channel.connect()
            except discord.errors.ClientException as e:
                print(str(e))
                print(
                    f'Already connected to a voice channel.')

            voice_client = self.bot.discord_client.voice_clients[0]
            winner = await determine_winner(self.bot.database)
            if winner.empty:
                print('No winner found')
                await voice_channel.disconnect()
                return
            winner_args = self.bot.songs.WINNER[winner['name']]
            random_winner_args = random.choice(winner_args)
            _, pacific_time = _get_current_time()
            current_date = pacific_time.date()
            # TODO: get these values from the `birthday_args` dictionary
            try:
                current_birthday = self.bot.songs.BIRTHDAY[(current_date.month, current_date.day)]
                birthday_name, birthday_link = current_birthday
                duration = 73
                if birthday_name == 'ben':
                    duration = 49
                text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
                await text_channel.send(f'Happy Birthday {birthday_name.capitalize()}!\n{birthday_link}')
                await play_audio(voice_client, f'data/songs/happy_birthday_{birthday_name}.mp3',
                                 self.bot.backend_client, duration, 0, disconnect_after_played=False)

                time.sleep(2)
            except KeyError:
                pass
            await play_audio(voice_client, f'data/songs/{random_winner_args[0]}', self.bot.backend_client,
                             random_winner_args[1], random_winner_args[2])
        else:
            print('not enough people in the vc')

        # schedule next run based on current configuration
        next_interval = self._seconds_until_next_run(self.bot.walk_constants.WINNER_MINUTE)
        self.determine_daily_winner.change_interval(seconds=next_interval)

    @determine_daily_winner.before_loop
    async def before_determine_daily_winner(self):
        await self.bot.discord_client.wait_until_ready()
        wait_seconds = self._seconds_until_next_run(self.bot.walk_constants.WINNER_MINUTE)
        next_time = datetime.datetime.now(self.tz) + timedelta(seconds=wait_seconds)
        print('Waiting until', next_time)
        print(f'wait time: {wait_seconds}')
        await asyncio.sleep(wait_seconds)

    @determine_monthly_winner.before_loop
    async def before_determine_monthly_winner(self):
        wait_seconds = self._seconds_until_next_run(self.bot.walk_constants.WINNER_MINUTE - 2, second=50)
        next_time = datetime.datetime.now(self.tz) + timedelta(seconds=wait_seconds)
        print('Monthly winner determined at', next_time)
        print(f'wait time for monthly winner check: {wait_seconds}')
        await asyncio.sleep(wait_seconds)

    @tasks.loop(hours=24)  # Adjust the interval as needed
    async def check_freethrow_logs(self):
        channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        if not channel:
            return

        async for message in channel.history(limit=100):  # Adjust the limit as needed
            if message.content.startswith('!log_freethrows'):
                await self.process_freethrow_log(message)

    async def process_freethrow_log(self, message):
        pattern = r'!log_freethrows(?:\s+(\S+))?\s+(\d+)(?:\s+(\d+))?'
        match = re.match(pattern, message.content)

        if match:
            date_str, number_made, number_attempted = match.groups()

            # Parse date
            if date_str is None:
                date = message.created_at.astimezone(pytz.timezone('US/Pacific'))
            elif date_str.lower() == 'yesterday':
                date = message.created_at.astimezone(pytz.timezone('US/Pacific'))
                date = (date - timedelta(days=1)).replace(microsecond=0)
            else:
                try:
                    date = datetime.datetime.strptime(date_str, '%m/%d/%Y').replace(tzinfo=pytz.timezone('US/Pacific')).replace(microsecond=0)
                except ValueError:
                    print(f"Invalid date format: {date_str}")
                    await message.add_reaction('❌')
                    return

            number_made = int(number_made)
            number_attempted = int(number_attempted) if number_attempted else 25  # Default to 25 if not provided

            # Check if the freethrow has already been logged
            if self.bot.database.freethrow_exists(
                name=message.author.name,
                id=str(message.author.id),
                date=date.strftime('%Y-%m-%d %H:%M:%S')
            ):
                print(f"Freethrow already logged for {message.author.name} on {date.strftime('%Y-%m-%d')}")
                # await message.add_reaction('⚠️')  # React to indicate duplicate entry
                # await message.channel.send(f"{message.author.mention}, you've already logged a freethrow for this date.")
                return

            self.bot.database.log_free_throw(
                message_id=str(message.id),
                name=message.author.name,
                id=str(message.author.id),
                date=date.strftime('%Y-%m-%d %H:%M:%S'),
                number_made=number_made,
                number_attempted=number_attempted
            )
            # Remove the ❌ reaction if it exists
            try:
                await message.remove_reaction('❌', self.bot.discord_client.user)
            except discord.errors.HTTPException:
                pass  # Ignore if the reaction doesn't exist or can't be removed

            await message.add_reaction('✅')  # React to confirm logging
            print(f"Freethrow logged for {message.author.name} on {date.strftime('%Y-%m-%d')} with {number_made} made and {number_attempted} attempted.")
        else:
            await message.add_reaction('❌')  # React to indicate an error

    @tasks.loop(hours=24)
    async def initialize_new_users(self):
        """Check for and initialize any new users daily"""
        print("\n=== Starting initialize_new_users task ===")
        try:
            guild = self.bot.discord_client.get_guild(self.bot.bot_constants.GUILD_ID)
            if not guild:
                print(f"Could not find guild with ID: {self.bot.bot_constants.GUILD_ID}")
                return
            print(f"Found guild: {guild.name}")
                
            walkers = get(guild.roles, name='Walker')
            if not walkers:
                print("Could not find Walker role in guild")
                return
            print(f"Found Walker role with {len(walkers.members)} members")

            await self._initialize_new_walkers(walkers.members)
            
        except Exception as e:
            print(f"Error in initialize_new_users task: {e}")
            import traceback
            print(traceback.format_exc())
        finally:
            print("=== Finished initialize_new_users task ===\n")

    async def _initialize_new_walkers(self, walkers):
        """Initialize any walkers that don't exist in the database"""
        print("Starting _initialize_new_walkers")
        
        # Get existing users from database
        existing_users = self.bot.stock_exchange_database.get_all_user_ids()
        print(f"Found {len(existing_users)} existing users in database")
        print(f"Existing user IDs: {existing_users}")
        
        # Find new users
        new_users = [
            walker for walker in walkers 
            if str(walker.id) not in existing_users
        ]
        
        if not new_users:
            print("No new users found to initialize")
            return

        print(f"Found {len(new_users)} new users to initialize:")
        for user in new_users:
            print(f"  - {user.name} (ID: {user.id})")

        # Initialize each new user
        for user in new_users:
            try:
                self.bot.stock_exchange_database.initialize_user(
                    user_id=user.id,
                    name=user.name,
                    balance=0
                )
                print(f"Successfully initialized new user {user.name} (ID: {user.id}) in stock exchange database")
            except Exception as e:
                print(f"Error initializing user {user.name} (ID: {user.id}): {e}")
                import traceback
                print(traceback.format_exc())

        self.bot.stock_exchange_database.connection.commit()
        print("Committed all new user initializations to database")
