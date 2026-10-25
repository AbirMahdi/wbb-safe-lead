"""Turn exported CSVs into one compact JSON file the web page embeds."""
import csv, json, math
from collections import defaultdict

M = json.load(open("model.json"))
C, BM, BP = M["c"], M["b_margin"], M["b_pregame"]


def wp(margin, t, pre):
    pre = min(max(pre, 0.005), 0.995)
    z = BM * margin / math.sqrt(t + C) + BP * math.log(pre / (1 - pre)) * (t / 40.0)
    return 1 / (1 + math.exp(-z))


rows = lambda f: list(csv.DictReader(open(f"web/data/{f}")))

# evidence: {bucket: {t: {lead: [n, held]}}}
ev = defaultdict(lambda: defaultdict(dict))
for r in rows("evidence.csv"):
    ev[r["bucket"]][int(r["t"])][int(r["lead"])] = [int(r["n"]), int(r["held"])]

games = {r["game_id"]: r for r in rows("replay_games.csv")}
plays = defaultdict(list)
for r in rows("replay_plays.csv"):
    plays[r["game_id"]].append(r)

replays = []
for gid, g in games.items():
    pre = float(g["home_pre"])
    pts, last = [], None
    for r in plays[gid]:
        if r["secs"] == "" or r["period"] == "":
            continue
        per, secs = int(r["period"]), int(r["secs"])
        # elapsed minutes on a continuous axis (OT periods are 5 min)
        elapsed = (2400 - secs) / 60 if per <= 4 else 40 + 5 * (per - 5) + (300 - secs) / 60
        t_left = secs / 60
        m = int(r["h"]) - int(r["a"])
        key = (round(elapsed, 3), m)
        if key == last:
            continue
        last = key
        pts.append([round(elapsed, 3), m, round(wp(m, t_left, pre), 4), int(r["h"]), int(r["a"]), per, r["clock"]])
    pts.append([pts[-1][0], pts[-1][1], 1.0 if pts[-1][1] > 0 else 0.0] + pts[-1][3:])
    replays.append({"id": gid, "date": g["game_date"], "note": g["note"], "home": g["home"], "away": g["away"],
                    "hf": int(g["home_final"]), "af": int(g["away_final"]), "pre": round(pre, 3),
                    "periods": int(g["max_period"]), "pts": pts})

for rp in replays:
    win_home = rp["hf"] > rp["af"]
    wps = [p[2] if win_home else 1 - p[2] for p in rp["pts"][:-1]]
    margins = [p[1] if win_home else -p[1] for p in rp["pts"]]
    i = min(range(len(wps)), key=lambda k: wps[k])
    rp["winner_min_wp"] = round(wps[i], 4)
    rp["winner_min_wp_at"] = rp["pts"][i][0]
    rp["winner_max_deficit"] = -min(margins)
    print(rp["home"], "vs", rp["away"], rp["hf"], rp["af"], "| winner min WP", rp["winner_min_wp"],
          "at min", rp["winner_min_wp_at"], "| max deficit", rp["winner_max_deficit"])

big_ten = [{k: (float(v) if k.endswith("pct") else (int(v) if v.isdigit() else v)) for k, v in r.items()}
           for r in rows("big_ten.csv")]
top = rows("top_comebacks.csv")
meta = rows("meta.csv")[0]

out = {"model": {"c": C, "bm": BM, "bp": BP, "brier": round(M["test_brier"], 4),
                 "brier_pre": round(M["pregame_only_brier"], 4), "test_games": M["n_test_games"],
                 "cal": M["calibration"]},
       "evidence": ev, "replays": replays, "bigten": big_ten, "top": top[:10], "meta": meta}
json.dump(out, open("web/data/site.json", "w"), separators=(",", ":"))
print("site.json bytes:", len(json.dumps(out, separators=(",", ":"))))
