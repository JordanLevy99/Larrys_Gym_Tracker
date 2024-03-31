import asyncio

import discord
from discord.ext import commands

from cli.args import parse_args
from src.backend import Dropbox
from src.types import BotConstants, Database

database = None


def run():
    bot_constants = BotConstants()
    args = parse_args()

    # current_text_channel = lambda member: discord.utils.get(member.guild.threads, name=bot_constants.TEXT_CHANNEL)
    # verbose = True
    # walk_constants = WalkArgs()
    # songs = Songs()

    def _get_intents():
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        return intents

    intents = _get_intents()
    bot = commands.Bot(command_prefix='!', intents=intents)

    async def load_extensions():
        await bot.load_extension('src.commands')
        await bot.load_extension('events')
        await bot.load_extension('src.tasks')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_extensions())
    if args.test:
        print('Running in test mode...')
        BotConstants.TEXT_CHANNEL_ID = 1193977937955913879
        BotConstants.VOICE_CHANNEL_ID = 1191159993861414922

    dropbox = Dropbox(BotConstants.DB_FILE)
    bot.run(bot_constants.TOKEN)
    download(dropbox)


# connect_to_database()




    # Read the file into a pandas DataFrame
    # conn = sqlite3.connect(bot_constants.DB_FILE)
    # c = conn.cursor()
    # df = pd.read_sql_query("SELECT * FROM voice_log", db.connection)
    #
    # # Print the last five entries of the DataFrame
    # print(df.tail())
    # df.to_sql(BotConstants.DB_FILE, db.connection, if_exists='replace', index=False)
