import requests

BASE = "https://api.sleeper.app/v1"
_session = requests.Session()


def _get(path):
    resp = _session.get(BASE + path, timeout=30)
    if resp.status_code == 404:
        raise SystemExit(f"Sleeper API: not found: {path}")
    resp.raise_for_status()
    data = resp.json()
    if data is None:
        raise SystemExit(f"Sleeper API: not found: {path}")
    return data


def league(league_id):
    return _get(f"/league/{league_id}")


def users(league_id):
    return _get(f"/league/{league_id}/users")


def rosters(league_id):
    return _get(f"/league/{league_id}/rosters")


def matchups(league_id, week):
    return _get(f"/league/{league_id}/matchups/{week}")


def nfl_state():
    return _get("/state/nfl")
