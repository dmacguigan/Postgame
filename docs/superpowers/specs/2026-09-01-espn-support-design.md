# ESPN Support Design

Date: 2026-09-01
Status: approved by owner (go ahead, no questions unless necessary)
Depends on: 2026-09-01-multi-platform-feasibility.md (decisions section)

## Approach

No new neutral model. `enrich` and `recap` already consume simple
Sleeper-shaped dicts and `enrich.gather` already accepts an injected
data module. A platform "client" object exposes the same function
signatures as `sleeper.py` (extra `league_id` args accepted and ignored
for ESPN) and produces those same dict shapes. Downstream code is
untouched.

## Components

### `sleeper_recap/platforms.py`

- `open(config, season=None) -> client`. Picks by `config["platform"]`
  (default "sleeper"). Resolves the season: Sleeper walks
  `previous_league_id`; ESPN sets the year. Raises SystemExit with the
  existing messages ("no {season} season found...").
- Client attributes: `league_id` (season-resolved), `league_obj`
  (result of `league()`), methods `league, users, rosters, matchups,
  nfl_state, transactions, draft_picks, players, season_stats`,
  `seasons() -> [{"season", "league_id"}]`.
- `SleeperClient`: `__getattr__` delegates to the `sleeper` module so
  existing monkeypatches keep working.

### `sleeper_recap/espn.py`

`Client(league_id, season, espn_s2=None, swid=None)` wrapping
`espn_api.football.League`. Shapes:

- `league()`: `{"name", "season": str, "league_id": str,
  "total_rosters"}`
- `users()`: one per team: `{"user_id": str(team_id), "display_name":
  "First Last" (fallback team name; never displayName, it can be an
  email), "metadata": {"team_name"}}`
- `rosters()`: `{"roster_id": team_id, "owner_id": str(team_id),
  "settings": {"wins", "losses", "fpts": points_for}, "players": [pid]}`
  where pid is `str(playerId)`
- `matchups(league_id, week)`: from `box_scores(week)`; two entries per
  box with shared `matchup_id`; `starters` = lineup with slot not in
  {"BE", "IR"}; `players` = all; `players_points` = {pid: points}. A box
  with a missing side produces one unpaired entry (recap skips it).
  Any library exception returns `[]` (unstarted seasons crash inside
  espn-api).
- `nfl_state()`: `{"week": league.current_week, "season": str(year)}`
- `transactions(league_id, week)`: `[]`. ESPN activity endpoint 404s on
  public leagues. ponytail ceiling: try `recent_activity()` only when
  cookies are set, mapping adds to `{"type": "waiver", "status":
  "complete", "adds": {pid: team_id}}`; still `[]` on any error.
- `draft_picks(league_id)`: `{"player_id", "round", "pick_no"}` with
  `pick_no = (round - 1) * team_count + round_pick`
- `players()`: dict from all rostered players plus any seen in box
  scores: `{"full_name", "position", "team": proTeam, "age": None}`
- `season_stats(season)`: `{pid: {"pts_ppr": total_points, "gp":
  round(total/avg) if avg else 0, "pass_td", "rush_td", "rec_td"}}` from
  `stats[0]["breakdown"]` keys `passingTouchdowns`,
  `rushingTouchdowns`, `receivingTouchdowns`. Yardage omitted (ESPN
  season breakdown mixes totals and per-game values).
- `seasons()`: `[{"season": str(y), "league_id": league_id}]` for
  y from season down to `league.settings` first year if available,
  else the 5 most recent years. ponytail: probe each year lazily is too
  slow; list season..season-4.
- Season default when None: current year, minus one if month < 3.
- Errors: `ESPNAccessDenied` -> SystemExit "ESPN league is private; add
  espn_s2 and SWID cookies"; `ESPNInvalidLeague` -> SystemExit "ESPN
  league {id} not found for {year}".

### Config

New optional keys: `platform` (default "sleeper"), `espn_s2`, `swid`
(only written when platform is espn). `scaffold(league_id,
platform="sleeper", espn_s2="", swid="")` builds a seed config and uses
`platforms.open(seed)` for league, users, rosters. ESPN owner names are
prefilled into `owner_name` since ESPN provides real names.

### CLI

`init --platform {sleeper,espn} --espn-s2 --swid`. `recap` unchanged;
`run_recap` uses `platforms.open(config, season)` and passes the client
to `enrich.gather(..., sleeper_mod=client)`.

### App

- League file key: sleeper `<id>.toml` (unchanged), espn `espn_<id>.toml`.
  All routes take `league_key` in place of `league_id`; `_path` validates
  `^(espn_)?[0-9]+$`. `/api/leagues` returns `{key, name, platform}`.
- `/api/init` body: `{league_id, platform, espn_s2, swid, force}`.
- Frontend: platform select (Sleeper / ESPN) beside the ID input; ESPN
  reveals two cookie fields and help text; saved leagues dropdown shows
  "(ESPN)" suffix. Cookies are saved in the league file (owner
  approved) and never rendered back into the page.
- Recaps: `recaps/<key>/...`.

### Tests

- `tests/test_espn.py`: fake `League` class with SimpleNamespace teams,
  players, box scores, draft; assert every shape above, unpaired box,
  library exception -> `[]`, access denied -> SystemExit.
- `tests/test_platforms.py`: Sleeper chain walk and delegation.
- Existing app and cli tests updated for `league_key`.

### README

ESPN section: league ID from URL `leagueId=`, private league cookie
steps (ESPN.com, dev tools, Application, Cookies, copy `espn_s2` and
`SWID`), note that pickups are unavailable for ESPN.
