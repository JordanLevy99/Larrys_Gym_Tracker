import asyncio
import random
import time
from datetime import datetime, timedelta

import pytz
import pandas as pd
from tabulate import tabulate

import discord
from discord.ext import commands, tasks

# from src.bot import LarrysBot
# from src.tasks import LarrysTasks
# from cli.main import database as db
# from src.bot import LarrysBot
# from cli.main import bot, bot_constants, walk_constants, database as db, download
from src.types import BotConstants, WalkArgs, Songs
# from src.tasks import determine_daily_winner
from src.util import _process_query, _get_current_time, upload, download, calculate_points, play_song, determine_winner, \
    append_to_database, log_and_upload


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



class LarrysCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start_time(self, ctx, start_time: int):
        # global start_hour, end_hour, winner_hour
        start_hour = start_time
        winner_hour = start_time
        end_hour = start_time + 2
        await ctx.send(f'Walk start time set to {start_hour}:00 Pacific time for today...')


    @commands.command()
    async def determine_daily_winner_backup(self, ctx):
        await self.determine_daily_winner()


    # @commands.command()
    # async def disconnect(ctx):
    #     voice_client = bot.voice_clients[0]
    #     await voice_client.disconnect(force=True)


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
    async def end_walk(self, ctx):
        if not self.bot.walk_constants.WALK_ENDED:
            current_time, _ = _get_current_time()
            await self.update_points(ctx, current_time)
            self.bot.bot_constants.WALK_ENDED = True


    @commands.command()
    async def drop_points(self, ctx):
        self.bot.database.cursor.execute("DROP TABLE points")
        self.bot.database.connection.commit()
        upload()


    @commands.command()
    async def delete_all_points(self, ctx):
        self.bot.database.cursor.execute("DELETE FROM points")
        self.bot.database.connection.commit()
        upload()
        # await ctx.send(f'Dropped points table...')


    @commands.command()
    async def download_db(self, ctx):
        download(BotConstants.DB_FILE)
        # await ctx.send(f'Downloaded {bot_constants.DB_FILE} from Google Drive!')


    @commands.command()
    async def upload_db(self, ctx):
        upload()
        print(f'Uploaded {BotConstants.DB_FILE} to Dropbox!')
        # await ctx.send(f'Uploaded {bot_constants.DB_FILE} to Google Drive!')


    @commands.command()
    async def leaderboard(self, ctx, *args):
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
        leaderboard_df = pd.read_sql_query(leaderboard_query, self.bot.database.connection)
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
        calculate_points(daily_voice_log_df, users_durations)
        print(pd.read_sql_query("""SELECT * FROM points""", self.database.connection).tail())
        await self.leaderboard(ctx, 'WEEKLY')
        await ctx.send('Getting Today\'s On Time Leaderboard')
        await self.leaderboard(ctx, 'on time today')
        upload()

    @tasks.loop(hours=24)
    async def determine_monthly_winner(self):
        _, pacific_time = _get_current_time()
        if pacific_time.day == 1:
            voice_channel = self.bot.discord_client.get_channel(BotConstants.VOICE_CHANNEL_ID)

            if voice_channel and len(voice_channel.members) >= 1:
                try:
                    voice_client = await voice_channel.connect()
                except discord.errors.ClientException:
                    print(
                        f'Already connected to a voice channel.')

                voice_client = self.bot.discord_client.voice_clients[0]
                leaderboard_query = """
                        SELECT name, SUM(points_awarded) AS total_points
                        FROM points
                        WHERE day >= date('now', '-1 month')
                        GROUP BY name
                        ORDER BY total_points DESC
                        LIMIT 1
                    """
                leaderboard_df = pd.read_sql_query(leaderboard_query, self.bot.database.connection)
                winner = leaderboard_df.iloc[0]
                if winner.empty:
                    print('No winner found')
                    await voice_channel.disconnect()
                    return
                # winner_args = winner_songs[winner['name']]
                text_channel = self.bot.discord_client.get_channel(BotConstants.TEXT_CHANNEL_ID)

                await text_channel.send(
                    f"Congrats to dinkstar for winning the month of January with {round(winner['total_points'])} points!\nhttps://www.youtube.com/watch?v=veb4_RB01iQ&ab_channel=KB8")
                await play_song(voice_client, f'data/songs/speech.wav', self.bot.backend_client, 5, 0, False)
                await play_song(voice_client, f'data/songs/all_of_the_lights.mp3', self.bot.backend_client, 14, 0, True)

    @tasks.loop(hours=24)
    async def draw_card(self):
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

        # # Create a deck of cards
        # deck = [f'{rank}{suit}' for suit in suits for rank in ranks]

        # # Draw a random card from the deck
        # card = random.choice(deck)

        # Unicode for playing cards
        suit = random.choice(suits)
        rank = random.choice(ranks)
        suit_str = f"\_\_\_\_\_\n|{suit}      |\n|    {rank}    |\n|      {suit}|\n\_\_\_\_\_"

        text_channel = self.bot.discord_client.get_channel(BotConstants.TEXT_CHANNEL_ID)
        await text_channel.send("Card of the day is:\n" + suit_str)

    @tasks.loop(hours=24)
    async def determine_daily_winner(self):
        voice_channel = self.bot.discord_client.get_channel(BotConstants.VOICE_CHANNEL_ID)

        if voice_channel and len(voice_channel.members) >= 1:
            try:
                voice_client = await voice_channel.connect()
            except discord.errors.ClientException:
                print(
                    f'Already connected to a voice channel.')

            voice_client = self.bot.discord_client.voice_clients[0]
            winner = await determine_winner(self.bot.database)
            if winner.empty:
                print('No winner found')
                await voice_channel.disconnect()
                return
            winner_args = Songs.WINNER[winner['name']]
            random_winner_args = random.choice(winner_args)
            _, pacific_time = _get_current_time()
            current_date = pacific_time.date()
            # TODO: get these values from the `birthday_args` dictionary
            try:
                current_birthday = Songs.BIRTHDAY[(current_date.month, current_date.day)]
                birthday_name, birthday_link = current_birthday
                duration = 73
                if birthday_name == 'ben':
                    duration = 49
                text_channel = self.bot.discord_client.get_channel(BotConstants.TEXT_CHANNEL_ID)
                await text_channel.send(f'Happy Birthday {birthday_name.capitalize()}!\n{birthday_link}')
                await play_song(voice_client, f'data/songs/happy_birthday_{birthday_name}.mp3',
                                self.bot.backend_client, duration, 0, disconnect_after_song=False)

                time.sleep(2)
            except KeyError:
                pass
            await play_song(voice_client, f'data/songs/{random_winner_args[0]}', self.bot.backend_client,
                            random_winner_args[1], random_winner_args[2])
        else:
            print('not enough people in the vc')

    @determine_daily_winner.before_loop
    async def before_determine_daily_winner(self):
        now = datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.replace(now, hour=WalkArgs.WINNER_HOUR, minute=WalkArgs.WINNER_MINUTE, second=0,
                                       microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Waiting until', target_time)
        print(f'wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @draw_card.before_loop
    async def before_draw_card(self):
        now = datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.replace(now, hour=6, minute=45, second=0, microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Drawing card at', target_time)
        print(f'wait time for draw card: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @determine_monthly_winner.before_loop
    async def before_determine_monthly_winner(self):
        now = datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.replace(now, hour=WalkArgs.WINNER_HOUR, minute=WalkArgs.WINNER_MINUTE - 1, second=0,
                                       microsecond=0)
        if now > target_time:
            target_time += timedelta(days=1)
        print('Monthly winner determined at', target_time)
        print(f'wait time for monthly winner check: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'We have logged in as {self.bot.discord_client.user}')
        self.determine_daily_winner.start()
        self.determine_monthly_winner.start()
        self.draw_card.start()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # global walk_ended, length_of_walk_in_minutes, max_on_time_points, max_duration_points, start_hour, end_hour

        # if member.voice is not None and member.voice.self_mute:
        #     print(f'{member.name} is muted')
        #     return
        current_time, pacific_time = _get_current_time()
        # pacific_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S.%f")
        walk_hour_condition = (pacific_time.hour >= self.bot.walk_constants.START_HOUR and
                               pacific_time.hour < self.bot.walk_constants.END_HOUR)

        if self.bot.walk_constants.WALK_ENDED:
            points = pd.read_sql('SELECT day FROM points ORDER BY day DESC LIMIT 1', self.bot.database.connection)
            current_day = str(pacific_time.date())
            walk_day = str(points.values[0][0])
            if current_day != walk_day and walk_hour_condition:
                self.bot.walk_constants.WALK_ENDED = False
                print('New walk starting')
                download()
            else:
                print('Walk already ended')
                return

        # Check if the time is between 7am and 9am in Pacific timezone
        if walk_hour_condition:
            if after.channel is not None and after.channel.name == self.bot.bot_constants.VOICE_CHANNEL:
                # Get current time in UTC
                join_time, _ = _get_current_time()
                append_to_database(member, after, join_time, joined=True)
                log_and_upload(member, join_time, True)
                await member.send(f"Welcome to The Walk™. You joined Larry\'s Gym within the proper time frame.")
            if before.channel is not None and before.channel.name == self.bot.bot_constants.VOICE_CHANNEL:
                leave_time, _ = _get_current_time()

                append_to_database(member, before, leave_time, joined=False)
                log_and_upload(member, leave_time, False)
        elif after.channel is not None and after.channel.name == self.bot.bot_constants.VOICE_CHANNEL:
            await member.send(
                f"Sorry buckaroo, you joined Larry\'s Gym at {current_time}. The Walk™ is only between "
                f"{self.bot.walk_constants.START_HOUR}:00 and {self.bot.walk_constants.END_HOUR}:00 Pacific time.")

# bot.run(bot_constants.TOKEN)
