import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH recent_matches AS (

    SELECT *
    FROM staging.matches_clean
    WHERE match_date >= '2023-01-01'

),

all_matches AS (

    SELECT
        home_team AS team,

        CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS wins,
        CASE WHEN home_score = away_score THEN 1 ELSE 0 END AS draws,
        CASE WHEN home_score < away_score THEN 1 ELSE 0 END AS losses,

        home_score AS goals_for,
        away_score AS goals_against

    FROM recent_matches

    UNION ALL

    SELECT
        away_team AS team,

        CASE WHEN away_score > home_score THEN 1 ELSE 0 END,
        CASE WHEN away_score = home_score THEN 1 ELSE 0 END,
        CASE WHEN away_score < home_score THEN 1 ELSE 0 END,

        away_score,
        home_score

    FROM recent_matches
)

SELECT
    team,

    COUNT(*) AS matches_played,

    SUM(wins) AS wins,
    SUM(draws) AS draws,
    SUM(losses) AS losses,

    SUM(goals_for) AS goals_for,
    SUM(goals_against) AS goals_against,

    SUM(goals_for) - SUM(goals_against) AS goal_difference,

    ROUND(
        SUM(wins)::numeric /
        NULLIF(COUNT(*),0),
        4
    ) AS win_rate,

    ROUND(
        (
            SUM(wins) * 3 +
            SUM(draws)
        )::numeric /
        NULLIF(COUNT(*),0),
        4
    ) AS points_per_game

FROM all_matches
WHERE team IS NOT NULL
GROUP BY team
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "team_recent_strength",
    engine,
    schema="mart",
    index=False
)

print(df.sort_values("win_rate", ascending=False).head(20))
print(f"{len(df)} seleções carregadas")