import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH ranked_indicators AS (
    SELECT
        iso3,
        country_name_api,
        indicator_name,
        year::int AS year,
        value,
        ROW_NUMBER() OVER (
            PARTITION BY iso3, indicator_name
            ORDER BY year::int DESC
        ) AS rn
    FROM raw.country_indicators
    WHERE value IS NOT NULL
)
SELECT
    iso3,
    country_name_api,
    MAX(CASE WHEN indicator_name = 'gdp_current_usd' THEN value END) AS gdp_current_usd,
    MAX(CASE WHEN indicator_name = 'gdp_per_capita_current_usd' THEN value END) AS gdp_per_capita_current_usd,
    MAX(CASE WHEN indicator_name = 'population_total' THEN value END) AS population_total,
    MAX(CASE WHEN indicator_name = 'life_expectancy' THEN value END) AS life_expectancy,
    MAX(CASE WHEN indicator_name = 'gdp_current_usd' THEN year END) AS gdp_year,
    MAX(CASE WHEN indicator_name = 'gdp_per_capita_current_usd' THEN year END) AS gdp_per_capita_year,
    MAX(CASE WHEN indicator_name = 'population_total' THEN year END) AS population_year,
    MAX(CASE WHEN indicator_name = 'life_expectancy' THEN year END) AS life_expectancy_year
FROM ranked_indicators
WHERE rn = 1
GROUP BY iso3, country_name_api
ORDER BY country_name_api
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "country_latest_indicators",
    engine,
    schema="mart",
    index=False
)

print(f"{len(df)} países carregados em mart.country_latest_indicators")
print(df.head())