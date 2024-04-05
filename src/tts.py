import asyncio
import datetime
import os
import random
from pathlib import Path

import discord
import openai
import pytz
from discord.ext import commands, tasks
from dotenv import load_dotenv
from openai import OpenAI

from src.types import ROOT_PATH
from src.util import play_song, upload


class TTSTasks(commands.Cog):
    DEFAULT_SYSTEM_MESSAGE = ("Calculate the reps for exercises I list, aiming for a 5-minute workout duration. "
                              "Responses should be brief, creative, and suitable for a morning walk announcement. "
                              "Keep it under 3 sentences.")

    def __init__(self, bot):
        self.bot = bot
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    @tasks.loop(hours=24)
    async def exercise_of_the_day(self):
        exercises = [
            'Stare at a wall for 5 minutes',
            'Squats',
            'Pushups',
            'Jumping Jacks',
            'Planks',
            # 'Jump rope',
            'Scorpion plank hold',
            'Boxing punches',
            'Yoga pose holds',
            'Mountain climbers',
            'Burpees',
        ]
        random_exercise = random.choice(exercises)
        print(random_exercise)
        response = self.create_chat(random_exercise)
        print(response)
        remote_speech_file_path = Path('data') / "exercise_of_the_day.mp3"
        local_speech_file_path = ROOT_PATH / remote_speech_file_path
        self.__produce_tts_audio(response, local_speech_file_path)


        # TODO: make a utility function to connect to the voice channel
        voice_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.VOICE_CHANNEL_ID)

        if voice_channel and len(voice_channel.members) >= 1:
            try:
                voice_client = await voice_channel.connect()
            except discord.errors.ClientException as e:
                print(str(e))
                print(
                    f'Already connected to a voice channel.')

            voice_client = self.bot.discord_client.voice_clients[0]

            await play_song(voice_client, str(remote_speech_file_path), self.bot.backend_client, duration=50,
                            start_second=0, download=False)
        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        await text_channel.send(response)

        self.bot.database.cursor.execute(f"INSERT INTO exercise_of_the_day (exercise, date, response) "
                                         f"VALUES (?, ?, ?)", (random_exercise,
                                                               datetime.datetime.now(tz=pytz.timezone('US/Pacific')).date(),
                                                               response))
        self.bot.database.connection.commit()
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
        # await ctx.send(response.choices[0].text)

    @exercise_of_the_day.before_loop
    async def before_exercise_of_the_day(self):
        await self.bot.discord_client.wait_until_ready()
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now, hour=self.bot.walk_constants.WINNER_HOUR,
                                                minute=self.bot.walk_constants.WINNER_MINUTE+2, second=0,
                                                microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        print('for exercise of the day, we wait until', target_time)
        print(f'exercise of the day wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @commands.command()
    async def done(self, ctx):
        if self.__exercise_already_logged(ctx):
            await ctx.send('You already logged your exercise for today.')
            return

        current_time = datetime.datetime.now(tz=pytz.timezone('US/Pacific'))
        current_date = current_time.date()
        current_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        daily_exercise = self.bot.database.cursor.execute(f"SELECT exercise FROM exercise_of_the_day "
                                                           f"WHERE date = "
                                                           f"'{current_date}'").fetchone()[0]
        self.bot.database.cursor.execute(f"INSERT INTO exercise_log (name, id, exercise, time)"
                                         f" VALUES (?, ?, ?, ?)", (ctx.author.name, ctx.author.id,
                                         daily_exercise, current_time))
        self.bot.database.connection.commit()
        await ctx.send(f'{ctx.author.name} has logged their exercise for today: {daily_exercise} at {current_time}')
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    def __exercise_already_logged(self, ctx):
        current_time = datetime.datetime.now(tz=pytz.timezone('US/Pacific'))
        current_date = current_time.date()
        return self.bot.database.cursor.execute(f"SELECT  name, id, exercise, date FROM " 
                                                f"(SELECT name, id, exercise, DATE(time) as date "
                                                f"FROM exercise_log)"
                                                f"WHERE date = "
                                                f"'{current_date}' AND id = {ctx.author.id}").fetchone()

    def __produce_tts_audio(self, response, speech_file_path):
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=response
        )
        response.write_to_file(speech_file_path)
        # upload(str(speech_file_path))

    def create_chat(self, user_message, system_message=DEFAULT_SYSTEM_MESSAGE):
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            model="gpt-4-0125-preview",
            max_tokens=150
        )

        return response.choices[0].message.content