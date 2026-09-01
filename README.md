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

Your browser opens to the app. Enter your league ID, fill in owner names
and fun facts, then generate a prompt for any week. The app never sends
email; paste the reply into your own email client. Saved leagues
appear in a dropdown next time. Everything lives in a `Postgame` folder in
your home directory (`leagues/` and `recaps/`).

Find your league ID: open your league at sleeper.com and copy the long
number after `/leagues/` in the URL. On the mobile app, open league
settings, copy the league link, and take the same number.

## Developers

Everything below is for running from source.

### Setup

1. Create the conda environment:

   ```bash
   mamba env create -f environment.yml
   mamba activate sleeper-recap
   ```

2. Find your league ID:

   Open your league on the Sleeper website (sleeper.com) and look at the
   browser URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID/...`. The long
   number after `/leagues/` is your league ID. On the mobile app, open the
   league, tap the league name for settings, and copy the league link; the
   ID is the same long number in that link.

3. Scaffold your league config:

   ```bash
   python -m sleeper_recap init --league-id YOUR_LEAGUE_ID
   ```

   Then edit `config.toml`: fill in each owner's real name, email, and
   fun facts. This file stays on your machine (it is gitignored).

4. (Optional) Set up API provider. Only needed if you set `provider` to anthropic, openai, or gemini in config.toml:

   ```bash
   pip install anthropic      # for Claude
   pip install openai         # for GPT
   pip install google-genai   # for Gemini
   ```

   Then set your API key as an environment variable (never stored on disk):

   ```bash
   export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY / GEMINI_API_KEY
   ```

   If your environment already supplies Anthropic credentials (for example
   via the Anthropic CLI login), the SDK may pick them up automatically;
   otherwise set ANTHROPIC_API_KEY.

### Usage

```bash
python -m sleeper_recap recap                                  # most recent completed week
python -m sleeper_recap recap --week 3                         # specific week
python -m sleeper_recap recap --season 2025 --week 10          # past season (requires --week)
python -m sleeper_recap recap --provider openai --model gpt-5
python -m sleeper_recap app                                    # local web app in your browser
```

The draft prints to the terminal and is saved to `recaps/week_N_prompt.md` (manual mode)
or `recaps/week_N.md` (API mode), followed by the recipient email list from your config.

### Manual mode (default)

By default, the tool runs in manual mode: it writes `recaps/week_N_prompt.md` with a ready-to-paste prompt.
Open the file, copy its contents into Claude.ai, ChatGPT, or Gemini, then copy the reply into your email.
No API key or environment setup needed. To use an API provider instead, set `provider` in config.toml
or pass `--provider anthropic` (and run optional setup step 4 above).

### Tests

```bash
python -m pytest
```

### Notes

- API keys are read from environment variables only and are never written
  to any file.
- Owner emails are never sent to the LLM; they are only printed locally.

### Releasing

Tag and push; GitHub Actions builds all three binaries and attaches them
to a Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```
