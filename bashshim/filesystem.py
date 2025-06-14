from pathlib import Path
import shutil
import os

class FileSystem:
    def __init__(self, root: Path):
        self.root = Path(root)

    def exists(self, path):
        return Path(path).exists()

    def mkdir(self, path, exist_ok=False, parents=False):
        Path(path).mkdir(exist_ok=exist_ok, parents=parents)

    def rmdir(self, path):
        shutil.rmtree(path)

    def listdir(self, path):
        return os.listdir(path)

    def open(self, path, mode='r', encoding=None):
        return open(path, mode, encoding=encoding)

    def read_text(self, path):
        return Path(path).read_text()

    def write_text(self, path, data):
        return Path(path).write_text(data)

    def touch(self, path, exist_ok=True):
        Path(path).touch(exist_ok=exist_ok)

    def remove(self, path):
        Path(path).unlink()

    def stat(self, path):
        return Path(path).stat()

    def is_file(self, path):
        return Path(path).is_file()

    def is_dir(self, path):
        return Path(path).is_dir()

    def append_text(self, path, data):
        """Append text to a file using read_text and write_text."""
        current = ""
        if self.exists(path):
            current = self.read_text(path)
        self.write_text(path, current + data)
