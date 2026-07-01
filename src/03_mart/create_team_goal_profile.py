import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH team_matches AS (
    SELECT home_team AS team_name, home_score AS goals_for, away_score AS goals_against
    FROM staging.matches_clean
    WHERE home_score IS NOT NULL AND away_score IS NOT NULL

    UNION ALL

    SELECT away_team AS team_name, away_score AS goals_for, home_score AS goals_against
    FROM staging.matches_clean
    WHERE home_score IS NOT NULL AND away_score IS NOT NULL
),

team_stats AS (
    SELECT
        team_name,
        COUNT(*) AS matches_played,
        AVG(goals_for::numeric) AS goals_for_per_game,
        AVG(goals_against::numeric) AS goals_against_per_game
    FROM team_matches
    GROUP BY team_name
),

base AS (
    SELECT
        dc.country_name AS team_name,
        dc.iso3,
        COALESCE(ts.matches_played, 0) AS matches_played,
        ts.goals_for_per_game,
        ts.goals_against_per_game,
        ss.team_strength_score,
        elo.elo_rating,
        elo.elo_score
    FROM mart.dim_country dc
    LEFT JOIN team_stats ts
        ON dc.country_name = ts.team_name
    LEFT JOIN mart.team_strength_score ss
        ON dc.country_name = ss.team_name
    LEFT JOIN mart.team_elo elo
        ON dc.country_name = elo.team_name
),

normalized AS (
    SELECT
        *,
        100 * (
            COALESCE(goals_for_per_game, 0)
            - MIN(COALESCE(goals_for_per_game, 0)) OVER()
        ) /
        NULLIF(
            MAX(COALESCE(goals_for_per_game, 0)) OVER()
            - MIN(COALESCE(goals_for_per_game, 0)) OVER(),
            0
        ) AS goals_for_score,

        100 * (
            MAX(COALESCE(goals_against_per_game, 0)) OVER()
            - COALESCE(goals_against_per_game, 0)
        ) /
        NULLIF(
            MAX(COALESCE(goals_against_per_game, 0)) OVER()
            - MIN(COALESCE(goals_against_per_game, 0)) OVER(),
            0
        ) AS goals_against_score
    FROM base
)

SELECT
    team_name,
    iso3,
    matches_played,
    goals_for_per_game,
    goals_against_per_game,
    goals_for_score,
    goals_against_score,
    team_strength_score,
    elo_rating,
    elo_score,

    (
        COALESCE(goals_for_score, 0) * 0.50 +
        COALESCE(team_strength_score, 0) * 0.30 +
        COALESCE(elo_score, 0) * 0.20
    ) AS attack_score,

    (
        COALESCE(goals_against_score, 0) * 0.50 +
        COALESCE(team_strength_score, 0) * 0.30 +
        COALESCE(elo_score, 0) * 0.20
    ) AS defense_score

FROM normalized
ORDER BY attack_score DESC
"""

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)

overwrite_table(

    df,
    "team_goal_profile",
    engine,
    schema="mart",
    index=False
)

print(df.head(30))
print(f"{len(df)} seleções carregadas em mart.team_goal_profile")