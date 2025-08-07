import json
import pytest
from pathlib import Path

from bashshim import curlshim

class DummyHome:
    pass

class DummyShell:
    def __init__(self, allow_networking: bool, overrides_path: str | None = None):
        self.allow_networking = allow_networking
        self._logs = []
        self.home = DummyHome()
        if overrides_path is not None:
            self.home.curl_override_path = overrides_path
    def _log(self, msg):  # pragma: no cover - simple helper
        self._logs.append(msg)

# ---------------- basic argument / error handling -----------------

def test_no_args():
    shell = DummyShell(allow_networking=False)
    code, out = curlshim.run(shell, [])
    assert code == 1
    assert out == "curl: no URL specified\n"


def test_url_after_flag(tmp_path):
    shell = DummyShell(allow_networking=False)
    code, out = curlshim.run(shell, ["-I", "http://example.com/404"])  # triggers early hardcoded path rejection
    assert code == 0
    assert "404 Not Found" in out

# ---------------- override rule file behaviours -----------------

@pytest.fixture
def overrides_file(tmp_path: Path):
    p = tmp_path / "curl_overrides.json"
    return p


def make_shell_with_overrides(tmp_path: Path, overrides: dict, allow_networking=False):
    f = tmp_path / "curl_overrides.json"
    f.write_text(json.dumps(overrides))
    return DummyShell(allow_networking=allow_networking, overrides_path=str(f))


def test_basic_route_override(tmp_path):
    overrides = {
        "example.com": {
            "/foo": {"status": 200, "headers": {"Content-Type": "text/plain"}, "body": "hello"}
        }
    }
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/foo"])
    assert code == 0
    assert out.startswith("HTTP/1.1 200")
    assert out.endswith("hello\n")


def test_upgrade_http_to_https(tmp_path):
    overrides = {
        "example.com": {
            "upgrade_http": True,
            "/foo": {"status": 200, "body": "unused"}
        }
    }
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/foo"])
    assert code == 0
    assert out.startswith("HTTP/1.1 301")
    assert "Location: https://example.com/foo" in out


def test_missing_path_falls_back_to_defined_404(tmp_path):
    overrides = {
        "example.com": {
            "/404": {"status": 404, "headers": {"Content-Type": "text/plain"}, "body": "nope"}
        }
    }
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/missing"])
    assert code == 0
    assert out.startswith("HTTP/1.1 404")
    assert out.endswith("nope\n")


def test_missing_path_without_404_uses_default(tmp_path):
    overrides = {"example.com": {}}
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/absent"])
    assert code == 0
    assert out.startswith("HTTP/1.1 404")
    assert out.endswith("404 Not Found\n")


def test_403_error_uses_custom_route_body(tmp_path):
    overrides = {
        "example.com": {
            "/403": {"status": 403, "body": "Forbidden body"},
            "/secure": {"status": 403}  # empty body triggers fallback
        }
    }
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/secure"])
    assert code == 0
    assert out.startswith("HTTP/1.1 403")
    assert out.endswith("Forbidden body\n")


def test_500_error_uses_custom_route_body(tmp_path):
    overrides = {
        "example.com": {
            "/500": {"status": 500, "body": "Boom"},
            "/explode": {"status": 500}
        }
    }
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/explode"])
    assert code == 0
    assert out.startswith("HTTP/1.1 500")
    assert out.endswith("Boom\n")


def test_redirect_to_header(tmp_path):
    overrides = {
        "example.com": {
            "/redir": {
                "status": 302,
                "headers": {"Content-Type": "text/plain"},
                "body": "redirecting",
                "redirect_to": "https://other.example/redir"
            }
        }
    }
    shell = make_shell_with_overrides(tmp_path, overrides)
    code, out = curlshim.run(shell, ["http://example.com/redir"])
    assert code == 0
    assert out.startswith("HTTP/1.1 302")
    assert "Location: https://other.example/redir" in out

# ---------------- networking path -----------------

def test_no_override_and_networking_disabled_returns_could_not_resolve():
    shell = DummyShell(allow_networking=False)
    code, out = curlshim.run(shell, ["http://no-overrides.test/"])
    assert code == 6
    assert "Could not resolve host" in out


def test_allow_networking_but_requests_missing(monkeypatch):
    shell = DummyShell(allow_networking=True)
    monkeypatch.setattr(curlshim, "requests", None)
    code, out = curlshim.run(shell, ["http://example.com/"])
    assert code == 6
    assert "Could not resolve host" in out


def test_allow_networking_blocked_by_turnstile(monkeypatch):
    shell = DummyShell(allow_networking=True)
    class DummyRequests:
        def get(self, *a, **k):
            raise AssertionError("Should not be called when blocked by turnstile")
    class DummyTT:
        @staticmethod
        def is_behind_turnstile(url):
            return True
    monkeypatch.setattr(curlshim, "requests", DummyRequests())
    monkeypatch.setattr(curlshim, "turnstile_test", DummyTT)
    code, out = curlshim.run(shell, ["http://blocked.example/"])
    assert code == 6
    assert "Could not resolve host" in out


def test_allow_networking_real_request_stub(monkeypatch):
    shell = DummyShell(allow_networking=True)
    class Resp:
        status_code = 200
        headers = {"Content-Type": "text/plain"}
        text = "hi"  # simple body
    class DummyRequests:
        def get(self, url, headers=None, timeout=10):
            assert "curl/7.88.1-bashshim" in headers.get("User-Agent", "")
            return Resp()
    class DummyTT:
        @staticmethod
        def is_behind_turnstile(url):
            return False
    monkeypatch.setattr(curlshim, "requests", DummyRequests())
    monkeypatch.setattr(curlshim, "turnstile_test", DummyTT)
    code, out = curlshim.run(shell, ["http://online.example/"])
    assert code == 0
    assert out.startswith("HTTP/1.1 200")
    assert out.endswith("hi")
