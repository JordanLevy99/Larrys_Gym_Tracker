import asyncio
import random
import time
from asyncio import tasks
from datetime import datetime, timedelta

import discord
import pandas as pd
import pytz
from discord.ext import commands

from cli.args import parse_args
from src.backend import Dropbox
from src.types import BotConstants, WalkArgs, Database, Songs
from src.util import _get_current_time, play_song


class LarrysBot:

    def __init__(self):

        self.args = parse_args()

        def _get_intents():
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            return intents

        intents = _get_intents()
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.bot_constants = BotConstants()
        self.database = Database(self.bot_constants)
        self.walk_constants = WalkArgs()
        self.songs = Songs()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.load_extensions())
        if self.args.test:
            print('Running in test mode...')
            BotConstants.TEXT_CHANNEL_ID = 1193977937955913879
            BotConstants.VOICE_CHANNEL_ID = 1191159993861414922

        self.backend_client = Dropbox(BotConstants.DB_FILE)
        self.bot.run(self.bot_constants.TOKEN)
        self.download(self.backend_client)


    async def load_extensions(self):
        await self.bot.load_extension('src.commands')
        await self.bot.load_extension('events')
        await self.bot.load_extension('src.tasks')
    @tasks.loop(hours=24)
    async def determine_monthly_winner(self):
        _, pacific_time = _get_current_time()
        if pacific_time.day == 1:
            voice_channel = self.bot.get_channel(BotConstants.VOICE_CHANNEL_ID)

            if voice_channel and len(voice_channel.members) >= 1:
                try:
                    voice_client = await voice_channel.connect()
                except discord.errors.ClientException:
                    print(
                        f'Already connected to a voice channel.')

                voice_client = self.bot.voice_clients[0]
                leaderboard_query = """
                    SELECT name, SUM(points_awarded) AS total_points
                    FROM points
                    WHERE day >= date('now', '-1 month')
                    GROUP BY name
                    ORDER BY total_points DESC
                    LIMIT 1
                """
                leaderboard_df = pd.read_sql_query(leaderboard_query, db.connection)
                winner = leaderboard_df.iloc[0]
                if winner.empty:
                    print('No winner found')
                    await voice_channel.disconnect()
                    return
                # winner_args = winner_songs[winner['name']]
                text_channel = self.bot.get_channel(BotConstants.TEXT_CHANNEL_ID)

                await text_channel.send(
                    f"Congrats to dinkstar for winning the month of January with {round(winner['total_points'])} points!\nhttps://www.youtube.com/watch?v=veb4_RB01iQ&ab_channel=KB8")
                await play_song(voice_client, f'data/songs/speech.wav', 5, 0, False)
                await play_song(voice_client, f'data/songs/all_of_the_lights.mp3', 14, 0, True)

    @tasks.loop(hours=24)
    async def draw_card(self):
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

        # # Create a deck of cards
        # deck = [f'{rank}{suit}' for suit in suits for rank in ranks]

        # # Draw a random card from the deck
        # card = random.choice(deck)

        # Unicode for playing cards
        suit = random.choice(suits)
        rank = random.choice(ranks)
        suit_str = f"\_\_\_\_\_\n|{suit}      |\n|    {rank}    |\n|      {suit}|\n\_\_\_\_\_"

        text_channel = self.bot.get_channel(BotConstants.TEXT_CHANNEL_ID)
        await text_channel.send("Card of the day is:\n" + suit_str)

    @tasks.loop(hours=24)
    async def determine_daily_winner(self):
        voice_channel = self.bot.get_channel(BotConstants.VOICE_CHANNEL_ID)

        if voice_channel and len(voice_channel.members) >= 1:
            try:
                voice_client = await voice_channel.connect()
            except discord.errors.ClientException:
                print(
                    f'Already connected to a voice channel.')

            voice_client = self.bot.voice_clients[0]
            winner = await self.determine_winner()
            if winner.empty:
                print('No winner found')
                await voice_channel.disconnect()
                return
            winner_args = Songs.WINNER[winner['name']]
            random_winner_args = random.choice(winner_args)
            _, pacific_time = _get_current_time()
            current_date = pacific_time.date()
            # TODO: get these values from the `birthday_args` dictionary
            try:
                current_birthday = Songs.BIRTHDAY[(current_date.month, current_date.day)]
                birthday_name, birthday_link = current_birthday
                duration = 73
                if birthday_name == 'ben':
                    duration = 49
                text_channel = self.bot.get_channel(BotConstants.TEXT_CHANNEL_ID)
                await text_channel.send(f'Happy Birthday {birthday_name.capitalize()}!\n{birthday_link}')
                await play_song(voice_client, f'data/songs/happy_birthday_{birthday_name}.mp3',
                                duration, 0, disconnect_after_song=False)

                time.sleep(2)
            except KeyError:
                pass
            await play_song(voice_client, f'data/songs/{random_winner_args[0]}', random_winner_args[1],
                            random_winner_args[2])
        else:
            print('not enough people in the vc')

    @determine_daily_winner.before_loop
    async def before_determine_daily_winner(self):
        now = datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.replace(now, hour=WalkArgs.WINNER_HOUR, minute=WalkArgs.WINNER_MINUTE, second=0,
                                       microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Waiting until', target_time)
        print(f'wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @draw_card.before_loop
    async def before_draw_card(self):
        now = datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.replace(now, hour=6, minute=45, second=0, microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Drawing card at', target_time)
        print(f'wait time for draw card: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @determine_monthly_winner.before_loop
    async def before_determine_monthly_winner(self):
        now = datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.replace(now, hour=WalkArgs.WINNER_HOUR, minute=WalkArgs.WINNER_MINUTE - 1, second=0,
                                       microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Monthly winner determined at', target_time)
        print(f'wait time for monthly winner check: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())
