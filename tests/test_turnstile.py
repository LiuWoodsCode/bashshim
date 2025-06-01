import pytest
import bashshim.turnstile_test as tt

class DummyResponse:
    def __init__(self, status_code=200, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

class DummyRequests:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
    def get(self, url, headers=None, timeout=10):
        if self._exc:
            raise self._exc
        return self._response


def test_no_requests_module(monkeypatch):
    monkeypatch.setattr(tt, "requests", None)
    assert tt.is_behind_turnstile("http://example.com") is False


def test_requests_exception(monkeypatch):
    dummy = DummyRequests(exc=RuntimeError("fail"))
    monkeypatch.setattr(tt, "requests", dummy)
    assert tt.is_behind_turnstile("http://example.com") is False


def test_challenge_detected_by_status_and_content(monkeypatch):
    resp = DummyResponse(
        status_code=403,
        headers={},
        text="<div id='cf-turnstile'></div>"
    )
    monkeypatch.setattr(tt, "requests", DummyRequests(response=resp))
    assert tt.is_behind_turnstile("http://example.com") is True


def test_challenge_detected_by_header(monkeypatch):
    resp = DummyResponse(
        status_code=200,
        headers={"cf-mitigated": "challenge"},
        text="<html>Verification Required</html>"
    )
    monkeypatch.setattr(tt, "requests", DummyRequests(response=resp))
    assert tt.is_behind_turnstile("http://example.com") is True


def test_non_challenge(monkeypatch):
    resp = DummyResponse(status_code=200, headers={}, text="hello")
    monkeypatch.setattr(tt, "requests", DummyRequests(response=resp))
    assert tt.is_behind_turnstile("http://example.com") is False


def test_real_example_no_challenge():
    import requests  # noqa: F401 - ensure real requests library is used
    assert tt.is_behind_turnstile("https://example.com") is False


def test_real_cloudflare_site():
    import requests  # noqa: F401 - ensure real requests library is used
    assert tt.is_behind_turnstile("https://www.cloudflare.com") is False

