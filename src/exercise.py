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

    @tasks.loop(hours=24)
    async def exercise_of_the_day(self):
        voice_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.VOICE_CHANNEL_ID)
        # Temporarily disable text-to-speech by forcing text-only mode
        full_response, tldr_response = self.__get_exercise('text')

        # TODO: make a utility function to connect to the voice channel

        if voice_channel and len(voice_channel.members) >= 1:
            text_channel, voice_client = await self.__get_voice_client_and_text_channel(voice_channel)
            await text_channel.send(full_response)
            await text_channel.send('\n\n' + tldr_response)
        else:
            await self.__send_responses_to_text_channel(full_response, tldr_response)

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
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now, hour=self.bot.walk_constants.WINNER_HOUR,
                                                minute=44, second=50,
                                                microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        print('for exercise of the day, we wait until', target_time)
        print(f'exercise of the day wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @commands.command()
    async def log_exercise(self, ctx):
        if self.__exercise_is_already_logged(ctx):
            await ctx.send('You already logged your exercise for today.')
            return

        current_time = datetime.datetime.now(tz=pytz.timezone('US/Pacific'))
        current_date = current_time.date()
        current_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        daily_exercise = self.bot.database.cursor.execute(f"SELECT exercise FROM exercise_of_the_day "
                                                          f"WHERE date = "
                                                          f"'{current_date}'").fetchone()[0]
        exercise_points = self.bot.database.cursor.execute(f"SELECT points FROM exercise_of_the_day "
                                                           f"WHERE date = "
                                                           f"'{current_date}'").fetchone()[0]
        self.bot.database.cursor.execute(f"INSERT INTO exercise_log (name, id, exercise, time)"
                                         f" VALUES (?, ?, ?, ?)", (ctx.author.name, ctx.author.id,
                                                                   daily_exercise, current_time))
        try:
            self.__update_points(ctx, current_date, exercise_points)
            self.__update_stock_balance(ctx, exercise_points)
            await ctx.send(f'{ctx.author.name} has logged their exercise for today: '
                           f'**{daily_exercise}** at **{current_time}** for **{int(exercise_points)}** points!')
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
        except ValueError as e:
            print(e)
            await ctx.send('There was an error logging your exercise. Contact @dinkster for help.')

    def __update_points(self, ctx, current_date, exercise_points):
        self.bot.database.cursor.execute(f"""INSERT INTO points (name, id, points_awarded, day, type)
                                                    VALUES (?, ?, ?, ?, ?)""",
                                         (ctx.author.name, ctx.author.id,
                                          int(exercise_points), current_date, 'EXERCISE'))
        self.bot.database.connection.commit()

    def __update_stock_balance(self, ctx, exercise_points):
        try:
            current_balance = self.bot.stock_exchange_database.get_user_balance(ctx.author.id)
            current_balance += int(exercise_points)
            self.bot.stock_exchange_database.update_user_balance(ctx.author.id, current_balance)
            self.bot.stock_exchange_database.connection.commit()
        except Exception as e:
            print(e)
        return

    def __exercise_is_already_logged(self, ctx):
        current_time = datetime.datetime.now(tz=pytz.timezone('US/Pacific'))
        current_date = current_time.date()
        return self.bot.database.cursor.execute(f"SELECT  name, id, exercise, date FROM "
                                                f"(SELECT name, id, exercise, DATE(time) as date "
                                                f"FROM exercise_log)"
                                                f"WHERE date = "
                                                f"'{current_date}' AND id = {ctx.author.id}").fetchone()

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
