-- Export compact datasets for the web page.

-- leader's perspective: lead > 0, pregame prob of the leading team, held = leader won
create or replace table lead_rows as
select s.game_id, s.season, s.t, abs(s.margin) lead,
       case when s.margin > 0 then p.php else 1 - p.php end leader_pre,
       round(p.php, 4) = 0.586 placeholder,
       sign(s.final_margin) = sign(s.margin) held
from snaps s join pre p using (game_id)
where s.margin <> 0 and s.t between 1 and 39;

create or replace table evidence as
select t, least(lead, 30) lead,
  case when placeholder then 'unk' when leader_pre >= 0.65 then 'fav' when leader_pre <= 0.35 then 'dog' else 'even' end bucket,
  count(*) n, sum(held::int) held
from lead_rows group by all;

copy (
  select t, lead, bucket, n, held from evidence
  union all
  select t, lead, 'all', sum(n), sum(held) from evidence group by t, lead
  order by 1, 2, 3
) to 'web/data/evidence.csv' (header);

-- replays: per-play margin for selected games, home perspective, with clock
copy (
  select p.game_id, p.game_play_number, p.period, p.end_game_seconds_remaining secs,
         p.clock_display_value clock, p.home_score h, p.away_score a, p.espn_home_wp espn_wp
  from read_parquet('data/pbp_202*.parquet') p
  where p.game_id in (401724590, 401516447, 401516439, 401825269)
  order by game_id, game_play_number
) to 'web/data/replay_plays.csv' (header);

copy (
  select g.game_id, d.game_date, d.note, g.home_display_name home, g.away_display_name away,
         g.home_final, g.away_final, p.php home_pre, g.max_period
  from games g join gdate d using (game_id) join pre p using (game_id)
  where g.game_id in (401724590, 401516447, 401516439, 401825269)
) to 'web/data/replay_games.csv' (header);

-- Big Ten 18-team era (2024-25, 2025-26)
copy (
  select *, round(100.0 * comeback_wins_10 / nullif(trailed10_games, 0), 1) comeback_pct,
         round(100.0 * (led10_games - blown_10) / nullif(led10_games, 0), 1) held_pct
  from b10 order by team
) to 'web/data/big_ten.csv' (header);

-- top comebacks (all D-I games in data)
copy (
  select g.season, d.game_date, g.winner, g.loser, g.wpts, g.lpts, g.max_deficit, g.winner_conf, g.loser_conf, g.max_period, d.note
  from gstats g join gdate d using (game_id) order by max_deficit desc, game_date limit 25
) to 'web/data/top_comebacks.csv' (header);

copy (select count(*) games, min(season) s0, max(season) s1 from games) to 'web/data/meta.csv' (header);
