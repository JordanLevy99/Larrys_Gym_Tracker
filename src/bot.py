import asyncio
import os
import random
import time
# from asyncio import tasks
from datetime import datetime, timedelta

import discord
import pandas as pd
import pytz
from discord.ext import commands, tasks
from dotenv import load_dotenv

from cli.args import parse_args
from src.backend import Dropbox
from src.commands import LarrysCommands
from src.types import BotConstants, WalkArgs, Database, Songs
from src.util import _get_current_time, play_song, download, determine_winner


class LarrysBot:

    def __init__(self):

        self.args = parse_args()

        def _get_intents():
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            return intents

        intents = _get_intents()
        self.discord_client = commands.Bot(command_prefix='!', intents=intents)
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

        load_dotenv()
        self.bot_constants.TOKEN = os.getenv('BOT_TOKEN')

        self.backend_client = Dropbox()
        self.discord_client.run(self.bot_constants.TOKEN)
        download(self.backend_client)

    async def load_extensions(self):
        await self.discord_client.add_cog(LarrysCommands(self))

        # await self.discord_client.load_extension('src.commands', package='LarrysCommands')
        # await self.discord_client.load_extension('events')
        # await self.discord_client.load_extension('src.tasks')

