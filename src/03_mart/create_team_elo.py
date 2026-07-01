import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT
    match_date,
    home_team,
    away_team,
    home_score,
    away_score,
    competition
FROM staging.matches_clean
WHERE home_team IS NOT NULL
  AND away_team IS NOT NULL
  AND home_score IS NOT NULL
  AND away_score IS NOT NULL
ORDER BY match_date
"""

with engine.connect() as conn:
    matches = pd.read_sql(text(query), conn)

INITIAL_ELO = 1500
K_BASE = 25
HOME_ADVANTAGE = 35

elos = {}
matches_played = {}


def get_elo(team):
    if team not in elos:
        elos[team] = INITIAL_ELO
        matches_played[team] = 0
    return elos[team]


def actual_score(home_score, away_score):
    if home_score > away_score:
        return 1.0
    if home_score == away_score:
        return 0.5
    return 0.0


def competition_weight(competition):
    comp = str(competition).lower()

    if "world cup" in comp:
        return 1.40
    if "euro" in comp or "copa américa" in comp or "african cup" in comp or "asian cup" in comp:
        return 1.20
    if "qualification" in comp:
        return 1.00
    if "nations league" in comp:
        return 0.90
    if "friendly" in comp:
        return 0.60

    return 1.00


for _, row in matches.iterrows():
    home_team = row["home_team"]
    away_team = row["away_team"]

    home_elo = get_elo(home_team)
    away_elo = get_elo(away_team)

    expected_home = 1 / (1 + 10 ** ((away_elo - (home_elo + HOME_ADVANTAGE)) / 400))
    actual_home = actual_score(row["home_score"], row["away_score"])

    goal_diff = abs(row["home_score"] - row["away_score"])
    goal_multiplier = 1 + min(goal_diff, 4) * 0.15

    k = K_BASE * competition_weight(row["competition"]) * goal_multiplier

    elo_change = k * (actual_home - expected_home)

    elos[home_team] = home_elo + elo_change
    elos[away_team] = away_elo - elo_change

    matches_played[home_team] += 1
    matches_played[away_team] += 1


elo_df = pd.DataFrame([
    {
        "team_name": team,
        "elo_rating": round(rating, 2),
        "matches_played": matches_played[team]
    }
    for team, rating in elos.items()
])

# Mantém só as seleções da Copa/dim_country
dim_query = """
SELECT country_name AS team_name, iso3
FROM mart.dim_country
"""

with engine.connect() as conn:
    dim = pd.read_sql(text(dim_query), conn)

result = dim.merge(elo_df, on="team_name", how="left")

result["elo_rating"] = result["elo_rating"].fillna(INITIAL_ELO)
result["matches_played"] = result["matches_played"].fillna(0).astype(int)

result["elo_score"] = (
    100
    * (result["elo_rating"] - result["elo_rating"].min())
    / (result["elo_rating"].max() - result["elo_rating"].min())
).round(4)

result = result.sort_values("elo_rating", ascending=False)

overwrite_table(

    result,
    "team_elo",
    engine,
    schema="mart",
    index=False
)

print(result.head(30))
print(f"{len(result)} seleções carregadas em mart.team_elo")