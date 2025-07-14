import os
import sqlite3
import uuid
from abc import ABC, abstractmethod

import dropbox
import pandas as pd
from dotenv import load_dotenv
from tabulate import tabulate

from src.extensions.stock_trading.types import Transaction
from src.types import ROOT_PATH
from src.util import upload


class BackendClient(ABC):

    @abstractmethod
    def download_file(self, file_name):
        pass

    @abstractmethod
    def upload_file(self, file_name):
        pass


class Local(BackendClient):

    def __init__(self):
        self.data_path = ROOT_PATH / 'data'

    def download_file(self, file_name):
        pass

    def upload_file(self, file_name):
        pass


class Dropbox(BackendClient):
    def __init__(self):
        load_dotenv()
        refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN')
        app_key = os.getenv('DROPBOX_KEY')
        app_secret = os.getenv('DROPBOX_SECRET')
        self.client = dropbox.Dropbox(app_key=app_key, app_secret=app_secret, oauth2_refresh_token=refresh_token)
        self.data_path = ROOT_PATH / 'data'

    def download_file(self, file_name):
        # Check if the file exists in Dropbox
        remote_file_path = f'/{file_name}'
        if not self.__file_exists(file_name, remote_file_path):
            return
        local_file_path = self.__get_local_file_path(file_name)
        print(f'Here is the local file path: {local_file_path}')
        with open(local_file_path, 'wb') as f:
            _, res = self.client.files_download(remote_file_path)
            f.write(res.content)
            print(f"Downloaded '{remote_file_path}' from Dropbox into '{local_file_path}'!")

    def upload_file(self, file_name):
        remote_file_path = f'/{file_name}'
        local_file_path = f'./{file_name}'
        with open(local_file_path, 'rb') as f:
            self.client.files_upload(f.read(), remote_file_path, mode=dropbox.files.WriteMode.overwrite)

    def __file_exists(self, file_name, remote_file_path):
        try:
            _ = self.client.files_get_metadata(remote_file_path)
        except dropbox.exceptions.ApiError as e:
            if e.error.is_path() and \
                    e.error.get_path().is_not_found():
                print(f'{file_name} does not exist in Dropbox.')
                return False
        return True

    @staticmethod
    def __get_local_file_path(file_name):
        return file_name


class Database:
    def __init__(self, db_file: str):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.db_file = db_file


class LarrysDatabase(Database):
    def __init__(self, db_file: str):
        super().__init__(db_file)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS voice_log
                        (name text, id text, time datetime, channel text, user_joined boolean)''')

        # Create table if it doesn't exist
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS points
                        (name text, id text, points_awarded float, day datetime, type text)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_of_the_day
                            (exercise text, date datetime, sets integer, reps integer, duration text, difficulty text, 
                            points integer, full_response text, tldr_response text)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_log
                        (name text, id text, exercise text, time datetime)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS daily_news
                        (message_id text, title text, url text, category text, news_json text, date text)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reactions
                        (message_id text, emoji text, count integer)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS freethrows
                        (message_id text, name text, id text, date datetime, number_made integer, number_attempted 
                        integer)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS sleep_log
                        (message_id text, date datetime, user_id text, name text, hours_slept float)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS sleep_points
                        (date datetime, user_id text, name text, points_type text, points integer)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                        (user_id text PRIMARY KEY, exercise_enabled boolean DEFAULT 0, news_enabled boolean DEFAULT 0)''')

    def add_daily_news(self, message_id, title, url, category, news_json, date):
        self.cursor.execute("INSERT INTO daily_news (message_id, title, url, category, news_json, date) VALUES (?, ?, ?, ?, ?, ?)",
                            (message_id, title, url, category, news_json, date))
        self.connection.commit()

    def update_reaction(self, message_id, emoji, increment):
        self.cursor.execute("SELECT * FROM reactions WHERE message_id = ? AND emoji = ?", (message_id, emoji))
        reaction = self.cursor.fetchone()
        if reaction:
            self.cursor.execute("UPDATE reactions SET count = count + ? WHERE message_id = ? AND emoji = ?",
                                (increment, message_id, emoji))
        else:
            self.cursor.execute("INSERT INTO reactions (message_id, emoji, count) VALUES (?, ?, ?)",
                                (message_id, emoji, increment))
        if increment == -1:
            self.cursor.execute("DELETE FROM reactions WHERE message_id = ? AND count = 0", (message_id,))
        self.connection.commit()

    def log_free_throw(self, message_id, name, id, date, number_made, number_attempted):
        self.cursor.execute("INSERT INTO freethrows (message_id, name, id, date, number_made, number_attempted) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (message_id, name, id, date, number_made, number_attempted))
        self.connection.commit()

    def upload(self):
        upload(self.connection, self.db_file)

    def freethrow_exists(self, name, id, date):
        self.cursor.execute("""
            SELECT COUNT(*) FROM freethrows 
            WHERE name = ? AND id = ? AND date = ?
        """, (name, id, date))
        count = self.cursor.fetchone()[0]
        return count > 0

    def log_sleep(self, message_id, date, user_id, name, hours_slept):
        self.cursor.execute("INSERT INTO sleep_log (message_id, date, user_id, name, hours_slept) VALUES (?, ?, ?, ?, ?)",
                            (message_id, date, user_id, name, hours_slept))
        self.connection.commit()

    def log_sleep_points(self, date, user_id, name, points_type, points):
        self.cursor.execute("INSERT INTO sleep_points (date, user_id, name, points_type, points) VALUES (?, ?, ?, ?, ?)",
                            (date, user_id, name, points_type, points))
        self.connection.commit()

    def sleep_exists(self, user_id, date):
        self.cursor.execute("""
            SELECT COUNT(*) FROM sleep_log 
            WHERE user_id = ? AND date(date) = date(?)
        """, (user_id, date))
        count = self.cursor.fetchone()[0]
        return count > 0

    def get_user_preference(self, user_id, preference_name):
        """Get a specific user preference (exercise_enabled or news_enabled)"""
        self.cursor.execute(f"SELECT {preference_name} FROM user_preferences WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return bool(result[0]) if result else False

    def set_user_preference(self, user_id, preference_name, value):
        """Set a specific user preference"""
        self.cursor.execute(f"INSERT OR REPLACE INTO user_preferences (user_id, {preference_name}) VALUES (?, ?)", (user_id, int(value)))
        self.connection.commit()

    def get_all_users_with_preference(self, preference_name, value=True):
        """Get all users who have a specific preference enabled"""
        self.cursor.execute(f"SELECT user_id FROM user_preferences WHERE {preference_name} = ?", (int(value),))
        return [row[0] for row in self.cursor.fetchall()]

    def toggle_user_preference(self, user_id, preference_name):
        """Toggle a user preference and return the new value"""
        current_value = self.get_user_preference(user_id, preference_name)
        new_value = not current_value
        self.set_user_preference(user_id, preference_name, new_value)
        return new_value


class LarrysStockExchange(Database):
    transaction_type_modifier = {
        'BUY': 1,
        'SELL': -1
    }

    def __init__(self, db_file: str):
        super().__init__(db_file)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            net_worth REAL NOT NULL,
            current_balance REAL NOT NULL
        );''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            transaction_date DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES User(id)
        );''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Portfolio (
            user_id INTEGER,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost_basis REAL NOT NULL,
            current_price REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES User(id)
        );''')

    def initialize_users(self, db_file, walkers):
        print(walkers)
        larrys_database = LarrysDatabase(db_file)
        all_users = larrys_database.cursor.execute(
            "SELECT DISTINCT(name) as name, id as user_id FROM points GROUP BY name").fetchall()
        users_starting_balance = larrys_database.cursor.execute(
            "SELECT DISTINCT(name) as name, SUM(points_awarded) as total_points FROM points GROUP BY name").fetchall()
        print('Here are the users and their starting balances:')
        print(users_starting_balance)
        users_df = pd.read_sql_query("SELECT * FROM User", self.connection)
        if users_df.empty:
            users_df = self.__initialize_all_users(all_users, users_starting_balance, walkers)
        balance_df = users_df[['name', 'current_balance']].sort_values(by='current_balance', ascending=False)
        balance_table = tabulate(balance_df, headers='keys', tablefmt='grid', showindex=False)
        return balance_table

    def __initialize_all_users(self, all_users, users_starting_balance, walkers):
        walkers = self.__initialize_active_walkers(all_users, users_starting_balance, walkers)
        self.__initialize_remaining_walkers(walkers)
        users_df = pd.read_sql_query("SELECT * FROM User", self.connection)
        return users_df

    def __initialize_remaining_walkers(self, walkers):
        for walker in walkers:
            self.initialize_user(walker.id, walker.name, 0)

    def __initialize_active_walkers(self, all_users, users_starting_balance, walkers):
        for idx, user in enumerate(all_users):
            name, user_id = user
            for walker in walkers:
                if walker.name == name:
                    walkers.pop(walkers.index(walker))
            balance = float(users_starting_balance[idx][1])
            self.initialize_user(int(user_id), name, balance)
        return walkers

    def initialize_user(self, user_id, name, balance):
        self.cursor.execute("INSERT INTO User (id, name, net_worth, current_balance) VALUES (?, ?, ?, ?)",
                            (user_id, name, balance, balance))

    def insert_transaction(self, t: Transaction):
        user_id, symbol, transaction_type, quantity, price, transaction_date, transaction_id = (
            t.user_id, t.symbol, t.transaction_type,
            t.quantity, t.price, t.transaction_date, t.transaction_id)
        print(f"Inserting transaction {transaction_id} for {user_id}...")

        self.cursor.execute(
            "INSERT INTO Transactions (id, user_id, symbol, transaction_type, quantity, price, transaction_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (transaction_id, user_id, symbol, transaction_type, quantity, price, transaction_date))
        return transaction_id

    def update_user_balance(self, user_id, new_balance):
        print('Updating user balance:', user_id, new_balance)
        self.cursor.execute("UPDATE User SET current_balance = ? WHERE id = ?", (new_balance, user_id))

    def get_user_stocks(self, user_id):
        self.cursor.execute(
            "SELECT user_id, symbol, quantity, cost_basis, current_price FROM Portfolio WHERE user_id = ?", (user_id,))
        user_stocks = self.cursor.fetchall()
        return [list(stock) for stock in user_stocks]

    def update_stock_price(self, user_id, symbol, current_price):
        self.cursor.execute("UPDATE Portfolio SET current_price = ? WHERE user_id = ? AND symbol = ?",
                            (current_price, user_id, symbol))

    def get_user_balance(self, user_id):
        self.cursor.execute("SELECT current_balance FROM User WHERE id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    def update_portfolio(self, transaction_id):
        transaction = self.__get_transaction_data(transaction_id)
        portfolio_data = self.__get_portfolio_data(transaction.symbol, transaction.user_id)
        self.__update_portfolio_stock_information(portfolio_data, transaction)

    def __update_portfolio_stock_information(self, portfolio_data, transaction):
        if portfolio_data:
            self.__update_cost_basis_quantity(portfolio_data, transaction)
        else:
            self.__add_stock(transaction)

    def __get_portfolio_data(self, symbol, user_id):
        self.cursor.execute("SELECT quantity, cost_basis FROM Portfolio WHERE user_id = ? AND symbol = ?",
                            (user_id, symbol))
        portfolio_data = self.cursor.fetchone()
        return portfolio_data

    def __get_transaction_data(self, transaction_id) -> Transaction:
        self.cursor.execute("SELECT user_id, symbol, transaction_type, quantity, price FROM Transactions WHERE id = ?",
                            (transaction_id,))
        transaction = self.cursor.fetchone()
        return Transaction(*transaction)

    def __add_stock(self, transaction: Transaction):
        price, quantity, symbol, user_id = (transaction.price, transaction.quantity,
                                            transaction.symbol, transaction.user_id)
        self.cursor.execute(
            "INSERT INTO Portfolio (user_id, symbol, quantity, cost_basis, current_price) VALUES (?, ?, ?, ?, ?)",
            (user_id, symbol, quantity, price, price))

    def __update_cost_basis_quantity(self, portfolio_data, transaction: Transaction):
        price, quantity, symbol, user_id, transaction_type = (transaction.price, transaction.quantity,
                                                              transaction.symbol, transaction.user_id,
                                                              transaction.transaction_type.upper())
        current_quantity, cost_basis = portfolio_data
        transaction_type_modifier = self.transaction_type_modifier[transaction_type]
        new_quantity = current_quantity + (quantity * transaction_type_modifier)
        if new_quantity == 0:
            self.cursor.execute("DELETE FROM Portfolio WHERE user_id = ? AND symbol = ?", (user_id, symbol))
            return
        new_cost_basis = ((cost_basis * current_quantity) + (
                    (price * quantity) * transaction_type_modifier)) / new_quantity
        self.cursor.execute("UPDATE Portfolio SET quantity = ?, cost_basis = ? WHERE user_id = ? AND symbol = ?",
                            (new_quantity, new_cost_basis, user_id, symbol))

    def get_all_user_ids(self) -> set:
        """Get all user IDs currently in the database"""
        self.cursor.execute("SELECT id FROM User")
        return {str(row[0]) for row in self.cursor.fetchall()}

    # --- Convenience helpers used by tests ---
    def get_user_portfolio(self, user_id):
        """Return basic portfolio info for the given user.

        This is a lightweight helper primarily used in tests. It returns an
        object with ``owner`` set to the user record tuple
        ``(name, id, net_worth, current_balance)``.
        """
        self.cursor.execute(
            "SELECT name, id, net_worth, current_balance FROM User WHERE id = ?",
            (user_id,)
        )
        owner = self.cursor.fetchone()
        class PortfolioInfo:
            def __init__(self, owner):
                self.owner = owner
        return PortfolioInfo(owner)

    def get_user_net_worth(self, user_id, stock_api=None):
        """Return the stored net worth for ``user_id``.

        ``stock_api`` is accepted for future expansion but ignored here.
        """
        info = self.get_user_portfolio(user_id)
        return info.owner[2] if info.owner else 0
