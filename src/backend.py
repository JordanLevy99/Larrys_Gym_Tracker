import os
import sqlite3
from pathlib import Path
from typing import Union

import dropbox
from dotenv import load_dotenv

from src.types import ROOT_PATH, BotConstants


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
            transaction_date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES User(id)
        );''')

    def get_user_portfolio(self, user_id):
        self.cursor.execute("SELECT * FROM User WHERE id = ?", (user_id,))
        user = self.cursor.fetchone()
        return Portfolio(user)
