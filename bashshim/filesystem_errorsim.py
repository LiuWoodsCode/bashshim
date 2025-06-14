from pathlib import Path
import shutil
import os
import random
import time

class FileSystem:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _maybe_fail(self, fail_rate=0.1, ignore_rate=0, latency=0.2):
        # Randomly raise an exception
        if random.random() < fail_rate:
            raise OSError("Random filesystem failure occurred.")
        # Randomly silently ignore
        if random.random() < ignore_rate:
            print("Randomly ignoring operation.")
            # return True
        # Randomly add latency
        if random.random() < 0.2:
            delay = random.uniform(0, latency)
            print(f"Injecting latency: {delay:.2f}s")
            time.sleep(delay)
        return False

    def _maybe_corrupt(self, data):
        # Randomly flip multiple bits in a string (for write operations only)
        if isinstance(data, str) and random.random() < 0.06 and data:
            n_flips = max(1, int(len(data) * 0.1))
            idxs = random.sample(range(len(data)), n_flips)
            data_list = list(data)
            for idx in idxs:
                data_list[idx] = chr(ord(data_list[idx]) ^ 1)
            data = ''.join(data_list)
            print(f"Randomly corrupted {n_flips} bytes of data.")
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
        return data  # No corruption on read

    def write_text(self, path, data):
        if self._maybe_fail(): return 0
        print(f"Writing text to: {path}")
        data = self._maybe_corrupt(data)  # Corrupt only the data being written
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

    def append_text(self, path, data):
        """Append text to a file using read_text and write_text."""
        current = ""
        if self.exists(path):
            current = self.read_text(path)
        # Only corrupt the appended data, not the whole file
        corrupted_data = self._maybe_corrupt(data)
        self.write_text(path, current + corrupted_data)
