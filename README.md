# Is the Lead Safe?

An interactive data story on how often the team ahead holds on in NCAA women's basketball, built for Purdue's Boiler Up, Hammer Data Challenge (Love Data Week 2027).

**Live page:** `index.html` (served by GitHub Pages). It is one self-contained file with no external dependencies other than Google Fonts.

## Data

BTAA 2027 Love Data Week NCAA Women's Basketball data set, sourced from ESPN via the [SportsDataverse wehoop](https://github.com/sportsdataverse/wehoop) project. Seasons 2022-23 through 2025-26: play-by-play, team box scores and schedules (Parquet).

## Reproduce

Requires [DuckDB](https://duckdb.org) and Python 3 with numpy and pandas. Put the Parquet files in `analysis/data/` as `pbp_YYYY.parquet`, `team_box_YYYY.parquet` and `sched_YYYY.parquet`, then from `analysis/`:

```
mkdir -p web/data
duckdb wbb.duckdb < sql/01_snapshots.sql   # cleaned games + per-minute score snapshots
duckdb wbb.duckdb < sql/015_tables.sql     # pregame odds, comeback stats, Big Ten table, model rows
duckdb wbb.duckdb < sql/02_export.sql      # CSVs for the page
python3 model.py        # fit + validate the win-probability model -> model.json
python3 build_data.py   # compact JSON for the page
python3 build_site.py   # embed data -> site/index.html
```

## Method in brief

- 22,707 of 23,453 games kept (complete play-by-play whose final matches the official score).
- Score read at each whole minute of regulation; "held" = team ahead went on to win.
- Model: logistic( 0.79 × margin / √(minutes left + 0.5) + 1.05 × pregame log-odds × minutes left / 40 ), trained on 2022-23 to 2024-25 and tested on 2025-26 (Brier 0.112 vs 0.159 for the pregame forecast alone).

## AI assistance

Data analysis, statistical modeling, code, and page design were developed with the assistance of an AI tool (Claude, Anthropic). The author directed the project, reviewed the analysis and its verification against the official BTAA data set, and takes responsibility for the accuracy and content of this work.
