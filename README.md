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
