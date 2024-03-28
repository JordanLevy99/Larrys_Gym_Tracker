import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cli.args import parse_args
from src.backend import Dropbox
from src.types import BotConstants, WalkArgs, Songs

from src.bot import *



bot_constants = BotConstants()
args = parse_args()
current_text_channel = lambda member: discord.utils.get(member.guild.threads, name=bot_constants.TEXT_CHANNEL)
verbose = True
walk_constants = WalkArgs()
songs = Songs()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

if args.test:
    print('Running in test mode...')
    bot_constants.TEXT_CHANNEL_ID = 1193977937955913879
    bot_constants.VOICE_CHANNEL_ID = 1191159993861414922

# Load the .env file
load_dotenv()

# permissions = Permissions(0x00000400 | 0x00000800 | 0x00800000)
# Get the bot token

intents.message_content = True
intents.members = True

dropbox = Dropbox()


bot.run(bot_constants.TOKEN)
