import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

from cli.args import parse_args
from src.backend import Dropbox, LarrysDatabase, LarrysStockExchange, Local
from src.commands import LarrysCommands, DebugCommands
from src.extensions.music_player.youtube import YoutubeMusicPlayer
# from src.extensions.news.larrys_news_recommender import LarrysNewsCogs
from src.extensions.stock_trading.larrys_stock_trader import FinnhubAPI, StockUserCommands, StockCommands
from src.profiles import ProfileCommands
from src.tasks import LarrysTasks
from src.events import LarrysEvents
from src.openai import OpenAICog
from src.exercise import ExerciseCog
from src.types import BotConstants, WalkArgs, Songs, ROOT_PATH
from src.util import upload


class LarrysBot:

    def __init__(self):

        self.args = parse_args()

        if self.args.test or self.args.local:
            print(discord.opus.is_loaded())
            discord.opus.load_opus('/usr/local/lib/libopus.so')
            #discord.opus.load_opus('/home/ec2-user/libopus-0.x86.dll')
            print(discord.opus.is_loaded())
            #discord.opus.load_opus('/usr/local/lib/libopus.dylib')

        intents = self._get_intents()
        self.discord_client = commands.Bot(command_prefix='!', intents=intents)
        self.bot_constants = BotConstants()
        if self.args.test:
            # TODO: add these (and the original IDs) to the .env file)
            print('Running in test mode...')
            self.bot_constants.TEXT_CHANNEL_ID = 1193977937955913879
            self.bot_constants.VOICE_CHANNEL_ID = 1191159993861414922
            self.bot_constants.DB_FILE = 'test.db'
            self.bot_constants.DB_PATH = ROOT_PATH / 'data' / self.bot_constants.DB_FILE
            self.bot_constants.STOCK_DB_FILE = 'test_stock_exchange.db'
        print('these are the bot constants:', self.bot_constants.__dict__)
        load_dotenv()
        self.database = LarrysDatabase(self.bot_constants.DB_FILE)
        self.backend_client = Local() if self.args.local else Dropbox()
        upload(self.backend_client, self.bot_constants.DB_FILE)
        self.stock_exchange_database = LarrysStockExchange(self.bot_constants.STOCK_DB_FILE)
        self.stock_api = FinnhubAPI(os.getenv('FINNHUB_API_KEY'))
        self.walk_constants = WalkArgs()
        self.songs = Songs()
        self.bot_constants.TOKEN = os.getenv('BOT_TOKEN')
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
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
        # await self.discord_client.add_cog(LarrysNewsCogs(self))
