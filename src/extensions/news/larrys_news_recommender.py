import asyncio
import datetime
from typing import List, Tuple, Dict
import pytz
from discord.ext import commands, tasks
from newsapi import NewsApiClient, const
import os
import pandas as pd
from collections import defaultdict

from src.util import upload

class NewsRecommenderEngine:
    def __init__(self, database, openai_client):
        self.database = database
        self.openai_client = openai_client
        
    def get_reaction_scores(self) -> pd.DataFrame:
        """Fetch and process reaction data from database"""
        query = """
        SELECT n.message_id, n.title, n.category, n.date, 
               SUM(CASE WHEN r.emoji = '👍' THEN r.count ELSE 0 END) as upvotes,
               SUM(CASE WHEN r.emoji = '👎' THEN r.count ELSE 0 END) as downvotes
        FROM daily_news n
        LEFT JOIN reactions r ON n.message_id = r.message_id
        GROUP BY n.message_id, n.title, n.category, n.date
        """
        return pd.read_sql_query(query, self.database.connection)
    
    def get_recommended_topic(self) -> str:
        """Use OpenAI to analyze reaction data and suggest a specific news topic"""
        df = self.get_reaction_scores()
        
        # Prepare the data for OpenAI analysis
        df['engagement_score'] = df['upvotes'] - df['downvotes']
        df = df.sort_values('engagement_score', ascending=False)
        
        # Create a summary of top performing articles
        top_articles = df.head(25)[['title', 'category', 'engagement_score']].to_string()
        
        prompt = f"""Based on these most engaged news articles and their reactions:

{top_articles}

Suggest a specific news topic (2-3 words) that would be interesting to this audience. 
Consider:
1. Topics that received positive engagement
2. Current trends related to popular categories
3. The general theme of well-received articles

Return only the suggested topic, nothing else. For example: "artificial intelligence", "space exploration", or "renewable energy"."""

        print(prompt)  
        response = self.openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a news topic recommender. Respond only with the suggested topic.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="gpt-4o",
            temperature=0.7
        )

        print(response)
        return response.choices[0].message.content.strip().lower()

class LarrysNewsRecommender:
    def __init__(self, database, openai_client):
        self.client = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        self.recommender_engine = NewsRecommenderEngine(database, openai_client)

    def get_news(self, topic=None, page_size=5, country='us') -> Tuple[str, List[dict]]:
        if topic is None:
            topic = self.recommender_engine.get_recommended_topic()
            
        news = self.client.get_everything(
            q=topic,
            language='en',
            page_size=page_size,
            sort_by='relevancy'
        )
        
        articles = news['articles']
        news_str = f'Today\'s recommended topic: {topic}\n\n'
        for i, article in enumerate(articles):
            news_str += f"Article {i + 1}: {article['title']}\n{article['url']}\n\n"
        return news_str, articles

class LarrysNewsCogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_recommender = LarrysNewsRecommender(self.bot.database, self.bot.openai_client)

    @tasks.loop(hours=24)
    async def get_daily_news(self):
        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        await self.__get_recommended_news(text_channel)

    @get_daily_news.before_loop
    async def before_get_daily_news(self):
        await self.bot.discord_client.wait_until_ready()
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now,
                                                hour=self.bot.walk_constants.WINNER_HOUR,
                                                minute=self.bot.walk_constants.WINNER_MINUTE + 2,
                                                second=0,
                                                microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        print(f'Waiting until {target_time} for daily news')
        print(f'daily news wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    async def __get_recommended_news(self, ctx):
        """Get news for AI-recommended topic based on user engagement"""
        news_message, articles = self.news_recommender.get_news(page_size=1)
        message = await ctx.send(news_message)
        await self.__add_reactions_to_message(message)
        
        for article in articles:
            await self.__store_article(message, article, "ai_recommended")

    async def __store_article(self, message, article, category):
        """Store article information in database"""
        date = str(datetime.datetime.now(tz=pytz.timezone('US/Pacific')).date())
        self.bot.database.add_daily_news(
            message.id, 
            article['title'], 
            article['url'], 
            category, 
            str(article),
            date
        )
        upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command(name='news')
    async def news(self, ctx, *args):
        """Get news for AI-recommended topic based on user engagement"""
        await self.__get_recommended_news(ctx)

    async def __default_get_news(self, ctx):
        categories = ['business', 'science', 'sports', 'technology']
        for category in categories:
            news_message, articles = self.news_recommender.get_news(category=category, page_size=1, country='us')
            message = await ctx.send(news_message)
            await self.__add_reactions_to_message(message)
            for article in articles:
                date = str(datetime.datetime.now(tz=pytz.timezone('US/Pacific')).date())
                print(f"Adding article {article['title']} to the database")
                print(date)
                self.bot.database.add_daily_news(message.id, article['title'], article['url'], category, str(article),
                                                 date)
                upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    async def __add_reactions_to_message(self, message):
        emojis = ['👍', '👎']
        for emoji in emojis:
            await message.add_reaction(emoji)
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Check if the reaction is for the message you're interested in
        # This is a basic example, you might want to add more checks
        # check text channel
        if reaction.message.channel.id != self.bot.bot_constants.TEXT_CHANNEL_ID:
            return
        if user != self.bot.discord_client.user:  # Ignore the bot's own reactions
            self.bot.database.update_reaction(reaction.message.id, reaction.emoji, 1)
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
            print(f"{user.name} reacted with {reaction.emoji} on the message {reaction.message.id}")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Check if the reaction is for the message you're interested in
        # This is a basic example, you might want to add more checks
        if reaction.message.channel.id != self.bot.bot_constants.TEXT_CHANNEL_ID:
            return
        if user != self.bot.discord_client.user:  # Ignore the bot's own reactions
            print(f"{user.name} removed their reaction of {reaction.emoji} on the message {reaction.message.id}")
            self.bot.database.update_reaction(reaction.message.id, reaction.emoji, -1)
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command(name='news_help')
    async def news_help(self, ctx):
        await ctx.send("Use the command '!news <topic>' to get news about a specific topic.")


