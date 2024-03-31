import os
import dropbox
from dotenv import load_dotenv

from src.types import ROOT_PATH


class Dropbox:
    def __init__(self):
        load_dotenv()
        refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN')
        app_key = os.getenv('DROPBOX_KEY')
        app_secret = os.getenv('DROPBOX_SECRET')
        self.client = dropbox.Dropbox(app_key=app_key, app_secret=app_secret, oauth2_refresh_token=refresh_token)
        self.data_path = ROOT_PATH / 'data'
        # self.db_filename = db_file
        # self.__remote_db_file_path = f'/{db_file}'
        # self.__local_db_file_path = f'../{db_file}'

    def download_file(self, file_name):
        # Check if the file exists in Dropbox
        remote_file_path = f'/{file_name}'
        if not self.__file_exists(file_name, remote_file_path):
            return
        local_file_path = self.__get_local_file_path(file_name)
        with open(local_file_path, 'wb') as f:
            _, res = self.client.files_download(remote_file_path)
            f.write(res.content)
            print(f'Downloaded {file_name} from Dropbox!')

    def __file_exists(self, file_name, remote_file_path):
        try:
            _ = self.client.files_get_metadata(remote_file_path)
        except dropbox.exceptions.ApiError as e:
            if e.error.is_path() and \
                    e.error.get_path().is_not_found():
                print(f'{file_name} does not exist in Dropbox.')
                return False
        return True

    def upload_file(self, file_name):
        remote_file_path = f'/{file_name}'
        local_file_path = f'./{file_name}'
        with open(local_file_path, 'rb') as f:
            self.client.files_upload(f.read(), remote_file_path, mode=dropbox.files.WriteMode.overwrite)

    def __get_local_file_path(self, file_name):
        return self.data_path / file_name
