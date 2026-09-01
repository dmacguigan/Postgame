from sleeper_recap import sleeper


def gather(league_id, season, week, matchups, rosters, sleeper_mod=None):
    """Returns the enrichment context dict, fetching everything it needs.
    sleeper_mod defaults to the sleeper module (injection point for tests)."""
    sp = sleeper_mod or sleeper

    players = sp.players()
    stats = sp.season_stats(season)
    draft_slots = _draft_slots(sp.draft_picks(league_id))
    pickups = _pickups(sp, league_id, week)
    prev_matchups = _prev_matchups(sp, league_id, week)
    team_streaks = _team_streaks(prev_matchups)
    hot_cold = _hot_cold(matchups, prev_matchups, stats)

    return {
        "players": players,
        "stats": stats,
        "draft_slots": draft_slots,
        "pickups": pickups,
        "prev_matchups": prev_matchups,
        "team_streaks": team_streaks,
        "hot_cold": hot_cold,
    }


def _draft_slots(picks):
    return {p["player_id"]: f"R{p['round']}.P{p['pick_no']}" for p in picks}


def _pickups(sp, league_id, week):
    pickups = []
    for wk in range(max(1, week - 1), week + 1):
        for t in sp.transactions(league_id, wk):
            if t.get("type") == "trade":
                continue
            if t.get("status") != "complete":
                continue
            adds = t.get("adds")
            if not adds:
                continue
            for pid, rid in adds.items():
                pickups.append((rid, pid))
    return list(dict.fromkeys(pickups))


def _prev_matchups(sp, league_id, week):
    result = {}
    start = max(1, week - 3)
    for wk in range(start, week):
        result[wk] = sp.matchups(league_id, wk)
    return result


def _team_streaks(prev_matchups):
    streaks = {}
    for wk in sorted(prev_matchups):
        games = {}
        for m in prev_matchups[wk]:
            games.setdefault(m["matchup_id"], []).append(m)
        for pair in games.values():
            if len(pair) != 2:
                continue
            hi, lo = sorted(pair, key=lambda m: m["points"], reverse=True)
            streaks.setdefault(hi["roster_id"], []).append((wk, hi["points"], "W"))
            streaks.setdefault(lo["roster_id"], []).append((wk, lo["points"], "L"))
    return streaks


def _hot_cold(matchups, prev_matchups, stats):
    candidates = set()
    for m in matchups:
        for pid in m.get("players") or []:
            candidates.add(pid)

    flags = {}
    for pid in candidates:
        values = []
        for wk_matchups in prev_matchups.values():
            for m in wk_matchups:
                pp = m.get("players_points") or {}
                if pid in pp:
                    values.append(pp[pid])
        if len(values) < 2:
            continue
        recent = sum(values) / len(values)

        pstats = stats.get(pid) or {}
        gp = pstats.get("gp", 0)
        ppg = pstats.get("pts_ppr", 0) / gp if gp > 0 else None
        if ppg is None:
            continue

        if recent >= 1.5 * ppg and recent >= 5:
            flags[pid] = "hot"
        elif recent <= 0.5 * ppg and ppg >= 8:
            flags[pid] = "cold"
    return flags
