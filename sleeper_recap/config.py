import json
import tomllib

from sleeper_recap import llm, platforms


def _toml_str(value):
    return json.dumps(str(value), ensure_ascii=False)


def load(path):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except OSError:
        raise SystemExit(f"{path} not found; run: python -m sleeper_recap init --league-id YOUR_ID")


def scaffold(league_id, platform="sleeper", espn_s2="", swid=""):
    seed = {"league_id": str(league_id), "platform": platform, "espn_s2": espn_s2, "swid": swid}
    sp = platforms.open(seed)
    league = sp.league_obj
    users = sp.users(sp.league_id)
    rosters = sp.rosters(sp.league_id)
    names = {}
    usernames = {}
    for u in users:
        meta = u.get("metadata") or {}
        names[u["user_id"]] = meta.get("team_name") or u["display_name"]
        usernames[u["user_id"]] = u["display_name"]
    teams = {}
    for r in sorted(rosters, key=lambda r: r["roster_id"]):
        owner_id = r.get("owner_id")
        teams[str(r["roster_id"])] = {
            "team_name": names.get(owner_id, ""),
            "sleeper_username": usernames.get(owner_id, ""),
            "owner_name": usernames.get(owner_id, "") if platform == "espn" else "",
            "email": "",
            "fun_facts": "",
        }
    cfg = {
        "league_id": str(league_id),
        "league_name": league.get("name", ""),
        "platform": platform,
        "provider": "manual",
        "model": llm.DEFAULT_MODELS["anthropic"],
        "tone": "funny, light trash talk, inside jokes welcome",
        "teams": teams,
    }
    if platform == "espn":
        cfg["espn_s2"] = espn_s2
        cfg["swid"] = swid
    return cfg


def save(path, cfg):
    lines = [
        f"league_id = {_toml_str(cfg['league_id'])}",
        f"league_name = {_toml_str(cfg.get('league_name', ''))}",
        f"platform = {_toml_str(cfg.get('platform', 'sleeper'))}",
        f"provider = {_toml_str(cfg.get('provider', 'manual'))}  # manual | anthropic | openai | gemini",
        f"model = {_toml_str(cfg.get('model', llm.DEFAULT_MODELS['anthropic']))}",
        f"tone = {_toml_str(cfg.get('tone', ''))}",
    ]
    if cfg.get("platform") == "espn":
        lines.append(f"espn_s2 = {_toml_str(cfg.get('espn_s2', ''))}")
        lines.append(f"swid = {_toml_str(cfg.get('swid', ''))}")
    lines.append("")
    for rid, t in cfg.get("teams", {}).items():
        lines.append(f"[teams.{rid}]")
        for key in ("team_name", "sleeper_username", "owner_name", "email", "fun_facts"):
            lines.append(f"{key} = {_toml_str(t.get(key, ''))}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
