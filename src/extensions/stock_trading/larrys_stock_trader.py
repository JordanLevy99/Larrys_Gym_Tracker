import os
from abc import ABC, abstractmethod
import datetime

import discord
import pytz
from discord.ext import commands
from dotenv import load_dotenv

import finnhub

from src.extensions.stock_trading.types import Transaction
from src.util import upload


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


class Portfolio:
    def __init__(self, stocks, stock_api, db):
        self.stocks = stocks
        self.stock_api = stock_api
        self.db = db
        self._update_stock_prices()

    def _update_stock_prices(self):
        for stock in self.stocks:
            user_id, symbol, price = stock[0], stock[1], stock[-1]
            # stock[-1] is price
            stock[-1] = self.stock_api.get_current_price(symbol)
            self.db.update_stock_price(user_id, symbol, price)
        self.db.connection.commit()

    def get_total_value(self):
        total_value = 0
        self._update_stock_prices()
        for stock in self.stocks:
            _, _, quantity, _, current_price = stock
            total_value += current_price * quantity
        return total_value


class StockUserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.stock_exchange_database
        self.stock_transaction_factory = StockTransactionFactory(self.bot)

    @commands.command()
    async def initialize_users(self, ctx, db_file):
        walkers = discord.utils.get(ctx.guild.roles, name='Walker').members
        balance_table = self.db.initialize_users(db_file, walkers)
        self.db.connection.commit()
        upload(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)
        await ctx.send(f"Users will start with the following balances: \n{balance_table}")

    @commands.command()
    async def buy(self, ctx, *args):
        symbol, quantity = self._parse_transaction_args(args)
        message = self.stock_transaction_factory.create(ctx.author.id, symbol, quantity, 'buy').execute()
        await ctx.send(message)

    @commands.command()
    async def sell(self, ctx, *args):
        symbol, quantity = self._parse_transaction_args(args)
        message = self.stock_transaction_factory.create(ctx.author.id, symbol, quantity, 'sell').execute()
        await ctx.send(message)

    @commands.command()
    async def portfolio(self, ctx):
        user_id = ctx.author.id
        portfolio = self.__get_portfolio(user_id)
        print('updated stock prices:',portfolio.stocks)
        portfolio_printer = PortfolioPrinter(portfolio)
        await ctx.send(portfolio_printer.print())

    @commands.command()
    async def balance(self, ctx):
        user_id = ctx.author.id
        balance = self.db.get_user_balance(user_id)
        print(balance)
        await ctx.send(f"Your current balance is **{round(balance, 2)}**")

    @commands.command()
    async def net_worth(self, ctx):
        user_id = ctx.author.id
        portfolio = self.__get_portfolio(user_id)
        net_worth = portfolio.get_total_value() + self.db.get_user_balance(user_id)
        await ctx.send(f"Your current net worth is **{round(net_worth, 2)}**")

    def __get_portfolio(self, user_id) -> Portfolio:
        user_stocks = self.db.get_user_stocks(user_id)
        print('original stock prices:', user_stocks)
        portfolio = Portfolio(user_stocks, self.bot.stock_api, self.db)
        upload(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)
        return portfolio

    @staticmethod
    def _parse_transaction_args(args):
        args = ' '.join(args)
        args = args.split()
        symbol = args[0].upper().strip().strip('$')
        quantity = int(args[1])
        return symbol, quantity


class StockTransaction:

    def __init__(self, user_id, symbol, quantity, bot):
        self.user_id = user_id
        self.symbol = symbol
        self.quantity = quantity
        self.bot = bot
        self.db = bot.stock_exchange_database
        self.stock_api = bot.stock_api
        self._setup_transaction()

    def _setup_transaction(self):
        self.user_balance = self.db.get_user_balance(self.user_id)
        self.current_price = self.stock_api.get_current_price(self.symbol)
        self.total_cost = self.current_price * self.quantity

    def execute(self):
        pass

    def update_database(self, transaction_type):
        self.db.update_user_balance(self.user_id, self.user_balance)
        transaction = Transaction(self.user_id,
                                  self.symbol,
                                  transaction_type,
                                  self.quantity,
                                  self.current_price,
                                  datetime.datetime.now(tz=pytz.timezone('US/Pacific')))
        transaction_id = self.db.insert_transaction(transaction)
        self.db.update_portfolio(transaction_id)
        self.db.connection.commit()
        upload(self.bot.backend_client, self.bot.bot_constants.STOCK_DB_FILE)


class StockBuyTransaction(StockTransaction):

    def execute(self) -> str:
        if self.user_balance >= self.total_cost:
            self.user_balance -= self.total_cost
            self.update_database('buy')
            return f"Purchased {self.quantity} shares of {self.symbol} at {self.current_price} each"
        else:
            return f"Insufficient balance ({self.user_balance} < {self.total_cost})"


class StockSellTransaction(StockTransaction):

    def execute(self) -> str:
        user_stocks = self.db.get_user_stocks(self.user_id)
        print('user stocks:', user_stocks)
        quantity = self.__get_stock_quantity(user_stocks)

        if quantity >= self.quantity:
            self.user_balance += self.total_cost
            self.update_database('sell')
            return f"Sold {self.quantity} shares of {self.symbol} at {self.current_price} each."
        else:
            return "Insufficient shares to sell."

    def __get_stock_quantity(self, user_stocks):
        quantity = 0
        for stock in user_stocks:
            if stock[1] == self.symbol:
                quantity = stock[2]
                break
        return quantity



class StockTransactionFactory:
    stock_transactions = {
        'buy': StockBuyTransaction,
        'sell': StockSellTransaction
    }

    def __init__(self, bot):
        self.bot = bot

    def create(self, user_id, symbol, quantity, transaction_type):
        return self.stock_transactions[transaction_type](user_id, symbol, quantity, self.bot)


class StockCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def price(self, ctx, symbol):
        current_price = self.get_price(symbol)
        await ctx.send(f"The current price of {symbol.upper()} is {current_price}")

    def get_price(self, symbol):
        symbol = symbol.upper().strip().strip('$')
        return self.bot.stock_api.get_current_price(symbol)


class PortfolioPrinter:

    def __init__(self, portfolio):
        self.portfolio = portfolio

    def print(self):
        return_string = ""
        for stock in self.portfolio.stocks:
            _, symbol, quantity, cost_basis, price = stock
            total_value = quantity * price
            return_string += (f"**{symbol}**: \n\tQuantity: **{quantity}**\n\t"
                              f"Cost Basis: **{cost_basis}**\n\tCurrent Price: **{price}**\n\t"
                              f"Total Value: **{total_value}**\n\n")
        return return_string

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
