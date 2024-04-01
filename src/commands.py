import shutil
from datetime import datetime

import pytz
import pandas as pd
from tabulate import tabulate
import discord
from discord.ext import commands

# from src.bot import LarrysBot
from src.types import BotConstants, ROOT_PATH
from src.backend import Database
from src.util import (_process_query, _get_current_time, upload, download, calculate_points)


class DebugCommands(commands.Cog):

    def __init__(self, bot: 'LarrysBot'):
        self.bot = bot


    @commands.command()
    async def winner_minute(self, ctx, minute: int):
        # global start_hour, end_hour, winner_hour
        self.bot.walk_constants.WINNER_MINUTE = minute
        await ctx.send(f'Walk winner time set to {self.bot.walk_constants.WINNER_HOUR}:'
                       f'{self.bot.walk_constants.WINNER_MINUTE} Pacific time for today...')
    @commands.command()
    async def drop_points(self, ctx):
        self.bot.database.cursor.execute("DROP TABLE points")
        self.bot.database.connection.commit()
        upload(self.bot.backend_client)

    @commands.command()
    async def delete_all_points(self, ctx):
        self.bot.database.cursor.execute("DELETE FROM points")
        self.bot.database.connection.commit()
        upload(self.bot.backend_client)

    @commands.command()
    async def download_database(self, ctx):
        download(self.bot.bot_constants.DB_FILE)

    @commands.command()
    async def upload_database(self, ctx):
        upload(self.bot.backend_client)
        print(f'Uploaded {BotConstants.DB_FILE} to Dropbox!')

    @commands.command()
    async def copy_database(self, ctx, new_db_file: str):
        db_path = self.bot.bot_constants.DB_PATH
        new_db_path = db_path.parent / new_db_file
        shutil.copyfile(db_path,  new_db_path)
        self.bot.bot_constants.DB_FILE = new_db_file
        self.bot.bot_constants.DB_PATH = new_db_path
        await ctx.send(f'Database file set to {self.bot.bot_constants.DB_FILE}. Path is {self.bot.bot_constants.DB_PATH}')
        self.bot.database = Database(self.bot.bot_constants)
        upload(self.bot.backend_client)

    @commands.command()
    async def get_id(self, ctx):
        # await ctx.send(
        channel = discord.utils.get(ctx.guild.channels, name=BotConstants.TEXT_CHANNEL)
        channel_id = channel.id
        print(f'The channel id for {BotConstants.TEXT_CHANNEL} is {channel_id}')
        channel = discord.utils.get(ctx.guild.channels, name=BotConstants.VOICE_CHANNEL)
        channel_id = channel.id
        print(f'The channel id for {BotConstants.VOICE_CHANNEL} is {channel_id}')


class LarrysCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start_time(self, ctx, start_hour: int):
        # global start_hour, end_hour, winner_hour
        self.bot.walk_constants.START_HOUR = start_hour
        self.bot.walk_constants.END_HOUR = start_hour + 2
        self.bot.walk_constants.WINNER_HOUR = start_hour
        await ctx.send(f'Walk start time set to {start_hour}:00 Pacific time for today...')

    @commands.command()
    async def end_walk(self, ctx):
        if not self.bot.walk_constants.WALK_ENDED:
            current_time, _ = _get_current_time()
            await self.update_points(ctx, current_time)
            self.bot.bot_constants.WALK_ENDED = True

    # noinspection SqlUnused
    @commands.command()
    async def leaderboard(self, ctx, *args):
        self.__walkers = discord.utils.get(ctx.guild.roles, name='Walker')
        query = ' '.join(args)
        points_column, time_filter, type_filter = _process_query(query)

        points_column = f'{points_column}' if points_column else 'total'
        leaderboard_query = self.__get_leaderboard_query(points_column, type_filter, time_filter)

        leaderboard_df = pd.read_sql_query(leaderboard_query, self.bot.database.connection)
        if leaderboard_df.empty:
            leaderboard_df = self.__get_zeroed_leaderboard(points_column)
        leaderboard_df[points_column] = leaderboard_df[points_column].round(2)
        # Convert the leaderboard to a table with borders
        leaderboard_table = tabulate(
            leaderboard_df.sort_values(by=points_column, ascending=False).reset_index(drop=True),
            headers='keys',
            showindex=False,
            tablefmt='simple_grid')
        print(f'{points_column.capitalize()} Leaderboard:\n', leaderboard_df)

        await ctx.send(f'```{leaderboard_table}```')

    @staticmethod
    def __get_leaderboard_query(points_column, type_filter, time_filter):
        return f"""SELECT name, SUM(points_awarded) as '{points_column}'
                    FROM (
                        SELECT name, id, points_awarded, day, type
                        FROM points
                        {type_filter}
                    )  
                    {time_filter}
                    GROUP BY id"""

    def __get_zeroed_leaderboard(self, points_column):
        leaderboard_series = pd.Series(dict(zip([member.name for member in self.__walkers.members],
                                                [0] * len(self.__walkers.members))))

        leaderboard_series.name = points_column
        leaderboard_df = leaderboard_series.to_frame()
        return leaderboard_df

    async def update_points(self, ctx, current_time):
        # Groupby name and id, extract day from date and groupby day, subtract max and min time to get duration
        # Divide duration by walk duration to get points
        voice_log_df = pd.read_sql_query("""
                                SELECT * 
                                FROM voice_log""", self.bot.database.connection)
        voice_log_df['time'] = voice_log_df['time'].astype('datetime64[ns]')
        voice_log_df['day'] = voice_log_df['time'].dt.date
        current_day = datetime.now(pytz.timezone('US/Pacific')).date()
        latest_voice_log_day = voice_log_df['day'].max()
        if current_day != latest_voice_log_day or self.bot.args.test:
            await ctx.send(
                f'No one has joined the walk today. Bad !end_walk command registered. 500 social credit will '
                f'be deducted from `{ctx.author.name}`.')
            return
        await ctx.send(f'Walk ended at {current_time}! Getting weekly leaderboard...')

        daily_voice_log_df = voice_log_df.loc[voice_log_df['day'] == current_day]
        users_durations = daily_voice_log_df.groupby(['id']).apply(lambda user: user['time'].max() - user['time'].min())
        calculate_points(self.bot.database, daily_voice_log_df, users_durations,
                         self.bot.walk_constants.LENGTH_OF_WALK_IN_MINUTES, self.bot.walk_constants.MAX_DURATION_POINTS,
                         self.bot.walk_constants.START_HOUR),
        print(pd.read_sql_query("""SELECT * FROM points""", self.bot.database.connection).tail())
        await self.leaderboard(ctx, 'WEEKLY')
        await ctx.send('Getting Today\'s On Time Leaderboard')
        await self.leaderboard(ctx, 'on time today')
        upload(self.bot.backend_client)
