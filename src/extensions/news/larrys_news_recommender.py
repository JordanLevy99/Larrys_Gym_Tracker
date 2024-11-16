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
        
    def get_past_topics(self) -> List[str]:
        """Fetch a list of previously used topics from the database."""
        query = """
        SELECT DISTINCT topic 
        FROM daily_news
        """
        past_topics = pd.read_sql_query(query, self.database.connection)
        return past_topics['topic'].tolist()
    
    def get_recommended_topic(self, n=10) -> str:
        """Use OpenAI to analyze reaction data and suggest a specific news topic, avoiding past topics."""
        df = self.get_reaction_scores()
        past_topics = self.get_past_topics()
        
        # Prepare the data for OpenAI analysis
        df['engagement_score'] = df['upvotes'] - df['downvotes']
        df = df.sort_values('engagement_score', ascending=False)
        
        # Get top and bottom performing articles
        top_articles = df.head(n)[['title', 'category', 'engagement_score']].to_string()
        bottom_articles = df.tail(n)[['title', 'category', 'engagement_score']].to_string()
        
        prompt = f"""Analyze these news articles and their engagement scores:

TOP PERFORMING ARTICLES (High Engagement):
{top_articles}

POORLY PERFORMING ARTICLES (Low Engagement):
{bottom_articles}

Suggest a specific news topic (2-3 words) that would be interesting to this audience. 
The topic should be:
1. Similar in theme/style to the top performing articles
2. Different from the poorly performing articles
3. Current and engaging
4. Specific enough to get relevant results
5. Excluded from this list of past topics: {', '.join(past_topics)}

Return only the suggested topic, nothing else. For example: "artificial intelligence", "space exploration", or "renewable energy".
Do not include any explanation or additional text."""

        print("Analyzing engagement patterns...")
        print(prompt)  
        response = self.openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a news topic recommender. Analyze the engagement patterns, avoid past topics, and respond only with a specific topic that matches successful articles and avoids unsuccessful ones. Respond with only the topic, no other text.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="gpt-4o",
            temperature=0.7
        )

        recommended_topic = response.choices[0].message.content.strip().lower()
        print(f"Recommended topic: {recommended_topic}")
        return recommended_topic

class LarrysNewsRecommender:
    def __init__(self, database, openai_client):
        self.client = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        self.recommender_engine = NewsRecommenderEngine(database, openai_client)

    def get_news(self, topic=None, page_size=5, country='us', max_retries=3) -> Tuple[str, List[dict]]:
        if topic is None:
            topic = self.recommender_engine.get_recommended_topic()
        
        articles = []
        attempt = 0
        
        while attempt < max_retries and not articles:
            news = self.client.get_everything(
                q=topic,
                language='en',
                page_size=page_size * 2,  # Request more articles to have backup options
                sort_by='relevancy'
            )
            
            # Filter out [Removed] articles
            articles = [
                article for article in news['articles']
                if article['title'] and 
                   article['url'] and 
                   '[Removed]' not in article['title'] and 
                   'removed.com' not in article['url'].lower()
            ][:page_size]  # Take only the requested number of valid articles
            
            if not articles:
                attempt += 1
                print(f"Attempt {attempt}: No valid articles found for topic '{topic}', retrying...")
                # Get a new topic for the next attempt
                topic = self.recommender_engine.get_recommended_topic()
        
        if not articles:
            raise ValueError(f"Could not find valid articles after {max_retries} attempts")
        
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
                                                minute=self.bot.walk_constants.WINNER_MINUTE - 2,
                                                second=0,
                                                microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        print(f'Waiting until {target_time} for daily news')
        print(f'daily news wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    async def __get_recommended_news(self, ctx):
        """Get news for AI-recommended topic based on user engagement"""
        try:
            news_message, articles = self.news_recommender.get_news(page_size=1)
            message = await ctx.send(news_message)
            await self.__add_reactions_to_message(message)
            
            for article in articles:
                await self.__store_article(message, article, "ai_recommended")
        except ValueError as e:
            error_message = "Sorry, I couldn't find any valid news articles at the moment. Please try again later."
            await ctx.send(error_message)
            print(f"Error getting news: {str(e)}")

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


