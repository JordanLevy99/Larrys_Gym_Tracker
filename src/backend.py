import os
import dropbox



class Dropbox:
    def __init__(self):
        refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN')
        app_key = os.getenv('DROPBOX_KEY')
        app_secret = os.getenv('DROPBOX_SECRET')
        self.dbx = dropbox.Dropbox(app_key=app_key, app_secret=app_secret, oauth2_refresh_token=refresh_token)


    def download_file(self, db_file):
        # Check if the file exists in Dropbox
        file_path = f'/{db_file}'
        if not self.__file_exists(db_file, file_path):
            return
        # Download the file
        file_path_local = f'./{db_file}'
        with open(file_path_local, 'wb') as f:
            _, res = self.dbx.files_download(file_path)
            f.write(res.content)
            print(f'Downloaded {db_file} from Dropbox!')


    def __file_exists(self, db_file, file_path):
        try:
            _ = self.dbx.files_get_metadata(file_path)
        except dropbox.exceptions.ApiError as e:
            if e.error.is_path() and \
                e.error.get_path().is_not_found():
                print(f'{db_file} does not exist in Dropbox.')
                return False
        return True

    def upload_file(self, db_file):
        file_path = f'/{db_file}'
        file_path_local = f'./{db_file}'
        with open(file_path_local, 'rb') as f:
            self.dbx.files_upload(f.read(), file_path, mode=dropbox.files.WriteMode.overwrite)