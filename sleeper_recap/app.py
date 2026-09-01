import functools
import os
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

from sleeper_recap import cli, sleeper
from sleeper_recap import config as cfgmod

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
CONFIG = "config.toml"
PORT = 8484


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SystemExit as e:
            return jsonify(error=str(e)), 400

    return wrapper


def create_app():
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/api/config")
    def get_config():
        if not os.path.exists(CONFIG):
            return jsonify(error="No league loaded yet. Enter your league ID."), 404
        return jsonify(cfgmod.load(CONFIG))

    @app.post("/api/init")
    @_guard
    def init():
        cfg = cfgmod.scaffold(str(request.json["league_id"]).strip())
        cfgmod.save(CONFIG, cfg)
        return jsonify(cfg)

    @app.post("/api/config")
    @_guard
    def put_config():
        cfgmod.save(CONFIG, request.json)
        return jsonify(cfgmod.load(CONFIG))

    @app.get("/api/seasons")
    @_guard
    def seasons():
        cfg = cfgmod.load(CONFIG)
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
        cfg = cfgmod.load(CONFIG)
        d = request.json or {}
        body, out = cli.run_recap(cfg, week=d.get("week"), season=d.get("season"), provider="manual")
        emails = [t["email"] for t in cfg.get("teams", {}).values() if t.get("email")]
        return jsonify(body=body, out_path=os.path.abspath(out), recipients=emails)

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
