import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH ranked AS (
    SELECT
        iso3,
        country_name_api,
        year,
        hdi,
        ROW_NUMBER() OVER (
            PARTITION BY iso3
            ORDER BY year DESC
        ) AS rn
    FROM raw.hdi_indicators
)
SELECT
    iso3,
    country_name_api,
    year,
    hdi
FROM ranked
WHERE rn = 1
ORDER BY country_name_api
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "country_latest_hdi",
    engine,
    schema="mart",
    index=False
)

print(f"{len(df)} países carregados")
print(df.head())