# Sleeper Weekly Recap Email Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI that pulls weekly Sleeper fantasy football results and drafts a fun recap email body with the user's chosen LLM (Anthropic, OpenAI, or Gemini).

**Architecture:** Small Python package `sleeper_recap` with four modules: `sleeper.py` (public Sleeper REST API via requests), `recap.py` (pure prompt builder), `llm.py` (lazy-import provider dispatch), `cli.py` (argparse: `init` scaffolds config, `recap` generates the email). Config is TOML read with stdlib `tomllib`.

**Tech Stack:** Python >= 3.11, conda/mamba env, `requests`, `pytest`; optional `anthropic` / `openai` / `google-genai` SDKs.

**Spec:** `docs/superpowers/specs/2026-09-01-sleeper-recap-design.md`

## Global Constraints

- Python >= 3.11 (needs stdlib `tomllib`).
- Required pip deps: `requests`, `pytest` only. Provider SDKs (`anthropic`, `openai`, `google-genai`) are OPTIONAL, imported lazily inside provider functions, listed commented-out in `environment.yml`.
- API keys come from env vars only (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`). NEVER write keys to disk, config, output files, or error messages. Config schema has no key fields.
- Anthropic may also resolve credentials from an `ant auth login` / Claude CLI profile, so do not hard-fail on missing `ANTHROPIC_API_KEY`.
- Owner email addresses must never appear in the LLM prompt; they are only printed as a recipient list.
- ASCII only in all code files. Minimal comments. No em dashes anywhere.
- Test league for live verification: `1312070289483378688`.
- Never `git push` except in Task 5 (explicitly authorized initial repo setup).
- Run all commands from repo root: `/home/dmacguig/Documents/GitHub/SleeperFFLeagueUpdates`.
- Tests run with the repo-root conda env python. If `pytest` is unavailable in the active env, run `mamba env create -f environment.yml` (or `conda`) once, then `conda run -n sleeper-recap python -m pytest`.

---

### Task 1: Scaffolding + Sleeper API client

**Files:**
- Create: `environment.yml`
- Create: `.gitignore`
- Create: `sleeper_recap/__init__.py` (empty)
- Create: `sleeper_recap/sleeper.py`
- Test: `tests/test_sleeper.py`

**Interfaces:**
- Produces: `sleeper.league(league_id) -> dict`, `sleeper.users(league_id) -> list[dict]`, `sleeper.rosters(league_id) -> list[dict]`, `sleeper.matchups(league_id, week) -> list[dict]`, `sleeper.nfl_state() -> dict`. All raise `SystemExit` with a clear message on 404/null responses.

- [ ] **Step 1: Write environment and gitignore files**

`environment.yml`:
```yaml
name: sleeper-recap
channels:
  - conda-forge
dependencies:
  - python>=3.11
  - pip
  - pip:
      - requests
      - pytest
      # Install only the SDK for your chosen LLM provider:
      # - anthropic
      # - openai
      # - google-genai
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
config.toml
recaps/
```

- [ ] **Step 2: Write the failing test**

`tests/test_sleeper.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_sleeper.py -v`
Expected: FAIL (ModuleNotFoundError or ImportError for `sleeper_recap.sleeper`)

- [ ] **Step 4: Write implementation**

`sleeper_recap/__init__.py`: empty file.

`sleeper_recap/sleeper.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_sleeper.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add environment.yml .gitignore sleeper_recap tests
git commit -m "Add env setup and Sleeper API client"
```

---

### Task 2: Recap prompt builder

**Files:**
- Create: `sleeper_recap/recap.py`
- Create: `tests/fixtures/week_data.py`
- Test: `tests/test_recap.py`

**Interfaces:**
- Consumes: raw dicts/lists shaped like Sleeper API responses (from Task 1 functions).
- Produces: `recap.build_prompt(league, users, rosters, matchups, week, config) -> str`. `config` is the parsed TOML dict; `config["teams"]` keys are roster_id strings.

- [ ] **Step 1: Write fixture data**

`tests/fixtures/__init__.py`: empty file.

`tests/fixtures/week_data.py`:
```python
LEAGUE = {"name": "Test League", "season": "2026", "total_rosters": 4}

USERS = [
    {"user_id": "u1", "display_name": "alice_ff", "metadata": {"team_name": "Alice Attack"}},
    {"user_id": "u2", "display_name": "bob_ff", "metadata": {}},
    {"user_id": "u3", "display_name": "carol_ff", "metadata": {"team_name": "Carol Crush"}},
    {"user_id": "u4", "display_name": "dave_ff", "metadata": {}},
]

ROSTERS = [
    {"roster_id": 1, "owner_id": "u1", "settings": {"wins": 2, "losses": 0, "fpts": 250}},
    {"roster_id": 2, "owner_id": "u2", "settings": {"wins": 1, "losses": 1, "fpts": 220}},
    {"roster_id": 3, "owner_id": "u3", "settings": {"wins": 0, "losses": 2, "fpts": 180}},
    {"roster_id": 4, "owner_id": "u4", "settings": {"wins": 1, "losses": 1, "fpts": 210}},
]

MATCHUPS = [
    {"roster_id": 1, "matchup_id": 1, "points": 130.5},
    {"roster_id": 2, "matchup_id": 1, "points": 90.25},
    {"roster_id": 3, "matchup_id": 2, "points": 100.0},
    {"roster_id": 4, "matchup_id": 2, "points": 101.5},
]

CONFIG = {
    "league_id": "999",
    "provider": "anthropic",
    "tone": "funny, light trash talk",
    "teams": {
        "1": {"team_name": "Alice Attack", "owner_name": "Alice", "email": "alice@example.com", "fun_facts": "afraid of kickers"},
        "2": {"team_name": "Bob Bombers", "owner_name": "Bob", "email": "bob@example.com", "fun_facts": "drafts by jersey color"},
        "3": {"team_name": "Carol Crush", "owner_name": "Carol", "email": "carol@example.com", "fun_facts": ""},
        "4": {"team_name": "Dave Dynasty", "owner_name": "Dave", "email": "dave@example.com", "fun_facts": "three-time last place"},
    },
}
```

- [ ] **Step 2: Write the failing test**

`tests/test_recap.py`:
```python
from sleeper_recap import recap
from tests.fixtures.week_data import CONFIG, LEAGUE, MATCHUPS, ROSTERS, USERS


def prompt():
    return recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG)


def test_matchup_results_present():
    p = prompt()
    assert "Alice Attack" in p
    assert "130.5" in p and "90.25" in p
    assert "week 2" in p.lower()


def test_superlatives():
    p = prompt()
    # matchup 2 margin 1.5 is closest, matchup 1 margin 40.25 is blowout
    closest_idx = p.index("Closest game")
    assert "Dave Dynasty" in p[closest_idx:closest_idx + 200]
    blowout_idx = p.index("Biggest blowout")
    assert "Alice Attack" in p[blowout_idx:blowout_idx + 200]
    top_idx = p.index("Top scorer")
    assert "Alice Attack" in p[top_idx:top_idx + 100]


def test_owner_info_included_emails_excluded():
    p = prompt()
    assert "afraid of kickers" in p
    assert "Alice" in p
    assert "alice@example.com" not in p
    assert "@example.com" not in p


def test_tone_and_records():
    p = prompt()
    assert "light trash talk" in p
    assert "2-0" in p
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_recap.py -v`
Expected: FAIL (no module `sleeper_recap.recap`)

- [ ] **Step 4: Write implementation**

`sleeper_recap/recap.py`:
```python
def _team_info(users, rosters, config):
    display = {}
    for u in users:
        meta = u.get("metadata") or {}
        display[u["user_id"]] = meta.get("team_name") or u["display_name"]
    teams_cfg = config.get("teams", {})
    info = {}
    for r in rosters:
        rid = r["roster_id"]
        cfg = teams_cfg.get(str(rid), {})
        settings = r.get("settings", {})
        info[rid] = {
            "name": cfg.get("team_name") or display.get(r.get("owner_id"), f"Roster {rid}"),
            "owner": cfg.get("owner_name", ""),
            "facts": cfg.get("fun_facts", ""),
            "record": f"{settings.get('wins', 0)}-{settings.get('losses', 0)}",
            "fpts": settings.get("fpts", 0),
        }
    return info


def build_prompt(league, users, rosters, matchups, week, config):
    info = _team_info(users, rosters, config)

    games = {}
    for m in matchups:
        games.setdefault(m["matchup_id"], []).append(m)
    results = []
    for pair in games.values():
        if len(pair) != 2:
            continue
        hi, lo = sorted(pair, key=lambda m: m["points"], reverse=True)
        results.append((hi, lo, hi["points"] - lo["points"]))
    if not results:
        raise SystemExit(f"no head-to-head matchups found for week {week}")

    def label(m):
        t = info[m["roster_id"]]
        return f"{t['name']} ({t['owner']})" if t["owner"] else t["name"]

    lines = [
        f"You are writing a weekly recap email for the fantasy football league '{league['name']}' (week {week}, {league['season']} season).",
        f"Tone: {config.get('tone', 'fun and lighthearted')}.",
        "",
        "This week's results:",
    ]
    for hi, lo, margin in results:
        lines.append(
            f"- {label(hi)} beat {label(lo)} {hi['points']}-{lo['points']} (margin {round(margin, 2)})"
        )

    closest = min(results, key=lambda r: r[2])
    blowout = max(results, key=lambda r: r[2])
    top = max(matchups, key=lambda m: m["points"])
    lines += [
        "",
        f"Closest game: {label(closest[0])} over {label(closest[1])} by {round(closest[2], 2)}.",
        f"Biggest blowout: {label(blowout[0])} over {label(blowout[1])} by {round(blowout[2], 2)}.",
        f"Top scorer of the week: {label(top)} with {top['points']}.",
        "",
        "Season standings (record, total points):",
    ]
    standings = sorted(info.values(), key=lambda t: (t["record"], t["fpts"]), reverse=True)
    for t in standings:
        lines.append(f"- {t['name']}: {t['record']}, {t['fpts']} pts")

    facts = [f"- {t['name']} ({t['owner']}): {t['facts']}" for t in info.values() if t["facts"]]
    if facts:
        lines += ["", "Fun facts about the owners (weave these in where funny):"] + facts

    lines += [
        "",
        "Write the recap email now. Requirements:",
        "- First line: 'Subject: <a fun subject line>'. Then a blank line, then the email body.",
        "- Plain text only, no markdown formatting.",
        "- Cover every matchup, call out the closest game, the blowout, and the top scorer.",
        "- Keep it fun and readable, roughly 300-500 words.",
        "- Do not invent players or stats beyond what is given.",
    ]
    return "\n".join(lines)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_recap.py -v`
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add sleeper_recap/recap.py tests
git commit -m "Add recap prompt builder"
```

---

### Task 3: LLM provider dispatch

**Files:**
- Create: `sleeper_recap/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: prompt string from `recap.build_prompt`.
- Produces: `llm.generate(provider, model, prompt) -> str` and `llm.DEFAULT_MODELS: dict[str, str]` with keys `anthropic`, `openai`, `gemini`.

- [ ] **Step 1: Write the failing test**

`tests/test_llm.py`:
```python
import sys
import types

import pytest

from sleeper_recap import llm


def test_unknown_provider_exits():
    with pytest.raises(SystemExit, match="unknown provider"):
        llm.generate("grok", "x", "hi")


def test_openai_missing_key_exits(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        llm.generate("openai", "gpt-5", "hi")


def test_gemini_missing_key_exits(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        llm.generate("gemini", "gemini-2.5-pro", "hi")


def test_missing_sdk_message(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(SystemExit, match="pip install openai"):
        llm.generate("openai", "gpt-5", "hi")


def test_anthropic_call_path(monkeypatch):
    fake = types.SimpleNamespace()

    class FakeBlock:
        type = "text"
        text = "Subject: Week 1\n\nHello league"

    class FakeResponse:
        stop_reason = "end_turn"
        content = [FakeBlock()]

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-5"
            assert kwargs["messages"][0]["content"] == "hi"
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self):
            self.messages = FakeMessages()

    fake.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    assert llm.generate("anthropic", "claude-opus-5", "hi") == "Subject: Week 1\n\nHello league"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_llm.py -v`
Expected: FAIL (no module `sleeper_recap.llm`)

- [ ] **Step 3: Write implementation**

Note: `import` of a `sys.modules` entry set to `None` raises `ImportError`, which is what `test_missing_sdk_message` exercises.

`sleeper_recap/llm.py`:
```python
import os

DEFAULT_MODELS = {
    "anthropic": "claude-opus-5",
    "openai": "gpt-5",
    "gemini": "gemini-2.5-pro",
}


def _require_env(var):
    if not os.environ.get(var):
        raise SystemExit(f"set {var} in your environment")


def _import(name):
    try:
        module = __import__(name)
        if module is None:
            raise ImportError(name)
        return module
    except ImportError:
        raise SystemExit(f"provider needs the SDK: pip install {name}")


def _anthropic(model, prompt):
    anthropic = _import("anthropic")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise SystemExit("model declined the request; try rewording tone or fun facts")
    return "".join(b.text for b in resp.content if b.type == "text")


def _openai(model, prompt):
    _require_env("OPENAI_API_KEY")
    openai = _import("openai")
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def _gemini(model, prompt):
    _require_env("GEMINI_API_KEY")
    genai = _import("google.genai").genai
    client = genai.Client()
    resp = client.models.generate_content(model=model, contents=prompt)
    return resp.text


_PROVIDERS = {"anthropic": _anthropic, "openai": _openai, "gemini": _gemini}


def generate(provider, model, prompt):
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise SystemExit(f"unknown provider '{provider}'; choose from {sorted(_PROVIDERS)}")
    return fn(model, prompt)
```

Implementation note for `_gemini`: `__import__("google.genai")` returns the top-level `google` package, so access the submodule via attribute. If the attribute access pattern fails under test, use `importlib.import_module("google.genai")` wrapped in the same try/except ImportError with message "pip install google-genai". The error message for the gemini SDK must say `pip install google-genai` (the PyPI name), so `_gemini` should catch and re-raise with the correct package name:

```python
def _gemini(model, prompt):
    _require_env("GEMINI_API_KEY")
    try:
        import importlib
        genai = importlib.import_module("google.genai")
        if genai is None:
            raise ImportError
    except ImportError:
        raise SystemExit("provider needs the SDK: pip install google-genai")
    client = genai.Client()
    resp = client.models.generate_content(model=model, contents=prompt)
    return resp.text
```

Use this second `_gemini` form (importlib) as the actual implementation, and use the plain `_import` helper only for `anthropic` and `openai`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_llm.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add sleeper_recap/llm.py tests/test_llm.py
git commit -m "Add LLM provider dispatch with lazy imports"
```

---

### Task 4: CLI, config scaffolding, README

**Files:**
- Create: `sleeper_recap/cli.py`
- Create: `sleeper_recap/__main__.py`
- Create: `config.example.toml`
- Create: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `sleeper.league/users/rosters/matchups/nfl_state` (Task 1), `recap.build_prompt` (Task 2), `llm.generate` and `llm.DEFAULT_MODELS` (Task 3).
- Produces: `cli.main(argv=None)` entry point; `python -m sleeper_recap init|recap`.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import pytest

from sleeper_recap import cli, llm, sleeper
from tests.fixtures.week_data import LEAGUE, MATCHUPS, ROSTERS, USERS


def _patch_sleeper(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: LEAGUE)
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: MATCHUPS)
    monkeypatch.setattr(sleeper, "nfl_state", lambda: {"week": 3})


def test_init_writes_config(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    text = cfg.read_text()
    assert 'league_id = "999"' in text
    assert "[teams.1]" in text
    assert "Alice Attack" in text
    assert 'owner_name = ""' in text


def test_init_refuses_overwrite(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    cfg = tmp_path / "config.toml"
    cfg.write_text("existing")
    with pytest.raises(SystemExit, match="--force"):
        cli.main(["init", "--league-id", "999", "--config", str(cfg)])


def test_recap_writes_output(tmp_path, monkeypatch, capsys):
    _patch_sleeper(monkeypatch)
    monkeypatch.setattr(llm, "generate", lambda p, m, prompt: "Subject: Wow\n\nBody here")
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    out = tmp_path / "email.md"
    cli.main(["recap", "--config", str(cfg), "--week", "2", "--out", str(out)])
    assert out.read_text() == "Subject: Wow\n\nBody here"
    captured = capsys.readouterr().out
    assert "Body here" in captured
    assert "Recipients:" in captured


def test_recap_default_week_from_state(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    seen = {}

    def fake_matchups(lid, week):
        seen["week"] = week
        return MATCHUPS

    monkeypatch.setattr(sleeper, "matchups", fake_matchups)
    monkeypatch.setattr(llm, "generate", lambda p, m, prompt: "x")
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    cli.main(["recap", "--config", str(cfg), "--out", str(tmp_path / "e.md")])
    assert seen["week"] == 2


def test_recap_no_scores_exits(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    zero = [dict(m, points=0) for m in MATCHUPS]
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: zero)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    with pytest.raises(SystemExit, match="no scores yet"):
        cli.main(["recap", "--config", str(cfg), "--week", "1"])


def test_recap_missing_config_exits():
    with pytest.raises(SystemExit, match="init"):
        cli.main(["recap", "--config", "/nonexistent/config.toml"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL (no module `sleeper_recap.cli`)

- [ ] **Step 3: Write implementation**

`sleeper_recap/cli.py`:
```python
import argparse
import os
import tomllib

from sleeper_recap import llm, recap, sleeper


def _toml_str(value):
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def cmd_init(args):
    if os.path.exists(args.config) and not args.force:
        raise SystemExit(f"{args.config} exists; use --force to overwrite")
    users = sleeper.users(args.league_id)
    rosters = sleeper.rosters(args.league_id)
    names = {}
    usernames = {}
    for u in users:
        meta = u.get("metadata") or {}
        names[u["user_id"]] = meta.get("team_name") or u["display_name"]
        usernames[u["user_id"]] = u["display_name"]
    lines = [
        f"league_id = {_toml_str(args.league_id)}",
        'provider = "anthropic"  # anthropic | openai | gemini',
        f'model = {_toml_str(llm.DEFAULT_MODELS["anthropic"])}',
        'tone = "funny, light trash talk, inside jokes welcome"',
        "",
    ]
    for r in sorted(rosters, key=lambda r: r["roster_id"]):
        owner_id = r.get("owner_id")
        lines += [
            f"[teams.{r['roster_id']}]",
            f"team_name = {_toml_str(names.get(owner_id, ''))}",
            f"sleeper_username = {_toml_str(usernames.get(owner_id, ''))}",
            'owner_name = ""',
            'email = ""',
            'fun_facts = ""',
            "",
        ]
    with open(args.config, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {args.config}. Fill in owner_name, email, and fun_facts for each team.")


def cmd_recap(args):
    try:
        with open(args.config, "rb") as f:
            config = tomllib.load(f)
    except FileNotFoundError:
        raise SystemExit(f"{args.config} not found; run: python -m sleeper_recap init --league-id YOUR_ID")
    league_id = config["league_id"]

    week = args.week or max(sleeper.nfl_state()["week"] - 1, 1)
    matchups = sleeper.matchups(league_id, week)
    if not matchups or all((m.get("points") or 0) == 0 for m in matchups):
        raise SystemExit(f"no scores yet for week {week}; pick another week with --week")

    prompt = recap.build_prompt(
        sleeper.league(league_id),
        sleeper.users(league_id),
        sleeper.rosters(league_id),
        matchups,
        week,
        config,
    )
    provider = args.provider or config.get("provider", "anthropic")
    model = args.model or config.get("model") or llm.DEFAULT_MODELS.get(provider, "")
    body = llm.generate(provider, model, prompt)

    out = args.out or f"recaps/week_{week}.md"
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w") as f:
        f.write(body)

    print(body)
    emails = [t["email"] for t in config.get("teams", {}).values() if t.get("email")]
    print()
    print("Recipients:", ", ".join(emails) if emails else "(none set in config)")
    print(f"Saved to {out}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sleeper_recap")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="scaffold config.toml from your league")
    p_init.add_argument("--league-id", required=True)
    p_init.add_argument("--config", default="config.toml")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(fn=cmd_init)

    p_recap = sub.add_parser("recap", help="draft the weekly recap email")
    p_recap.add_argument("--week", type=int)
    p_recap.add_argument("--provider", choices=["anthropic", "openai", "gemini"])
    p_recap.add_argument("--model")
    p_recap.add_argument("--config", default="config.toml")
    p_recap.add_argument("--out")
    p_recap.set_defaults(fn=cmd_recap)

    args = parser.parse_args(argv)
    args.fn(args)
```

`sleeper_recap/__main__.py`:
```python
from sleeper_recap.cli import main

main()
```

`config.example.toml`:
```toml
league_id = "1312070289483378688"
provider = "anthropic"  # anthropic | openai | gemini
model = "claude-opus-5"
tone = "funny, light trash talk, inside jokes welcome"

# One block per team, keyed by Sleeper roster_id.
# Run `python -m sleeper_recap init --league-id YOUR_ID` to prefill these.
[teams.1]
team_name = "Example Team"
sleeper_username = "example_user"
owner_name = "Jane Example"
email = "jane@example.com"
fun_facts = "Has never won a championship. Owns a dachshund named Gronk."
```

`README.md`:
```markdown
# Sleeper Weekly Recap

Drafts a fun weekly recap email for your Sleeper fantasy football league
using the LLM of your choice (Anthropic Claude, OpenAI, or Google Gemini).
You copy the draft into your own email client and send it yourself.

## Setup

1. Create the conda environment:

   ```bash
   mamba env create -f environment.yml
   mamba activate sleeper-recap
   ```

2. Install the SDK for your LLM provider (pick one or more):

   ```bash
   pip install anthropic      # for Claude
   pip install openai         # for GPT
   pip install google-genai   # for Gemini
   ```

3. Set your API key as an environment variable (never stored on disk):

   ```bash
   export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY / GEMINI_API_KEY
   ```

   Claude users with the Claude CLI already logged in (`ant auth login`)
   can skip this; the SDK picks up those credentials.

4. Scaffold your league config:

   ```bash
   python -m sleeper_recap init --league-id YOUR_LEAGUE_ID
   ```

   Then edit `config.toml`: fill in each owner's real name, email, and
   fun facts. This file stays on your machine (it is gitignored).

## Usage

```bash
python -m sleeper_recap recap                 # most recent completed week
python -m sleeper_recap recap --week 3        # specific week
python -m sleeper_recap recap --provider openai --model gpt-5
```

The draft prints to the terminal and is saved to `recaps/week_N.md`,
followed by the recipient email list from your config.

## Notes

- API keys are read from environment variables only and are never written
  to any file.
- Owner emails are never sent to the LLM; they are only printed locally.
```

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest -v`
Expected: all tests PASS (Tasks 1-4)

- [ ] **Step 5: Commit**

```bash
git add sleeper_recap config.example.toml README.md tests/test_cli.py
git commit -m "Add CLI, example config, and README"
```

---

### Task 5: Private GitHub repo

**Files:** none created; git/GitHub operations only.

**Interfaces:**
- Consumes: completed working tree from Tasks 1-4.

- [ ] **Step 1: Verify clean tree and passing tests**

Run: `git status --short` (expect empty) and `python -m pytest` (expect all pass).

- [ ] **Step 2: Create private repo and push**

```bash
gh repo create SleeperFFLeagueUpdates --private --source . --push
```

Expected: repo created at `dmacguigan/SleeperFFLeagueUpdates`, main branch pushed. This is the ONLY authorized push.

- [ ] **Step 3: Verify**

Run: `gh repo view dmacguigan/SleeperFFLeagueUpdates --json visibility,defaultBranchRef`
Expected: `"visibility": "PRIVATE"`, default branch `main`.

---

### Task 6: Live verification against test league

**Files:** none committed; produces local `config.toml` and `recaps/` output (both gitignored).

**Interfaces:**
- Consumes: full CLI from Task 4.

- [ ] **Step 1: Live init**

Run: `python -m sleeper_recap init --league-id 1312070289483378688`
Expected: `config.toml` written with 8 `[teams.N]` blocks and real team names from the HMMMMF Keeper League.

- [ ] **Step 2: Live recap attempt**

Run: `python -m sleeper_recap recap --week 1`
Expected either:
- A drafted email saved to `recaps/week_1.md` (if week 1 has scores and Anthropic credentials resolve), or
- Exit with `no scores yet for week 1` (valid: 2026 week 1 may be in progress), or
- A clear credential message naming the env var (valid if no key available).

Record which outcome occurred; all three are acceptable. Do NOT commit `config.toml` or `recaps/`.

- [ ] **Step 3: Report**

Summarize live results (league name seen, teams found, recap outcome) back to the orchestrator.
