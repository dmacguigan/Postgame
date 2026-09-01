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
        wins = settings.get("wins", 0)
        info[rid] = {
            "name": cfg.get("team_name") or display.get(r.get("owner_id"), f"Roster {rid}"),
            "owner": cfg.get("owner_name", ""),
            "facts": cfg.get("fun_facts", ""),
            "wins": wins,
            "record": f"{wins}-{settings.get('losses', 0)}",
            "fpts": settings.get("fpts", 0),
        }
    return info


def _player_name(players, pid):
    p = players.get(pid) or {}
    return p.get("full_name") or pid


def _key_stats(s):
    parts = []
    for key, label in (
        ("pass_yd", "pass yd"), ("pass_td", "pass TD"),
        ("rush_yd", "rush yd"), ("rush_td", "rush TD"),
        ("rec_yd", "rec yd"), ("rec_td", "rec TD"),
    ):
        v = s.get(key) or 0
        if v:
            parts.append(f"{v} {label}")
    return ", ".join(parts) if parts else "-"


def _matchup_team_lines(label, m, players_blob):
    starters = m.get("starters") or []
    players_pts = m.get("players_points") or {}
    parts = []
    for pid in starters:
        p = players_blob.get(pid) or {}
        name = p.get("full_name") or pid
        pos = p.get("position") or "?"
        team = p.get("team") or "FA"
        pts = round(players_pts.get(pid, 0), 1)
        parts.append(f"{name} ({pos}, {team}) {pts}")
    lines = [f"  {label} starters: " + "; ".join(parts)]

    all_players = m.get("players") or []
    bench = [pid for pid in all_players if pid not in starters]
    bench_total = round(sum(players_pts.get(pid, 0) for pid in bench), 1)
    if bench:
        best_pid = max(bench, key=lambda pid: players_pts.get(pid, 0))
        p = players_blob.get(best_pid) or {}
        best_name = p.get("full_name") or best_pid
        best_pts = round(players_pts.get(best_pid, 0), 1)
        lines.append(
            f"  {label} best bench: {best_name} {best_pts}; total bench points {bench_total} (points left on bench)"
        )
    else:
        lines.append(f"  {label} best bench: none; total bench points {bench_total} (points left on bench)")
    return lines


def _recent_avg(prev_matchups, pid):
    values = []
    for wk_matchups in prev_matchups.values():
        for m in wk_matchups:
            pp = m.get("players_points") or {}
            if pid in pp:
                values.append(pp[pid])
    return sum(values) / len(values) if values else None


def _ppg(stats, pid):
    s = stats.get(pid) or {}
    gp = s.get("gp", 0)
    return s.get("pts_ppr", 0) / gp if gp > 0 else None


def _enrichment_lines(info, rosters, matchups, results, extra):
    players_blob = extra["players"]
    stats = extra["stats"]
    draft_slots = extra["draft_slots"]

    lines = ["", "Matchup details:"]
    for hi, lo, _margin in results:
        team_a = info[hi["roster_id"]]["name"]
        team_b = info[lo["roster_id"]]["name"]
        lines.append(f"{team_a} {hi['points']} vs {team_b} {lo['points']}")
        lines += _matchup_team_lines(team_a, hi, players_blob)
        lines += _matchup_team_lines(team_b, lo, players_blob)

    lines += ["", "Full rosters (for color, do not reprint these tables in the email):"]
    for r in rosters:
        if "players" not in r:
            continue
        rid = r["roster_id"]
        lines.append(f"### {info[rid]['name']}")
        lines.append("| Player | Pos | Age | NFL team | Drafted | YTD fantasy pts | YTD key stats |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for pid in r["players"]:
            p = players_blob.get(pid) or {}
            name = p.get("full_name") or pid
            pos = p.get("position") or "?"
            age = p.get("age")
            age = age if age is not None else "-"
            nfl_team = p.get("team") or "-"
            drafted = draft_slots.get(pid, "waiver/FA")
            s = stats.get(pid) or {}
            ytd_pts = round(s.get("pts_ppr", 0), 1)
            key_stats = _key_stats(s)
            lines.append(f"| {name} | {pos} | {age} | {nfl_team} | {drafted} | {ytd_pts} | {key_stats} |")

    pickups = extra["pickups"]
    if pickups:
        lines += ["", "Recent waiver/FA pickups (last 2 weeks):"]
        for rid, pid in pickups:
            team_name = info.get(rid, {}).get("name", f"Roster {rid}")
            player_name = _player_name(players_blob, pid)
            lines.append(f"- {team_name} added {player_name}")

    pid_to_roster = {}
    for m in matchups:
        for pid in m.get("players") or []:
            pid_to_roster[pid] = m["roster_id"]

    lines += ["", "Form guide:"]
    for r in rosters:
        rid = r["roster_id"]
        streak = extra["team_streaks"].get(rid)
        if not streak:
            continue
        wl = "".join(s[2] for s in streak)
        pts = ", ".join(str(s[1]) for s in streak)
        lines.append(f"- {info[rid]['name']}: last {len(streak)} weeks {wl} ({pts})")

    for pid, flag in extra["hot_cold"].items():
        rid = pid_to_roster.get(pid)
        team_name = info.get(rid, {}).get("name", "") if rid is not None else ""
        player_name = _player_name(players_blob, pid)
        recent = _recent_avg(extra["prev_matchups"], pid)
        ppg = _ppg(stats, pid)
        lines.append(
            f"- {player_name} ({team_name}) is {flag}: recent {round(recent, 1)} vs season {round(ppg, 1)} PPG"
        )

    return lines


def build_prompt(league, users, rosters, matchups, week, config, extra=None):
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
    standings = sorted(info.values(), key=lambda t: (t["wins"], t["fpts"]), reverse=True)
    for t in standings:
        lines.append(f"- {t['name']}: {t['record']}, {t['fpts']} pts")

    if extra is not None:
        lines += _enrichment_lines(info, rosters, matchups, results, extra)

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
    if extra is not None:
        lines.append(
            "- Use the roster tables, bench numbers, pickups, and form guide for color and trash talk; "
            "do not reprint tables or list every stat."
        )
    return "\n".join(lines)
