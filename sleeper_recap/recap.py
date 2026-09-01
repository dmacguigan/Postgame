def _team_info(users, rosters, config):
    display = {}
    for u in users:
        meta = u.get("metadata") or {}
        display[u["user_id"]] = meta.get("team_name") or u["display_name"]
    teams_cfg = config.get("teams", {})
    info = {}
    for r in rosters:
        rid = r["roster_id"]
        cfg = teams_cfg.get(str(rid), {})
        settings = r.get("settings", {})
        info[rid] = {
            "name": cfg.get("team_name") or display.get(r.get("owner_id"), f"Roster {rid}"),
            "owner": cfg.get("owner_name", ""),
            "facts": cfg.get("fun_facts", ""),
            "record": f"{settings.get('wins', 0)}-{settings.get('losses', 0)}",
            "fpts": settings.get("fpts", 0),
        }
    return info


def build_prompt(league, users, rosters, matchups, week, config):
    info = _team_info(users, rosters, config)

    games = {}
    for m in matchups:
        games.setdefault(m["matchup_id"], []).append(m)
    results = []
    for pair in games.values():
        if len(pair) != 2:
            continue
        hi, lo = sorted(pair, key=lambda m: m["points"], reverse=True)
        results.append((hi, lo, hi["points"] - lo["points"]))
    if not results:
        raise SystemExit(f"no head-to-head matchups found for week {week}")

    def label(m):
        t = info[m["roster_id"]]
        return f"{t['name']} ({t['owner']})" if t["owner"] else t["name"]

    lines = [
        f"You are writing a weekly recap email for the fantasy football league '{league['name']}' (week {week}, {league['season']} season).",
        f"Tone: {config.get('tone', 'fun and lighthearted')}.",
        "",
        "This week's results:",
    ]
    for hi, lo, margin in results:
        lines.append(
            f"- {label(hi)} beat {label(lo)} {hi['points']}-{lo['points']} (margin {round(margin, 2)})"
        )

    closest = min(results, key=lambda r: r[2])
    blowout = max(results, key=lambda r: r[2])
    top = max(matchups, key=lambda m: m["points"])
    lines += [
        "",
        f"Closest game: {label(closest[0])} over {label(closest[1])} by {round(closest[2], 2)}.",
        f"Biggest blowout: {label(blowout[0])} over {label(blowout[1])} by {round(blowout[2], 2)}.",
        f"Top scorer of the week: {label(top)} with {top['points']}.",
        "",
        "Season standings (record, total points):",
    ]
    standings = sorted(info.values(), key=lambda t: (t["record"], t["fpts"]), reverse=True)
    for t in standings:
        lines.append(f"- {t['name']}: {t['record']}, {t['fpts']} pts")

    facts = [f"- {t['name']} ({t['owner']}): {t['facts']}" for t in info.values() if t["facts"]]
    if facts:
        lines += ["", "Fun facts about the owners (weave these in where funny):"] + facts

    lines += [
        "",
        "Write the recap email now. Requirements:",
        "- First line: 'Subject: <a fun subject line>'. Then a blank line, then the email body.",
        "- Plain text only, no markdown formatting.",
        "- Cover every matchup, call out the closest game, the blowout, and the top scorer.",
        "- Keep it fun and readable, roughly 300-500 words.",
        "- Do not invent players or stats beyond what is given.",
    ]
    return "\n".join(lines)
