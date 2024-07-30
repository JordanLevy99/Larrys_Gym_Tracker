import asyncio
import datetime

import pytz
from discord.ext import commands, tasks
from newsapi import NewsApiClient, const
import os

from src.openai import OpenAICog

from src.util import upload


class LarrysNewsRecommender:

    def __init__(self, bot):
        print('Categories:', const.categories)

        self.bot = bot  # LarrysBot
        self.client = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        self.openai_client = OpenAICog(bot)

    def get_topic(self):
        message = self.get_previous_news_articles()
        print(f"Message: {message}")
        response = self.openai_client.create_chat(self.openai_client.bot.openai_client, message,
                                       system_message="""You are a news recommender that will provide queries for finding news 
                articles. Given a list of news articles with headline, category, and number of likes and dislikes
                mentioned, provide a query that will return the most interesting news articles, something that 
                should get more likes than dislikes. The query should be concise and to the point, utlitizing the 
                following  format: 'query={query}' without the single quotes and replacing the query variable name 
                with the topic""",
                                       temperature=0.5)
        return response.replace('query=', '')

    def get_news(self, category=None, topic=None, page_size=5, country='us'):
        # categories = ['business', 'science', 'sports', 'technology']
        news = self.client.get_top_headlines(category=category, q=topic,
                                             language='en', page_size=page_size, country=country)
        print(news)

        articles = news['articles']
        if not articles:
            return 'No articles found', []
        if category:
            news_str = 'Category: ' + category + '\n'
        elif topic:
            news_str = 'Topic: ' + topic + '\n'
        else:
            raise ValueError('Must provide a category or topic')
        for i, article in enumerate(articles):
            news_str += f"Article {i + 1}: {article['title']}\n{article['url']}\n\n"
        return news_str, articles

    def get_previous_news_articles(self):
        emoji_map = {
            '👍': 'Likes',
            '👎': 'Dislikes'
        }
        print(self.bot.database.get_all_news_reactions())
        article_strs = {}
        for message_id, title, category, emoji, count in self.bot.database.get_all_news_reactions():
            # message = await ctx.fetch_message(message_id)
            article_strs[message_id] = article_strs.get(message_id, "")
                                        # + f"{emoji_map[emoji]}: {count}\n")
            if not article_strs[message_id]:
                article_strs[message_id] = f"Title: {title}\nCategory: {category}\n"
            article_strs[message_id] += f"{emoji_map[emoji]}: {count}\n"
            # print(f"Title: {title}\nCategory: {category}")
            # print(f"{emoji_map[emoji]}: {count}")
        total_article_str = ""
        for _, article_str in article_strs.items():
            total_article_str += article_str
        return total_article_str


class LarrysNewsCogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_recommender = LarrysNewsRecommender(bot)

    @tasks.loop(hours=24)
    async def get_daily_news(self):
        text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
        await self.__default_get_news(text_channel)

    @commands.command(name='get_news')
    async def get_news(self, ctx, *args):
        topic = self.news_recommender.get_topic()
        print(f"Topic: {topic}")
        news_message, _ = self.news_recommender.get_news(topic=topic, page_size=1, country='us')
        message = await ctx.send(news_message)
        await self.__add_reactions_to_message(message)

    async def get_previous_news_articles(self):
        emoji_map = {
            '👍': 'Likes',
            '👎': 'Dislikes'
        }
        print(self.bot.database.get_all_news_reactions())
        article_strs = {}
        for message_id, title, category, emoji, count in self.bot.database.get_all_news_reactions():
            # message = await ctx.fetch_message(message_id)
            article_strs[message_id] = article_strs.get(message_id, "")
                                        # + f"{emoji_map[emoji]}: {count}\n")
            if not article_strs[message_id]:
                article_strs[message_id] = f"Title: {title}\nCategory: {category}\n"
            article_strs[message_id] += f"{emoji_map[emoji]}: {count}\n"
            # print(f"Title: {title}\nCategory: {category}")
            # print(f"{emoji_map[emoji]}: {count}")
        total_article_str = ""
        for _, article_str in article_strs.items():
            total_article_str += article_str

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
