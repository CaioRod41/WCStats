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
    h.country_name_api,
    h.hdi,
    h.year
FROM mart.dim_country dc
LEFT JOIN mart.country_latest_hdi h
    ON dc.iso3 = h.iso3
ORDER BY dc.country_name
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "team_hdi",
    engine,
    schema="mart",
    index=False
)

print(df.head())
print(f"{len(df)} seleções carregadas")