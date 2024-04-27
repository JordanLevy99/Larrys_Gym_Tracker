import os
from abc import ABC, abstractmethod
import datetime

import dotenv
import pytz
import requests
from discord.ext import commands
from dotenv import load_dotenv

import finnhub


class StockAPI(ABC):

    def __init__(self, api_key):
        self.api_key = api_key

    @abstractmethod
    def get_current_price(self, symbol):
        pass


class FinnhubAPI:
    def __init__(self, api_key):
        self.client = finnhub.Client(api_key=api_key)

    def get_current_price(self, symbol):
        quote = self.client.quote(symbol)
        return quote['c']


class StockUserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.stock_exchange_database

    @commands.command()
    async def buy(self, ctx, *args):
        user_id = ctx.author.id
        portfolio = self.db.get_user_portfolio(user_id)
        symbol, quantity = self._parse_buy_args(args)
        price = stock_api.get_current_price(symbol)
        total_cost = price * quantity
        if self.balance >= total_cost:
            self.balance -= total_cost
            portfolio.add_stock(symbol, quantity, price)
            self.db.insert_transaction(user_id, symbol, 'buy', quantity, price,
                                       datetime.datetime.now(tz=pytz.timezone('US/Pacific')))
            return f"Purchased {quantity} shares of {symbol} at {price} each."
        else:
            return "Insufficient balance."

    @commands.command()
    def net_worth(self, stock_api):
        return self.db.get_user_net_worth(self.user_id, stock_api)

    @staticmethod
    def _parse_buy_args(args):
        args = args.split()
        symbol = args[0]
        quantity = int(args[1])
        return symbol, quantity


class StockCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def price(self, ctx, symbol):
        symbol = symbol.upper().strip().strip('$')
        current_price = stock_api.get_current_price(symbol)
        ctx.send(f"The current price of {symbol} is {current_price}.")


class Portfolio:
    def __init__(self, owner):
        self.owner = owner
        self.stocks = {}

    def add_stock(self, symbol, quantity, price):
        if symbol in self.stocks:
            self.stocks[symbol]['quantity'] += quantity
        else:
            self.stocks[symbol] = {'quantity': quantity, 'average_price': price}
        print(self.stocks)

    def value(self, stock_api):
        total_value = 0
        for symbol, details in self.stocks.items():
            current_price = stock_api.get_current_price(symbol)
            total_value += current_price * details['quantity']
            print(symbol, current_price, details['quantity'])
        return total_value


if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    stock_api = StockAPI(api_key)
    stock_api.get_top_volume()
    # user = User(1, "Alice")
    # portfolio = Portfolio(user)
    # user.buy_stock("FXAIX", 10, stock_api)
    # total_value = user.get_portfolio_value()
    # print(total_value)
