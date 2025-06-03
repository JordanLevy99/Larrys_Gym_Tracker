import pandas as pd
from discord.ext import commands

from src.util import (
    download,
    _get_current_time,
    log_data,
    upload,
    append_to_database,
    append_mute_event,
)


class LarrysEvents(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'We have logged in as {self.bot.discord_client.user}')
        self.bot.discord_client.cogs['LarrysTasks'].determine_daily_winner.start()
        self.bot.discord_client.cogs['LarrysTasks'].determine_monthly_winner.start()
        self.bot.discord_client.cogs['LarrysTasks'].check_freethrow_logs.start()
        self.bot.discord_client.cogs['ExerciseCog'].exercise_of_the_day.start()
        self.bot.discord_client.cogs['LarrysNewsCogs'].get_daily_news.start()
        self.bot.discord_client.cogs['YearInReview'].check_year_end.start()
        download(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
        download(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)
        print(pd.read_sql_query("SELECT * FROM voice_log", self.bot.database.connection).tail())
        self.bot.discord_client.cogs['LarrysTasks'].initialize_new_users.start()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.self_mute != after.self_mute:
            await self.__log_mute_event(member, before, after)

        print(f'here are the bot constants again: {self.bot.bot_constants.__dict__}')
        current_time, pacific_time = _get_current_time()
        
        # Determine if it's a weekend
        is_weekend = pacific_time.weekday() >= 5
        start_hour = self.bot.walk_constants.WEEKEND_START_HOUR if is_weekend else self.bot.walk_constants.START_HOUR
        end_hour = start_hour + 2
        
        walk_hour_condition = (start_hour <= pacific_time.hour < end_hour)

        if self.bot.walk_constants.WALK_ENDED:
            await self.__check_to_start_new_walk(member, pacific_time, walk_hour_condition)

        # Check if the time is between start_hour and end_hour in Pacific timezone
        if walk_hour_condition:
            if self.__voice_channel_status_changed(after):
                await self.__log_voice_channel_event(after, member, joined=True)
                await member.send(f"Welcome to The Walk™. You joined Larry\'s Gym within the proper time frame.")
            if self.__voice_channel_status_changed(before):
                await self.__log_voice_channel_event(before, member, joined=False)
        elif self.__voice_channel_status_changed(after):
            day_type = "weekend" if is_weekend else "weekday"
            await member.send(
                f"Sorry buckaroo, you joined Larry\'s Gym at {current_time}. The Walk™ is only between "
                f"{start_hour}:00 and {end_hour}:00 Pacific time on {day_type}s.")

    def log_and_upload(self, member, event_time, joining):
        if self.bot.args.verbose:
            log_data(self.bot.database, member, event_time, joining)
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    def __voice_channel_status_changed(self, event):
        return event.channel is not None and event.channel.name == self.bot.bot_constants.VOICE_CHANNEL

    async def __log_voice_channel_event(self, event, member, joined):
        current_time, _ = _get_current_time()
        append_to_database(self.bot.database, member, event, current_time, joined)
        self.log_and_upload(member, current_time, joined)

    async def __log_mute_event(self, member, before, after):
        current_time, _ = _get_current_time()
        channel = after.channel or before.channel
        channel_name = channel.name if channel else "Unknown"
        muted = after.self_mute
        append_mute_event(self.bot.database, member, current_time, channel_name, muted)
        status = "muted" if muted else "unmuted"
        print(f"{member.name} {status} in {channel_name} at {current_time}")

    async def __check_to_start_new_walk(self, member, pacific_time, walk_hour_condition):
        points = pd.read_sql('SELECT day FROM points ORDER BY day DESC LIMIT 1', self.bot.database.connection)
        current_day = str(pacific_time.date())
        walk_day = str(points.values[0][0])
        if current_day != walk_day and walk_hour_condition:
            self.bot.walk_constants.WALK_ENDED = False
            print('New walk starting')
            download(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
            download(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)
        else:
            print('Walk already ended')
            await member.send('The walk has already ended for today. Please join tomorrow.')
