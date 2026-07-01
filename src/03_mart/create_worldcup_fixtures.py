import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT
    w.data::date AS match_date,

    CASE
        WHEN mh.canonical_name = 'United States' THEN 'USA'
        WHEN mh.canonical_name = 'Czechia' THEN 'Czech Republic'
        WHEN mh.canonical_name IN ('Bosnia and Herzegovina', 'Bosnia-Herzegovina') THEN 'Bosnia & Herzegovina'
        ELSE mh.canonical_name
    END AS home_team,

    CASE
        WHEN ma.canonical_name = 'United States' THEN 'USA'
        WHEN ma.canonical_name = 'Czechia' THEN 'Czech Republic'
        WHEN ma.canonical_name IN ('Bosnia and Herzegovina', 'Bosnia-Herzegovina') THEN 'Bosnia & Herzegovina'
        ELSE ma.canonical_name
    END AS away_team,

    w.status,
    'FIFA World Cup 2026' AS competition,
    'future_fixture' AS data_source

FROM raw.worldcup_matches w

LEFT JOIN staging.team_mapping mh
    ON w.time_casa = mh.team_name

LEFT JOIN staging.team_mapping ma
    ON w.time_fora = ma.team_name

WHERE LOWER(w.status) IN ('agendado', 'scheduled')
  AND w.time_casa IS NOT NULL
  AND w.time_fora IS NOT NULL
  AND w.time_casa NOT LIKE '%TBD%'
  AND w.time_fora NOT LIKE '%TBD%'
  AND w.time_casa NOT LIKE '%/%'
  AND w.time_fora NOT LIKE '%/%'
  AND w.time_casa !~ '^[0-9]'
  AND w.time_fora !~ '^[0-9]'
"""

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn)

overwrite_table(

    df,
    "worldcup_fixtures",
    engine,
    schema="staging",
    index=False
)

print(df.head(30))
print(f"{len(df)} jogos futuros carregados em staging.worldcup_fixtures")

print("Jogos com time nulo:")
print(df[df["home_team"].isna() | df["away_team"].isna()])