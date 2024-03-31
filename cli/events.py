import pandas as pd

from cli.main import bot, walk_constants, database as db, bot_constants
from src.tasks import determine_daily_winner, determine_monthly_winner, draw_card
from src.util import _get_current_time, append_to_database, log_and_upload, download


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    determine_daily_winner.start()
    determine_monthly_winner.start()
    draw_card.start()


@bot.event
async def on_voice_state_update(member, before, after):
    # global walk_ended, length_of_walk_in_minutes, max_on_time_points, max_duration_points, start_hour, end_hour

    # if member.voice is not None and member.voice.self_mute:
    #     print(f'{member.name} is muted')
    #     return
    current_time, pacific_time = _get_current_time()
    # pacific_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S.%f")
    walk_hour_condition = pacific_time.hour >= walk_constants.START_HOUR and pacific_time.hour < walk_constants.END_HOUR

    if walk_constants.WALK_ENDED:
        points = pd.read_sql('SELECT day FROM points ORDER BY day DESC LIMIT 1', db.connection)
        current_day = str(pacific_time.date())
        walk_day = str(points.values[0][0])
        if current_day != walk_day and walk_hour_condition:
            walk_ended = False
            print('New walk starting')
            download()
        else:
            print('Walk already ended')
            return

    # Check if the time is between 7am and 9am in Pacific timezone
    if walk_hour_condition:
        if after.channel is not None and after.channel.name == bot_constants.VOICE_CHANNEL:
            # Get current time in UTC
            join_time, _ = _get_current_time()
            append_to_database(member, after, join_time, joined=True)
            log_and_upload(member, join_time, True)
            await member.send(f"Welcome to The Walk™. You joined Larry\'s Gym within the proper time frame.")
        if before.channel is not None and before.channel.name == bot_constants.VOICE_CHANNEL:
            leave_time, _ = _get_current_time()

            append_to_database(member, before, leave_time, joined=False)
            log_and_upload(member, leave_time, False)
    elif after.channel is not None and after.channel.name == bot_constants.VOICE_CHANNEL:
        await member.send(
            f"Sorry buckaroo, you joined Larry\'s Gym at {current_time}. The Walk™ is only between "
            f"{walk_constants.START_HOUR}:00 and {walk_constants.END_HOUR}:00 Pacific time.")
