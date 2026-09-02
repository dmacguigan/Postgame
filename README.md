# Postgame

Weekly recap emails for your fantasy football league, drafted by AI, sent by you.

Postgame pulls your league's scores, rosters, standings, and form from
**Sleeper** or **ESPN**, builds a ready-to-paste prompt, and hands it to you.
Drop it into Claude, ChatGPT, or Gemini, then paste the reply into your
email client. No accounts, no API keys, no data leaves your computer except
the prompt you choose to paste.

## Download

Grab the file for your computer from the
[Releases page](https://github.com/dmacguigan/Postgame/releases), then:

| OS | File | Steps |
| --- | --- | --- |
| Windows | `Postgame-windows.zip` | Unzip, double-click `Postgame.exe`. If SmartScreen appears, click **More info**, then **Run anyway**. |
| macOS | `Postgame-macos.zip` | Unzip, right-click `Postgame`, choose **Open** (first time only; the app is unsigned). A Terminal window opens; that is the app. Close it to quit. |
| Linux | `Postgame-linux.tar.gz` | Extract, `chmod +x Postgame` if needed, run it. |

Your browser opens to the app automatically.

## Using the app

1. **League.** Pick Sleeper or ESPN, paste your league ID, click **Load league**.
2. **Teams.** Add owner names and fun facts for each team. Set the tone. Click **Save**.
3. **Generate.** Pick a season and week, click **Generate prompt**, then **Copy prompt**.
4. Paste the prompt into claude.ai, ChatGPT, or Gemini. Paste its reply into your email.

Saved leagues show up in a dropdown next time. Everything lives in a
`Postgame` folder in your home directory: `leagues/` holds your league
files, `recaps/` holds every prompt you generated.

### Finding your league ID

**Sleeper.** Open your league at sleeper.com. The URL looks like
`https://sleeper.com/leagues/1234567890123456789/...`; the long number is
your league ID. On the mobile app, open league settings, copy the league
link, and take the same number.

**ESPN.** Open your league at fantasy.espn.com. The URL contains
`leagueId=12345678`; that number is your league ID.

### Private ESPN leagues

Public ESPN leagues need nothing else. Private leagues need two cookies
so the app can read your league as you:

1. Log in at espn.com in your browser.
2. Open the browser's developer tools (F12), then **Application** (Chrome)
   or **Storage** (Firefox), then **Cookies**, then the espn.com entry.
3. Copy the values of `espn_s2` and `SWID` into the two fields under the
   league ID box before clicking **Load league**.

The cookies are saved in your league file on this computer only and are
never shown in the app again.

## What goes into the prompt

- Every matchup with score and margin, plus the closest game, biggest
  blowout, and top scorer.
- Season standings.
- Starters and bench for each matchup, including points left on the bench.
- Full rosters with position, NFL team, draft slot, and season points.
- Recent waiver pickups (Sleeper; ESPN only with cookies set).
- Team form over the last three weeks and hot or cold players.
- Your owner names, fun facts, and tone.

Owner emails are never part of the prompt.

## Developers

Everything below is for running from source.

### Setup

```bash
mamba env create -f environment.yml
mamba activate sleeper-recap
```

### Command line

Scaffold a league config, then edit `config.toml` to add owner names,
emails, and fun facts. The file is gitignored.

```bash
python -m sleeper_recap init --league-id YOUR_LEAGUE_ID                        # Sleeper
python -m sleeper_recap init --platform espn --league-id YOUR_LEAGUE_ID        # public ESPN league
python -m sleeper_recap init --platform espn --league-id ID --espn-s2 ... --swid ...   # private ESPN league
```

Draft a recap:

```bash
python -m sleeper_recap recap                             # most recent completed week
python -m sleeper_recap recap --week 3                    # specific week
python -m sleeper_recap recap --season 2025 --week 10     # past season (requires --week)
python -m sleeper_recap recap --provider openai --model gpt-5
python -m sleeper_recap app                               # the web app, using the current folder
```

The draft prints to the terminal and is saved under `recaps/`, followed
by the recipient email list from your config. Emails are a CLI-only
feature; the app never collects or shows them.

### Optional: call an LLM API directly

The CLI defaults to manual mode (prompt file only). To have it call an
API instead, install the SDK, export the key, and set `provider` in
`config.toml` or pass `--provider`:

```bash
pip install anthropic      # or openai, google-genai
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY / GEMINI_API_KEY
```

Keys are read from environment variables only and never written to disk.
The packaged app is manual mode only.

### Tests

```bash
python -m pytest
```

### Releasing

Tag and push. GitHub Actions builds the Windows, macOS, and Linux
binaries and attaches them to a GitHub Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

### Layout

| Path | Purpose |
| --- | --- |
| `sleeper_recap/sleeper.py` | Sleeper API client |
| `sleeper_recap/espn.py` | ESPN adapter, same shapes as the Sleeper client |
| `sleeper_recap/platforms.py` | Picks the client for a league config |
| `sleeper_recap/enrich.py` | Rosters, pickups, form guide, hot/cold flags |
| `sleeper_recap/recap.py` | Builds the prompt |
| `sleeper_recap/config.py` | League config read/write |
| `sleeper_recap/cli.py` | `init`, `recap`, `app` commands |
| `sleeper_recap/app.py` | Flask app behind the packaged binary |
| `postgame.py` | Packaged app entry point |
| `icon/make_icon.py` | Regenerates the PG icon files (needs `pip install pillow`) |
