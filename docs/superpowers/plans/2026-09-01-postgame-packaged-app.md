# Postgame Packaged App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Postgame, a double-click executable (Windows, macOS, Linux) that opens a local browser page for drafting Sleeper recap prompts, built and attached to a GitHub Release on tag push.

**Architecture:** Extract config read/write from `cli.py` into `config.py` and the recap pipeline into a reusable `cli.run_recap`. A small Flask app (`app.py`) exposes thin JSON routes over those functions plus one static HTML page. A root `postgame.py` entry script chdirs into `~/Postgame/` and starts the server; PyInstaller bundles it; GitHub Actions builds the three binaries.

**Tech Stack:** Python 3.11+, Flask, requests, pytest, PyInstaller, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-01-postgame-packaged-app-design.md`

## Global Constraints

- API keys from env vars only, never on disk, never in logs or output.
- Owner emails never included in any LLM prompt.
- ASCII only in code. Minimal comments. No em dashes anywhere.
- Never git push without explicit owner instruction.
- App produces manual (copy-paste) prompts only; no provider SDKs bundled.
- Data dir for the packaged app: `~/Postgame/`. CLI keeps cwd-relative paths.
- Config TOML format written by app must equal what CLI writes.
- Run tests with: `conda run -n sleeper-recap python -m pytest -q` (36 passing at start).

---

## File map

- Create `sleeper_recap/config.py`: `load`, `save`, `scaffold`, `_toml_str`.
- Modify `sleeper_recap/cli.py`: use `config.py`; add `run_recap(config, week, season, provider, model, out)`; add `app` subcommand.
- Create `sleeper_recap/app.py`: Flask `create_app()` and `main(data_dir=None)`.
- Create `sleeper_recap/static/index.html`: single page UI.
- Create `postgame.py` (repo root): PyInstaller entry, sets data dir.
- Create `requirements.txt`; modify `environment.yml`.
- Create `.github/workflows/release.yml`.
- Modify `README.md`.
- Create `tests/test_config.py`, `tests/test_app.py`; modify `tests/test_cli.py` (move `_toml_str` test).

---

### Task 1: Extract config helpers

**Files:**
- Create: `sleeper_recap/config.py`
- Modify: `sleeper_recap/cli.py` (cmd_init, cmd_recap config loading)
- Test: `tests/test_config.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `config.load(path) -> dict` (raises SystemExit with "init" hint if missing), `config.save(path, cfg) -> None`, `config.scaffold(league_id) -> dict` with keys `league_id, provider, model, tone, teams` where `teams` maps `str(roster_id)` to `{team_name, sleeper_username, owner_name, email, fun_facts}`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
import tomllib

import pytest

from sleeper_recap import config, sleeper
from tests.fixtures.week_data import ROSTERS, USERS


def _patch(monkeypatch):
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)


def test_scaffold_builds_teams(monkeypatch):
    _patch(monkeypatch)
    cfg = config.scaffold("999")
    assert cfg["league_id"] == "999"
    assert cfg["provider"] == "manual"
    assert cfg["teams"]["1"]["team_name"] == "Alice Attack"
    assert cfg["teams"]["2"]["team_name"] == "bob_ff"
    assert cfg["teams"]["1"]["owner_name"] == ""


def test_save_load_roundtrip(tmp_path, monkeypatch):
    _patch(monkeypatch)
    cfg = config.scaffold("999")
    cfg["tone"] = "dry"
    cfg["teams"]["1"]["owner_name"] = "Alice \U0001F600"
    cfg["teams"]["1"]["email"] = "a@example.com"
    path = tmp_path / "config.toml"
    config.save(str(path), cfg)
    assert config.load(str(path)) == cfg


def test_save_matches_cli_format(tmp_path, monkeypatch):
    _patch(monkeypatch)
    path = tmp_path / "config.toml"
    config.save(str(path), config.scaffold("999"))
    text = path.read_text(encoding="utf-8")
    assert 'league_id = "999"' in text
    assert "[teams.1]" in text
    assert 'owner_name = ""' in text


def test_load_missing_hints_init(tmp_path):
    with pytest.raises(SystemExit, match="init"):
        config.load(str(tmp_path / "nope.toml"))


def test_toml_str_roundtrips_emoji():
    name = "Team \U0001F600"
    parsed = tomllib.loads(f"x = {config._toml_str(name)}")
    assert parsed["x"] == name
```

- [ ] **Step 2: Run to verify failure**

Run: `conda run -n sleeper-recap python -m pytest tests/test_config.py -q`
Expected: ImportError / ModuleNotFoundError for `sleeper_recap.config`.

- [ ] **Step 3: Create `sleeper_recap/config.py`**

```python
import json
import tomllib

from sleeper_recap import llm, sleeper


def _toml_str(value):
    return json.dumps(str(value), ensure_ascii=False)


def load(path):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except OSError:
        raise SystemExit(f"{path} not found; run: python -m sleeper_recap init --league-id YOUR_ID")


def scaffold(league_id):
    users = sleeper.users(league_id)
    rosters = sleeper.rosters(league_id)
    names = {}
    usernames = {}
    for u in users:
        meta = u.get("metadata") or {}
        names[u["user_id"]] = meta.get("team_name") or u["display_name"]
        usernames[u["user_id"]] = u["display_name"]
    teams = {}
    for r in sorted(rosters, key=lambda r: r["roster_id"]):
        owner_id = r.get("owner_id")
        teams[str(r["roster_id"])] = {
            "team_name": names.get(owner_id, ""),
            "sleeper_username": usernames.get(owner_id, ""),
            "owner_name": "",
            "email": "",
            "fun_facts": "",
        }
    return {
        "league_id": str(league_id),
        "provider": "manual",
        "model": llm.DEFAULT_MODELS["anthropic"],
        "tone": "funny, light trash talk, inside jokes welcome",
        "teams": teams,
    }


def save(path, cfg):
    lines = [
        f"league_id = {_toml_str(cfg['league_id'])}",
        f"provider = {_toml_str(cfg.get('provider', 'manual'))}  # manual | anthropic | openai | gemini",
        f"model = {_toml_str(cfg.get('model', llm.DEFAULT_MODELS['anthropic']))}",
        f"tone = {_toml_str(cfg.get('tone', ''))}",
        "",
    ]
    for rid, t in cfg.get("teams", {}).items():
        lines.append(f"[teams.{rid}]")
        for key in ("team_name", "sleeper_username", "owner_name", "email", "fun_facts"):
            lines.append(f"{key} = {_toml_str(t.get(key, ''))}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
```

- [ ] **Step 4: Rewire `cli.py` to use it**

Replace the top of `cli.py` through the end of `cmd_init`, and the config loading in `cmd_recap`:

```python
import argparse
import os

from sleeper_recap import config as cfgmod
from sleeper_recap import enrich, llm, recap, sleeper


def cmd_init(args):
    if os.path.exists(args.config) and not args.force:
        raise SystemExit(f"{args.config} exists; use --force to overwrite")
    cfgmod.save(args.config, cfgmod.scaffold(args.league_id))
    print(f"Wrote {args.config}. Fill in owner_name, email, and fun_facts for each team.")


def cmd_recap(args):
    config = cfgmod.load(args.config)
    league_id = config.get("league_id")
    if not league_id:
        raise SystemExit("config missing league_id; re-run init")
    # rest of cmd_recap unchanged for now
```

Delete `_toml_str`, `json`, and `tomllib` imports from `cli.py`. In `tests/test_cli.py` delete `test_toml_str_roundtrips_emoji` (moved to test_config.py) and its `tomllib` import if unused.

- [ ] **Step 5: Run full suite**

Run: `conda run -n sleeper-recap python -m pytest -q`
Expected: all pass (35 existing minus 1 moved plus 5 new = 40).

- [ ] **Step 6: Commit**

```bash
git add sleeper_recap/config.py sleeper_recap/cli.py tests/test_config.py tests/test_cli.py
git commit -m "Extract config helpers into config.py"
```

---

### Task 2: Extract `run_recap` pipeline

**Files:**
- Modify: `sleeper_recap/cli.py` (cmd_recap)
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `cli.run_recap(config, week=None, season=None, provider=None, model=None, out=None) -> (body: str, out_path: str)`. Writes `body` to `out_path` (default `recaps/week_N_prompt.md` for manual, `recaps/week_N.md` otherwise). Raises SystemExit with the existing one-line messages. Prints enrichment warning to stdout as before.

- [ ] **Step 1: Write failing test**

Append to `tests/test_cli.py`:

```python
def test_run_recap_returns_body_and_path(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    monkeypatch.chdir(tmp_path)
    cfg = {"league_id": "999", "tone": "dry", "teams": {}}
    body, out = cli.run_recap(cfg, week=2, provider="manual")
    assert "Copy everything below" in body
    assert out == "recaps/week_2_prompt.md"
    assert (tmp_path / out).read_text(encoding="utf-8") == body
```

- [ ] **Step 2: Run to verify failure**

Run: `conda run -n sleeper-recap python -m pytest tests/test_cli.py::test_run_recap_returns_body_and_path -q`
Expected: AttributeError, `cli` has no `run_recap`.

- [ ] **Step 3: Implement**

Replace `cmd_recap` in `cli.py` with:

```python
def run_recap(config, week=None, season=None, provider=None, model=None, out=None):
    league_id = config.get("league_id")
    if not league_id:
        raise SystemExit("config missing league_id; re-run init")
    if season and not week:
        raise SystemExit("--season requires --week (past seasons have no current week)")
    league_obj = None
    if season:
        lg = sleeper.league(league_id)
        while lg.get("season") != str(season):
            prev = lg.get("previous_league_id")
            if not prev:
                raise SystemExit(f"no {season} season found in this league's history")
            lg = sleeper.league(prev)
        league_id = lg["league_id"]
        league_obj = lg

    week = week or max(sleeper.nfl_state()["week"] - 1, 1)
    matchups = sleeper.matchups(league_id, week)
    if not matchups or all((m.get("points") or 0) == 0 for m in matchups):
        raise SystemExit(f"no scores yet for week {week}; pick another week with --week")

    if league_obj is None:
        league_obj = sleeper.league(league_id)
    users_list = sleeper.users(league_id)
    rosters_list = sleeper.rosters(league_id)

    try:
        extra = enrich.gather(league_id, league_obj["season"], week, matchups, rosters_list)
    except (SystemExit, Exception) as e:
        print(f"warning: enrichment unavailable ({e}); using basic recap data")
        extra = None

    prompt = recap.build_prompt(league_obj, users_list, rosters_list, matchups, week, config, extra=extra)
    provider = provider or config.get("provider", "manual")
    if provider == "manual":
        header = (
            "Copy everything below into your AI chat of choice "
            "(claude.ai, ChatGPT, Gemini), then copy its reply into your email.\n\n---\n\n"
        )
        body = header + prompt
        default_out = f"recaps/week_{week}_prompt.md"
    else:
        model = model or config.get("model") or llm.DEFAULT_MODELS.get(provider, "")
        body = llm.generate(provider, model, prompt)
        default_out = f"recaps/week_{week}.md"

    out = out or default_out
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    return body, out


def cmd_recap(args):
    config = cfgmod.load(args.config)
    body, out = run_recap(
        config, week=args.week, season=args.season, provider=args.provider, model=args.model, out=args.out
    )
    print(body)
    emails = [t["email"] for t in config.get("teams", {}).values() if t.get("email")]
    print()
    print("Recipients:", ", ".join(emails) if emails else "(none set in config)")
    print(f"Saved to {out}")
```

- [ ] **Step 4: Run full suite**

Run: `conda run -n sleeper-recap python -m pytest -q`
Expected: 41 pass.

- [ ] **Step 5: Commit**

```bash
git add sleeper_recap/cli.py tests/test_cli.py
git commit -m "Extract run_recap from cmd_recap"
```

---

### Task 3: Flask app routes

**Files:**
- Create: `sleeper_recap/app.py`
- Modify: `environment.yml`, create `requirements.txt`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `config.load/save/scaffold`, `cli.run_recap`, `sleeper.league`.
- Produces: `app.create_app() -> Flask`, `app.main(data_dir=None)`, `app.CONFIG = "config.toml"`, `app.PORT = 8484`. Routes per spec section 3; errors as `{"error": msg}` with 400 (404 for missing config on GET /api/config).

- [ ] **Step 1: Add Flask dependency**

`requirements.txt`:

```
requests
flask
```

In `environment.yml` add `- flask` under the pip list after `- requests`. Install: `conda run -n sleeper-recap pip install flask`.

- [ ] **Step 2: Write failing tests**

Create `tests/test_app.py`:

```python
import re

import pytest

from sleeper_recap import app as appmod
from sleeper_recap import enrich, sleeper
from tests.fixtures.week_data import LEAGUE, MATCHUPS, ROSTERS, USERS

_EMPTY_EXTRA = {
    "players": {},
    "stats": {},
    "draft_slots": {},
    "pickups": [],
    "prev_matchups": {},
    "team_streaks": {},
    "hot_cold": {},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sleeper, "league", lambda lid: dict(LEAGUE, league_id=lid, previous_league_id=None))
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: MATCHUPS)
    monkeypatch.setattr(sleeper, "nfl_state", lambda: {"week": 3})
    monkeypatch.setattr(enrich, "gather", lambda *a, **k: dict(_EMPTY_EXTRA))
    return appmod.create_app().test_client()


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Postgame" in r.data


def test_config_404_before_init(client):
    r = client.get("/api/config")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_init_then_get_config(client):
    r = client.post("/api/init", json={"league_id": "999"})
    assert r.status_code == 200
    assert r.get_json()["teams"]["1"]["team_name"] == "Alice Attack"
    assert client.get("/api/config").get_json()["league_id"] == "999"


def test_save_config(client):
    cfg = client.post("/api/init", json={"league_id": "999"}).get_json()
    cfg["teams"]["1"]["email"] = "a@example.com"
    cfg["tone"] = "dry"
    r = client.post("/api/config", json=cfg)
    assert r.status_code == 200
    assert client.get("/api/config").get_json()["teams"]["1"]["email"] == "a@example.com"


def test_seasons_walks_chain(client, monkeypatch):
    leagues = {
        "999": {"name": "T", "season": "2026", "league_id": "999", "previous_league_id": "888"},
        "888": {"name": "T", "season": "2025", "league_id": "888", "previous_league_id": None},
    }
    monkeypatch.setattr(sleeper, "league", lambda lid: leagues[lid])
    client.post("/api/init", json={"league_id": "999"})
    r = client.get("/api/seasons")
    assert r.get_json() == [
        {"season": "2026", "league_id": "999"},
        {"season": "2025", "league_id": "888"},
    ]


def test_generate_manual(client):
    cfg = client.post("/api/init", json={"league_id": "999"}).get_json()
    cfg["teams"]["1"]["email"] = "a@example.com"
    client.post("/api/config", json=cfg)
    r = client.post("/api/generate", json={"week": 2})
    assert r.status_code == 200
    d = r.get_json()
    assert "Copy everything below" in d["body"]
    assert d["out_path"].endswith("week_2_prompt.md")
    assert d["recipients"] == ["a@example.com"]
    assert not re.search(r"[\w.]+@[\w.]+", d["body"])


def test_generate_no_scores_is_400(client, monkeypatch):
    zero = [dict(m, points=0) for m in MATCHUPS]
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: zero)
    client.post("/api/init", json={"league_id": "999"})
    r = client.post("/api/generate", json={"week": 1})
    assert r.status_code == 400
    assert "no scores yet" in r.get_json()["error"]


def test_generate_without_config_is_400(client):
    r = client.post("/api/generate", json={"week": 2})
    assert r.status_code == 400
    assert "init" in r.get_json()["error"]
```

- [ ] **Step 3: Run to verify failure**

Run: `conda run -n sleeper-recap python -m pytest tests/test_app.py -q`
Expected: ImportError for `sleeper_recap.app`.

- [ ] **Step 4: Create `sleeper_recap/app.py`**

```python
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
```

Then create a placeholder `sleeper_recap/static/index.html` containing only `<title>Postgame</title>` so the index test passes (replaced in Task 4).

- [ ] **Step 5: Run full suite**

Run: `conda run -n sleeper-recap python -m pytest -q`
Expected: 49 pass.

- [ ] **Step 6: Commit**

```bash
git add sleeper_recap/app.py sleeper_recap/static/index.html tests/test_app.py requirements.txt environment.yml
git commit -m "Add Flask app with JSON routes"
```

---

### Task 4: Frontend page

**Files:**
- Modify: `sleeper_recap/static/index.html`

**Interfaces:**
- Consumes: routes from Task 3.

- [ ] **Step 1: Write `sleeper_recap/static/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Postgame</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #222; }
  h1 { margin-bottom: 0; }
  section { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
  label { display: block; font-size: 0.85rem; color: #555; margin-top: 0.5rem; }
  input, select, textarea { width: 100%; box-sizing: border-box; padding: 0.4rem; font: inherit; }
  textarea { min-height: 300px; font-family: monospace; }
  button { padding: 0.5rem 1rem; font: inherit; cursor: pointer; margin-top: 0.5rem; }
  .team { border-top: 1px solid #eee; padding: 0.5rem 0; }
  .team h3 { margin: 0.25rem 0; }
  #error { background: #fee; color: #900; padding: 0.5rem; border-radius: 6px; display: none; }
  .muted { color: #666; font-size: 0.9rem; }
  .row { display: flex; gap: 1rem; }
  .row > * { flex: 1; }
</style>
</head>
<body>
<h1>Postgame</h1>
<p class="muted">Weekly recap prompts for your Sleeper league.</p>
<div id="error"></div>

<section id="league">
  <h2>1. League</h2>
  <label>Sleeper league ID (the long number in your league URL)</label>
  <div class="row">
    <input id="league_id" placeholder="1234567890123456789">
    <button id="load">Load league</button>
  </div>
</section>

<section id="teams" style="display:none">
  <h2>2. Teams</h2>
  <label>Tone</label>
  <input id="tone">
  <div id="team_list"></div>
  <button id="save">Save</button>
  <span id="saved" class="muted"></span>
</section>

<section id="generate" style="display:none">
  <h2>3. Generate</h2>
  <div class="row">
    <div><label>Season</label><select id="season"></select></div>
    <div><label>Week</label><select id="week"></select></div>
  </div>
  <button id="go">Generate prompt</button>
  <label>Prompt (paste into claude.ai, ChatGPT, or Gemini, then paste the reply into your email)</label>
  <textarea id="result" readonly></textarea>
  <button id="copy">Copy prompt</button>
  <p id="recipients" class="muted"></p>
  <p id="saved_path" class="muted"></p>
</section>

<script>
const $ = id => document.getElementById(id);
let cfg = null;

function showError(msg) { $("error").textContent = msg; $("error").style.display = msg ? "block" : "none"; }

async function api(path, body) {
  const opts = body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opts);
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

function renderTeams() {
  $("tone").value = cfg.tone || "";
  $("team_list").innerHTML = "";
  for (const [rid, t] of Object.entries(cfg.teams)) {
    const div = document.createElement("div");
    div.className = "team";
    div.innerHTML = `<h3>${t.team_name}</h3>
      <label>Owner name</label><input data-rid="${rid}" data-key="owner_name" value="${t.owner_name || ""}">
      <label>Email</label><input data-rid="${rid}" data-key="email" value="${t.email || ""}">
      <label>Fun facts</label><input data-rid="${rid}" data-key="fun_facts" value="${t.fun_facts || ""}">`;
    $("team_list").appendChild(div);
  }
  $("teams").style.display = "";
  $("generate").style.display = "";
}

async function loadSeasons() {
  const seasons = await api("/api/seasons");
  $("season").innerHTML = seasons.map(s => `<option value="${s.season}">${s.season}</option>`).join("");
  $("week").innerHTML = Array.from({ length: 18 }, (_, i) => `<option value="${i + 1}">Week ${i + 1}</option>`).join("");
}

async function boot() {
  try {
    cfg = await api("/api/config");
    $("league_id").value = cfg.league_id;
    renderTeams();
    await loadSeasons();
  } catch (e) { /* no config yet */ }
}

$("load").onclick = async () => {
  showError("");
  try {
    cfg = await api("/api/init", { league_id: $("league_id").value.trim() });
    renderTeams();
    await loadSeasons();
  } catch (e) { showError(e.message); }
};

$("save").onclick = async () => {
  showError("");
  cfg.tone = $("tone").value;
  for (const el of $("team_list").querySelectorAll("input")) cfg.teams[el.dataset.rid][el.dataset.key] = el.value;
  try {
    cfg = await api("/api/config", cfg);
    $("saved").textContent = "Saved.";
    setTimeout(() => $("saved").textContent = "", 2000);
  } catch (e) { showError(e.message); }
};

$("go").onclick = async () => {
  showError("");
  $("result").value = "Working...";
  try {
    const d = await api("/api/generate", { season: Number($("season").value), week: Number($("week").value) });
    $("result").value = d.body;
    $("recipients").textContent = "Send to: " + (d.recipients.length ? d.recipients.join(", ") : "(no emails set)");
    $("saved_path").textContent = "Saved to " + d.out_path;
  } catch (e) { $("result").value = ""; showError(e.message); }
};

$("copy").onclick = async () => {
  await navigator.clipboard.writeText($("result").value);
  $("copy").textContent = "Copied!";
  setTimeout(() => $("copy").textContent = "Copy prompt", 1500);
};

boot();
</script>
</body>
</html>
```

Note: `season` is always sent, so `run_recap` walks the chain even for the current season (one extra league fetch, harmless). Week is required by the UI so the season+week guard never fires.

- [ ] **Step 2: Add `app` subcommand to CLI**

In `cli.py` `main()`, after `p_recap`:

```python
    p_app = sub.add_parser("app", help="run the local web app")
    p_app.set_defaults(fn=lambda args: __import__("sleeper_recap.app", fromlist=["main"]).main())
```

- [ ] **Step 3: Manual smoke**

Run: `conda run -n sleeper-recap python -m sleeper_recap app` from the repo root (uses existing local `config.toml`). Browser opens. Verify: teams render, edit a fun fact and Save, pick 2025 week 10, Generate, Copy. Confirm `recaps/week_10_prompt.md` written. Ctrl-C to stop.

- [ ] **Step 4: Run suite and commit**

Run: `conda run -n sleeper-recap python -m pytest -q` (49 pass).

```bash
git add sleeper_recap/static/index.html sleeper_recap/cli.py
git commit -m "Add Postgame web page and app subcommand"
```

---

### Task 5: PyInstaller entry and local build

**Files:**
- Create: `postgame.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `postgame.py`**

```python
import os

from sleeper_recap.app import main

main(os.path.join(os.path.expanduser("~"), "Postgame"))
```

- [ ] **Step 2: Ignore build output**

Append to `.gitignore`:

```
build/
dist/
*.spec
```

- [ ] **Step 3: Local build**

```bash
conda run -n sleeper-recap pip install pyinstaller
conda run -n sleeper-recap pyinstaller --onefile --name Postgame \
  --add-data "sleeper_recap/static:sleeper_recap/static" postgame.py
```

Expected: `dist/Postgame` exists.

- [ ] **Step 4: Smoke the binary**

Run `./dist/Postgame`. Expected: console prints the URL, browser opens, page loads (proves static bundling works), `~/Postgame/` created. Load test league 1312070289483378688, generate 2025 week 10. Confirm `~/Postgame/recaps/week_10_prompt.md`. Ctrl-C.

- [ ] **Step 5: Commit**

```bash
git add postgame.py .gitignore
git commit -m "Add PyInstaller entry point"
```

---

### Task 6: Release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Write workflow**

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            asset: Postgame-linux.tar.gz
          - os: macos-latest
            asset: Postgame-macos.zip
          - os: windows-latest
            asset: Postgame-windows.zip
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt pytest pyinstaller
      - run: python -m pytest -q
      - run: pyinstaller --onefile --name Postgame --add-data "sleeper_recap/static${{ runner.os == 'Windows' && ';' || ':' }}sleeper_recap/static" postgame.py
      - name: Archive (Linux)
        if: runner.os == 'Linux'
        run: tar -czf ${{ matrix.asset }} -C dist Postgame
      - name: Archive (macOS)
        if: runner.os == 'macOS'
        run: cd dist && zip ../${{ matrix.asset }} Postgame
      - name: Archive (Windows)
        if: runner.os == 'Windows'
        run: Compress-Archive -Path dist/Postgame.exe -DestinationPath ${{ matrix.asset }}
      - uses: softprops/action-gh-release@v2
        with:
          files: ${{ matrix.asset }}
```

- [ ] **Step 2: Validate YAML locally**

Run: `conda run -n sleeper-recap python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml')); print('ok')"` (install pyyaml if missing: `pip install pyyaml`). Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "Add release workflow for tagged builds"
```

---

### Task 7: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite top of README**

Replace the title and intro through the end of "## Setup" heading with:

```markdown
# Postgame

Drafts a fun weekly recap email for your Sleeper fantasy football league.
Postgame writes a ready-to-paste prompt; you drop it into Claude, ChatGPT,
or Gemini and paste the reply into your email client.

## Download (no install)

Grab the latest file for your computer from the
[Releases page](https://github.com/dmacguigan/Postgame/releases):

- Windows: `Postgame-windows.zip`. Unzip, double-click `Postgame.exe`.
  If SmartScreen appears, click "More info" then "Run anyway".
- macOS: `Postgame-macos.zip`. Unzip, then right-click `Postgame` and
  choose Open (needed the first time; the app is not signed). A Terminal
  window appears; that is the app. Close it to quit.
- Linux: `Postgame-linux.tar.gz`. Extract, then `chmod +x Postgame` if
  needed and run it.

Your browser opens to the app. Enter your league ID, fill in owner names,
emails, and fun facts, then generate a prompt for any week. Everything is
saved in a `Postgame` folder in your home directory.

Find your league ID: open your league at sleeper.com and copy the long
number after `/leagues/` in the URL. On the mobile app, open league
settings, copy the league link, and take the same number.

## Developers

Everything below is for running from source.

### Setup
```

Keep the existing setup, usage, manual mode, tests, and notes sections under "## Developers", demoting their headings one level (`##` becomes `###`). Add under Usage:

```markdown
python -m sleeper_recap app        # local web app in your browser
```

Add a "### Releasing" section:

```markdown
### Releasing

Tag and push; GitHub Actions builds all three binaries and attaches them
to a Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Document Postgame download and release"
```

---

## Self-review

- Spec coverage: data dir (Task 5), config helpers (1), Flask routes and error mapping (3), frontend three panels (4), packaging and requirements (3, 5), release workflow with archives (6), README (7), tests including no-scores 400 and no-email body (3). Covered.
- `--add-data` separator differs on Windows (`;`); handled in workflow expression.
- Type consistency: `run_recap` signature used identically in Tasks 2 and 3; `config.load/save/scaffold` names consistent across 1, 3.
