-- Build per-game, per-minute score snapshots in regulation, plus final outcome.
-- Seasons 2023-2026 (ESPN / wehoop play-by-play).

create or replace table pbp as
select season, season_type, game_id, game_play_number, period, end_game_seconds_remaining as secs,
       home_score, away_score, home_team_id, away_team_id
from read_parquet('data/pbp_202*.parquet');

create or replace table sched as
select game_id, season, season_type, home_id, away_id, home_display_name, away_display_name,
       home_conference_id, away_conference_id, cast(home_score as int) home_final, cast(away_score as int) away_final,
       neutral_site, status_type_completed
from read_parquet('data/sched_202*.parquet');

-- final score per game from pbp (last play)
create or replace table pbp_final as
select game_id, arg_max(home_score, game_play_number) h, arg_max(away_score, game_play_number) a,
       max(period) max_period, count(*) n_plays,
       count(distinct period) filter (where period <= 4) reg_periods
from pbp group by game_id;

-- keep only games whose pbp is complete and agrees with the official schedule score
create or replace table games as
select s.*, f.max_period, f.n_plays
from sched s join pbp_final f using (game_id)
where s.status_type_completed and f.reg_periods = 4 and f.h = s.home_final and f.a = s.away_final
  and s.home_final <> s.away_final and f.n_plays > 200;

-- minute marks: T = minutes remaining in regulation (40 = tip-off ... 0 = end of regulation)
create or replace table marks as select range as t from range(0, 41);

-- score at each mark = last regulation play at or before that clock point
-- collapse to one row per (game, clock second): the score after the last play at that second
create or replace table clockstate as
select p.game_id, p.secs, arg_max(p.home_score - p.away_score, p.game_play_number) margin
from pbp p join games g using (game_id)
where p.period <= 4
group by 1, 2;

-- ASOF: for each mark, the state at the smallest clock value still >= t*60 (= most recent play)
create or replace table grid as
select g.game_id, g.season, g.season_type, m.t, m.t * 60 as tsec,
       g.home_final - g.away_final as final_margin, g.max_period
from games g cross join marks m;

create or replace table snaps as
select gr.game_id, gr.season, gr.season_type, gr.t, gr.final_margin, gr.max_period,
       coalesce(c.margin, 0) as margin
from grid gr asof left join clockstate c
  on gr.game_id = c.game_id and c.secs >= gr.tsec;
