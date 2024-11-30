import asyncio
import datetime
from typing import Dict, List
import pandas as pd
import pytz
from discord.ext import commands, tasks
from tabulate import tabulate

class YearInReview(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = bot.openai_client
        self.db = bot.database
        self.stock_db = bot.stock_exchange_database

    @tasks.loop(hours=24)
    async def check_year_end(self):
        """Check if it's the end of the year to send year in review"""
        now = datetime.datetime.now(pytz.timezone('US/Pacific'))
        print(f"\n=== Checking Year End Review ({now}) ===")
        if now.month == 12 and now.day == 1:
            print("🎉 It's time for year end review!")
            await self.send_year_in_review()
        else:
            print(f"Not yet time for year end review. Waiting for 11/30 (current: {now.month}/{now.day})")

    async def send_year_in_review(self):
        """Send year in review to all walkers"""
        print("\n=== Starting Year In Review Distribution ===")
        guild = self.bot.discord_client.get_guild(self.bot.bot_constants.GUILD_ID)
        if not guild:
            print(f"❌ Could not find guild with ID: {self.bot.bot_constants.GUILD_ID}")
            return
            
        walkers = [member for member in guild.members if any(role.name == 'Walker' for role in member.roles)]
        
        print(f"Found {len(walkers)} walkers to process")
        
        for walker in walkers:
            print(f"\n📊 Processing review for {walker.name} (ID: {walker.id})")
            try:
                review = await self.generate_user_review(walker.id, walker.name)
                print(f"Successfully generated review for {walker.name}")
                print(review)
                await walker.send(review)
                print(f"✅ Sent review to {walker.name}")
            except Exception as e:
                print(f"❌ Error processing {walker.name}: {e}")
                import traceback
                print(traceback.format_exc())

    async def generate_user_review(self, user_id: int, username: str) -> str:
        """Generate personalized year in review for a user"""
        stats = await self.gather_user_stats(user_id, username)
        return await self.format_review(stats, username)

    async def gather_user_stats(self, user_id: int, username: str) -> Dict:
        """Gather all relevant stats for a user's year in review"""
        print(f"\n=== Gathering Stats for {username} ===")
        year = datetime.datetime.now().year
        
        try:
            # Get profile text
            profile_text = await self.bot.discord_client.cogs['ProfileCommands'].get_profile_text(user_id, username)
            print(f"Got profile text for {username}")
            
            walk_stats = self._get_walk_stats(user_id, year)
            print(f"Walk stats: {walk_stats}")
            
            stock_stats = self._get_stock_stats(user_id, year)
            print(f"Stock stats: {stock_stats}")
            
            exercise_stats = self._get_exercise_stats(user_id, year)
            print(f"Exercise stats: {exercise_stats}")
            
            sleep_stats = self._get_sleep_stats(user_id, year)
            print(f"Sleep stats: {sleep_stats}")
            
            freethrow_stats = self._get_freethrow_stats(user_id, year)
            print(f"Freethrow stats: {freethrow_stats}")
            
            achievements = self._calculate_achievements(user_id, year)
            print(f"Achievements: {achievements}")
            
            stats = {
                "username": username,
                "current_year": year,
                "profile_text": profile_text,
                "walk_stats": walk_stats,
                "stock_stats": stock_stats,
                "exercise_stats": exercise_stats,
                "sleep_stats": sleep_stats,
                "freethrow_stats": freethrow_stats,
                "achievements": achievements
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ Error gathering stats for {username}: {e}")
            import traceback
            print(traceback.format_exc())
            raise
    
    @check_year_end.before_loop
    async def before_check_year_end(self):
        await self.bot.discord_client.wait_until_ready()
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now,
                                                hour=self.bot.walk_constants.WINNER_HOUR,
                                                minute=0,
                                                second=0,
                                                microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        print('Waiting to check for year end until', target_time)
        print(f'wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    def _get_walk_stats(self, user_id: int, year: int) -> Dict:
        """Get walking statistics for the year"""
        print(f"Getting walk stats for user {user_id}, year {year}")
        query = f"""
        SELECT 
            COUNT(DISTINCT day) as total_walks,
            SUM(points_awarded) as total_points,
            AVG(points_awarded) as avg_points
        FROM points 
        WHERE id = ? 
        AND strftime('%Y', day) = ?
        """
        print(f"Executing query: {query}")
        self.db.cursor.execute(query, (str(user_id), str(year)))
        result = self.db.cursor.fetchone()
        print(f"Raw walk stats result: {result}")
        
        stats = {
            "total_walks": result[0],
            "total_points": round(result[1] if result[1] else 0, 2),
            "avg_points": round(result[2] if result[2] else 0, 2)
        }
        print(f"Processed walk stats: {stats}")
        return stats

    def _get_stock_stats(self, user_id: int, year: int) -> Dict:
        """Get stock trading statistics for the year"""
        query = f"""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN transaction_type = 'buy' THEN 1 ELSE 0 END) as buys,
            SUM(CASE WHEN transaction_type = 'sell' THEN 1 ELSE 0 END) as sells
        FROM Transactions
        WHERE user_id = ? 
        AND strftime('%Y', transaction_date) = ?
        """
        self.stock_db.cursor.execute(query, (user_id, str(year)))
        result = self.stock_db.cursor.fetchone()
        
        return {
            "total_trades": result[0],
            "buys": result[1],
            "sells": result[2],
            "current_portfolio_value": self._get_current_portfolio_value(user_id)
        }

    def _get_exercise_stats(self, user_id: int, year: int) -> Dict:
        """Get exercise statistics for the year"""
        query = """
        SELECT exercise, COUNT(*) as count
        FROM exercise_log
        WHERE id = ? 
        AND strftime('%Y', time) = ?
        GROUP BY exercise
        ORDER BY count DESC
        """
        self.db.cursor.execute(query, (str(user_id), str(year)))
        exercises = self.db.cursor.fetchall()
        
        return {
            "total_exercises": sum(ex[1] for ex in exercises),
            "favorite_exercise": exercises[0][0] if exercises else None,
            "exercise_breakdown": dict(exercises)
        }

    def _get_sleep_stats(self, user_id: int, year: int) -> Dict:
        """Get sleep statistics for the year"""
        query = """
        SELECT 
            AVG(hours_slept) as avg_sleep,
            MAX(hours_slept) as max_sleep,
            MIN(hours_slept) as min_sleep
        FROM sleep_log
        WHERE user_id = ? 
        AND strftime('%Y', date) = ?
        """
        self.db.cursor.execute(query, (str(user_id), str(year)))
        result = self.db.cursor.fetchone()
        
        return {
            "avg_sleep": round(result[0], 2) if result[0] else 0,
            "max_sleep": result[1],
            "min_sleep": result[2]
        }

    def _get_freethrow_stats(self, user_id: int, year: int) -> Dict:
        """Get freethrow statistics for the year"""
        query = """
        SELECT 
            SUM(number_made) as made,
            SUM(number_attempted) as attempted
        FROM freethrows
        WHERE id = ? 
        AND strftime('%Y', date) = ?
        """
        self.db.cursor.execute(query, (str(user_id), str(year)))
        result = self.db.cursor.fetchone()
        
        return {
            "total_made": result[0] if result[0] else 0,
            "total_attempted": result[1] if result[1] else 0,
            "percentage": round((result[0] / result[1] * 100), 2) if result[1] else 0
        }

    def _calculate_achievements(self, user_id: int, year: int) -> List[str]:
        """Calculate special achievements for the year"""
        achievements = []
        
        # Example achievement calculations
        if self._get_walk_stats(user_id, year)["total_walks"] >= 150:
            achievements.append("🏆 Dedicated Walker: Completed 150+ walks")
        
        if self._get_freethrow_stats(user_id, year)["percentage"] >= 70:
            achievements.append("🏀 Sharpshooter: 70%+ freethrow accuracy")
            
        return achievements

    def _get_current_portfolio_value(self, user_id: int) -> float:
        """Calculate current portfolio value"""
        stocks = self.stock_db.get_user_stocks(user_id)
        return sum(quantity * price for _, _, quantity, _, price in stocks)

    async def format_review(self, stats: Dict, username: str) -> str:
        """Format the year in review with OpenAI-generated commentary"""
        print(f"\n=== Formatting Review for {username} ===")
        
        # Create a basic summary for OpenAI to enhance
        basic_summary = self._create_basic_summary(stats)
        print("Generated basic summary:")
        print(basic_summary)
        
        try:
            print("Requesting OpenAI commentary...")
            prompt = f"""
            Given this user's year in review data for Larry's Gym for the year {stats['current_year']}:
            
            {basic_summary}
            
            Additional All-Time Profile Stats:
            {stats['profile_text']}
            
            Create a fun, engaging summary in the style of Spotify Wrapped, but don't mention Spotify. Address the user in the second person. The review is called "Larry's Gym Year in Review".

            Be creative, witty, and personal. Include specific numbers but make them interesting.
            Keep it concise but entertaining. Use emojis.
            
            Make sure to highlight their all-time stats and achievements, especially their win rates and participation history, including any notable  streaks!

            Remember that the current year is {stats['current_year']}!
            """
            
            response = self.bot.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are creating a fun year-in-review summary."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            formatted_review = response.choices[0].message.content
            print("Successfully generated OpenAI response")
            print("Final formatted review:")
            print(formatted_review)
            return formatted_review
            
        except Exception as e:
            print(f"❌ Error formatting review with OpenAI: {e}")
            import traceback
            print(traceback.format_exc())
            # Fallback to basic summary if OpenAI fails
            print("Falling back to basic summary due to error")
            return basic_summary

    def _create_basic_summary(self, stats: Dict) -> str:
        """Create a basic summary of the stats"""
        return f"""
📊 Year in Review for {stats['username']} 📊

🚶 Walk Stats:
• {stats['walk_stats']['total_walks']} total walks
• {stats['walk_stats']['total_points']} points earned
• {stats['walk_stats']['avg_points']} average points per walk

💰 Stock Trading:
• {stats['stock_stats']['total_trades']} total trades
• Portfolio value: ${stats['stock_stats']['current_portfolio_value']:,.2f}

💪 Exercise:
• {stats['exercise_stats']['total_exercises']} exercises completed
• Favorite: {stats['exercise_stats']['favorite_exercise']}

😴 Sleep:
• {stats['sleep_stats']['avg_sleep']} hours average sleep
• Best sleep: {stats['sleep_stats']['max_sleep']} hours

🏀 Freethrows:
• {stats['freethrow_stats']['total_made']}/{stats['freethrow_stats']['total_attempted']} ({stats['freethrow_stats']['percentage']}%)

🏆 Achievements:
{chr(10).join(stats['achievements'])}
"""
