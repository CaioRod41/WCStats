import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH market_value_mapped AS (
    SELECT
       CASE
    WHEN LOWER(TRIM(team_name)) = 'democratic republic of the congo'
        THEN 'DR Congo'

    WHEN LOWER(TRIM(team_name)) = 'bosnia-herzegovina'
        THEN 'Bosnia & Herzegovina'

    WHEN LOWER(TRIM(team_name)) = 'united states'
        THEN 'USA'

    WHEN LOWER(TRIM(team_name)) IN ('turkiye', 'türkiye', 'turkey')
        THEN 'Turkey'

    WHEN LOWER(TRIM(team_name)) = 'czechia'
        THEN 'Czech Republic'

    ELSE TRIM(team_name)
END AS team_name_mapped,
        players_count,
        avg_age,
        market_value_text,
        market_value_eur
    FROM raw.team_market_value
)
SELECT
    dc.country_name AS team_name,
    dc.iso3,
    mv.players_count,
    mv.avg_age,
    mv.market_value_text,
    mv.market_value_eur,
    mv.market_value_eur / NULLIF(mv.players_count, 0) AS avg_market_value_eur
FROM mart.dim_country dc
LEFT JOIN market_value_mapped mv
    ON dc.country_name = mv.team_name_mapped
ORDER BY mv.market_value_eur DESC
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "team_market_value",
    engine,
    schema="mart",
    index=False
)

print(df)
print(f"{len(df)} seleções carregadas em mart.team_market_value")

print("Seleções sem valor de mercado:")
print(df[df["market_value_eur"].isna()])