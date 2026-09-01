import datetime

from espn_api.football import League
from espn_api.requests.espn_requests import ESPNAccessDenied, ESPNInvalidLeague


def _default_season():
    today = datetime.date.today()
    return today.year - 1 if today.month < 3 else today.year


class Client:
    def __init__(self, league_id, season=None, espn_s2=None, swid=None):
        self.league_id = str(league_id)
        self.season = season or _default_season()
        self.espn_s2 = espn_s2
        self.swid = swid
        try:
            self._league = League(
                league_id=int(league_id), year=self.season, espn_s2=espn_s2, swid=swid
            )
        except ESPNAccessDenied:
            raise SystemExit("ESPN league is private; add espn_s2 and SWID cookies")
        except ESPNInvalidLeague:
            raise SystemExit(f"ESPN league {league_id} not found for {self.season}")

        self._players = {}
        for team in self._league.teams:
            for p in team.roster:
                self._players[str(p.playerId)] = {
                    "full_name": p.name,
                    "position": p.position,
                    "team": p.proTeam,
                    "age": None,
                }

        self.league_obj = self.league()

    def league(self, league_id=None):
        return {
            "name": self._league.settings.name,
            "season": str(self.season),
            "league_id": self.league_id,
            "total_rosters": self._league.settings.team_count,
        }

    def users(self, league_id=None):
        result = []
        for team in self._league.teams:
            name = None
            owners = team.owners or []
            if owners:
                o = owners[0]
                full = f"{o.get('firstName') or ''} {o.get('lastName') or ''}".strip()
                if full:
                    name = full
            if not name:
                name = team.team_name
            result.append(
                {
                    "user_id": str(team.team_id),
                    "display_name": name,
                    "metadata": {"team_name": team.team_name},
                }
            )
        return result

    def rosters(self, league_id=None):
        result = []
        for team in self._league.teams:
            result.append(
                {
                    "roster_id": team.team_id,
                    "owner_id": str(team.team_id),
                    "settings": {
                        "wins": team.wins,
                        "losses": team.losses,
                        "fpts": team.points_for,
                    },
                    "players": [str(p.playerId) for p in team.roster],
                }
            )
        return result

    def matchups(self, league_id, week):
        try:
            boxes = self._league.box_scores(week=week)
            result = []
            for idx, box in enumerate(boxes, start=1):
                for team, lineup, score in (
                    (box.home_team, box.home_lineup, box.home_score),
                    (box.away_team, box.away_lineup, box.away_score),
                ):
                    if not team:
                        continue
                    all_players = []
                    starters = []
                    players_points = {}
                    for p in lineup:
                        pid = str(p.playerId)
                        all_players.append(pid)
                        players_points[pid] = p.points
                        if p.slot_position not in ("BE", "IR"):
                            starters.append(pid)
                        if pid not in self._players:
                            self._players[pid] = {
                                "full_name": p.name,
                                "position": p.position,
                                "team": p.proTeam,
                                "age": None,
                            }
                    result.append(
                        {
                            "roster_id": team.team_id,
                            "matchup_id": idx,
                            "points": score,
                            "starters": starters,
                            "players": all_players,
                            "players_points": players_points,
                        }
                    )
            return result
        except Exception:
            return []

    def nfl_state(self):
        return {"week": self._league.current_week, "season": str(self.season)}

    def transactions(self, league_id, week):
        if not (self.espn_s2 and self.swid):
            return []
        try:
            activity = self._league.recent_activity(size=25)
        except Exception:
            return []
        result = []
        for act in activity:
            for entry in act.actions:
                team, action_str, player = entry[:3]
                if action_str in ("FA ADDED", "WAIVER ADDED"):
                    # ponytail: no clean per-week filter in espn-api activity; week arg ignored
                    result.append(
                        {
                            "type": "waiver",
                            "status": "complete",
                            "adds": {str(player.playerId): team.team_id},
                        }
                    )
        return result

    def draft_picks(self, league_id=None):
        team_count = self._league.settings.team_count
        return [
            {
                "player_id": str(p.playerId),
                "round": p.round_num,
                "pick_no": (p.round_num - 1) * team_count + p.round_pick,
            }
            for p in self._league.draft
        ]

    def players(self):
        return self._players

    def season_stats(self, season=None):
        result = {}
        for team in self._league.teams:
            for p in team.roster:
                pid = str(p.playerId)
                total = p.total_points
                avg = p.avg_points
                gp = round(total / avg) if avg else 0
                stats0 = (p.stats or {}).get(0) or {}
                breakdown = stats0.get("breakdown") or {}
                result[pid] = {
                    "pts_ppr": total,
                    "gp": gp,
                    "pass_td": breakdown.get("passingTouchdowns", 0),
                    "rush_td": breakdown.get("rushingTouchdowns", 0),
                    "rec_td": breakdown.get("receivingTouchdowns", 0),
                }
        return result

    def seasons(self):
        return [
            {"season": str(y), "league_id": self.league_id}
            for y in range(self.season, self.season - 5, -1)
        ]
