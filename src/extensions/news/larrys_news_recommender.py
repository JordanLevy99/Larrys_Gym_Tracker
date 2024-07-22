import asyncio
import datetime

import pytz
from discord.ext import commands, tasks
from newsapi import NewsApiClient, const
import os

from src.util import upload


class LarrysNewsRecommender:

    def __init__(self):
        print('Categories:', const.categories)

        self.client = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))

    def get_news(self, category='general', topic=None, page_size=5, country='us'):
        # categories = ['business', 'science', 'sports', 'technology']
        news = self.client.get_top_headlines(category=category, q=topic,
                                             language='en', page_size=page_size, country=country)
        print(news)

        articles = news['articles']
        news_str = 'Category: ' + category + '\n'
        for i, article in enumerate(articles):
            news_str += f"Article {i + 1}: {article['title']}\n{article['url']}\n\n"
        return news_str, articles


class LarrysNewsCogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_recommender = LarrysNewsRecommender()

    @tasks.loop(hours=24)
    async def get_daily_news(self):
        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        await self.__default_get_news(text_channel)

    @get_daily_news.before_loop
    async def before_get_daily_news(self):
        await self.bot.discord_client.wait_until_ready()
        now = datetime.datetime.now()
        now = now.astimezone(pytz.timezone('US/Pacific'))
        target_time = datetime.datetime.replace(now,
                                                hour=self.bot.walk_constants.WINNER_HOUR,
                                                minute=self.bot.walk_constants.WINNER_MINUTE - 5,
                                                second=0,
                                                microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        print(f'Waiting until {target_time} for daily news')
        print(f'daily news wait time: {(target_time - now).total_seconds()}')
        await asyncio.sleep((target_time - now).total_seconds())

    @commands.command(name='news')
    async def news(self, ctx, *args):
        await self.__default_get_news(ctx)

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
        if user != self.bot.discord_client.user:  # Ignore the bot's own reactions
            self.bot.database.update_reaction(reaction.message.id, reaction.emoji, 1)
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)
            print(f"{user.name} reacted with {reaction.emoji} on the message {reaction.message.id}")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Check if the reaction is for the message you're interested in
        # This is a basic example, you might want to add more checks
        if user != self.bot.discord_client.user:  # Ignore the bot's own reactions
            print(f"{user.name} removed their reaction of {reaction.emoji} on the message {reaction.message.id}")
            self.bot.database.update_reaction(reaction.message.id, reaction.emoji, -1)
            upload(self.bot.backend_client, self.bot.bot_constants.DB_FILE)

    @commands.command(name='news_help')
    async def news_help(self, ctx):
        await ctx.send("Use the command '!news <topic>' to get news about a specific topic.")