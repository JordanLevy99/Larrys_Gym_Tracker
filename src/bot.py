import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cli.args import parse_args
from src.backend import Dropbox, Database
from src.commands import LarrysCommands, DebugCommands
from src.profiles import ProfileCommands
from src.tasks import LarrysTasks
from src.events import LarrysEvents
from src.tts import TTSTasks
from src.types import BotConstants, WalkArgs, Songs, ROOT_PATH
from src.util import download


class LarrysBot:

    def __init__(self):

        self.args = parse_args()

        if self.args.test:
            discord.opus.load_opus('/opt/local/lib/libopus.0.dylib')

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
        print('these are the bot constants:', self.bot_constants.__dict__)
        self.database = Database(self.bot_constants)
        self.walk_constants = WalkArgs()
        self.songs = Songs()
        load_dotenv()
        self.bot_constants.TOKEN = os.getenv('BOT_TOKEN')
        self.backend_client = Dropbox()

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
        await self.discord_client.add_cog(TTSTasks(self))
        if self.args.test:
            await self.discord_client.add_cog(DebugCommands(self))
