# Sleeper Weekly Recap Email Generator - Design

Date: 2026-09-01
Status: approved design, pending user spec review

## Purpose

CLI tool for a Sleeper fantasy football league manager. Pulls weekly matchup
results from the Sleeper API, combines them with manager-maintained owner info,
and uses an LLM (Anthropic, OpenAI, or Google Gemini) to draft a fun recap
email body. The manager copies the draft into their own email client and sends
it manually. Automated sending is out of scope for now.

Test league: `1312070289483378688` ("HMMMMF Keeper League", 8 teams, 2026
season).

## Environment and dependencies

- Python >= 3.11, managed with conda/mamba via `environment.yml`.
- Required dependency (pip section of environment.yml): `requests`.
- Provider SDKs are optional: `anthropic`, `openai`, `google-genai` appear
  commented out in environment.yml; user uncomments/installs only the one(s)
  for their chosen provider. `llm.py` imports the SDK lazily inside each
  provider function; a missing package exits with a clear message, e.g.
  "provider anthropic needs: pip install anthropic".
- Anthropic note: the `anthropic` SDK also picks up `ant auth login` / Claude
  CLI credentials automatically, so `ANTHROPIC_API_KEY` may be unnecessary
  for those users. OpenAI and Gemini always need their env var.
- Config parsing: stdlib `tomllib` (read), plain string templating (write).

## Security: API keys

- Keys are read from environment variables only: `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `GEMINI_API_KEY`.
- Keys are NEVER written to disk: not in config files, not in generated
  output, not in logs or error messages.
- Error messages that involve a provider name the env var to set; they never
  echo key values. Exception text from provider SDKs is passed through only
  after confirming SDK errors do not embed the key (they do not; they carry
  request IDs and status codes).
- `config.toml` schema has no key fields at all, so keys cannot end up there.
- `.gitignore` excludes `config.toml` (contains real names and email
  addresses) and generated `recaps/` output. A committed
  `config.example.toml` documents the schema with placeholder values.

## Package layout

```
sleeper_recap/
  __init__.py
  __main__.py      # python -m sleeper_recap
  cli.py           # argparse, subcommands: init, recap
  sleeper.py       # Sleeper API client (requests, public API, no auth)
  recap.py         # join matchup data + config, build LLM prompt
  llm.py           # provider dispatch: anthropic | openai | gemini
config.example.toml
environment.yml
README.md
tests/
  test_recap.py    # prompt building against canned fixture
  fixtures/        # canned Sleeper API JSON
```

## Config schema (`config.toml`)

```toml
league_id = "1312070289483378688"
provider = "anthropic"            # anthropic | openai | gemini
model = "claude-opus-5"           # provider-specific model id
tone = "funny, light trash talk, inside jokes welcome"  # optional style notes

[teams.1]                          # keyed by Sleeper roster_id
team_name = "Team Name"            # prefilled by init from Sleeper
sleeper_username = "someuser"      # prefilled by init
owner_name = ""                    # manager fills in
email = ""                         # manager fills in
fun_facts = ""                     # manager fills in, free text
```

Default models per provider when `model` omitted: anthropic
`claude-opus-5`, openai `gpt-5`, gemini `gemini-2.5-pro`.

## Sleeper API client (`sleeper.py`)

Base URL `https://api.sleeper.app/v1`. Public, read-only, no key. Endpoints:

- `GET /league/{id}` - league name, season, settings
- `GET /league/{id}/users` - display names, user ids
- `GET /league/{id}/rosters` - roster_id, owner_id, season record, points
- `GET /league/{id}/matchups/{week}` - per-roster points and matchup_id
- `GET /state/nfl` - current week auto-detection

One thin function per endpoint returning parsed JSON; raise a clear error on
HTTP failure or unknown league. Requests use a shared `requests.Session` and
a timeout.

Default week when `--week` not given: `state.week - 1` clamped to >= 1
(most recently completed week). If the requested week's matchups have all-zero
points, exit with a clear "no scores yet for week N" message.

## Recap builder (`recap.py`)

Pure function: (league, rosters, users, matchups, week, config) -> prompt
string. Assembles per-matchup pairs via `matchup_id`, computes:

- winner/loser and score per matchup
- margin; flags closest game and biggest blowout
- top-scoring team of the week
- season records/standings from roster data

Prompt includes tone notes, per-team owner names and fun facts, and
instructs the LLM to write an email body only (no subject line handling
beyond a suggested subject as the first line), plain text, fun tone.
Owner emails are NOT included in the LLM prompt; they are printed separately
as a recipient list (that is their only use for now).

## LLM dispatch (`llm.py`)

`generate(provider, model, prompt) -> str`. Three small functions using
official SDKs:

- anthropic: `anthropic.Anthropic()`, `client.messages.create(model=...,
  max_tokens=16000, messages=[{"role": "user", "content": prompt}])`, join
  text blocks; check `stop_reason == "refusal"` and report clearly.
- openai: `openai.OpenAI()`, chat completions.
- gemini: `google.genai.Client()`, `generate_content`.

Each provider function checks its env var up front and exits with
"set FOO_API_KEY" if missing. SDK errors surface as short messages
(status + request id), never key material.

## CLI (`cli.py`)

- `python -m sleeper_recap init [--league-id ID] [--config PATH]`
  Fetches league users/rosters, writes prefilled `config.toml` (team names,
  usernames; blank owner fields). Refuses to overwrite existing config
  without `--force`.
- `python -m sleeper_recap recap [--week N] [--provider P] [--model M]
  [--config PATH] [--out FILE]`
  Fetches data, builds prompt, calls LLM, prints email body to stdout,
  writes to `--out` (default `recaps/week_N.md`), prints recipient email
  list from config at the end.

Flags override config values. Errors exit nonzero with one-line messages.

## Error handling

- Bad league id -> "League not found" with the id.
- Missing config -> point at `init`.
- Roster in matchups but missing from config -> warn, use Sleeper team name.
- No scores for week -> clear message, exit 1.
- Provider/network errors -> short message, exit 1, no key leakage.

## Testing

- `tests/test_recap.py`: canned fixture JSON (real shape from the test
  league) -> assert prompt contains correct winners, scores, closest game,
  blowout, and excludes email addresses.
- Live end-to-end run against league 1312070289483378688 once week 1 scores
  exist (or with `--week` pointed at a scored week).

## Repo

Private GitHub repo `SleeperFFLeagueUpdates` under `dmacguigan`, created with
`gh repo create --private`. Initial push only; no further pushes without
explicit instruction.

## Out of scope (later)

- Automated email sending
- GUI/simple app for non-technical users
- HTML email formatting
