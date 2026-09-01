# Multi-Platform Feasibility: ESPN and Yahoo

Date: 2026-09-01
Status: investigation only, no implementation
Scope: add ESPN and Yahoo fantasy football leagues alongside Sleeper, with
matching league and player detail, selectable per league in CLI and app.

## Current shape

Everything downstream of `sleeper.py` assumes Sleeper JSON: `roster_id`,
`matchup_id`, `players_points`, `starters`, user `metadata.team_name`,
`previous_league_id` chains, Sleeper player IDs keyed into the players
blob. `enrich.gather` and `recap.build_prompt` both read those shapes
directly. Adding a platform means either faking Sleeper shapes (fragile)
or introducing one neutral data model that all three platforms fill.

Recommendation: neutral model. Roughly:

- league: name, season, week, platform, team count
- teams: id, name, owner display name, wins, losses, points for
- matchups: pairs of (team id, points, starters[{name, pos, slot, points,
  projected}], bench[{...}])
- pickups this week: team id, player name, pos
- previous week results (for streaks and form)
- draft slots: player name to (round, pick)
- player season stats: name to key stats (ppg, games)

Config gains `platform = "sleeper" | "espn" | "yahoo"` (default sleeper).
CLI: `init --platform espn --league-id ...`. App: platform toggle next to
the league ID field; saved leagues dropdown shows platform badge.

## ESPN

Feasibility: high.

- API: undocumented but stable v3 JSON API at
  `lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{id}`
  with `view=` params (mTeam, mRoster, mMatchupScore, mBoxscore,
  mSettings, mDraftDetail, mTransactions2, kona_player_info).
- Library: `espn-api` 0.46.0 (Mar 2026), single maintainer, active,
  requests only. Football `League(league_id, year, espn_s2, swid)` gives
  teams, standings, `box_scores(week)` with per-player points, projected,
  slot, position, pro team; `draft`; `recent_activity()` for adds, drops,
  trades; `free_agents()`; player season stats via `player_info`.
- Auth: public leagues need nothing. Private leagues need two browser
  cookies, `espn_s2` and `SWID`, copied from ESPN.com dev tools. Cookies
  are long lived (reported months to a year, not documented). A Chrome
  extension "ESPN Cookie Finder" exists to ease this.
- Seasons: ESPN league ID is stable across years, so past seasons are
  just `year=2025`. Seasons 2018+ use the path above; pre-2018 use
  `leagueHistory` which ESPN cookie-gated on 2025-08-01.
- Parity vs Sleeper: equal or better. Projections included (Sleeper has
  none). Player detail per matchup is richer. Waiver pickups come from
  `recent_activity`, draft from `draft`.
- Gaps and risks: unofficial API can change without notice; private
  league cookie copy is the biggest UX hurdle for non-technical users.
- Constraint check: cookies are secrets for the user's own ESPN account.
  Options: (a) memory only, pasted each launch; (b) stored in the league
  toml with an explicit "remember on this computer" checkbox. Owner
  decision needed. Recommend (b) opt-in, since the app already keeps
  personal data (emails) in that folder and cookies are per-user.

## Yahoo

Feasibility: medium. Data is fine; auth is the cost.

- API: official, documented, XML by default, `?format=json` supported.
  Resources: league settings, standings, `scoreboard;week=N`, team
  `roster;week=N` with `players/stats;type=week;week=N` for per-player
  weekly points, `transactions`, `draftresults`, player stats by week or
  season. Yahoo throttles heavy use; caching the player pool locally as
  we do for Sleeper is enough.
- Auth: OAuth 2.0 required for everything, including public leagues.
  Needs a registered Yahoo app (client ID + client secret). First use
  opens a browser consent page; redirect is either `oob` (user pastes a
  code) or `https://localhost:PORT` (browser cert warning). Access token
  lasts 1 hour; refresh token is long lived and must be persisted or the
  user re-consents every launch.
- Libraries: `yfpy` 17.0.0 (Sep 2025, py>=3.10, heavier deps) or
  `yahoo_fantasy_api` + `yahoo_oauth` (lighter, uses an oauth2.json). Both
  cover matchups, rosters by week, player stats, transactions, draft.
- Seasons: each season is a separate league key. `league.renew` and
  `renewed` fields link seasons; user's own leagues across years come
  from `users;use_login=1/games;game_keys=nfl/leagues`.
- Parity vs Sleeper: equal for scores, rosters, standings, transactions,
  draft. Gap: Yahoo API exposes no projected points. Player names and
  positions are inline, no separate player blob needed.
- Key distribution problem: a one-click app must ship a client ID and
  secret inside the binary (extractable) or make each user register a
  Yahoo developer app (too technical for the target audience). Yahoo's
  "Installed Application" type is meant for the former. PKCE support by
  Yahoo would remove the secret; unverified, needs a spike.
- Constraint check: refresh token is a user credential. Same decision as
  ESPN cookies: memory only vs opt-in storage under ~/Postgame.

## Comparison

| Item | Sleeper | ESPN | Yahoo |
|------|---------|------|-------|
| Auth for public league | none | none | OAuth |
| Auth for private league | none (all public) | 2 cookies | OAuth |
| Per-player weekly points | yes | yes | yes |
| Projections | no | yes | no |
| Transactions / pickups | yes | yes | yes |
| Draft results | yes | yes | yes |
| Past seasons | chain walk | same ID + year | separate keys |
| API stability | unofficial, stable | unofficial, stable | official |
| Extra deps in binary | none | espn-api | yfpy or yahoo_fantasy_api |

## Action plan

Phase 0: neutral model (prerequisite, no visible change)
1. Define the neutral dicts above in `sleeper_recap/model.py`.
2. `sleeper.py` grows `fetch(league_id, season, week) -> model` using
   existing functions; `enrich` and `recap` consume the model only.
3. Convert test fixtures once; all existing tests stay green.
4. Config `platform` field, CLI `--platform`, app toggle (sleeper only
   still works).
Size: medium. Riskiest refactor of the three; do it alone.

Phase 1: ESPN
1. Spike (half day): pull the test-league-sized public ESPN league with
   `espn-api`, confirm box score, draft, activity fields.
2. `espn.py` adapter -> model. Public leagues first.
3. Private leagues: cookie fields in app League panel and CLI env vars
   `ESPN_S2` / `ESPN_SWID`; storage per owner decision.
4. Fixture-based tests from recorded JSON.
5. README: how to find ESPN league ID and cookies.
Size: medium.

Phase 2: Yahoo
1. Spike (1 day): register a Postgame Yahoo app, verify oob code flow
   from the packaged binary, test whether PKCE works without secret,
   confirm refresh token persistence.
2. `yahoo.py` adapter -> model using the chosen library.
3. App: "Connect Yahoo" button, code paste field, token storage per
   owner decision. CLI: same via prompt.
4. Season list via renew/renewed chain.
5. Fixture-based tests; README.
Size: large, mostly auth UX.

Phase 3: polish
- Platform badge in saved leagues dropdown; per-platform league ID help
  text; binary size check after adding deps.

## Owner decisions (2026-09-01)

1. Yahoo deferred indefinitely; too complex for the target audience.
2. ESPN cookies may be stored on disk under ~/Postgame (opt-in checkbox).
3. ESPN goes next, after the neutral model refactor.
4. App is manual mode only and does not collect or show emails; emails
   stay a CLI-only feature.

## Sources

- ESPN endpoints gist: https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c
- espn-api: https://github.com/cwendt94/espn-api and https://pypi.org/project/espn-api/
- fflr note on 2025-08-01 change: https://k5cents.github.io/fflr/
- Yahoo dev portal: https://sports.yahoo.com/developer/
- yfpy: https://github.com/uberfastman/yfpy and https://pypi.org/project/yfpy/
- yahoo_fantasy_api docs: https://yahoo-fantasy-api.readthedocs.io/en/latest/yahoo_fantasy_api.html
- OAuth public client guidance: https://blog.sentry.security/oauth-2-0-client-credentials-misuse-in-public-apps/
