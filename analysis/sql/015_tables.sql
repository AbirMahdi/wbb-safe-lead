-- Intermediate tables between snapshots (01) and export (02).

-- pregame win probability per game (ESPN); 0.586 is a placeholder used when no forecast exists
create or replace table pre as
select game_id, arg_max(pregame_home_prob, game_play_number) php
from read_parquet('data/pbp_202*.parquet') group by 1;

create or replace table snaps2 as
select s.*, p.php, (p.php between 0.35 and 0.65 and round(p.php, 4) <> 0.586) even
from snaps s join pre p using (game_id);

create or replace table gdate as
select game_id, any_value(game_date) game_date, any_value(neutral_site) neutral, any_value(notes_headline) note
from read_parquet('data/sched_202*.parquet') group by 1;

-- per-game comeback stats from the winner's perspective (all periods, every play)
create or replace table gstats as
with p as (select p.game_id, p.secs, p.period, p.home_score - p.away_score m from pbp p join games g using (game_id)),
w as (select g.*, case when home_final > away_final then 1 else -1 end ws from games g)
select w.game_id, w.season, w.season_type, w.ws,
  case when ws = 1 then home_display_name else away_display_name end winner,
  case when ws = 1 then away_display_name else home_display_name end loser,
  case when ws = 1 then home_conference_id else away_conference_id end winner_conf,
  case when ws = 1 then away_conference_id else home_conference_id end loser_conf,
  case when ws = 1 then home_final else away_final end wpts,
  case when ws = 1 then away_final else home_final end lpts,
  -min(p.m * w.ws) as max_deficit,
  -min(p.m * w.ws) filter (where p.period = 4 and p.secs <= 300) as max_deficit_last5,
  max(p.m * w.ws) as winner_max_lead, w.max_period
from w join p using (game_id) group by all;

-- one row per team per game
create or replace table team_games as
select season, game_id, winner team, winner_conf conf, true won, max_deficit trailed_by, winner_max_lead led_by from gstats
union all
select season, game_id, loser, loser_conf, false, winner_max_lead, max_deficit from gstats;

-- Big Ten (ESPN conference id 7), 18-team era: 2024-25 and 2025-26
create or replace table b10 as
select team, count(*) games, sum(won::int) wins,
  count(*) filter (where won and trailed_by >= 10) comeback_wins_10,
  count(*) filter (where trailed_by >= 10) trailed10_games,
  count(*) filter (where not won and led_by >= 10) blown_10,
  count(*) filter (where led_by >= 10) led10_games
from team_games where conf = 7 and season in (2025, 2026) group by 1;

-- rows for model fitting (excludes placeholder-forecast games)
copy (select game_id, season, t, margin, final_margin, php, even, max_period
      from snaps2 where t between 1 and 40 and round(php, 4) <> 0.586) to 'model_rows.csv' (header);
