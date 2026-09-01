import argparse
import os

from sleeper_recap import config as cfgmod
from sleeper_recap import enrich, llm, recap, sleeper


def cmd_init(args):
    if os.path.exists(args.config) and not args.force:
        raise SystemExit(f"{args.config} exists; use --force to overwrite")
    cfgmod.save(args.config, cfgmod.scaffold(args.league_id))
    print(f"Wrote {args.config}. Fill in owner_name, email, and fun_facts for each team.")


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
    p_recap.add_argument("--season", type=int)
    p_recap.add_argument("--provider", choices=["anthropic", "openai", "gemini", "manual"])
    p_recap.add_argument("--model")
    p_recap.add_argument("--config", default="config.toml")
    p_recap.add_argument("--out")
    p_recap.set_defaults(fn=cmd_recap)

    args = parser.parse_args(argv)
    args.fn(args)
