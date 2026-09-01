import pytest

from sleeper_recap import sleeper


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_get_returns_json(monkeypatch):
    monkeypatch.setattr(
        sleeper._session, "get", lambda url, timeout: FakeResponse(200, {"week": 3})
    )
    assert sleeper.nfl_state() == {"week": 3}


def test_get_null_body_exits(monkeypatch):
    monkeypatch.setattr(
        sleeper._session, "get", lambda url, timeout: FakeResponse(200, None)
    )
    with pytest.raises(SystemExit, match="not found"):
        sleeper.league("badid")


def test_get_http_error_exits(monkeypatch):
    monkeypatch.setattr(
        sleeper._session, "get", lambda url, timeout: FakeResponse(404, None)
    )
    with pytest.raises(SystemExit, match="not found"):
        sleeper.league("badid")
