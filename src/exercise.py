import asyncio
import datetime
from pathlib import Path
import re
from datetime import timedelta

import discord
import numpy as np
import pytz
from discord.ext import commands, tasks

from src.openai import OpenAICog
from src.types import ROOT_PATH
from src.util import play_audio, get_mp3_duration, upload


class ExerciseOfTheDayResponseParser:
    """
    Parses the formatted response for exercise of the day into the following fields:
    - Exercise
    - Sets
    - Reps
    - Duration
    - Points
    """

    def __init__(self, response):
        self.response = response
        self.exercise_map = {
            'exercise': '',
            'sets': '',
            'reps': '',
            'duration': '',
            'difficulty': '',
            'points': ''
        }

    def parse(self):
        response = self.response.split('\n')
        response = response[1:]
        for line in response:
            line = line.split(':')
            key = line[0].strip().lower()
            value = line[1].strip().strip('**').replace('N/A', '')
            self.exercise_map[key] = value
        return self.exercise_map


class ExerciseCog(commands.Cog):
    FULL_RESPONSE_SYSTEM_MESSAGE = (
        "You are an assistant that is designed to motivate people who are on their morning walk"
        " to do the exercise of the day. Announce the exercise, reps and/or duration, and the "
        "number of points awarded from the user message in a motivational, "
        "competitive, concise manner with some flair. Give a brief explanation on how to do the exercise at the end.")

    FORMATTED_RESPONSE_SYSTEM_MESSAGE = ('Given a difficulty ranging from easy to extreme '
                                         '(with medium and hard in between), points awarded, '
                                         'and recent previous exercises from that difficulty,'
                                         ' you will create a unique exercise '
                                         'that can be completed in one\'s home/apartment in 5-20 minutes '
                                         '(depending on the difficulty), is different from the previous '
                                         'exercises, and formatted in the following way with no extra text:'
                                         '"Exercise: **{name_of_exercise}**\n'
                                         '\tSets: **{number_of_sets}**\n'
                                         '\tReps: **{number_of_reps}**\n'
                                         '\tDuration: **{duration_per_set_or_total_duration_in_minutes_or_seconds}**\n'
                                         '\tDifficulty: **{difficulty}**\n'
                                         '\tPoints: **{points_awarded}**" '
                                         'If any of this information is not needed for this exercise, output N/A for that field.')

    NUM_EXERCISES = 5
    DIFFICULTY_PROBABILITIES = [0.3, 0.5, 0.18, 0.02]

    difficulty_points_map = {
        'Easy': 10,
        'Medium': 25,
        'Hard': 50,
        'Extreme': 100
    }

    def __init__(self, bot):
        self.bot = bot
        self.exercise_map = {}
        self.remote_speech_file_path = Path('data') / "exercise_of_the_day.mp3"
        self.local_speech_file_path = ROOT_PATH / self.remote_speech_file_path
        self.tz = pytz.timezone('US/Pacific')

    def _seconds_until_next_run(self, minute: int, hour_offset: int = 0, second: int = 0) -> float:
        now = datetime.datetime.now(self.tz)
        start_hour_today = self.bot.walk_constants.get_start_hour(now) + hour_offset
        target = now.replace(hour=start_hour_today, minute=minute, second=second, microsecond=0)
        if now >= target:
            next_day = now + datetime.timedelta(days=1)
            start_hour_next = self.bot.walk_constants.get_start_hour(next_day) + hour_offset
            target = next_day.replace(hour=start_hour_next, minute=minute, second=second, microsecond=0)
        return (target - now).total_seconds()

    @tasks.loop(hours=24)
    async def exercise_of_the_day(self):
        # Generate exercise content
        full_response, tldr_response = self.__get_exercise('text')
        
        # Send to users who have exercise enabled
        enabled_users = self.bot.database.get_all_users_with_preference('exercise_enabled', True)
        for user_id in enabled_users:
            try:
                user = await self.bot.discord_client.fetch_user(int(user_id))
                await user.send(full_response)
                await user.send('\n\n' + tldr_response)
            except Exception as e:
                print(f"Failed to send exercise to user {user_id}: {e}")

        response_parser = ExerciseOfTheDayResponseParser(tldr_response)
        self.exercise_map = response_parser.parse()
        self.bot.database.cursor.execute(f"INSERT INTO exercise_of_the_day "
                                         f"(exercise, date, sets, reps, duration, difficulty, "
                                         f"points, full_response, tldr_response) "
                                         f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                         (self.exercise_map['exercise'],
                                          datetime.datetime.now(tz=pytz.timezone('US/Pacific')).date(),
                                          self.exercise_map['sets'], self.exercise_map['reps'],
                                          self.exercise_map['duration'], self.exercise_map['difficulty'],
                                          self.exercise_map['points'], full_response, tldr_response))
        self.bot.database.connection.commit()
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

        # schedule next run based on current configuration
        next_interval = self._seconds_until_next_run(44, second=50)
        self.exercise_of_the_day.change_interval(seconds=next_interval)

    async def __get_voice_client_and_text_channel(self, voice_channel):
        try:
            voice_client = await voice_channel.connect()
        except discord.errors.ClientException as e:
            print(str(e))
            print(
                f'Already connected to a voice channel.')
        voice_client = self.bot.discord_client.voice_clients[0]
        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        return text_channel, voice_client

    async def __send_responses_to_text_channel(self, full_response, tldr_response):
        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        await text_channel.send(full_response)
        await text_channel.send('\n\n' + tldr_response)

    @commands.command()
    async def exercise(self, ctx, *args):
        args = ' '.join(args)
        
        # Check if user wants to toggle exercise notifications
        if 'toggle' in args or not args:
            user_id = str(ctx.author.id)
            new_value = self.bot.database.toggle_user_preference(user_id, 'exercise_enabled')
            status = "enabled" if new_value else "disabled"
            await ctx.send(f"Exercise notifications have been {status}. You will {'now receive' if new_value else 'no longer receive'} daily exercise updates via DM.")
            return
        
        # Generate and send exercise
        full_response, tldr_response = self.__get_exercise(args)
        if 'send' in args:
            await ctx.send(full_response)
            await ctx.send('\n\n' + tldr_response)
        return full_response, tldr_response

    def __get_exercise(self, args=''):
        difficulty = np.random.choice(list(self.difficulty_points_map.keys()),
                                      p=self.DIFFICULTY_PROBABILITIES)
        previous_exercises = self.__get_previous_exercises(difficulty)
        points = self.difficulty_points_map[difficulty]
        user_message = f"Previous exercises in this difficulty: {previous_exercises}\nDifficulty: {difficulty}\nPoints Awarded: {points}"
        print(user_message)
        tldr_response = OpenAICog.create_chat(self.bot.openai_client, user_message,
                                              system_message=self.FORMATTED_RESPONSE_SYSTEM_MESSAGE)
        full_response = OpenAICog.create_chat(self.bot.openai_client, tldr_response,
                                              system_message=self.FULL_RESPONSE_SYSTEM_MESSAGE)
        print(full_response)
        if 'text' not in args.strip().lower():
            OpenAICog.produce_tts_audio(self.bot.openai_client, full_response, self.local_speech_file_path)
        tldr_response = 'tldr:\n\t' + tldr_response
        print(tldr_response)
        return full_response, tldr_response

    def __get_previous_exercises(self, difficulty):
        try:
            previous_exercises = list(self.bot.database.cursor.execute(f"""
                                SELECT exercise FROM exercise_of_the_day 
                                WHERE difficulty = '{difficulty}'
                                ORDER BY date DESC 
                                LIMIT {self.NUM_EXERCISES}""").fetchall())
            previous_exercises = [exercise[0] for exercise in previous_exercises]
        except TypeError:
            previous_exercises = None
        if previous_exercises is None:
            previous_exercises = ['N/A']
        return ', '.join(previous_exercises)

    @exercise_of_the_day.before_loop
    async def before_exercise_of_the_day(self):
        await self.bot.discord_client.wait_until_ready()
        wait_seconds = self._seconds_until_next_run(44, second=50)
        next_time = datetime.datetime.now(self.tz) + datetime.timedelta(seconds=wait_seconds)
        print('for exercise of the day, we wait until', next_time)
        print(f'exercise of the day wait time: {wait_seconds}')
        await asyncio.sleep(wait_seconds)

    @commands.command()
    async def log_exercise(self, ctx):
        if self.__exercise_is_already_logged(ctx):
            await ctx.send('You already logged your exercise for today.')
            return

        current_time = datetime.datetime.now(tz=pytz.timezone('US/Pacific'))
        current_date = current_time.date()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        try:
            # Start transaction
            # self.bot.database.connection.begin()
            
            # Get exercise and points
            daily_exercise = self.bot.database.cursor.execute(
                "SELECT exercise FROM exercise_of_the_day WHERE date = ?",
                (current_date,)
            ).fetchone()
            
            if not daily_exercise:
                raise ValueError("No exercise found for today")
                
            daily_exercise = daily_exercise[0]
            
            exercise_points = self.bot.database.cursor.execute(
                "SELECT points FROM exercise_of_the_day WHERE date = ?",
                (current_date,)
            ).fetchone()
            
            if not exercise_points:
                raise ValueError("No points found for today's exercise")
                
            exercise_points = exercise_points[0]

            # Log exercise
            self.bot.database.cursor.execute(
                "INSERT INTO exercise_log (name, id, exercise, time) VALUES (?, ?, ?, ?)",
                (ctx.author.name, ctx.author.id, daily_exercise, current_time_str)
            )
            
            # Update points
            self.__update_points(ctx, current_date, exercise_points)
            
            # Update stock balance
            self.__update_stock_balance(ctx, exercise_points)
            
            # Commit all changes
            self.bot.database.connection.commit()
            
            await ctx.send(
                f'{ctx.author.name} has logged their exercise for today: '
                f'**{daily_exercise}** at **{current_time_str}** for **{int(exercise_points)}** points!'
            )
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
            
        except Exception as e:
            # Rollback on any error
            self.bot.database.connection.rollback()
            print(f"Error in log_exercise: {str(e)}")
            await ctx.send('There was an error logging your exercise. Contact @dinkster for help.')

    def __update_points(self, ctx, current_date, exercise_points):
        self.bot.database.cursor.execute(f"""INSERT INTO points (name, id, points_awarded, day, type)
                                                    VALUES (?, ?, ?, ?, ?)""",
                                         (ctx.author.name, ctx.author.id,
                                          int(exercise_points), current_date, 'EXERCISE'))
        self.bot.database.connection.commit()

    def __update_stock_balance(self, ctx, exercise_points):
        current_balance = self.bot.stock_exchange_database.get_user_balance(ctx.author.id)
        current_balance += int(exercise_points)
        self.bot.stock_exchange_database.update_user_balance(ctx.author.id, current_balance)
        # Note: We don't commit here as it's part of the main transaction

    def __exercise_is_already_logged(self, ctx):
        current_time = datetime.datetime.now(tz=pytz.timezone('US/Pacific'))
        current_date = current_time.date()
        return self.bot.database.cursor.execute(
            """SELECT name, id, exercise, date FROM 
               (SELECT name, id, exercise, DATE(time) as date FROM exercise_log)
               WHERE date = ? AND id = ?""",
            (current_date, ctx.author.id)
        ).fetchone()

    @commands.command()
    async def log_freethrows(self, ctx, *args):
        """Log freethrows in the database. Usage: !log_freethrows [date] <made> [attempted]"""
        message_content = f"!log_freethrows {' '.join(args)}"
        message = ctx.message
        message.content = message_content  # Temporarily modify the message content
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
                    date = datetime.datetime.strptime(date_str, '%m/%d/%Y').date().replace(microsecond=0)
                except ValueError:
                    await message.add_reaction('❌')
                    await message.channel.send(f"Invalid date format. Use DD/MM/YYYY or 'yesterday'.")
                    return

            number_made = int(number_made)
            number_attempted = int(number_attempted) if number_attempted else 25  # Default to 25 if not provided
            
            # Check if the freethrow has already been logged
            if self.bot.database.freethrow_exists(
                name=message.author.name,
                id=str(message.author.id),
                date=date.strftime('%Y-%m-%d')
            ):
                await message.add_reaction('⚠️')  # React to indicate duplicate entry
                await message.channel.send(f"{message.author.mention}, you've already logged a freethrow for this date.")
                return
            
            self.bot.database.log_free_throw(
                message_id=str(message.id),
                name=message.author.name,
                id=str(message.author.id),
                date=date.strftime('%Y-%m-%d %H:%M:%S'),
                number_made=number_made,
                number_attempted=number_attempted
            )
            
            await message.add_reaction('✅')  # React to confirm logging
            await message.channel.send(f"{message.author.mention} has logged {number_made}/{number_attempted} freethrows for {date.strftime('%Y-%m-%d')}.")
            self.bot.database.upload()
        else:
            await message.add_reaction('❌')  # React to indicate an error
            await message.channel.send("Invalid format. Usage: !log_freethrows [date] <made> [attempted]")
