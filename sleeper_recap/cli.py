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
