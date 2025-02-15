import asyncio
import os
from pathlib import Path

import discord
from discord.ext import commands
from openai import OpenAI

from cli.args import parse_args
from src.backend import Dropbox, LarrysDatabase, LarrysStockExchange, Local
from src.commands import LarrysCommands, DebugCommands
from src.config import Config
from src.extensions.music_player.youtube import YoutubeMusicPlayer
from src.extensions.news.larrys_news_recommender import LarrysNewsCogs
# from src.extensions.realtime.realtime_cog import RealtimeCog
from src.extensions.stock_trading.larrys_stock_trader import FinnhubAPI, StockUserCommands, StockCommands
from src.profiles import ProfileCommands
from src.tasks import LarrysTasks
from src.events import LarrysEvents
from src.openai import OpenAICog
from src.exercise import ExerciseCog
from src.types import BotConstants, WalkArgs, Songs, ROOT_PATH
from src.util import upload
from src.extensions.sleep_tracker.sleep import SleepTracker
from src.extensions.year_in_review import YearInReview


class LarrysBot:

    def __init__(self):
        self.args = parse_args()
        
        # Load appropriate config based on mode
        config_path = Path('test_config.json') if self.args.test else Path('config.json')
        self.config = Config(config_path)

        if self.args.test or self.args.local:
            print(discord.opus.is_loaded())
            try:
                discord.opus.load_opus('/usr/local/lib/libopus.so')
            except Exception as e:
                print(f"Failed to load opus: {e}")
                try:
                    discord.opus.load_opus('/usr/local/lib/libopus.dylib')
                except Exception as e:
                    print(f"Failed to load opus: {e}")
            #discord.opus.load_opus('/home/ec2-user/libopus-0.x86.dll')
            print(discord.opus.is_loaded())

        intents = self._get_intents()
        self.discord_client = commands.Bot(command_prefix='!', intents=intents)
        
        # Initialize bot constants from config
        self.bot_constants = BotConstants()
        self.bot_constants.TOKEN = self.config.discord.token
        self.bot_constants.TEXT_CHANNEL = self.config.discord.text_channel_name
        self.bot_constants.VOICE_CHANNEL = self.config.discord.voice_channel_name
        self.bot_constants.TEXT_CHANNEL_ID = self.config.discord.text_channel_id
        self.bot_constants.VOICE_CHANNEL_ID = self.config.discord.voice_channel_id
        self.bot_constants.GUILD_ID = self.config.discord.guild_id
        self.bot_constants.DB_FILE = self.config.database.main_db
        self.bot_constants.STOCK_DB_FILE = self.config.database.stock_db
        self.bot_constants.DB_PATH = ROOT_PATH / 'data' / self.bot_constants.DB_FILE

        if self.args.test:
            print('Running in test mode...')
            self.bot_constants.TEXT_CHANNEL_ID = 1193977937955913879
            self.bot_constants.VOICE_CHANNEL_ID = 1191159993861414922
            self.bot_constants.DB_FILE = 'test.db'
            self.bot_constants.DB_PATH = ROOT_PATH / 'data' / self.bot_constants.DB_FILE
            self.bot_constants.STOCK_DB_FILE = 'test_stock_exchange.db'
            self.bot_constants.GUILD_ID = 1184194460884672513

        print('Bot constants:', self.bot_constants.__dict__)
        
        self.database = LarrysDatabase(self.bot_constants.DB_FILE)
        self.backend_client = Local() if self.args.local else Dropbox()
        upload(self.backend_client, self.bot_constants.DB_FILE)
        self.stock_exchange_database = LarrysStockExchange(self.bot_constants.STOCK_DB_FILE)
        self.stock_api = FinnhubAPI(self.config.api_keys.finnhub)
        self.walk_constants = WalkArgs()
        
        # Initialize songs from config
        self.songs = Songs()
        self.songs.BIRTHDAY = self.config.birthday_tuples
        self.songs.WINNER = self.config.winner_song_tuples
        
        self.perplexity_client = OpenAI(
            api_key=self.config.api_keys.perplexity,
            base_url="https://api.perplexity.ai"
        )
        self.openai_client = OpenAI(
            api_key=self.config.api_keys.openai,
        )

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.load_extensions())
        self.discord_client.run(self.bot_constants.TOKEN)

    @staticmethod
    def _get_intents():
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        return intents

    async def load_extensions(self):
        await self.discord_client.add_cog(LarrysEvents(self))
        await self.discord_client.add_cog(LarrysCommands(self))
        await self.discord_client.add_cog(LarrysTasks(self))
        await self.discord_client.add_cog(ProfileCommands(self))
        await self.discord_client.add_cog(OpenAICog(self))
        await self.discord_client.add_cog(ExerciseCog(self))
        await self.discord_client.add_cog(StockUserCommands(self))
        await self.discord_client.add_cog(StockCommands(self))
        await self.discord_client.add_cog(DebugCommands(self))
        await self.discord_client.add_cog(YoutubeMusicPlayer(self))
        await self.discord_client.add_cog(LarrysNewsCogs(self))
        await self.discord_client.add_cog(SleepTracker(self))
        await self.discord_client.add_cog(YearInReview(self))
        # await self.discord_client.add_cog(RealtimeCog(self))
