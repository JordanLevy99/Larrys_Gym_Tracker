import pandas as pd
from tabulate import tabulate

import discord
from discord.ext import commands

from cli.main import database as db
# from cli.main import bot, bot_constants, walk_constants, database as db, download
from src.types import BotConstants, WalkArgs
from src.tasks import determine_daily_winner
from src.util import _process_query, _get_current_time, upload, update_points

# bot_constants = BotConstants()
# args = parse_args()
# current_text_channel = lambda member: discord.utils.get(member.guild.threads, name=bot_constants.TEXT_CHANNEL)
# verbose = True
# walk_constants = WalkArgs()
# songs = Songs()
# intents = discord.Intents.default()
# bot = commands.Bot(command_prefix='!', intents=intents)
#
# if args.test:
#     print('Running in test mode...')
#     bot_constants.TEXT_CHANNEL_ID = 1193977937955913879
#     bot_constants.VOICE_CHANNEL_ID = 1191159993861414922
#
# # Load the .env file
# load_dotenv()
# bot_constants.TOKEN = os.getenv('BOT_TOKEN')
#
# # permissions = Permissions(0x00000400 | 0x00000800 | 0x00800000)
# # Get the bot token
#
# intents.message_content = True
# intents.members = True
#
# dropbox = Dropbox()


# connect_to_database()
# download()


@commands.command()
async def start_time(ctx, start_time: int):
    # global start_hour, end_hour, winner_hour
    start_hour = start_time
    winner_hour = start_time
    end_hour = start_time + 2
    await ctx.send(f'Walk start time set to {start_hour}:00 Pacific time for today...')


@commands.command()
async def determine_daily_winner_backup(ctx):
    await determine_daily_winner()


# @commands.command()
# async def disconnect(ctx):
#     voice_client = bot.voice_clients[0]
#     await voice_client.disconnect(force=True)


@commands.command()
async def get_id(ctx):
    # await ctx.send(
    channel = discord.utils.get(ctx.guild.channels, name=BotConstants.TEXT_CHANNEL)
    channel_id = channel.id
    print(f'The channel id for {BotConstants.TEXT_CHANNEL} is {channel_id}')
    channel = discord.utils.get(ctx.guild.channels, name=BotConstants.VOICE_CHANNEL)
    channel_id = channel.id
    print(f'The channel id for {BotConstants.VOICE_CHANNEL} is {channel_id}')



@commands.command()
async def end_walk(ctx):
    if not WalkArgs.WALK_ENDED:
        current_time, _ = _get_current_time()
        await update_points(ctx, current_time)
        WalkArgs.WALK_ENDED = True


@commands.command()
async def drop_points(ctx):
    db.cursor.execute("DROP TABLE points")
    db.connection.commit()
    upload()


@commands.command()
async def delete_all_points(ctx):
    db.cursor.execute("DELETE FROM points")
    db.connection.commit()
    upload()
    # await ctx.send(f'Dropped points table...')


@commands.command()
async def download_db(ctx):
    download()
    # await ctx.send(f'Downloaded {bot_constants.DB_FILE} from Google Drive!')


@commands.command()
async def upload_db(ctx):
    upload()
    print(f'Uploaded {BotConstants.DB_FILE} to Dropbox!')
    # await ctx.send(f'Uploaded {bot_constants.DB_FILE} to Google Drive!')


@commands.command()
async def leaderboard(ctx, *args):
    query = ' '.join(args)
    role = discord.utils.get(ctx.guild.roles, name='Walker')
    # Select all rows from the points table
    points_column, time_filter, type_filter = _process_query(query)

    points_column = f'{points_column}' if points_column else 'total'
    print(points_column, time_filter, type_filter)
    leaderboard_query = f"""SELECT name, SUM(points_awarded) as '{points_column}'
                            FROM (
                                SELECT name, id, points_awarded, day, type
                                FROM points
                                {type_filter}
                            )  
                            {time_filter}
                            GROUP BY id"""
    leaderboard_df = pd.read_sql_query(leaderboard_query, db.connection)
    print(leaderboard_df)
    if leaderboard_df.empty:
        # Find all users in the text_channel and output 0 for their points
        leaderboard_series = pd.Series(dict(zip([member.name for member in role.members], [0] * len(role.members))))
        leaderboard_series.name = points_column
        leaderboard_df = leaderboard_series.to_frame()
    leaderboard_df[points_column] = leaderboard_df[points_column].round(2)
    # Convert the leaderboard to a table with borders
    leaderboard_table = tabulate(leaderboard_df.sort_values(by=points_column, ascending=False).reset_index(drop=True),
                                 headers='keys',
                                 showindex=False,
                                 tablefmt='simple_grid')
    print(f'{points_column.capitalize()} Leaderboard:\n', leaderboard_df)

    await ctx.send(f'```{leaderboard_table}```')




# bot.run(bot_constants.TOKEN)
