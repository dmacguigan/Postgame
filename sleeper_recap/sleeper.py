import json
import os
import time

import requests

BASE = "https://api.sleeper.app/v1"
CACHE_DIR = ".cache"
CACHE_TTL_SECONDS = 24 * 60 * 60
_session = requests.Session()


def _get(path):
    try:
        resp = _session.get(BASE + path, timeout=30)
        if resp.status_code == 404:
            raise SystemExit(f"Sleeper API: not found: {path}")
        resp.raise_for_status()
    except requests.RequestException as e:
        raise SystemExit(f"Sleeper API error: {e}")
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


def _cached_get(path, cache_file):
    if os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < CACHE_TTL_SECONDS:
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    data = _get(path)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def players():
    return _cached_get("/players/nfl", os.path.join(CACHE_DIR, "players.json"))


def season_stats(season):
    return _cached_get(f"/stats/nfl/regular/{season}", os.path.join(CACHE_DIR, f"stats_{season}.json"))


def transactions(league_id, week):
    return _get(f"/league/{league_id}/transactions/{week}")


def draft_picks(league_id):
    drafts = _get(f"/league/{league_id}/drafts")
    if not drafts:
        return []
    draft_id = drafts[0]["draft_id"]
    return _get(f"/draft/{draft_id}/picks")
