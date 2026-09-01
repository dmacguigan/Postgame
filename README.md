# Sleeper Weekly Recap

Drafts a fun weekly recap email for your Sleeper fantasy football league.
By default, writes a ready-to-paste prompt file you share with Claude, ChatGPT, or Gemini;
can instead call Claude, OpenAI, or Google Gemini APIs directly if configured.
You copy the draft (or API response) into your own email client and send it yourself.

## Setup

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

## Usage

```bash
python -m sleeper_recap recap                                  # most recent completed week
python -m sleeper_recap recap --week 3                         # specific week
python -m sleeper_recap recap --season 2025 --week 10          # past season (requires --week)
python -m sleeper_recap recap --provider openai --model gpt-5
```

The draft prints to the terminal and is saved to `recaps/week_N_prompt.md` (manual mode)
or `recaps/week_N.md` (API mode), followed by the recipient email list from your config.

## Manual mode (default)

By default, the tool runs in manual mode: it writes `recaps/week_N_prompt.md` with a ready-to-paste prompt.
Open the file, copy its contents into Claude.ai, ChatGPT, or Gemini, then copy the reply into your email.
No API key or environment setup needed. To use an API provider instead, set `provider` in config.toml
or pass `--provider anthropic` (and run optional setup step 4 above).

## Tests

```bash
python -m pytest
```

## Notes

- API keys are read from environment variables only and are never written
  to any file.
- Owner emails are never sent to the LLM; they are only printed locally.
