import os
from pathlib import Path
import pytest
import sys
from bashshim.shell import BashShim

@pytest.fixture
def shim(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    def minimal_pop(self):
        (self.fakeroot / "bin").mkdir(parents=True, exist_ok=True)
        (self.fakeroot / "home" / self.username).mkdir(parents=True, exist_ok=True)
        (self.fakeroot / "proc").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(BashShim, "_populate_structure", minimal_pop)
    return BashShim(log_dmesg=False, allow_networking=False)

@pytest.mark.usefixtures("capsys")
def test_echo(shim, capsys):
    code, out = shim.run("echo hello world")
    print(f"test_echo output: {out!r}")
    assert code == 0
    assert out == "hello world\n"

@pytest.mark.usefixtures("capsys")
def test_pwd_and_cd(shim, capsys):
    code, out = shim.run("pwd")
    print(f"test_pwd_and_cd initial pwd: {out!r}")
    assert out.strip().startswith("/")
    code, _ = shim.run(f"cd /home/{shim.username}")
    assert code == 0
    code, out = shim.run("pwd")
    print(f"test_pwd_and_cd after cd pwd: {out!r}")
    assert out.strip() == f"/home/{shim.username}"

@pytest.mark.usefixtures("capsys")
def test_ls(shim, capsys):
    test_file = shim.fakeroot / "home" / shim.username / "file.txt"
    test_file.write_text("hi")
    code, out = shim.run(f"ls /home/{shim.username}")
    print(f"test_ls output: {out!r}")
    assert code == 0
    assert "file.txt" in out

@pytest.mark.usefixtures("capsys")
def test_to_real_path_clamps(shim, tmp_path, capsys):
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    real = shim._to_real_path("../../outside.txt")
    print(f"test_to_real_path_clamps real path: {real!r}")
    # Should be within fakeroot
    assert str(real).startswith(str(shim.fakeroot))
