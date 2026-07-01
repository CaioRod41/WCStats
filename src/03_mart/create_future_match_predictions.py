import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT
    f.match_date,
    f.competition,
    f.home_team,
    f.away_team,
    f.status,

    hs.team_strength_score AS home_strength_score,
    aws.team_strength_score AS away_strength_score,

    hs.team_strength_score - aws.team_strength_score AS strength_diff,

    hs.recent_ppg AS home_recent_ppg,
    aws.recent_ppg AS away_recent_ppg,

    hs.historical_ppg AS home_historical_ppg,
    aws.historical_ppg AS away_historical_ppg,

    hs.market_value_eur AS home_market_value_eur,
    aws.market_value_eur AS away_market_value_eur,

    hs.fifa_rank AS home_fifa_rank,
    aws.fifa_rank AS away_fifa_rank,

    hs.fifa_points AS home_fifa_points,
    aws.fifa_points AS away_fifa_points,

    hgp.attack_score AS home_attack_score,
    hgp.defense_score AS home_defense_score,
    agp.attack_score AS away_attack_score,
    agp.defense_score AS away_defense_score

FROM staging.worldcup_fixtures f

INNER JOIN mart.team_strength_score hs
    ON f.home_team = hs.team_name

INNER JOIN mart.team_strength_score aws
    ON f.away_team = aws.team_name

LEFT JOIN mart.team_goal_profile hgp
    ON f.home_team = hgp.team_name

LEFT JOIN mart.team_goal_profile agp
    ON f.away_team = agp.team_name

WHERE f.home_team NOT LIKE 'W%%'
  AND f.away_team NOT LIKE 'W%%'
  AND f.home_team NOT LIKE 'L%%'
  AND f.away_team NOT LIKE 'L%%'
"""

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)


def calculate_probabilities(strength_diff):
    expected_home = 1 / (1 + 10 ** (-strength_diff / 50))

    draw_prob = 0.30 - min(abs(strength_diff) / 250, 0.12)
    draw_prob = max(draw_prob, 0.18)

    remaining = 1 - draw_prob

    home_win_prob = expected_home * remaining
    away_win_prob = (1 - expected_home) * remaining

    return round(home_win_prob, 4), round(draw_prob, 4), round(away_win_prob, 4)


def calculate_xg(row):
    base_home_xg = 1.45
    base_away_xg = 1.15

    home_attack = float(row["home_attack_score"])
    away_attack = float(row["away_attack_score"])
    home_defense = float(row["home_defense_score"])
    away_defense = float(row["away_defense_score"])
    strength_diff = float(row["strength_diff"])

    home_attack_mult = 0.70 + (home_attack / 100) * 0.60
    away_attack_mult = 0.70 + (away_attack / 100) * 0.60

    away_defense_vulnerability = 1.30 - (away_defense / 100) * 0.60
    home_defense_vulnerability = 1.30 - (home_defense / 100) * 0.60

    home_strength_adj = max(min(1 + strength_diff / 250, 1.20), 0.80)
    away_strength_adj = max(min(1 - strength_diff / 250, 1.20), 0.80)

    home_xg = (
        base_home_xg
        * home_attack_mult
        * away_defense_vulnerability
        * home_strength_adj
    )

    away_xg = (
        base_away_xg
        * away_attack_mult
        * home_defense_vulnerability
        * away_strength_adj
    )

    home_xg = max(min(home_xg, 3.20), 0.25)
    away_xg = max(min(away_xg, 3.00), 0.25)

    return round(home_xg, 3), round(away_xg, 3)


probs = df["strength_diff"].apply(calculate_probabilities)

df["home_win_prob"] = probs.apply(lambda x: x[0])
df["draw_prob"] = probs.apply(lambda x: x[1])
df["away_win_prob"] = probs.apply(lambda x: x[2])

df["predicted_result"] = np.select(
    [
        (df["home_win_prob"] > df["draw_prob"]) & (df["home_win_prob"] > df["away_win_prob"]),
        (df["away_win_prob"] > df["draw_prob"]) & (df["away_win_prob"] > df["home_win_prob"])
    ],
    ["HOME_WIN", "AWAY_WIN"],
    default="DRAW"
)

df["favorite_team"] = np.select(
    [
        df["predicted_result"] == "HOME_WIN",
        df["predicted_result"] == "AWAY_WIN"
    ],
    [df["home_team"], df["away_team"]],
    default="Draw"
)

df["prediction_confidence"] = (
    df[["home_win_prob", "draw_prob", "away_win_prob"]]
    .max(axis=1)
    * 100
).round(2)

xg = df.apply(calculate_xg, axis=1)

df["home_xg"] = xg.apply(lambda x: x[0])
df["away_xg"] = xg.apply(lambda x: x[1])
df["total_xg"] = (df["home_xg"] + df["away_xg"]).round(3)

df["match_balance_index"] = (
    100 - (abs(df["strength_diff"]) * 1.2)
).clip(lower=0, upper=100).round(2)

result = df[
    [
        "match_date",
        "competition",
        "home_team",
        "away_team",
        "status",
        "home_strength_score",
        "away_strength_score",
        "strength_diff",
        "home_win_prob",
        "draw_prob",
        "away_win_prob",
        "predicted_result",
        "favorite_team",
        "prediction_confidence",
        "home_xg",
        "away_xg",
        "total_xg",
        "match_balance_index",
        "home_attack_score",
        "away_attack_score",
        "home_defense_score",
        "away_defense_score",
        "home_recent_ppg",
        "away_recent_ppg",
        "home_historical_ppg",
        "away_historical_ppg",
        "home_market_value_eur",
        "away_market_value_eur",
        "home_fifa_rank",
        "away_fifa_rank",
        "home_fifa_points",
        "away_fifa_points"
    ]
]

overwrite_table(

    result,
    "future_match_predictions",
    engine,
    schema="mart",
    index=False
)

print(result.head(30))
print(f"{len(result)} jogos futuros carregados em mart.future_match_predictions")