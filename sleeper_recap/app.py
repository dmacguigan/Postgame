import functools
import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

import re
import socket

from sleeper_recap import cli, platforms
from sleeper_recap import config as cfgmod

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
LEAGUES_DIR = "leagues"
PORT = 8484
HEARTBEAT_GRACE = 10
FIRST_PAGE_GRACE = 120
_last_ping = {"t": None}


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SystemExit as e:
            return jsonify(error=str(e)), 400
        except Exception as e:
            return jsonify(error=f"unexpected error: {e}"), 500

    return wrapper


def _path(key):
    key = str(key or "").strip()
    if not re.fullmatch(r"(espn_)?[0-9]+", key):
        raise SystemExit("bad league key")
    return os.path.join(LEAGUES_DIR, f"{key}.toml")


def _key(platform, league_id):
    lid = str(league_id or "").strip()
    if not lid.isdigit():
        raise SystemExit("league ID must be a number")
    return lid if platform == "sleeper" else f"{platform}_{lid}"


def _load(key):
    path = _path(key)
    if not os.path.exists(path):
        raise SystemExit("league not saved yet; enter its ID and click Load")
    return cfgmod.load(path)


def create_app():
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.post("/api/ping")
    def ping():
        _last_ping["t"] = time.time()
        return jsonify(ok=True)

    @app.get("/icon.svg")
    def icon():
        return send_from_directory(STATIC, "icon.svg")

    @app.get("/api/leagues")
    def leagues():
        out = []
        if os.path.isdir(LEAGUES_DIR):
            for name in sorted(os.listdir(LEAGUES_DIR)):
                if name.endswith(".toml"):
                    cfg = cfgmod.load(os.path.join(LEAGUES_DIR, name))
                    out.append({
                        "key": name[:-5],
                        "name": cfg.get("league_name") or cfg["league_id"],
                        "platform": cfg.get("platform", "sleeper"),
                    })
        return jsonify(out)

    @app.get("/api/config")
    @_guard
    def get_config():
        cfg = _load(request.args.get("league_key"))
        cfg.pop("espn_s2", None)
        cfg.pop("swid", None)
        return jsonify(cfg)

    @app.post("/api/init")
    @_guard
    def init():
        d = request.json or {}
        platform = d.get("platform") or "sleeper"
        if platform not in ("sleeper", "espn"):
            raise SystemExit("unknown platform")
        key = _key(platform, d.get("league_id"))
        path = _path(key)
        if os.path.exists(path) and not d.get("force"):
            return jsonify(error="league already saved"), 409
        cfg = cfgmod.scaffold(key.split("_")[-1], platform, d.get("espn_s2") or "", d.get("swid") or "")
        os.makedirs(LEAGUES_DIR, exist_ok=True)
        cfgmod.save(path, cfg)
        cfg.pop("espn_s2", None)
        cfg.pop("swid", None)
        return jsonify(dict(cfg, key=key))

    @app.post("/api/config")
    @_guard
    def put_config():
        new = request.json or {}
        key = _key(new.get("platform", "sleeper"), new.get("league_id"))
        cfg = _load(key)
        for field in ("tone", "teams"):
            if field in new:
                cfg[field] = new[field]
        cfgmod.save(_path(key), cfg)
        cfg.pop("espn_s2", None)
        cfg.pop("swid", None)
        return jsonify(dict(cfg, key=key))

    @app.get("/api/seasons")
    @_guard
    def seasons():
        cfg = _load(request.args.get("league_key"))
        return jsonify(platforms.open(cfg).seasons())

    @app.post("/api/generate")
    @_guard
    def generate():
        d = request.json or {}
        key = d.get("league_key")
        cfg = _load(key)
        try:
            season = int(d["season"])
            week = int(d["week"])
        except (KeyError, TypeError, ValueError):
            raise SystemExit("season and week must be numbers")
        week_to = d.get("week_to")
        if week_to:
            try:
                week_to = int(week_to)
            except (TypeError, ValueError):
                raise SystemExit("week_to must be a number")
            out = os.path.join("recaps", key, f"{season}_weeks_{week}-{week_to}_prompt.md")
            body, out = cli.run_range(cfg, week, week_to, season=season, out=out)
        else:
            out = os.path.join("recaps", key, f"{season}_week_{week}_prompt.md")
            body, out = cli.run_recap(cfg, week=week, season=season, provider="manual", out=out, header=False)
        return jsonify(body=body, out_path=os.path.abspath(out))

    return app


def _free_port(start):
    for port in range(start, start + 20):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("no free port found; close other Postgame windows")


def _should_quit(last_ping, started, now):
    if last_ping is None:
        return now - started > FIRST_PAGE_GRACE
    return now - last_ping > HEARTBEAT_GRACE


def _watchdog():
    started = time.time()
    while True:
        time.sleep(2)
        if _should_quit(_last_ping["t"], started, time.time()):
            print("Browser tab closed; quitting.")
            os._exit(0)


def main(data_dir=None):
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        os.chdir(data_dir)
    port = _free_port(PORT)
    url = f"http://127.0.0.1:{port}"
    threading.Timer(1.0, webbrowser.open, [url]).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    print(f"Postgame running at {url}")
    print("Close this window to quit.")
    create_app().run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
