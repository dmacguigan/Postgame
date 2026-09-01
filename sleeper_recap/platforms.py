from sleeper_recap import sleeper


class SleeperClient:
    def __init__(self, league_id, season=None):
        lg = sleeper.league(league_id)
        if season:
            while lg.get("season") != str(season):
                prev = lg.get("previous_league_id")
                if not prev:
                    raise SystemExit(f"no {season} season found in this league's history")
                lg = sleeper.league(prev)
        self.league_id = lg.get("league_id", league_id)
        self.league_obj = lg

    def __getattr__(self, name):
        return getattr(sleeper, name)

    def seasons(self):
        out = []
        lg = self.league_obj
        while lg:
            out.append({"season": lg["season"], "league_id": lg["league_id"]})
            prev = lg.get("previous_league_id")
            lg = sleeper.league(prev) if prev else None
        return out


def open(config, season=None):
    league_id = config.get("league_id")
    if not league_id:
        raise SystemExit("config missing league_id; re-run init")
    if config.get("platform", "sleeper") == "espn":
        from sleeper_recap import espn

        return espn.Client(league_id, season, espn_s2=config.get("espn_s2") or None, swid=config.get("swid") or None)
    return SleeperClient(league_id, season)
