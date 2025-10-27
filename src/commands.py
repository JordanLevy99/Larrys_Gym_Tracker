import shutil
from datetime import datetime

import pytz
import pandas as pd
from tabulate import tabulate
import discord
from discord.ext import commands

from src.extensions.stock_trading.larrys_stock_trader import StockUserCommands
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
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command()
    async def drop_today_points(self, ctx):
        self.bot.database.cursor.execute("DROP FROM points WHERE day = ?", (datetime.now().date(),))
        self.bot.database.connection.commit()
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command()
    async def delete_all_points(self, ctx):
        self.bot.database.cursor.execute("DELETE FROM points")
        self.bot.database.connection.commit()
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command()
    async def download_database(self, ctx):
        download(self.bot.bot_constants.DB_FILE)
        download(self.bot.bot_constants.STOCK_DB_FILE)

    @commands.command()
    async def upload_database(self, ctx):
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
        upload(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)
        print(f'Uploaded {self.bot.bot_constants.DB_FILE} to Dropbox!')
        print(f'Uploaded {self.bot.bot_constants.STOCK_DB_FILE} to Dropbox!')

    @commands.command()
    async def copy_database(self, ctx, new_db_file: str):
        db_path = self.bot.bot_constants.DB_PATH
        new_db_path = db_path.parent / new_db_file
        shutil.copyfile(db_path, new_db_path)
        self.bot.bot_constants.DB_FILE = new_db_file
        self.bot.bot_constants.DB_PATH = new_db_path
        await ctx.send(
            f'Database file set to {self.bot.bot_constants.DB_FILE}. Path is {self.bot.bot_constants.DB_PATH}')
        self.bot.database = Database(self.bot.bot_constants)
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command()
    async def get_id(self, ctx):
        # await ctx.send(
        channel = discord.utils.get(ctx.guild.channels, name=BotConstants.TEXT_CHANNEL)
        channel_id = channel.id
        print(f'The channel id for {BotConstants.TEXT_CHANNEL} is {channel_id}')
        channel = discord.utils.get(ctx.guild.channels, name=BotConstants.VOICE_CHANNEL)
        channel_id = channel.id
        print(f'The channel id for {BotConstants.VOICE_CHANNEL} is {channel_id}')

    @commands.command()
    async def delete_users(self, ctx):
        self.bot.stock_exchange_database.cursor.execute("DELETE FROM User")
        self.bot.stock_exchange_database.connection.commit()
        await ctx.send('Users stock accounts have been deleted, use !initialize_users <db_file> to setup again')

    @commands.command()
    async def delete_transactions(self, ctx):
        self.bot.stock_exchange_database.cursor.execute("DELETE FROM Transaction")
        self.bot.stock_exchange_database.connection.commit()
        await ctx.send('Transactions have been deleted')


class LarrysCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.__walkers = None

    @commands.command()
    async def start_time(self, ctx, start_hour: int = None, day_type: str = "weekday"):
        """Set the walk start time for weekdays or weekends

        Usage: !start_time <hour> [weekday|weekend]
        Examples:
            !start_time 8          - Sets weekday start time to 8am
            !start_time 8 weekday  - Sets weekday start time to 8am
            !start_time 9 weekend  - Sets weekend start time to 9am
        """
        # Validate day_type parameter
        day_type = day_type.lower()
        if day_type not in ["weekday", "weekend"]:
            await ctx.send(f'Invalid day type "{day_type}". Please use "weekday" or "weekend".')
            self.bot.logger.warning(f'User {ctx.author.name} attempted to set start_time with invalid day_type: {day_type}')
            return

        # If no hour provided, show current settings
        if start_hour is None:
            weekday_time = self.bot.walk_constants.START_HOUR
            weekend_time = self.bot.walk_constants.WEEKEND_START_HOUR
            await ctx.send(
                f'Current walk start times:\n'
                f'Weekday: {weekday_time}:00 PST\n'
                f'Weekend: {weekend_time}:00 PST'
            )
            return

        # Validate hour range
        if start_hour < 0 or start_hour > 23:
            await ctx.send(f'Invalid hour {start_hour}. Please provide an hour between 0 and 23.')
            self.bot.logger.warning(f'User {ctx.author.name} attempted to set start_time with invalid hour: {start_hour}')
            return

        # Update the appropriate start hour based on day_type
        is_weekend = day_type == "weekend"
        old_hour = self.bot.walk_constants.WEEKEND_START_HOUR if is_weekend else self.bot.walk_constants.START_HOUR

        if is_weekend:
            self.bot.walk_constants.WEEKEND_START_HOUR = start_hour
        else:
            self.bot.walk_constants.START_HOUR = start_hour

        # Log the change
        self.bot.logger.info(
            f'Walk start time updated by {ctx.author.name}: '
            f'{day_type} start time changed from {old_hour}:00 to {start_hour}:00 PST'
        )

        # Send confirmation message to user
        end_hour = start_hour + 2
        await ctx.send(
            f'Walk start time updated!\n'
            f'**{day_type.capitalize()}** walks now start at **{start_hour}:00 PST** and end at **{end_hour}:00 PST**\n'
            f'_(Changed from {old_hour}:00 PST)_'
        )

    @commands.command()
    async def end_walk(self, ctx):
        pacific_time = datetime.now(pytz.timezone('US/Pacific'))
        if pacific_time.hour > self.bot.walk_constants.END_HOUR:
            await ctx.send('Walk has already ended for today! *sus*')
            return
        if not self.bot.walk_constants.WALK_ENDED:
            current_time, _ = _get_current_time()
            await self.update_points(ctx, current_time)
            net_worth_leaderboard = await StockUserCommands(self.bot).get_net_worth_leaderboard(ctx)
            self.bot.bot_constants.WALK_ENDED = True
            await ctx.send(f'Getting the Net Worth Leaderboard...')
            await ctx.send(net_worth_leaderboard)

    # noinspection SqlUnused
    @commands.command()
    async def leaderboard(self, ctx, *args):
        self.__walkers = discord.utils.get(ctx.guild.roles, name='Walker')
        query = ' '.join(args)
        points_column, time_filter, type_filter = _process_query(query)
        points_column = f'{points_column}' if points_column else 'total'
        if points_column == 'sleep':
            points_column = 'sleep'
        leaderboard_query = self.__get_leaderboard_query(points_column, type_filter, time_filter)
        print(leaderboard_query)
        print('database connection', self.bot.database.connection)
        leaderboard_df = pd.read_sql_query(leaderboard_query, self.bot.database.connection)
        print(leaderboard_df)
        if leaderboard_df.empty:
            leaderboard_df = self.__get_zeroed_leaderboard(points_column)
        leaderboard_df[points_column] = leaderboard_df[points_column].round(2)
        # Convert the leaderboard to a table with borders
        leaderboard_table = tabulate(
            leaderboard_df.sort_values(by=points_column, ascending=False).reset_index(drop=True),
            headers='keys',
            showindex=False,
            tablefmt='grid')
        print(f'{points_column.capitalize()} Leaderboard:\n', leaderboard_df)

        embed = discord.Embed(description=f"**{points_column.capitalize()} Leaderboard**")
        embed.set_footer(text=leaderboard_table)
        await ctx.send(embed=embed)


    def __get_leaderboard_query(self, points_column, type_filter, time_filter):
        sleep_points_subquery = f"""
            SELECT user_id as id, SUM(points) as sleep_points
            FROM sleep_points
            GROUP BY user_id
        """
        
        main_query = f"""
            SELECT p.name, 
                   SUM(p.points_awarded) as '{points_column}', 
                   COUNT(DISTINCT p.day) as 'days'
            FROM (
                SELECT name, id, points_awarded, day, type
                FROM points
                {type_filter}
            ) p
            {time_filter}
            GROUP BY p.id
        """
            # LEFT JOIN ({sleep_points_subquery}) sp ON p.id = sp.id

        
        if points_column == 'sleep':
            main_query = f"""
                SELECT name, SUM(points) as '{points_column}', COUNT(DISTINCT date) as 'days'
                FROM sleep_points
                {time_filter}
                GROUP BY user_id
            """
        
        return main_query

    def __get_zeroed_leaderboard(self, points_column):
        leaderboard_series = pd.Series(dict(zip([member.name for member in self.__walkers.members],
                                                [0] * len(self.__walkers.members))))

        leaderboard_series.name = points_column
        leaderboard_df = leaderboard_series.to_frame()
        return leaderboard_df.reset_index().rename(columns={'index': 'name'})

    async def update_points(self, ctx, current_time):
        # Group by name and id, extract day from date and group by day, subtract max and min time to get duration
        # Divide duration by walk duration to get points
        voice_log_df = pd.read_sql_query("""
                                SELECT * 
                                FROM voice_log""", self.bot.database.connection)
        voice_log_df['time'] = voice_log_df['time'].astype('datetime64[ns]')
        voice_log_df['day'] = voice_log_df['time'].dt.date
        current_day = datetime.now(pytz.timezone('US/Pacific')).date()
        latest_voice_log_day = voice_log_df['day'].max()
        if current_day != latest_voice_log_day:
            await ctx.send(
                f'No one has joined the walk today. Bad !end_walk command registered. 500 social credit will '
                f'be deducted from `{ctx.author.name}`.')
            return
        await ctx.send(f'Walk ended at {current_time}! Getting this Season\'s leaderboard...')

        daily_voice_log_df = voice_log_df.loc[voice_log_df['day'] == current_day]
        users_durations = daily_voice_log_df.groupby(['id']).apply(lambda user: user['time'].max() - user['time'].min())
        # Use get_start_hour() to get correct start time for weekdays (7am) and weekends (9am)
        current_start_hour = self.bot.walk_constants.get_start_hour(datetime.now(pytz.timezone('US/Pacific')))
        calculate_points(self.bot.database, daily_voice_log_df, users_durations,
                         self.bot.walk_constants.LENGTH_OF_WALK_IN_MINUTES, self.bot.walk_constants.MAX_DURATION_POINTS,
                         current_start_hour, self.bot.stock_exchange_database)
        print(pd.read_sql_query("""SELECT * FROM points""", self.bot.database.connection).tail())
        await self.leaderboard(ctx, '')
        await ctx.send('Getting Today\'s On Time Leaderboard')
        await self.leaderboard(ctx, 'on time today')
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
        upload(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)

    @commands.command()
    async def toggle_join_messages(self, ctx):
        """Toggle whether join messages are sent to users"""
        # For now, this is a global config setting that requires admin privileges
        # In future, this could be per-user setting
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You need administrator permissions to toggle join messages.")
            return
            
        current_value = self.bot.config.user_preferences.get('show_join_message', True)
        new_value = not current_value
        
        # Update the config - this would need to be saved to file to persist
        self.bot.config.user_preferences['show_join_message'] = new_value
        
        status = "enabled" if new_value else "disabled"
        await ctx.send(f"Join messages have been {status}.")
