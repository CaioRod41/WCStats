import pandas as pd
from scipy.stats import poisson
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT *
FROM mart.future_match_predictions
WHERE home_xg IS NOT NULL
  AND away_xg IS NOT NULL
"""

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)


def score_matrix(home_xg, away_xg, max_goals=6):
    rows = []

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            prob = (
                poisson.pmf(home_goals, home_xg)
                * poisson.pmf(away_goals, away_xg)
            )

            rows.append({
                "home_goals": home_goals,
                "away_goals": away_goals,
                "scoreline": f"{home_goals}x{away_goals}",
                "probability": prob
            })

    return pd.DataFrame(rows)


results = []

for _, row in df.iterrows():
    matrix = score_matrix(row["home_xg"], row["away_xg"])

    matrix["total_goals"] = matrix["home_goals"] + matrix["away_goals"]
    matrix["btts"] = (matrix["home_goals"] > 0) & (matrix["away_goals"] > 0)

    top5 = matrix.sort_values("probability", ascending=False).head(5)
    most_likely = top5.iloc[0]

    btts_prob = matrix.loc[matrix["btts"], "probability"].sum()
    over_1_5 = matrix.loc[matrix["total_goals"] > 1.5, "probability"].sum()
    over_2_5 = matrix.loc[matrix["total_goals"] > 2.5, "probability"].sum()
    over_3_5 = matrix.loc[matrix["total_goals"] > 3.5, "probability"].sum()
    under_2_5 = matrix.loc[matrix["total_goals"] < 2.5, "probability"].sum()

    results.append({
        "match_date": row["match_date"],
        "competition": row["competition"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "status": row["status"],

        "home_win_prob": row["home_win_prob"],
        "draw_prob": row["draw_prob"],
        "away_win_prob": row["away_win_prob"],
        "favorite_team": row["favorite_team"],
        "prediction_confidence": row["prediction_confidence"],

        "home_xg": row["home_xg"],
        "away_xg": row["away_xg"],
        "total_xg": row["total_xg"],
        "match_balance_index": row["match_balance_index"],

        "most_likely_score": most_likely["scoreline"],
        "most_likely_score_prob": round(most_likely["probability"], 4),

        "top_1_score": top5.iloc[0]["scoreline"],
        "top_1_score_prob": round(top5.iloc[0]["probability"], 4),
        "top_2_score": top5.iloc[1]["scoreline"],
        "top_2_score_prob": round(top5.iloc[1]["probability"], 4),
        "top_3_score": top5.iloc[2]["scoreline"],
        "top_3_score_prob": round(top5.iloc[2]["probability"], 4),
        "top_4_score": top5.iloc[3]["scoreline"],
        "top_4_score_prob": round(top5.iloc[3]["probability"], 4),
        "top_5_score": top5.iloc[4]["scoreline"],
        "top_5_score_prob": round(top5.iloc[4]["probability"], 4),

        "btts_prob": round(btts_prob, 4),
        "over_1_5_prob": round(over_1_5, 4),
        "over_2_5_prob": round(over_2_5, 4),
        "over_3_5_prob": round(over_3_5, 4),
        "under_2_5_prob": round(under_2_5, 4)
    })


result = pd.DataFrame(results)

overwrite_table(
    result,
    "score_probabilities",
    engine,
    schema="mart",
    index=False
)

print(result.head(30))
print(f"{len(result)} jogos atualizados em mart.score_probabilities")
