import pandas as pd
from discord.ext import commands

from src.util import download, _get_current_time, log_data, upload, append_to_database


class LarrysEvents(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'We have logged in as {self.bot.discord_client.user}')
        self.bot.discord_client.cogs['LarrysTasks'].determine_daily_winner.start()
        self.bot.discord_client.cogs['LarrysTasks'].determine_monthly_winner.start()
        self.bot.discord_client.cogs['ExerciseCog'].exercise_of_the_day.start()
        # self.bot.discord_client.cogs['LarrysNewsCogs'].get_daily_news.start()
        download(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
        download(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)
        print(pd.read_sql_query("SELECT * FROM voice_log", self.bot.database.connection).tail())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # TODO: implement mute checker/logging
        # if member.voice is not None and member.voice.self_mute:
        #     print(f'{member.name} is muted')
        #     return
        print(f'here are the bot constants again: {self.bot.bot_constants.__dict__}')
        current_time, pacific_time = _get_current_time()
        walk_hour_condition = (
                    self.bot.walk_constants.START_HOUR <= pacific_time.hour < self.bot.walk_constants.END_HOUR)

        if self.bot.walk_constants.WALK_ENDED:
            await self.__check_to_start_new_walk(member, pacific_time, walk_hour_condition)

        # Check if the time is between 7am and 9am in Pacific timezone
        if walk_hour_condition:
            if self.__voice_channel_status_changed(after):
                await self.__log_voice_channel_event(after, member, joined=True)
                await member.send(f"Welcome to The Walk™. You joined Larry\'s Gym within the proper time frame.")
            if self.__voice_channel_status_changed(before):
                await self.__log_voice_channel_event(before, member, joined=False)
        elif self.__voice_channel_status_changed(after):
            await member.send(
                f"Sorry buckaroo, you joined Larry\'s Gym at {current_time}. The Walk™ is only between "
                f"{self.bot.walk_constants.START_HOUR}:00 and {self.bot.walk_constants.END_HOUR}:00 Pacific time.")

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
