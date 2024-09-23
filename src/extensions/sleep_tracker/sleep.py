import re
from datetime import datetime, timedelta
import pytz
from discord.ext import commands

class SleepTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def log_sleep(self, ctx, *args):
        """Log sleep hours in the database. Usage: !log_sleep [yesterday] <hours_slept>"""
        message_content = f"!log_sleep {' '.join(args)}"
        message = ctx.message
        message.content = message_content  # Temporarily modify the message content
        await self.process_sleep_log(message)

    async def process_sleep_log(self, message):
        pattern = r'!log_sleep(?:\s+(yesterday))?\s+(\d+(?:\.\d+)?)'
        match = re.match(pattern, message.content)
        
        if match:
            yesterday, hours_slept = match.groups()
            
            # Parse date
            if yesterday:
                date = message.created_at.astimezone(pytz.timezone('US/Pacific')) - timedelta(days=1)
            else:
                date = message.created_at.astimezone(pytz.timezone('US/Pacific'))
            
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            hours_slept = float(hours_slept)
            
            # Check if sleep has already been logged for this date
            if self.bot.database.sleep_exists(
                user_id=str(message.author.id),
                date=date.strftime('%Y-%m-%d')
            ):
                await message.add_reaction('⚠️')  # React to indicate duplicate entry
                await message.channel.send(f"{message.author.mention}, you've already logged sleep for this date.")
                return
            
            self.bot.database.log_sleep(
                message_id=str(message.id),
                date=date.strftime('%Y-%m-%d %H:%M:%S'),
                user_id=str(message.author.id),
                name=message.author.name,
                hours_slept=hours_slept
            )
            
            # Calculate and log sleep points
            points = self.calculate_sleep_points(hours_slept)
            self.bot.database.log_sleep_points(
                date=date.strftime('%Y-%m-%d %H:%M:%S'),
                user_id=str(message.author.id),
                name=message.author.name,
                points_type='time_slept',
                points=points
            )
            
            await message.add_reaction('✅')  # React to confirm logging
            # await message.channel.send(f"{message.author.mention} has logged {hours_slept} hours of sleep for {date.strftime('%Y-%m-%d')}.")
            # await message.channel.send(f"You have been awarded {points} sleep points on {date.strftime('%Y-%m-%d')}.")
            self.bot.database.upload()
        else:
            await message.add_reaction('❌')  # React to indicate an error
            await message.channel.send("Invalid format. Usage: !log_sleep [yesterday] <hours_slept>")

    def calculate_sleep_points(self, hours_slept):
        if hours_slept >= 8:
            return 50
        elif hours_slept <= 0:
            return 0
        else:
            return int((hours_slept / 8) * 50)

def setup(bot):
    bot.add_cog(SleepTracker(bot))
