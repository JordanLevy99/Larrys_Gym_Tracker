import sys
import types
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Provide stub implementations of the discord modules so that the stock
# trading code can be imported without having discord.py installed.  These
# stubs only implement the minimal attributes used during tests.
discord_stub = types.ModuleType("discord")
discord_stub.utils = MagicMock()
commands_stub = types.ModuleType("commands")
def dummy_command(*args, **kwargs):
    def wrapper(func):
        return func
    return wrapper
commands_stub.Cog = object
commands_stub.command = dummy_command
discord_ext_stub = types.ModuleType("discord.ext")
discord_ext_stub.commands = commands_stub
sys.modules.setdefault("discord", discord_stub)
sys.modules.setdefault("discord.ext", discord_ext_stub)
sys.modules.setdefault("discord.ext.commands", commands_stub)
pytz_stub = types.ModuleType("pytz")
pytz_stub.timezone = lambda name: None
sys.modules.setdefault("pytz", pytz_stub)
finnhub_stub = types.ModuleType("finnhub")
finnhub_stub.Client = MagicMock()
sys.modules.setdefault("finnhub", finnhub_stub)
sys.modules.setdefault("pandas", types.ModuleType("pandas"))
mutagen_stub = types.ModuleType("mutagen")
mutagen_mp3_stub = types.ModuleType("mutagen.mp3")
mutagen_mp3_stub.MP3 = MagicMock()
mutagen_stub.mp3 = mutagen_mp3_stub
sys.modules.setdefault("mutagen", mutagen_stub)
sys.modules.setdefault("mutagen.mp3", mutagen_mp3_stub)

# Allow imports from src
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extensions.stock_trading.larrys_stock_trader import (
    StockCommands,
    StockUserCommands,
    StockBuyTransaction,
    StockSellTransaction,
)


class FakeBot:
    def __init__(self):
        self.stock_exchange_database = MagicMock()
        self.stock_api = MagicMock()
        self.backend_client = MagicMock()
        self.bot_constants = MagicMock()
        self.bot_constants.STOCK_DB_FILE = "test.db"
        self.database = MagicMock()


class StockTransactionTests(unittest.TestCase):
    def setUp(self):
        self.bot = FakeBot()
        self.bot.stock_exchange_database.get_user_balance.return_value = 1000
        self.bot.stock_api.get_current_price.return_value = 10

    def test_buy_transaction_success(self):
        with patch(
            "src.extensions.stock_trading.larrys_stock_trader.StockTransaction.update_database"
        ) as update_db:
            tx = StockBuyTransaction(1, "AAPL", 5, self.bot)
            msg = tx.execute()
            update_db.assert_called_once_with("buy")
            self.assertEqual(tx.user_balance, 950)
            self.assertEqual(
                msg,
                "Purchased **5** shares of **AAPL** at **10** each for a total of **50**",
            )

    def test_buy_transaction_insufficient_balance(self):
        self.bot.stock_exchange_database.get_user_balance.return_value = 20
        with patch(
            "src.extensions.stock_trading.larrys_stock_trader.StockTransaction.update_database"
        ) as update_db:
            tx = StockBuyTransaction(1, "AAPL", 5, self.bot)
            msg = tx.execute()
            update_db.assert_not_called()
            self.assertEqual(
                msg, "Insufficient balance (**20** < **50**)")

    def test_sell_transaction_success(self):
        self.bot.stock_exchange_database.get_user_stocks.return_value = [[1, "AAPL", 10, 0, 0]]
        with patch(
            "src.extensions.stock_trading.larrys_stock_trader.StockTransaction.update_database"
        ) as update_db:
            tx = StockSellTransaction(1, "AAPL", 5, self.bot)
            msg = tx.execute()
            update_db.assert_called_once_with("sell")
            self.assertEqual(tx.user_balance, 1050)
            self.assertEqual(
                msg,
                "Sold **5** shares of **AAPL** at **10** each for a total of **50**",
            )

    def test_sell_transaction_insufficient_shares(self):
        self.bot.stock_exchange_database.get_user_stocks.return_value = [[1, "AAPL", 2, 0, 0]]
        with patch(
            "src.extensions.stock_trading.larrys_stock_trader.StockTransaction.update_database"
        ) as update_db:
            tx = StockSellTransaction(1, "AAPL", 5, self.bot)
            msg = tx.execute()
            update_db.assert_not_called()
            self.assertEqual(
                msg, "Insufficient shares to sell (**5** > **2**)")


class StockCommandsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = FakeBot()

    def test_get_price(self):
        self.bot.stock_api.get_current_price.return_value = 123
        commands = StockCommands(self.bot)
        price = commands.get_price("aapl")
        self.assertEqual(price, 123)
        self.bot.stock_api.get_current_price.assert_called_with("AAPL")

    async def test_get_net_worth_leaderboard(self):
        commands = StockUserCommands(self.bot)
        ctx = MagicMock()
        leaderboard_list = [("Alice", [100, 10]), ("Bob", [50, -5])]
        leaderboard_str = "test_string"
        with patch.object(
            commands,
            "_StockUserCommands__get_net_worth_leaderboard_list",
            return_value=leaderboard_list,
        ) as list_mock, patch.object(
            commands,
            "_StockUserCommands__get_net_worth_leaderboard_string",
            return_value=leaderboard_str,
        ) as str_mock:
            result = await commands.get_net_worth_leaderboard(ctx)
            self.assertEqual(result, leaderboard_str)
            list_mock.assert_called_once_with(ctx)
            str_mock.assert_called_once_with(leaderboard_list)


if __name__ == "__main__":
    unittest.main()
