import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH base AS (
    SELECT
        dc.country_name AS team_name,
        dc.iso3,

        rs.points_per_game AS recent_ppg,
        hs.points_per_game AS historical_ppg,

        mv.market_value_eur,

        tr.fifa_rank,
        tr.fifa_points,

        env.avg_temperature_annual,
        env.avg_humidity_annual,
        env.avg_elevation_meters,

        ci.gdp_per_capita_current_usd,
        ci.life_expectancy,
        ci.population_total,

        elo.elo_rating,
        elo.elo_score,
        hdi.hdi

    FROM mart.dim_country dc

    LEFT JOIN mart.team_recent_strength rs
        ON dc.country_name = rs.team

    LEFT JOIN mart.team_historical_strength hs
        ON dc.country_name = hs.team

    LEFT JOIN mart.team_market_value mv
        ON dc.country_name = mv.team_name

    LEFT JOIN mart.team_ranking tr
        ON dc.country_name = tr.team_name

    LEFT JOIN mart.team_environment_profile env
        ON dc.country_name = env.team_name

    LEFT JOIN mart.team_country_indicators ci
        ON dc.country_name = ci.team_name

    LEFT JOIN mart.team_hdi hdi
        ON dc.country_name = hdi.team_name

    LEFT JOIN mart.team_elo elo
        ON dc.country_name = elo.team_name
),

normalized AS (
    SELECT
        *,

        100 * (recent_ppg - MIN(recent_ppg) OVER()) /
            NULLIF(MAX(recent_ppg) OVER() - MIN(recent_ppg) OVER(), 0) AS recent_score,

        100 * (historical_ppg - MIN(historical_ppg) OVER()) /
            NULLIF(MAX(historical_ppg) OVER() - MIN(historical_ppg) OVER(), 0) AS historical_score,

        100 * (market_value_eur - MIN(market_value_eur) OVER()) /
            NULLIF(MAX(market_value_eur) OVER() - MIN(market_value_eur) OVER(), 0) AS market_score,

        100 * (fifa_points - MIN(fifa_points) OVER()) /
            NULLIF(MAX(fifa_points) OVER() - MIN(fifa_points) OVER(), 0) AS fifa_score,

        100 * (
            COALESCE(gdp_per_capita_current_usd, 0)
            - MIN(COALESCE(gdp_per_capita_current_usd, 0)) OVER()
        ) /
            NULLIF(
                MAX(COALESCE(gdp_per_capita_current_usd, 0)) OVER()
                - MIN(COALESCE(gdp_per_capita_current_usd, 0)) OVER(),
                0
            ) AS gdp_score,

        100 * (
            COALESCE(hdi, 0)
            - MIN(COALESCE(hdi, 0)) OVER()
        ) /
            NULLIF(
                MAX(COALESCE(hdi, 0)) OVER()
                - MIN(COALESCE(hdi, 0)) OVER(),
                0
            ) AS hdi_score,

        100 * (
            COALESCE(life_expectancy, 0)
            - MIN(COALESCE(life_expectancy, 0)) OVER()
        ) /
            NULLIF(
                MAX(COALESCE(life_expectancy, 0)) OVER()
                - MIN(COALESCE(life_expectancy, 0)) OVER(),
                0
            ) AS life_expectancy_score,

        100 * (
            1 - (
                ABS(COALESCE(avg_elevation_meters, 0) - 500)
                /
                NULLIF(MAX(ABS(COALESCE(avg_elevation_meters, 0) - 500)) OVER(), 0)
            )
        ) AS environment_score

    FROM base
)

SELECT
    team_name,
    iso3,

    recent_ppg,
    historical_ppg,

    market_value_eur,

    fifa_rank,
    fifa_points,

    recent_score,
    market_score,
    historical_score,
    fifa_score,
    environment_score,
    elo_rating,
    elo_score,

    (
        COALESCE(gdp_score, 0) * 0.40 +
        COALESCE(hdi_score, 0) * 0.40 +
        COALESCE(life_expectancy_score, 0) * 0.20
    ) AS socioeconomic_score,

    (
        COALESCE(elo_score, 0) * 0.45 +
        COALESCE(fifa_score, 0) * 0.23 +
        COALESCE(recent_score, 0) * 0.15 +
        COALESCE(market_score, 0) * 0.10 +
        COALESCE(historical_score, 0) * 0.05 +
        COALESCE(environment_score, 0) * 0.01 +
        (
            COALESCE(gdp_score, 0) * 0.40 +
            COALESCE(hdi_score, 0) * 0.40 +
            COALESCE(life_expectancy_score, 0) * 0.20
        ) * 0.01
    ) AS team_strength_score

FROM normalized
ORDER BY team_strength_score DESC
"""

df = pd.read_sql(query, engine)

overwrite_table(
    df,
    "team_strength_score",
    engine,
    schema="mart",
    index=False
)

print(df.head(30))
print(f"{len(df)} seleções atualizadas em mart.team_strength_score")
