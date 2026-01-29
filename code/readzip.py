import zipfile

class ZipReader:
    def __init__(self):

    def read_file(self, zip_path, internal_file_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            with zip_ref.open(internal_file_path) as file:
                return file.read()