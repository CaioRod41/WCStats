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

    AVG(cce.avg_temperature_annual) AS avg_temperature_annual,
    AVG(cce.avg_humidity_annual) AS avg_humidity_annual,
    AVG(cce.elevation_meters) AS avg_elevation_meters,

    MIN(cce.elevation_meters) AS min_elevation_meters,
    MAX(cce.elevation_meters) AS max_elevation_meters,

    COUNT(cce.city_name) AS cities_used
FROM mart.dim_country dc
LEFT JOIN raw.country_city_environment cce
    ON dc.iso3 = cce.iso3
GROUP BY
    dc.country_name,
    dc.iso3
ORDER BY
    dc.country_name
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "team_environment_profile",
    engine,
    schema="mart",
    index=False
)

print(df.head(50))
print(f"{len(df)} seleções carregadas em mart.team_environment_profile")