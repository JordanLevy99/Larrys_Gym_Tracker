import datetime
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import discord
import pandas as pd
from discord.ext import commands
from discord.utils import get


class ProfileCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.__sections = ['days', 'wins', 'times', 'points']
        self.__walkers = None
        self.__walk_start_date = datetime(2024, 1, 1)
        self.__total_number_of_days = (datetime.now() - self.__walk_start_date).days

    @commands.command()
    async def profile(self, ctx, name: str = ''):
        self.__walkers = discord.utils.get(ctx.guild.roles, name='Walker').members
        if name != '' and not get(self.__walkers, name=name) and name not in self.__sections:
            await ctx.send(f"**{name}** is not a walker")
            return
        self.__total_number_of_days = (datetime.now() - self.__walk_start_date).days
        member = get(self.__walkers, name=name) or ctx.author
        winner_df = self.__get_winner_df()
        user_joins_df = self.__get_user_joins_df(member.name)
        user_points_df = self.__get_user_points_df(member.name)

        profile_data = {
            'days': (len(user_joins_df), self.__total_number_of_days),
            'wins': (winner_df, len(user_joins_df), member, self.__total_number_of_days),
            'times': (user_joins_df,),
            'points': (user_points_df,)
        }
        profile = ''
        if name.lower() in self.__sections:
            name = name.lower()
            profile += ProfileFactory().create(name, profile_data[name]).generate()
            await ctx.send(profile)
            return
        for section in self.__sections:
            profile += ProfileFactory().create(section, profile_data[section]).generate()
        await ctx.send(f"**{member.display_name}**'s Stats:{profile}")

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


class Profile(ABC):

    def __init__(self, data):
        pass

    @abstractmethod
    def generate(self):
        pass


class ProfileDays(Profile):

    def __init__(self, data):
        super().__init__(data)
        self.days_joined, self.__total_number_of_days = data[0], data[1]

    def generate(self):
        number_of_days_joined = f'Number of days joined: **{self.days_joined}** out of **{self.__total_number_of_days}** possible days'
        percentage_days_joined = f'Percentage of days joined: **{self.days_joined / self.__total_number_of_days * 100:.2f}%**'
        days = f"\n\n**Days**" \
               f"\n\t{number_of_days_joined}" \
               f"\n\t{percentage_days_joined}"
        return days


class ProfileWins(Profile):

    def __init__(self, data):
        super().__init__(data)
        self.winner_df, self.days_joined, self.member, self.__total_number_of_days = data[0], data[1], data[2], data[3]

    def generate(self):
        days_won_df = self.winner_df.query(f'name == "{self.member.name}"')
        number_of_days_won = f'Number of days won: **{len(days_won_df)}**'
        win_rate_of_days_joined = f'Win rate of days joined: **{len(days_won_df) / self.days_joined * 100:.2f}%**'
        win_rate_of_days_walked = (f'Win rate of days where someone walked: '
                                   f'**{len(days_won_df) / len(self.winner_df) * 100:.2f}%**')
        # total_win_rate = f'Win rate over all days: **{len(days_won_df) / self.__total_number_of_days * 100:.2f}%**'

        total_win_rate = f'Win rate over all days: **{len(days_won_df) / self.__total_number_of_days * 100:.2f}%**'
        wins = f"\n\n**Wins**" \
               f"\n\t{number_of_days_won}" \
               f"\n\t{win_rate_of_days_joined}" \
               f"\n\t{win_rate_of_days_walked}" \
               f"\n\t{total_win_rate}"
        return wins


class ProfileTimes(Profile):

    def __init__(self, data):
        super().__init__(data)
        self.user_joins_df = data[0]

    def generate(self):
        self.user_joins_df['time_seconds'] = self.user_joins_df['time'].apply(self.__time_to_seconds)
        average_time_seconds = self.user_joins_df['time_seconds'].mean()
        average_time = self.__seconds_to_time(average_time_seconds)
        self.user_joins_df = self.user_joins_df.query('day > "2024-01-04"')
        earliest_time_joined = self.user_joins_df.loc[self.user_joins_df['time'].idxmin(), ['name', 'day', 'time']]
        times = f"\n\n**Times**" \
                f"\n\tAverage time joined: **{average_time}**" \
                f"\n\tEarliest time joined: **{earliest_time_joined['time']}** on **{earliest_time_joined['day']}**"
        return times

    @staticmethod
    def __time_to_seconds(t):
        return (t.hour * 60 + t.minute) * 60 + t.second

    @staticmethod
    def __seconds_to_time(sec):
        return str(timedelta(seconds=sec))


class ProfilePoints(Profile):

    def __init__(self, data):
        super().__init__(data)
        self.user_points_df = data[0]
        self.__points = ''

    def generate(self):
        average_points_per_day = self.user_points_df['total_points'].mean()
        self.__points = f"\n\n**Points**" \
                        f"\n\tAverage points per day: **{average_points_per_day:.2f}**" \

        weekday_query = 'weekday != "Saturday" and weekday != "Sunday"'
        self.__set_points_per_day(weekday_query, day_order=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])

        weekend_query = 'weekday == "Saturday" or weekday == "Sunday"'
        self.__set_points_per_day(weekend_query, day_order=['Saturday', 'Sunday'])
        return self.__points

    def __set_points_per_day(self, query, day_order):
        points_df = self.user_points_df.query(query)
        average_daily_points = points_df['total_points'].mean()
        self.__points += f"\n\t\tAverage points per weekday: **{average_daily_points:.2f}**"
        average_points_per_day = points_df.groupby('weekday').agg(
            {'total_points': 'mean'})
        average_points_per_day = average_points_per_day.loc[day_order, :].reset_index()

        for row in average_points_per_day.iterrows():
            self.__points += f"\n\t\t\t{row[1]['weekday']}: **{row[1]['total_points']:.2f}**"


class ProfileFactory:
    profile_segments = {
        'days': ProfileDays,
        'wins': ProfileWins,
        'times': ProfileTimes,
        'points': ProfilePoints
    }

    def create(self, name, data):
        return self.profile_segments[name](data)
