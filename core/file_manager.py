import os
from kivy.utils import platform

class FileManager:
    def __init__(self):
        self.pdf_paths = []

    def pick_files(self):
        # TODO: implement filechooser logic (plyer or Kivy FileChooser)
        return []

    def add_file(self, path):
        if os.path.isfile(path) and path.lower().endswith('.pdf'):
            self.pdf_paths.append(path)

    def remove_file(self, path):
        self.pdf_paths.remove(path)

    def get_files(self):
        return self.pdf_paths

    def get_output_path(self):
        # TODO: prompt user for output location or return default
        return os.path.join(os.getcwd(), 'combined.pdf')