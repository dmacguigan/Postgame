# Postgame: One-Click Packaged App

Date: 2026-09-01
Repo: github.com/dmacguigan/Postgame (renamed from SleeperFFLeagueUpdates)
Status: design approved by owner, supersedes HANDOFF_SleeperFFLeagueUpdates-main_local-web-app.MD

## Goal

Non-technical league members download one file from a GitHub Release,
double-click it, and get a browser page that drafts a paste-ready recap
prompt. No Python, conda, terminal, or API key required.

## Decisions

- App and executable name: Postgame.
- Distribution: PyInstaller onefile binaries for Windows, macOS, Linux,
  attached to a GitHub Release built by GitHub Actions on `v*` tag push.
- UI shell: Flask on 127.0.0.1:8484, default browser auto-opened.
  Console window stays visible and says "close this window to quit".
- LLM handling: manual mode only in the app. No provider SDKs bundled,
  no key entry, no env-var lookup. The CLI keeps its API providers.
- Data dir: `~/Postgame/` holds `config.toml`, `recaps/`, `.cache/`.
- CLI stays unchanged in behavior (cwd-relative paths).

## Hard constraints (unchanged)

- API keys from env vars only, never on disk, never in logs or output.
- Owner emails never included in any LLM prompt.
- ASCII only in code. Minimal comments. No em dashes anywhere.
- Never git push without explicit owner instruction.

## Design

### 1. Data dir

App entry creates `~/Postgame/` if missing and `os.chdir` into it before
anything else. All existing cwd-relative paths then work unchanged.

### 2. Config helpers (`sleeper_recap/config.py`)

Extract from `cli.py`:

- `load(path)` -> dict (tomllib)
- `save(path, cfg)` -> writes TOML, same format CLI writes today
  (keep `_toml_str` json.dumps ensure_ascii=False behavior)
- `scaffold(league_id)` -> dict from Sleeper league + users + rosters

`cli.py` calls these. Existing 36 tests stay green.

### 3. Flask app (`sleeper_recap/app.py`)

Routes, thin wrappers over existing modules:

- `GET /` serves `sleeper_recap/static/index.html`
- `GET /api/config` -> config dict, or 404 `{"error": "..."}`
- `POST /api/init` `{league_id}` -> scaffold, save, return config
- `POST /api/config` body = config dict -> save, return it
- `GET /api/seasons` -> `[{season, league_id}]` by walking
  `previous_league_id` chain from config league
- `POST /api/generate` `{season, week}` -> `{body, out_path, recipients}`;
  reuses cmd_recap season-resolution and no-scores guard; writes
  `recaps/week_N_prompt.md`

`SystemExit` raised by existing modules is caught and returned as
`{"error": message}` with status 400. UI shows it inline.

`main()`: chdir data dir, start a timer thread that opens
`http://127.0.0.1:8484` after 1s, run Flask (no debug, no reloader).
`python -m sleeper_recap app` calls the same `main()` without chdir
(dev mode keeps cwd).

### 4. Frontend (`sleeper_recap/static/index.html`)

One HTML file, vanilla JS, no build step. Three panels:

1. League: league ID input + Load. Loads config if present, else init.
2. Teams: one row per team (team name read-only, owner_name, email,
   fun_facts editable) plus tone field. Save button.
3. Generate: season select, week select, Generate button. Result
   textarea, Copy button, recipient list, saved-file path.

Error banner at top for `{"error"}` responses.

### 5. Packaging

`requirements.txt`: requests, flask. `environment.yml` adds flask.

Build command (same on all OS):

    pyinstaller --onefile --name Postgame \
      --add-data sleeper_recap/static:sleeper_recap/static \
      sleeper_recap/app.py

Static dir resolved via `os.path.dirname(__file__)`, valid both installed
and frozen.

### 6. Release workflow (`.github/workflows/release.yml`)

- Trigger: push of tag `v*`.
- Matrix: ubuntu-latest, windows-latest, macos-latest.
- Steps: checkout, setup-python 3.12, pip install -r requirements.txt
  pyinstaller, run tests, build, archive:
  - `Postgame-windows.zip`
  - `Postgame-macos.zip`
  - `Postgame-linux.tar.gz`
- `softprops/action-gh-release` attaches archives to the Release for the tag.

Archives are required: raw binary download loses the exec bit.

Skipped: code signing, notarization, macOS .app bundle, version constant
(tag name is the version).

### 7. README

New top section "Download" with per-OS steps and warnings:

- Windows: SmartScreen "More info > Run anyway".
- macOS: unsigned; right-click > Open the first time. A Terminal window
  appears; that is the app. Close it to quit.
- Linux: `chmod +x Postgame` if needed.

Existing setup/CLI docs move under "Developers".

### 8. Testing

- `tests/test_config.py`: load/save round-trip, emoji team name survives.
- `tests/test_app.py`: Flask test client with sleeper monkeypatched
  (follow `_patch_sleeper` in tests/test_cli.py): init, config save,
  seasons, generate happy path, generate week-with-no-scores returns
  400 with message not 500, generated body contains no email addresses.
- Build verified by CI on all three OS plus a local Linux PyInstaller
  smoke against test league 1312070289483378688 (season 2025, week 10).

## Out of scope

- API providers in the app, key entry of any kind.
- Automated email sending.
- Code signing, auto-update.
