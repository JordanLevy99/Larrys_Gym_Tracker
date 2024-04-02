import datetime
from datetime import datetime, timedelta

import discord
import pandas as pd
from discord.ext import commands
from discord.utils import get


class ProfileCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.__walkers = None
        self.__walk_start_date = datetime(2024, 1, 1)
        self.__total_number_of_days = (datetime.now() - self.__walk_start_date).days

    @commands.command()
    async def profile(self, ctx, name: str = ''):
        self.__walkers = discord.utils.get(ctx.guild.roles, name='Walker').members
        if name != '' and not get(self.__walkers, name=name):
            await ctx.send(f"**{name}** is not a walker")
            return
        self.__total_number_of_days = (datetime.now() - self.__walk_start_date).days
        member = get(self.__walkers, name=name) or ctx.author
        winner_df = self.__get_winner_df()
        days_won_df = winner_df.query(f'name == "{member.name}"')
        user_joins_df = self.__get_user_joins_df(member.name)
        # user_points_by_type_df = self.__get_user_points_by_type_df(member.name)
        user_points_df = self.__get_user_points_df(member.name)

        number_of_days_joined, days_joined = self.__get_number_of_days_joined(user_joins_df)
        number_of_days_won = f'Number of days won: **{len(days_won_df)}**'
        win_rate_of_days_joined = f'Win rate of days joined: **{len(days_won_df) / days_joined * 100:.2f}%**'
        win_rate_of_days_walked = f'Win rate of days where someone walked: **{len(days_won_df) / len(winner_df) * 100:.2f}%**'
        total_win_rate = f'Win rate over all days: **{len(days_won_df) / self.__total_number_of_days * 100:.2f}%**'
        earliest_time_joined = self.__get_earliest_time_joined(user_joins_df)
        average_time_joined = self.__get_average_time_joined(user_joins_df)
        average_points_per_day = self.__get_average_points_per_day(user_points_df)
        average_points_per_weekday = self.__get_average_points_per_weekday(user_points_df)
        average_points_per_weekend = self.__get_average_points_per_weekend(user_points_df)

        await ctx.send(f"**{member.display_name}**'s Stats:"
                       f"\n\n**Days**"
                       f"\n\t{number_of_days_joined}"
                       f"\n\n**Wins**"
                       f"\n\t{number_of_days_won}"
                       f"\n\t{win_rate_of_days_joined}"
                       f"\n\t{win_rate_of_days_walked}"
                       f"\n\t{total_win_rate}"
                       f"\n\n**Times**"
                       f"\n\t{average_time_joined}"
                       f"\n\t{earliest_time_joined}"
                       f"\n\n**Points**"
                       f"\n\t{average_points_per_day}"
                       f"{average_points_per_weekday}"
                       f"{average_points_per_weekend}"
                       )

    def __get_number_of_days_joined(self, user_joins_df):
        days_joined = len(user_joins_df)
        percentage_days_joined = days_joined / self.__total_number_of_days * 100
        number_of_days_joined = (f'Number of days joined: **{days_joined}** out of **{self.__total_number_of_days}** '
                                 f'possible days')
        percentage_days_joined = f'\n\tPercentage of days joined: **{percentage_days_joined:.2f}%**'
        return number_of_days_joined + percentage_days_joined, len(user_joins_df)

    @staticmethod
    def __get_average_points_per_day(user_points_df):
        average_points_per_day = user_points_df['total_points'].mean()
        return f'Average points per day: **{average_points_per_day:.2f}**'

    @staticmethod
    def __get_average_points_per_weekday(user_points_df):
        weekday_points_df = user_points_df.query('weekday != "Saturday" and weekday != "Sunday"')
        average_weekday_points = weekday_points_df['total_points'].mean()
        average_points_per_weekday_str = f'\n\t\tAverage points per weekday: **{average_weekday_points:.2f}**'
        average_points_per_weekday = weekday_points_df.groupby('weekday').agg({'total_points': 'mean'})
        average_points_per_weekday = average_points_per_weekday.loc[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], :].reset_index()
        for row in average_points_per_weekday.iterrows():
            average_points_per_weekday_str += f'\n\t\t\t{row[1]["weekday"]}: **{row[1]["total_points"]:.2f}**'
        return average_points_per_weekday_str

    @staticmethod
    def __get_average_points_per_weekend(user_points_df):
        weekend_points_df = user_points_df.query('weekday == "Saturday" or weekday == "Sunday"')
        average_weekend_points = weekend_points_df['total_points'].mean()
        average_points_per_weekend= weekend_points_df.groupby('weekday').agg({'total_points': 'mean'}).reset_index()
        average_points_per_weekend_str = f'\n\t\tAverage points per weekend: **{average_weekend_points:.2f}**'
        for row in average_points_per_weekend.iterrows():
            average_points_per_weekend_str += f'\n\t\t\t{row[1]["weekday"]}: **{row[1]["total_points"]:.2f}**'
        return average_points_per_weekend_str

    def __get_user_points_by_type_df(self, name):
        name = name.replace("'", "''")
        return pd.read_sql_query(f"""
                                        SELECT name, day, points_awarded, type
                                        FROM points
                                        WHERE name = '{name}'
                                        GROUP BY name, day
                                        """, self.bot.database.connection)

    def __get_user_points_df(self, name):
        name = name.replace("'", "''")
        user_points_df = pd.read_sql_query(f"""
                                        SELECT name, day, SUM(points_awarded) as 'total_points'
                                        FROM points
                                        WHERE name = '{name}'
                                        GROUP BY name, day
                                        """, self.bot.database.connection)
        user_points_df['day'] = pd.to_datetime(user_points_df['day'])
        user_points_df['weekday'] = user_points_df['day'].dt.day_name()
        return user_points_df

    def __get_winner_df(self):
        return pd.read_sql_query(f"""SELECT day, name, MAX(total_points) as 'max_points'
                                          FROM (
                                                SELECT day, name, SUM(points_awarded) as 'total_points'
                                                FROM points
                                                GROUP BY day, name
                                               ) as daily_points
                                          GROUP BY day
                                        """, self.bot.database.connection)

    @staticmethod
    def __get_average_time_joined(user_joins_df):
        def time_to_seconds(t):
            return (t.hour * 60 + t.minute) * 60 + t.second

        def seconds_to_time(sec):
            return str(timedelta(seconds=sec))

        user_joins_df['time_seconds'] = user_joins_df['time'].apply(time_to_seconds)
        average_time_seconds = user_joins_df['time_seconds'].mean()
        average_time = seconds_to_time(average_time_seconds)
        return f'Average time joined: **{average_time}**'

    def __get_user_joins_df(self, name):
        user_joins_df = pd.read_sql_query(f"""
                                        SELECT name, MIN(time) as 'time', day
                                        FROM (
                                            SELECT name, time, DATE(time) as 'day'
                                            FROM voice_log
                                            WHERE user_joined = 1
                                            )
                                        GROUP BY name, day
                                        """, self.bot.database.connection)
        user_joins_df['time'] = user_joins_df['time'].apply(
            lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'))
        user_joins_df['time'] = user_joins_df['time'].apply(lambda x: x.time())
        user_joins_df = user_joins_df.query(f'name == "{name}"')
        user_joins_df = user_joins_df.groupby(['name', 'day']).agg({'time': 'min'}).reset_index()
        return user_joins_df

    @staticmethod
    def __get_earliest_time_joined(user_joins_df):
        user_joins_df = user_joins_df.query('day > "2024-01-04"')
        min_time_joined = user_joins_df.loc[user_joins_df['time'].idxmin(), ['name', 'day', 'time']]
        earliest_time_joined = f'Earliest time joined: **{min_time_joined["time"]}** on **{min_time_joined["day"]}**'
        return earliest_time_joined
