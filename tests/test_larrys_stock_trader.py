import unittest
from unittest.mock import MagicMock

from src.backend import LarrysStockExchange
from src.bot import LarrysBot
from src.extensions.stock_trading.larrys_stock_trader import StockCommands


class LarrysStockTraderTests(unittest.TestCase):

    def setUpClass(cls):
        cls.bot = MagicMock(LarrysBot())
        # cls.stock_commands = StockCommands(cls.bot)

    def test_get_price(self):
        self.bot.stock_api.get_current_price = MagicMock(return_value=100)
        stock_commands = StockCommands(self.bot)
        price = stock_commands.get_price("AAPL")
        self.assertEqual(price, 100)  # add assertion here


# class StockCommandsTests(unittest.IsolatedAsyncioTestCase):
#
#     async def asyncSetUp(self):
#         self.bot = MagicMock(LarrysBot())
#         self.stock_commands = StockCommands(self.bot)
#
#     async def test_price_command(self):
#         # Arrange
#         bot = MagicMock(LarrysBot())
#         bot.stock_api.get_current_price = MagicMock(return_value=100)
#         stock_commands = StockCommands(bot)
#         ctx = MagicMock()
#         symbol = "AAPL"
#         # Act
#         await stock_commands.price(stock_commands, ctx, symbol)
#         # Assert
#         ctx.send.assert_called_once_with("The current price of AAPL is 100.")


class LarrysStockExchangeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bot = MagicMock(LarrysBot())
        cls.stock_exchange = LarrysStockExchange('test.db')
        cls.stock_exchange.cursor = MagicMock()
        cls.stock_exchange.cursor.execute.return_value = None
        cls.stock_exchange.cursor.fetchone = MagicMock(return_value=('user', 1, 100, 100))

    def test_get_user_portfolio(self):
        portfolio = self.stock_exchange.get_user_portfolio(1)
        self.assertEqual(('user', 1, 100, 100), portfolio.owner)

    def test_get_user_net_worth(self):
        # self.stock_exchange.get_user_portfolio = MagicMock(return_value=MagicMock(value=100))
        net_worth = self.stock_exchange.get_user_net_worth(1, self.bot.stock_api)
        self.assertEqual(100, net_worth)

    def test_buy_stock(self):
        pass

    def test_sell_stock(self):
        pass

    def test_net_worth(self):
        pass


if __name__ == '__main__':
    unittest.main()
