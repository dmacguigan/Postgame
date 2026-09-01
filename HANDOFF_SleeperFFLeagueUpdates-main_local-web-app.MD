# Handoff: Local Web App for Sleeper Recap Tool

Date: 2026-09-01
Repo: github.com/dmacguigan/SleeperFFLeagueUpdates (private), branch main at ad95a74
Status: design approved by owner, not yet implemented

## What exists today

Working Python CLI (`python -m sleeper_recap`) that drafts fantasy football
recap emails for a Sleeper league. Modules in `sleeper_recap/`:

- `sleeper.py`: Sleeper API client (public, keyless). League, users, rosters,
  matchups, NFL state, transactions, draft picks, plus cached `players()` and
  `season_stats()` blobs (24h mtime cache in gitignored `.cache/`).
- `enrich.py`: `gather(league_id, season, week, matchups, rosters)` builds
  enrichment context: draft slots, waiver pickups, previous-week matchups,
  team W/L streaks, player hot/cold flags.
- `recap.py`: `build_prompt(league, users, rosters, matchups, week, config,
  extra=None)` pure prompt builder; `extra` adds matchup details, roster
  tables, pickups, form guide sections.
- `llm.py`: `generate(provider, model, prompt)` for anthropic/openai/gemini,
  lazy SDK imports; `DEFAULT_MODELS`.
- `cli.py`: `init` (scaffold config.toml from league) and `recap`
  (`--week`, `--season`, `--provider`, `--model`, `--out`).

Key behaviors: provider defaults to `manual` (writes paste-ready prompt to
`recaps/week_N_prompt.md`, no API needed); `--season` walks Sleeper's
`previous_league_id` chain (requires `--week`); enrichment degrades
gracefully to basic prompt with a warning if fetches fail.

Environment: conda env `sleeper-recap` from `environment.yml` (python>=3.11,
requests, pytest; provider SDKs optional). Tests: `python -m pytest`,
currently 36 passing. Test league ID: 1312070289483378688 (8-team keeper
league, live-verified).

## Hard constraints (owner requirements, do not relax)

- API keys from env vars only. NEVER written to disk, config, logs, output,
  or error messages. Config schema has no key fields.
- `config.toml` and `recaps/` are gitignored (real names and emails).
- Owner emails never included in any LLM prompt; local recipient list only.
- ASCII only in code. Minimal comments. No em dashes anywhere.
- Never git push without explicit owner instruction.

## Approved app decisions

1. Staged approach: local web UI now for users who can run Python; packaged
   one-click installers (PyInstaller or similar) deferred to a later phase.
2. Manual-first LLM handling: app's happy path is copy-the-prompt into
   claude.ai/ChatGPT/Gemini. API providers usable only when their env var
   was set before launch. The app itself never collects or stores keys.
3. Stack: Flask (add to environment.yml pip deps). Localhost only.

## Design

New command `python -m sleeper_recap app`:

- Flask server bound to 127.0.0.1:8484 only; auto-open browser
  (`webbrowser.open`) after start.
- Single page, four panels:
  1. League: league ID input + Load button. Loads existing `config.toml`
     if present, else runs init logic to scaffold from the Sleeper API.
  2. Teams: form per team (team name read-only from Sleeper, editable
     owner_name, email, fun_facts). Save writes `config.toml`, exact same
     TOML format the CLI writes (CLI and app stay interchangeable).
  3. Generate: season picker (walk previous_league_id chain to list
     available seasons), week picker, provider dropdown (manual default;
     anthropic/openai/gemini options disabled unless their env var is set,
     grayed out with a tooltip naming the var), tone text field, Generate.
  4. Result: output textarea (prompt in manual mode, drafted email in API
     mode), Copy to clipboard button, recipient email list below, and note
     of the file path saved under `recaps/`.
- Backend routes are thin wrappers over existing modules; extract the
  config read/write from `cli.py` into shared functions (e.g. a small
  `sleeper_recap/config.py`) rather than duplicating. Suggested routes:
  - `GET /` static page
  - `GET /api/config` -> parsed config or 404-with-hint
  - `POST /api/init` {league_id} -> scaffold + return config
  - `POST /api/config` -> save edited teams/tone/provider
  - `GET /api/seasons` -> [{season, league_id}] from chain walk
  - `POST /api/generate` {season, week, provider, model} -> {body, out_path,
    recipients, mode}
  - `GET /api/providers` -> {anthropic: bool, openai: bool, gemini: bool}
    (env var presence only; never values)
- Errors: convert SystemExit from existing modules into JSON error payloads
  with the same one-line messages; the UI shows them inline.
- No auth (localhost only). No new disk writes beyond config.toml and
  recaps/ (both already gitignored).

## Implementation plan sketch

1. Extract config read/write helpers from cli.py into `config.py`; keep CLI
   tests green (36).
2. Flask app module `sleeper_recap/app.py` with the routes above, plus
   `app` subcommand in cli.py. Route tests via Flask test client with
   sleeper/llm monkeypatched (follow the mocking pattern in
   tests/test_cli.py `_patch_sleeper`).
3. Static single-page frontend (one HTML file, vanilla JS, no build step)
   in `sleeper_recap/static/`.
4. README section "App" with launch instructions.
5. Live smoke against test league: load, edit a team, generate 2025 week 10
   manual prompt, copy button works.

Note for step 2 tests: `cmd_recap`-equivalent logic in the app should reuse
the same season-resolution and no-scores guard behavior; add a route test
for the week-with-no-scores case (returns the "no scores yet" message, not
a 500) and one asserting no email addresses appear in generated prompt body.

## Gotchas learned during CLI development

- Sleeper matchup pairing: group by `matchup_id`, exactly-2 entries make a
  game; unpaired entries are skipped everywhere.
- Standings/team sort must be numeric (wins, fpts), never the record string.
- TOML writing: `_toml_str` uses `json.dumps(value, ensure_ascii=False)`;
  plain `json.dumps` breaks emoji team names (surrogate escapes are invalid
  TOML).
- Always `encoding="utf-8"` on file writes; LLM prose and team names carry
  non-ASCII.
- Week clamps: current-week default is `nfl_state week - 1` min 1; any
  lookback loops must clamp at week 1 (Sleeper has no week 0).
- The 2026 season had no scored weeks as of this handoff; use
  `--season 2025 --week N` (season chain) for real-data testing.
- `conda run` output is occasionally swallowed when piped in command chains;
  re-run solo if a result line is missing.

## Out of scope for this phase

- Packaged installers (phase 2; PyInstaller plus the Flask app is the
  intended route).
- Automated email sending.
- Any key entry/storage in the UI.
