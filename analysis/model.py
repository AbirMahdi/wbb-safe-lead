"""Fit and validate a simple in-game win-probability model for NCAA women's basketball.

logit P(home wins) = b1 * margin / sqrt(t + c) + b2 * logit(pregame) * (t / 40)   (no intercept: pregame prob already carries home court)
  margin = home score - away score, t = minutes left in regulation.
Train on 2022-23..2024-25, test on 2025-26 (held out).
"""
import json
import numpy as np
import pandas as pd

df = pd.read_csv("model_rows.csv")
df["y"] = (df.final_margin > 0).astype(float)
php = df.php.clip(0.005, 0.995)
df["lp"] = np.log(php / (1 - php))


def feats(d, c):
    return np.column_stack([
        d.margin / np.sqrt(d.t + c),
        d.lp * (d.t / 40.0),
    ])


def fit(X, y, iters=40):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b))
        w = p * (1 - p) + 1e-9
        g = X.T @ (y - p)
        H = X.T @ (X * w[:, None])
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def logloss(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


train = df[df.season <= 2025]
test = df[df.season == 2026]

best = None
for c in [0.25, 0.5, 0.75, 1, 1.5, 2]:
    b = fit(feats(train, c), train.y.values)
    ll = logloss(1 / (1 + np.exp(-feats(train, c) @ b)), train.y.values)
    if best is None or ll < best[0]:
        best = (ll, c, b)
ll_tr, c, b = best

p_te = 1 / (1 + np.exp(-feats(test, c) @ b))
y_te = test.y.values
brier = np.mean((p_te - y_te) ** 2)
# baseline: pregame only
p0 = test.php.clip(0.005, 0.995).values
print(f"c={c}  coef={b.round(4)}")
print(f"TEST 2025-26: logloss={logloss(p_te, y_te):.4f}  brier={brier:.4f}   pregame-only brier={np.mean((p0-y_te)**2):.4f}")

# calibration on test
bins = np.linspace(0, 1, 11)
idx = np.clip(np.digitize(p_te, bins) - 1, 0, 9)
cal = []
for k in range(10):
    m = idx == k
    cal.append({"bin": f"{bins[k]:.1f}-{bins[k+1]:.1f}", "n": int(m.sum()),
                "pred": round(float(p_te[m].mean()), 3), "actual": round(float(y_te[m].mean()), 3)})
for r in cal:
    print(r)

json.dump({"c": c, "b_margin": b[0], "b_pregame": b[1],
           "test_brier": brier, "test_logloss": logloss(p_te, y_te),
           "pregame_only_brier": float(np.mean((p0 - y_te) ** 2)),
           "n_train_rows": int(len(train)), "n_test_rows": int(len(test)),
           "n_test_games": int(test.game_id.nunique()), "calibration": cal},
          open("model.json", "w"), indent=1)
