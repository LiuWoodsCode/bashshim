import os
from pathlib import Path
import pytest
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

def test_echo(shim):
    code, out = shim.run("echo hello world")
    assert code == 0
    assert out == "hello world\n"

def test_pwd_and_cd(shim):
    code, out = shim.run("pwd")
    assert out.strip().startswith("/")
    code, _ = shim.run(f"cd /home/{shim.username}")
    assert code == 0
    code, out = shim.run("pwd")
    assert out.strip() == f"/home/{shim.username}"

def test_ls(shim):
    test_file = shim.fakeroot / "home" / shim.username / "file.txt"
    test_file.write_text("hi")
    code, out = shim.run(f"ls /home/{shim.username}")
    assert code == 0
    assert "file.txt" in out

def test_to_real_path_clamps(shim, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    real = shim._to_real_path("../../outside.txt")
    # Should be within fakeroot
    assert str(real).startswith(str(shim.fakeroot))
