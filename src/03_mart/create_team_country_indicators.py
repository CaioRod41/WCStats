import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT
    dc.country_name AS team_name,
    dc.iso3,
    cli.country_name_api,
    cli.gdp_current_usd,
    cli.gdp_per_capita_current_usd,
    cli.population_total,
    cli.life_expectancy,
    cli.gdp_year,
    cli.gdp_per_capita_year,
    cli.population_year,
    cli.life_expectancy_year
FROM mart.dim_country dc
LEFT JOIN mart.country_latest_indicators cli
    ON dc.iso3 = cli.iso3
ORDER BY dc.country_name
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "team_country_indicators",
    engine,
    schema="mart",
    index=False
)

print(f"{len(df)} seleções carregadas em mart.team_country_indicators")
print(df.head(50))

print("Seleções sem indicadores:")
print(df[df["gdp_current_usd"].isna()])