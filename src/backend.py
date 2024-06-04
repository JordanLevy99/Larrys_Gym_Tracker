import os
import sqlite3
import uuid

import dropbox
import pandas as pd
from dotenv import load_dotenv
from tabulate import tabulate

from src.extensions.stock_trading.types import Transaction
from src.types import ROOT_PATH


class Dropbox:
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
