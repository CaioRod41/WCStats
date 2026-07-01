import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT
    m.match_date,
    m.competition,
    m.home_team,
    m.away_team,
    m.home_score,
    m.away_score,
    m.city,
    m.country,
    m.neutral,
    m.data_source,

    hs.team_strength_score AS home_strength_score,
    aws.team_strength_score AS away_strength_score,

    hs.team_strength_score - aws.team_strength_score AS strength_diff,

    hs.recent_ppg AS home_recent_ppg,
    aws.recent_ppg AS away_recent_ppg,
    hs.recent_ppg - aws.recent_ppg AS recent_ppg_diff,

    hs.historical_ppg AS home_historical_ppg,
    aws.historical_ppg AS away_historical_ppg,
    hs.historical_ppg - aws.historical_ppg AS historical_ppg_diff,

    hs.market_value_eur AS home_market_value_eur,
    aws.market_value_eur AS away_market_value_eur,
    hs.market_value_eur - aws.market_value_eur AS market_value_diff,

    hs.fifa_rank AS home_fifa_rank,
    aws.fifa_rank AS away_fifa_rank,
    aws.fifa_rank - hs.fifa_rank AS fifa_rank_advantage,

    hs.fifa_points AS home_fifa_points,
    aws.fifa_points AS away_fifa_points,
    hs.fifa_points - aws.fifa_points AS fifa_points_diff,

    hs.environment_score AS home_environment_score,
    aws.environment_score AS away_environment_score,
    hs.environment_score - aws.environment_score AS environment_score_diff,

    hs.socioeconomic_score AS home_socioeconomic_score,
    aws.socioeconomic_score AS away_socioeconomic_score,
    hs.socioeconomic_score - aws.socioeconomic_score AS socioeconomic_score_diff,

    CASE
        WHEN m.home_score > m.away_score THEN 'HOME_WIN'
        WHEN m.home_score = m.away_score THEN 'DRAW'
        WHEN m.home_score < m.away_score THEN 'AWAY_WIN'
        ELSE NULL
    END AS match_result

FROM staging.matches_clean m

INNER JOIN mart.team_strength_score hs
    ON m.home_team = hs.team_name

INNER JOIN mart.team_strength_score aws
    ON m.away_team = aws.team_name

WHERE m.home_team IS NOT NULL
  AND m.away_team IS NOT NULL
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "match_features",
    engine,
    schema="mart",
    index=False
)

print(df.head())
print(f"{len(df)} jogos carregados em mart.match_features")

print("Jogos com força nula:")
print(df[
    df["home_strength_score"].isna() |
    df["away_strength_score"].isna()
])