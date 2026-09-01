import functools
import os
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

from sleeper_recap import cli, sleeper
from sleeper_recap import config as cfgmod

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
LEAGUES_DIR = "leagues"
PORT = 8484


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SystemExit as e:
            return jsonify(error=str(e)), 400

    return wrapper


def _path(league_id):
    lid = str(league_id or "").strip()
    if not lid.isdigit():
        raise SystemExit("league ID must be a number")
    return os.path.join(LEAGUES_DIR, f"{lid}.toml")


def _load(league_id):
    path = _path(league_id)
    if not os.path.exists(path):
        raise SystemExit("league not saved yet; enter its ID and click Load")
    return cfgmod.load(path)


def create_app():
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/api/leagues")
    def leagues():
        out = []
        if os.path.isdir(LEAGUES_DIR):
            for name in sorted(os.listdir(LEAGUES_DIR)):
                if name.endswith(".toml"):
                    cfg = cfgmod.load(os.path.join(LEAGUES_DIR, name))
                    out.append({"league_id": cfg["league_id"], "name": cfg.get("league_name") or cfg["league_id"]})
        return jsonify(out)

    @app.get("/api/config")
    @_guard
    def get_config():
        return jsonify(_load(request.args.get("league_id")))

    @app.post("/api/init")
    @_guard
    def init():
        d = request.json or {}
        path = _path(d.get("league_id"))
        if os.path.exists(path) and not d.get("force"):
            return jsonify(error="league already saved"), 409
        cfg = cfgmod.scaffold(str(d["league_id"]).strip())
        os.makedirs(LEAGUES_DIR, exist_ok=True)
        cfgmod.save(path, cfg)
        return jsonify(cfg)

    @app.post("/api/config")
    @_guard
    def put_config():
        cfg = request.json or {}
        path = _path(cfg.get("league_id"))
        os.makedirs(LEAGUES_DIR, exist_ok=True)
        cfgmod.save(path, cfg)
        return jsonify(cfgmod.load(path))

    @app.get("/api/seasons")
    @_guard
    def seasons():
        cfg = _load(request.args.get("league_id"))
        out = []
        lg = sleeper.league(cfg["league_id"])
        while lg:
            out.append({"season": lg["season"], "league_id": lg["league_id"]})
            prev = lg.get("previous_league_id")
            lg = sleeper.league(prev) if prev else None
        return jsonify(out)

    @app.post("/api/generate")
    @_guard
    def generate():
        d = request.json or {}
        cfg = _load(d.get("league_id"))
        out = os.path.join("recaps", cfg["league_id"], f"{d.get('season')}_week_{d.get('week')}_prompt.md")
        body, out = cli.run_recap(cfg, week=d.get("week"), season=d.get("season"), provider="manual", out=out)
        return jsonify(body=body, out_path=os.path.abspath(out))

    return app


def main(data_dir=None):
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        os.chdir(data_dir)
    url = f"http://127.0.0.1:{PORT}"
    threading.Timer(1.0, webbrowser.open, [url]).start()
    print(f"Postgame running at {url}")
    print("Close this window to quit.")
    create_app().run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
