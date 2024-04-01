import asyncio
import random
import time
from datetime import timedelta
import datetime

import discord
import pandas as pd
import pytz
from discord.ext import commands, tasks

from src.types import Songs
from src.util import _get_current_time, play_song, determine_winner


class LarrysTasks(commands.Cog):

    def __init__(self, bot: 'LarrysBot'):
        self.bot = bot

    @tasks.loop(hours=24)
    async def determine_monthly_winner(self):
        _, pacific_time = _get_current_time()
        if pacific_time.day == 31:
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

                await text_channel.send(
                    f"Congrats to kyboydigital for winning the month of January with {round(winner['total_points'])} points!\nhttps://www.youtube.com/watch?v=veb4_RB01iQ&ab_channel=KB8")
                await play_song(voice_client, f'data/songs/march_winner_2024.wav', self.bot.backend_client, 6, 0, False)
                await play_song(voice_client, f'data/songs/first_of_the_month.mp3', self.bot.backend_client, 21, 41, True)

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

        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        await text_channel.send("Card of the day is:\n" + suit_str)

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
                text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
                await text_channel.send(f'Happy Birthday {birthday_name.capitalize()}!\n{birthday_link}')
                await play_song(voice_client, f'data/songs/happy_birthday_{birthday_name}.mp3',
                                self.bot.backend_client, duration, 0, disconnect_after_song=False)

                time.sleep(2)
            except KeyError:
                pass
            await play_song(voice_client, f'data/songs/{random_winner_args[0]}', self.bot.backend_client,
                            random_winner_args[1], random_winner_args[2])
        else:
            print('not enough people in the vc')

    @determine_daily_winner.before_loop
    async def before_determine_daily_winner(self):
        await self.bot.discord_client.wait_until_ready()
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now, hour=self.bot.walk_constants.WINNER_HOUR, minute=self.bot.walk_constants.WINNER_MINUTE, second=0,
                                       microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Waiting until', target_time)
        print(f'wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @draw_card.before_loop
    async def before_draw_card(self):
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now, hour=6, minute=45, second=0, microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Drawing card at', target_time)
        print(f'wait time for draw card: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @determine_monthly_winner.before_loop
    async def before_determine_monthly_winner(self):
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now, hour=self.bot.walk_constants.WINNER_HOUR,
                                                minute=self.bot.walk_constants.WINNER_MINUTE - 1, second=0,
                                       microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Monthly winner determined at', target_time)
        print(f'wait time for monthly winner check: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())
