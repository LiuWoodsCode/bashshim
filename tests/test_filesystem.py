import os
from pathlib import Path
import pytest
from bashshim.filesystem import FileSystem


def test_basic_write_and_read(tmp_path):
    fs = FileSystem(tmp_path)
    file_path = tmp_path / "file.txt"
    fs.write_text(file_path, "hello")
    assert fs.read_text(file_path) == "hello"
    assert fs.exists(file_path) is True
    assert fs.is_file(file_path) is True
    assert fs.is_dir(file_path) is False


def test_append_text(tmp_path):
    fs = FileSystem(tmp_path)
    file_path = tmp_path / "append.txt"
    fs.write_text(file_path, "first")
    fs.append_text(file_path, "+second")
    assert fs.read_text(file_path) == "first+second"


def test_touch_and_remove(tmp_path):
    fs = FileSystem(tmp_path)
    file_path = tmp_path / "touchme"
    fs.touch(file_path)
    assert fs.exists(file_path)
    fs.remove(file_path)
    assert not fs.exists(file_path)


def test_mkdir_and_rmdir(tmp_path):
    fs = FileSystem(tmp_path)
    d = tmp_path / "subdir"
    fs.mkdir(d)
    assert fs.exists(d)
    assert fs.is_dir(d)
    # create nested structure to test rmdir (shutil.rmtree)
    nested = d / "nested"
    fs.mkdir(nested)
    fs.rmdir(d)
    assert not fs.exists(d)


def test_listdir(tmp_path):
    fs = FileSystem(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    listing = fs.listdir(tmp_path)
    assert set(listing) >= {"a.txt", "b.txt"}


def test_stat(tmp_path):
    fs = FileSystem(tmp_path)
    file_path = tmp_path / "stat.txt"
    fs.write_text(file_path, "data")
    st = fs.stat(file_path)
    assert st.st_size == 4
