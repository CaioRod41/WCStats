import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# --------------------------------------------------
# Médias históricas globais
# --------------------------------------------------

avg_query = """
SELECT
    AVG(home_score)::numeric AS avg_home_goals,
    AVG(away_score)::numeric AS avg_away_goals
FROM staging.matches_clean
WHERE home_score IS NOT NULL
  AND away_score IS NOT NULL
"""

avg_df = pd.read_sql(avg_query, engine)

AVG_HOME_GOALS = float(avg_df.iloc[0]["avg_home_goals"])
AVG_AWAY_GOALS = float(avg_df.iloc[0]["avg_away_goals"])

print(f"Média gols casa: {AVG_HOME_GOALS:.3f}")
print(f"Média gols fora: {AVG_AWAY_GOALS:.3f}")

# --------------------------------------------------
# Match Features
# --------------------------------------------------

matches = pd.read_sql(
    """
    SELECT
        *
    FROM mart.match_features
    """,
    engine
)

# --------------------------------------------------
# Cálculo de xG
# --------------------------------------------------

def calculate_xg(row):

    strength_diff = row["strength_diff"]

    # Normalização
    strength_factor = strength_diff / 100.0

    # Limite para evitar exageros
    strength_factor = max(min(strength_factor, 0.50), -0.50)

    home_xg = AVG_HOME_GOALS * (1 + strength_factor)
    away_xg = AVG_AWAY_GOALS * (1 - strength_factor)

    home_xg = max(home_xg, 0.20)
    away_xg = max(away_xg, 0.20)

    return pd.Series(
        [
            round(home_xg, 3),
            round(away_xg, 3),
            round(home_xg + away_xg, 3)
        ]
    )

matches[
    [
        "home_xg",
        "away_xg",
        "total_xg"
    ]
] = matches.apply(
    calculate_xg,
    axis=1
)

# --------------------------------------------------
# Favorito esperado
# --------------------------------------------------

matches["expected_favorite"] = matches.apply(
    lambda x:
        x["home_team"]
        if x["home_xg"] > x["away_xg"]
        else x["away_team"],
    axis=1
)

# --------------------------------------------------
# Índice de equilíbrio
# --------------------------------------------------

matches["match_balance_index"] = (
    100
    - (
        abs(
            matches["home_xg"]
            - matches["away_xg"]
        )
        * 25
    )
)

matches["match_balance_index"] = (
    matches["match_balance_index"]
    .clip(lower=0, upper=100)
    .round(2)
)

# --------------------------------------------------
# Resultado
# --------------------------------------------------

result = matches[
    [
        "match_date",
        "competition",
        "home_team",
        "away_team",
        "home_xg",
        "away_xg",
        "total_xg",
        "expected_favorite",
        "match_balance_index"
    ]
]

overwrite_table(

    result,
    "match_xg",
    engine,
    schema="mart",
    index=False
)

print(result.head(20))

print(
    f"{len(result)} jogos carregados em mart.match_xg"
)