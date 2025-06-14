from pathlib import Path
import shutil
import os
import random
import time

class FileSystem:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _maybe_fail(self, fail_rate=0.1, ignore_rate=0.05, latency=0.2):
        # Randomly raise an exception
        if random.random() < fail_rate:
            raise OSError("Random filesystem failure occurred.")
        # Randomly silently ignore
        if random.random() < ignore_rate:
            print("Randomly ignoring operation.")
            return True
        # Randomly add latency
        if random.random() < 0.2:
            delay = random.uniform(0, latency)
            print(f"Injecting latency: {delay:.2f}s")
            time.sleep(delay)
        return False

    def _maybe_corrupt(self, data):
        # Randomly flip a bit in a string
        if isinstance(data, str) and random.random() < 0.1 and data:
            idx = random.randint(0, len(data)-1)
            c = chr(ord(data[idx]) ^ 1)
            data = data[:idx] + c + data[idx+1:]
            print("Randomly corrupted data.")
        return data

    def exists(self, path):
        if self._maybe_fail(): return False
        print(f"Checking existence of: {path}")
        return Path(path).exists()

    def mkdir(self, path, exist_ok=False, parents=False):
        if self._maybe_fail(): return
        print(f"Making directory: {path}, exist_ok={exist_ok}, parents={parents}")
        Path(path).mkdir(exist_ok=exist_ok, parents=parents)

    def rmdir(self, path):
        if self._maybe_fail(): return
        print(f"Removing directory tree: {path}")
        shutil.rmtree(path)

    def listdir(self, path):
        if self._maybe_fail(): return []
        print(f"Listing directory: {path}")
        items = os.listdir(path)
        # Randomly forget some files
        if random.random() < 0.2 and items:
            n = random.randint(1, len(items))
            items = random.sample(items, n)
            print("Randomly forgot some directory entries.")
        return items

    def open(self, path, mode='r', encoding=None):
        if self._maybe_fail(): return open(os.devnull, mode, encoding=encoding)
        print(f"Opening file: {path}, mode={mode}, encoding={encoding}")
        return open(path, mode, encoding=encoding)

    def read_text(self, path):
        if self._maybe_fail(): return ""
        print(f"Reading text from: {path}")
        data = Path(path).read_text()
        return self._maybe_corrupt(data)

    def write_text(self, path, data):
        if self._maybe_fail(): return 0
        print(f"Writing text to: {path}")
        data = self._maybe_corrupt(data)
        return Path(path).write_text(data)

    def touch(self, path, exist_ok=True):
        if self._maybe_fail(): return
        print(f"Touching file: {path}, exist_ok={exist_ok}")
        Path(path).touch(exist_ok=exist_ok)

    def remove(self, path):
        if self._maybe_fail(): return
        print(f"Removing file: {path}")
        Path(path).unlink()

    def stat(self, path):
        if self._maybe_fail(): raise FileNotFoundError("Randomly failed to stat file.")
        print(f"Getting stat for: {path}")
        return Path(path).stat()

    def is_file(self, path):
        if self._maybe_fail(): return False
        print(f"Checking if file: {path}")
        return Path(path).is_file()

    def is_dir(self, path):
        if self._maybe_fail(): return False
        print(f"Checking if directory: {path}")
        return Path(path).is_dir()
