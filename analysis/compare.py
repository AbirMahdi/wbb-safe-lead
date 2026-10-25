"""Compare every page-stated figure between two pipeline runs (A = wehoop release, B = official BTAA pbp)."""
import json, subprocess, sys
A = "/home/claude/wbb"; B = sys.argv[1]
def site(d): return json.load(open(f"{d}/web/data/site.json"))
def q(d, sql): return subprocess.run([f"/home/claude/wbb/bin/duckdb", "-list", "-noheader", f"{d}/wbb.duckdb", "-c", sql], capture_output=True, text=True).stdout.strip()
def ev(s, b, t, l): x = s["evidence"][b].get(str(t), {}).get(str(l)); return x
def pct(x): return f"{100*x[1]/x[0]:.1f}% ({x[1]}/{x[0]})" if x else "-"
rows = []
for name, d in [("wehoop", A), ("official", B)]:
    s = site(d); r = {}
    r["games kept"] = s["meta"]["games"]
    r["even games"] = q(d, "select count(distinct game_id) from snaps2 where even")
    r["placeholder games"] = q(d, "select count(*) from pre join games using(game_id) where round(php,4)=0.586")
    r["up 10 at half (all)"] = pct(ev(s, "all", 20, 10))
    r["up 10, 2 min (all)"] = pct(ev(s, "all", 2, 10))
    r["up 3, 5 min (all)"] = pct(ev(s, "all", 5, 3))
    r["up 10 half (even)"] = pct(ev(s, "even", 20, 10))
    r["model bm/bp"] = f"{s['model']['bm']:.4f} / {s['model']['bp']:.4f}"
    r["brier / pregame"] = f"{s['model']['brier']} / {s['model']['brier_pre']}"
    r["cal 0.8-0.9 actual"] = str(s["model"]["cal"][8]["actual"])
    bt = {x["team"]: x for x in s["bigten"]}
    for t in ["Purdue Boilermakers", "UCLA Bruins"]:
        x = bt[t]; r[t] = f"held {x['led10_games']-x['blown_10']}/{x['led10_games']}, comeback {x['comeback_wins_10']}/{x['trailed10_games']}"
    hp = sorted(x["held_pct"] for x in s["bigten"]); r["B1G median held"] = str((hp[8]+hp[9])/2)
    r["top 10 comebacks"] = "; ".join(f"{x['winner'].split()[0]} {x['max_deficit']}" for x in s["top"])
    r["B1G-vs-B1G rank of PUR-WIS"] = q(d, "select rk from (select game_id, row_number() over (order by max_deficit desc) rk from gstats where winner_conf=7 and loser_conf=7) where game_id=401516439")
    for rp in s["replays"]: r["replay " + rp["home"].split()[0] + "-" + rp["away"].split()[0]] = f"min WP {rp['winner_min_wp']}, deficit {rp['winner_max_deficit']}"
    rows.append(r)
w = max(len(k) for k in rows[0])
print(f"{'':{w}}  {'WEHOOP (page)':45}  OFFICIAL BTAA")
for k in rows[0]:
    a, b = rows[0][k], rows[1][k]; flag = "" if a == b else "  <-- differs"
    print(f"{k:{w}}  {a:45}  {b}{flag}")
