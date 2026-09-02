from sleeper_recap.recap import _player_name, _team_info


def _games(matchups):
    pairs = {}
    for m in matchups:
        pairs.setdefault(m["matchup_id"], []).append(m)
    for pair in pairs.values():
        if len(pair) == 2:
            hi, lo = sorted(pair, key=lambda m: m["points"], reverse=True)
            yield hi, lo


def _bench(m):
    if not m.get("starters"):
        return 0.0
    starters = set(m["starters"])
    pp = m.get("players_points") or {}
    return sum(v for pid, v in pp.items() if pid not in starters)


def _longest(results, letter):
    best = (0, 0)
    for rid, wl in results.items():
        run = 0
        for r in wl:
            run = run + 1 if r == letter else 0
            if run > best[0]:
                best = (run, rid)
    return best


def build_prompt(sp, week_from, week_to, config):
    if not 1 <= week_from < week_to <= 18:
        raise SystemExit("week range must be within 1-18 and start before it ends")
    league = sp.league_obj
    weeks = {}
    for wk in range(week_from, week_to + 1):
        ms = sp.matchups(sp.league_id, wk)
        if ms and any((m.get("points") or 0) for m in ms):
            weeks[wk] = ms
    if not weeks:
        raise SystemExit(f"no scores for weeks {week_from}-{week_to}")
    first, last = min(weeks), max(weeks)

    players_blob = sp.players()
    info = _team_info(sp.users(sp.league_id), sp.rosters(sp.league_id), config)
    name = lambda rid: info.get(rid, {}).get("name", f"Roster {rid}")

    team = {rid: {"wl": [], "pts": [], "bench": 0.0} for rid in info}
    games = []
    player_pts, player_owner = {}, {}
    for wk in sorted(weeks):
        for m in weeks[wk]:
            t = team.setdefault(m["roster_id"], {"wl": [], "pts": [], "bench": 0.0})
            t["pts"].append((m["points"], wk))
            t["bench"] += _bench(m)
            for pid, v in (m.get("players_points") or {}).items():
                player_pts[pid] = player_pts.get(pid, 0) + v
                player_owner[pid] = m["roster_id"]
        for hi, lo in _games(weeks[wk]):
            team[hi["roster_id"]]["wl"].append("W")
            team[lo["roster_id"]]["wl"].append("L")
            games.append((wk, hi, lo, hi["points"] - lo["points"]))

    lines = [
        f"You are writing a multi-week recap email for the fantasy football league '{league['name']}' "
        f"({league['season']} season, covering weeks {first}-{last}).",
        f"Tone: {config.get('tone', 'fun and lighthearted')}.",
        "",
        f"Team summary for weeks {first}-{last}:",
        "| Team | W-L | Total pts | Avg pts | Best week | Worst week | Bench pts wasted |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rid, t in sorted(team.items(), key=lambda kv: (kv[1]["wl"].count("W"), sum(p for p, _ in kv[1]["pts"])), reverse=True):
        if not t["pts"]:
            continue
        total = sum(p for p, _ in t["pts"])
        best, worst = max(t["pts"]), min(t["pts"])
        lines.append(
            f"| {name(rid)} | {t['wl'].count('W')}-{t['wl'].count('L')} | {round(total, 1)} | "
            f"{round(total / len(t['pts']), 1)} | {best[0]} (wk {best[1]}) | {worst[0]} (wk {worst[1]}) | {round(t['bench'], 1)} |"
        )

    scores = [(p, wk, rid) for rid, t in team.items() for p, wk in t["pts"]]
    hi_s, lo_s = max(scores), min(scores)
    blow = max(games, key=lambda g: g[3])
    close = min(games, key=lambda g: g[3])
    wl_map = {rid: t["wl"] for rid, t in team.items()}
    w_run, w_rid = _longest(wl_map, "W")
    l_run, l_rid = _longest(wl_map, "L")
    lines += [
        "",
        "Records over the range:",
        f"- Highest single-week score: {name(hi_s[2])} {hi_s[0]} (week {hi_s[1]})",
        f"- Lowest single-week score: {name(lo_s[2])} {lo_s[0]} (week {lo_s[1]})",
        f"- Biggest blowout: {name(blow[1]['roster_id'])} over {name(blow[2]['roster_id'])} by {round(blow[3], 2)} (week {blow[0]})",
        f"- Closest game: {name(close[1]['roster_id'])} over {name(close[2]['roster_id'])} by {round(close[3], 2)} (week {close[0]})",
        f"- Longest win streak: {name(w_rid)} ({w_run})",
        f"- Longest losing streak: {name(l_rid)} ({l_run})",
        "",
        "Weekly results:",
    ]
    for wk, hi, lo, _ in games:
        lines.append(f"Wk {wk}: {name(hi['roster_id'])} {hi['points']} def {name(lo['roster_id'])} {lo['points']}")

    top = sorted(player_pts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    if top:
        lines += ["", "Top scoring players over the range (all rostered weeks, bench included):"]
        for pid, pts in top:
            lines.append(f"- {_player_name(players_blob, pid)} ({name(player_owner[pid])}): {round(pts, 1)}")

    try:
        pickups = []
        for wk in sorted(weeks):
            for tx in sp.transactions(sp.league_id, wk):
                if tx.get("type") == "trade" or tx.get("status") != "complete":
                    continue
                for pid, rid in (tx.get("adds") or {}).items():
                    pts = sum(
                        (m.get("players_points") or {}).get(pid, 0)
                        for w2 in weeks if w2 >= wk for m in weeks[w2] if m["roster_id"] == rid
                    )
                    if pts > 0:
                        pickups.append((pts, pid, rid, wk))
    except Exception:
        pickups = []
    if pickups:
        lines += ["", "Waiver pickups that paid off:"]
        for pts, pid, rid, wk in sorted(pickups, reverse=True)[:5]:
            lines.append(f"- {_player_name(players_blob, pid)} ({name(rid)}, added week {wk}): {round(pts, 1)} pts since")

    lines += ["", "Current season standings (record, total points):"]
    for t in sorted(info.values(), key=lambda t: (t["wins"], t["fpts"]), reverse=True):
        lines.append(f"- {t['name']}: {t['record']}, {t['fpts']} pts")

    facts = [f"- {t['name']} ({t['owner']}): {t['facts']}" for t in info.values() if t["facts"]]
    if facts:
        lines += ["", "Fun facts about the owners (weave these in where funny):"] + facts

    lines += [
        "",
        "Write the recap email now. Requirements:",
        "- First line: 'Subject: <a fun subject line>'. Then a blank line, then the email body.",
        "- Plain text only, no markdown formatting.",
        "- Tell the story of the stretch: who rose, who fell, the records, the streaks, and the standout players and pickups.",
        "- Give every team at least a mention; do not walk through every week one by one.",
        "- Keep it fun and readable, roughly 500-800 words.",
        "- Do not invent players or stats beyond what is given; do not reprint the tables.",
    ]
    return "\n".join(lines)
