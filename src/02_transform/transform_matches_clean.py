import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

historical_query = """
SELECT
    h.date::date AS match_date,

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

    h.home_score,
    h.away_score,
    h.tournament AS competition,
    h.city,
    h.country,
    h.neutral,
    'historical' AS data_source
FROM raw.historical_matches h
LEFT JOIN staging.team_mapping mh
    ON h.home_team = mh.team_name
LEFT JOIN staging.team_mapping ma
    ON h.away_team = ma.team_name
WHERE h.home_score IS NOT NULL
  AND h.away_score IS NOT NULL
"""

worldcup_query = """
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

    w.gols_casa AS home_score,
    w.gols_fora AS away_score,
    'FIFA World Cup 2026' AS competition,
    NULL AS city,
    NULL AS country,
    NULL AS neutral,
    'worldcup_2026' AS data_source
FROM raw.worldcup_matches w
LEFT JOIN staging.team_mapping mh
    ON w.time_casa = mh.team_name
LEFT JOIN staging.team_mapping ma
    ON w.time_fora = ma.team_name
WHERE w.status = 'Finalizado'
  AND w.gols_casa IS NOT NULL
  AND w.gols_fora IS NOT NULL
"""

historical_df = pd.read_sql(historical_query, engine)
worldcup_df = pd.read_sql(worldcup_query, engine)

matches_clean = pd.concat(
    [historical_df, worldcup_df],
    ignore_index=True
)

overwrite_table(

    matches_clean,
    "matches_clean",
    engine,
    schema="staging",
    index=False
)

print(f"{len(matches_clean)} jogos carregados em staging.matches_clean")
print(matches_clean.head())