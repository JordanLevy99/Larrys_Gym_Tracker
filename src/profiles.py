import datetime
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import discord
import pandas as pd
import pytz
from discord.ext import commands
from discord.utils import get


class ProfileCommands(commands.Cog):

    sections = ['days', 'streaks', 'wins', 'times', 'points', 'freethrows', 'sleep']
    def __init__(self, bot):
        self.bot = bot
        self.__walkers = None
        self.__sections = ProfileCommands.sections
        self.__walk_start_date = datetime(2024, 1, 1, tzinfo=pytz.timezone('US/Pacific'))
        self.__total_number_of_days = self.__get_total_number_of_days()

    def __get_total_number_of_days(self):
        return (datetime.now(tz=pytz.timezone('US/Pacific')) - self.__walk_start_date).days

    @commands.command()
    async def profile(self, ctx, *args):
        query = ' '.join(args)
        name = self.__parse_query(query)
        self.__walkers = discord.utils.get(ctx.guild.roles, name='Walker').members
        if name != '' and not get(self.__walkers, name=name) and name not in self.__sections:
            await ctx.send(f"**{name}** is not a walker")
            return
        self.__total_number_of_days = self.__get_total_number_of_days()
        member = get(self.__walkers, name=name) or ctx.author
        winner_df = self.__get_winner_df()
        user_joins_df = self.__get_user_joins_df(member.name)
        user_exercise_df = self.__get_user_exercise_df(member.name)
        user_points_df = self.__get_user_points_df(member.name)
        user_freethrows_df = self.__get_user_freethrows_df(member.name)
        user_sleep_df = self.__get_user_sleep_df(member.name)
        profile_data = {
            'days': (user_joins_df, self.__total_number_of_days),
            'streaks': (user_joins_df, user_exercise_df, winner_df.query(f'name == "{member.name}"')),
            'wins': (winner_df, len(user_joins_df), member, self.__total_number_of_days),
            'times': (user_joins_df,),
            'points': (user_points_df,),
            'freethrows': (user_freethrows_df, member.name),
            'sleep': (user_sleep_df, member.name)
        }
        profile = ''
        print(self.__sections)
        for section in self.__sections:
            profile += ProfileFactory().create(section, profile_data[section]).generate()
        await ctx.send(profile)

    def __parse_query(self, query):
        self.__sections = ProfileCommands.sections  # resets state for sections
        query = query.split()
        self.__validate_preconditions(query)
        name = self.__set_name(query)
        self.__set_sections(name, query)
        return name

    def __validate_preconditions(self, query):
        if len(query) > len(self.__sections) + 1:
            raise ValueError('Too many arguments')

    def __set_name(self, query):
        return query[0] if query and query[0] not in self.__sections else ''

    def __set_sections(self, name, query):
        if len(query) > 1 and name == query[0]:
            self.__sections = query[1:]
        elif name == '' and query:
            self.__sections = query

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

    def __get_user_exercise_df(self, name):
        user_exercise_df = pd.read_sql_query(f"""
                                        SELECT name, MIN(time) as 'time', day
                                        FROM (
                                            SELECT name, time, DATE(time) as 'day'
                                            FROM exercise_log
                                            )
                                        WHERE name = '{name}'
                                        GROUP BY name, day
                                        """, self.bot.database.connection)
        user_exercise_df['time'] = user_exercise_df['time'].apply(
            lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'))
        user_exercise_df['time'] = user_exercise_df['time'].apply(lambda x: x.time())
        user_exercise_df = user_exercise_df.groupby(['name', 'day']).agg({'time': 'min'}).reset_index()
        return user_exercise_df

    @staticmethod
    def __get_earliest_time_joined(user_joins_df):
        user_joins_df = user_joins_df.query('day > "2024-01-04"')
        min_time_joined = user_joins_df.loc[user_joins_df['time'].idxmin(), ['name', 'day', 'time']]
        earliest_time_joined = f'Earliest time joined: **{min_time_joined["time"]}** on **{min_time_joined["day"]}**'
        return earliest_time_joined

    def __get_user_freethrows_df(self, name):
        return pd.read_sql_query(f"""
            SELECT date, number_made, number_attempted
            FROM freethrows
            WHERE name = '{name}'
            ORDER BY date DESC
        """, self.bot.database.connection)

    def __get_user_sleep_df(self, name):
        return pd.read_sql_query(f"""
            SELECT date, hours_slept
            FROM sleep_log
            WHERE name = '{name}'
            ORDER BY date DESC
        """, self.bot.database.connection)


class Profile(ABC):

    def __init__(self, data):
        pass

    @abstractmethod
    def generate(self):
        pass


class ProfileDays(Profile):

    def __init__(self, data):
        super().__init__(data)
        self.user_joins_df, self.__total_number_of_days = data[0], data[1]
        self.days_joined = len(self.user_joins_df)

    def generate(self):
        number_of_days_joined = f'Number of days joined: **{self.days_joined}** out of **{self.__total_number_of_days}** possible days'
        percentage_days_joined = f'Percentage of days joined: **{self.days_joined / self.__total_number_of_days * 100:.2f}%**'
        days = f"\n\n**Days**" \
               f"\n\t{number_of_days_joined}" \
               f"\n\t{percentage_days_joined}"
        return days


class ProfileStreaks(Profile):

    def __init__(self, data):
        super().__init__(data)
        self.streaks = [StreakGenerator(data[0], 'days'), StreakGenerator(data[1], 'exercise'),
                        StreakGenerator(data[2], 'wins')]

    def generate(self):
        streaks = ''
        for streak in self.streaks:
            try:
                streaks += streak.generate()
            except ValueError:
                pass
            streaks += '\n'
        streaks = streaks.rstrip('\n')
        return f"\n\n**Streaks**" \
               f"{streaks}"


class StreakGenerator:

    def __init__(self, data: pd.DataFrame, name: str):
        self.data = data
        self.name = name
        self.__streak_day_counts = pd.DataFrame()

    def generate(self):
        self.__get_days_in_a_row()
        longest_streak = self.__get_longest_streak()
        latest_streak = self.__get_latest_streak()
        return f"\n\t{longest_streak}" \
               f"\n\t{latest_streak}"

    def __get_longest_streak(self):
        max_days_in_a_row = self.__streak_day_counts.max()
        range_of_days = self.__get_range_of_days(self.__streak_day_counts.idxmax())
        return self.get_streak_text('Longest', max_days_in_a_row, range_of_days)

    def __get_latest_streak(self):
        latest_streak_idx = self.__streak_day_counts.index[-1]
        latest_days_in_a_row = self.__streak_day_counts.loc[latest_streak_idx]
        range_of_days = self.__get_range_of_days(latest_streak_idx)
        return self.get_streak_text('Latest', latest_days_in_a_row, range_of_days)

    def get_streak_text(self, streak_type, days_in_a_row, range_of_days):
        return f'{streak_type} {self.name.capitalize()} streak: **{days_in_a_row}** days in a row {range_of_days}'

    def __get_days_in_a_row(self):
        self.__get_streak_groups()
        self.__streak_day_counts = self.data.groupby('group')['day'].count()

    def __get_streak_groups(self):
        self.data['day'] = pd.to_datetime(self.data['day'])
        self.data['next_day'] = self.data['day'].shift(-1)
        self.data['next_day'] = self.data['next_day'].fillna(pd.to_datetime(datetime.now().date() + timedelta(days=1)))
        self.data['diff'] = (self.data['next_day'] - self.data['day']).dt.days
        self.data['is_consecutive'] = self.data['diff'] == 1
        self.data['is_consecutive_shifted'] = self.data['is_consecutive'].shift(fill_value=False)
        self.data['group'] = (~self.data['is_consecutive_shifted']).cumsum()

    def __get_range_of_days(self, group_idx):
        streak_days = self.data.query(f'group == {group_idx}')['day']
        return f'from **{streak_days.min().strftime("%B %d")}** to **{streak_days.max().strftime("%B %d")}**'


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
        try:
            average_points_per_day = average_points_per_day.loc[day_order, :].reset_index()
        except KeyError:
            pass

        for row in average_points_per_day.iterrows():
            self.__points += f"\n\t\t\t{row[1]['weekday']}: **{row[1]['total_points']:.2f}**"


class ProfileFreethrows(Profile):
    def __init__(self, data):
        super().__init__(data)
        self.user_freethrows_df = data[0]
        self.name = data[1]

    def generate(self):
        current_streak = self.__get_current_streak()
        total_made, total_attempted = self.__get_total_freethrows()
        percentage = (total_made / total_attempted * 100) if total_attempted > 0 else 0

        longest_streak, streak_start, streak_end = self.__get_longest_streak()
        freethrows = f"\n\n**Freethrows**" \
                     f"\n\tCurrent Freethrows Streak: **{current_streak}** days" \
                     f"\n\tLongest Freethrows Streak: **{longest_streak}** days (from **{streak_start}** to **{streak_end}**)" \
                     f"\n\tTotal Freethrows Made: **{total_made}** out of **{total_attempted}**" \
                     f"\n\tTotal Freethrow Percentage: **{percentage:.1f}%**" \
                     f"\n\tPersonal Record: **{self.__get_personal_record()}** freethrows made in a single day on **{self.__get_personal_record_date()}**\n\n"
        return freethrows
    
    def __get_personal_record(self):
        if self.user_freethrows_df.empty:
            return 0
        return self.user_freethrows_df['number_made'].max()
    
    def __get_personal_record_date(self):
        if self.user_freethrows_df.empty:
            return ""
        max_made = self.user_freethrows_df['number_made'].max()
        max_date = self.user_freethrows_df.loc[self.user_freethrows_df['number_made'] == max_made, 'date'].iloc[0]
        return max_date.strftime('%Y-%m-%d')
    
    def __get_longest_streak(self):
        if self.user_freethrows_df.empty:
            return 0

        self.user_freethrows_df['date'] = pd.to_datetime(self.user_freethrows_df['date']).dt.date
        self.user_freethrows_df = self.user_freethrows_df.sort_values('date')

        longest_streak = 0
        current_streak = 1
        prev_date = None

        for date in self.user_freethrows_df['date']:
            if prev_date is not None and (date - prev_date).days == 1:
                current_streak += 1
            else:
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
            prev_date = date

        longest_streak = max(longest_streak, current_streak)
        if longest_streak == 0:
            return longest_streak, "", ""
        
        streak_start = None
        streak_end = None
        current_streak = 1
        prev_date = None
        
        for date in self.user_freethrows_df['date']:
            if prev_date is not None and (date - prev_date).days == 1:
                current_streak += 1
                if current_streak == longest_streak:
                    streak_end = date
            else:
                if current_streak == longest_streak:
                    streak_start = prev_date - timedelta(days=longest_streak - 1)
                    break
                current_streak = 1
            prev_date = date
        
        if streak_start is None and current_streak == longest_streak:
            streak_start = prev_date - timedelta(days=longest_streak - 1)
            streak_end = prev_date
        
        return longest_streak, streak_start, streak_end


    def __get_current_streak(self):
        if self.user_freethrows_df.empty:
            return 0

        today = datetime.now(pytz.timezone('US/Pacific')).date()
        self.user_freethrows_df['date'] = pd.to_datetime(self.user_freethrows_df['date']).dt.date
        self.user_freethrows_df = self.user_freethrows_df.sort_values('date', ascending=False)

        streak = 0
        for i, row in self.user_freethrows_df.iterrows():
            if row['date'] == today - timedelta(days=streak):
                streak += 1
            else:
                break
        return streak

    def __get_total_freethrows(self):
        if self.user_freethrows_df.empty:
            return 0, 0
        total_made = self.user_freethrows_df['number_made'].sum()
        total_attempted = self.user_freethrows_df['number_attempted'].sum()
        return total_made, total_attempted

class ProfileSleep(Profile):
    def __init__(self, data):
        super().__init__(data)
        self.user_sleep_df = data[0]
        self.name = data[1]
        self.user_sleep_df['date'] = pd.to_datetime(self.user_sleep_df['date'])

    def generate(self):
        avg_sleep = self.__get_average_sleep()
        avg_sleep_week = self.__get_average_sleep(days=7)
        avg_sleep_month = self.__get_average_sleep(days=30)

        sleep_info = f"\n\n**Sleep**" \
                     f"\n\tAverage Sleep Duration: **{avg_sleep:.2f}** hours" \
                     f"\n\tAverage Sleep Duration (past week): **{avg_sleep_week:.2f}** hours" \
                     f"\n\tAverage Sleep Duration (past month): **{avg_sleep_month:.2f}** hours"
        return sleep_info

    def __get_average_sleep(self, days=None):
        if self.user_sleep_df.empty:
            return 0

        if days:
            cutoff_date = datetime.now(pytz.timezone('US/Pacific')) - timedelta(days=days)
            filtered_df = self.user_sleep_df[self.user_sleep_df['date'] > cutoff_date]
        else:
            filtered_df = self.user_sleep_df

        return filtered_df['hours_slept'].mean() if not filtered_df.empty else 0

class ProfileFactory:
    profile_segments = {
        'days': ProfileDays,
        'streaks': ProfileStreaks,
        'wins': ProfileWins,
        'times': ProfileTimes,
        'points': ProfilePoints,
        'freethrows': ProfileFreethrows,
        'sleep': ProfileSleep
    }

    def create(self, name, data):
        return self.profile_segments[name](data)
