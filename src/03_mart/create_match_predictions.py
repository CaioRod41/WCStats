import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

df = pd.read_sql(
    "SELECT * FROM mart.match_features",
    engine
)

# --------------------------------------------------
# Probabilidade estilo Elo
# --------------------------------------------------

def calculate_probabilities(strength_diff):

    expected_home = 1 / (1 + 10 ** (-strength_diff / 20))

    draw_prob = (
        0.30
        - min(abs(strength_diff) / 200, 0.15)
    )

    draw_prob = max(draw_prob, 0.15)

    remaining = 1 - draw_prob

    home_win_prob = expected_home * remaining
    away_win_prob = (1 - expected_home) * remaining

    return (
        round(home_win_prob, 4),
        round(draw_prob, 4),
        round(away_win_prob, 4)
    )

probs = df["strength_diff"].apply(calculate_probabilities)

df["home_win_prob"] = probs.apply(lambda x: x[0])
df["draw_prob"] = probs.apply(lambda x: x[1])
df["away_win_prob"] = probs.apply(lambda x: x[2])

# --------------------------------------------------
# Favorito
# --------------------------------------------------

df["predicted_result"] = np.select(
    [
        df["home_win_prob"] >= df["draw_prob"],
        df["draw_prob"] > df["home_win_prob"]
    ],
    [
        np.where(
            df["home_win_prob"] > df["away_win_prob"],
            "HOME_WIN",
            "AWAY_WIN"
        ),
        "DRAW"
    ],
    default="DRAW"
)

# --------------------------------------------------
# Confiança
# --------------------------------------------------

df["prediction_confidence"] = (
    df[
        [
            "home_win_prob",
            "draw_prob",
            "away_win_prob"
        ]
    ]
    .max(axis=1)
    * 100
).round(2)

# --------------------------------------------------
# Salva
# --------------------------------------------------

columns = [
    "match_date",
    "competition",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "match_result",
    "strength_diff",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "predicted_result",
    "prediction_confidence"
]

predictions = df[columns]

overwrite_table(

    predictions,
    "match_predictions",
    engine,
    schema="mart",
    index=False
)

print(predictions.head(20))

print(
    f"{len(predictions)} jogos carregados em mart.match_predictions"
)