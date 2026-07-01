import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
WITH ranking_mapped AS (
    SELECT
        CASE
            WHEN LOWER(TRIM(team_name)) IN (
                'united states',
                'estados unidos',
                'usa'
            ) THEN 'USA'

            WHEN LOWER(TRIM(team_name)) IN (
                'czechia',
                'czech republic',
                'república checa',
                'republica checa',
                'rep. checa'
            ) THEN 'Czech Republic'

            WHEN LOWER(TRIM(team_name)) IN (
                'bosnia and herzegovina',
                'bosnia-herzegovina',
                'bósnia-herzegovina',
                'bosnia & herzegovina',
                'bósnia e herzegovina',
                'bosnia e herzegovina'
            ) THEN 'Bosnia & Herzegovina'

            WHEN LOWER(TRIM(team_name)) IN (
                'côte d''ivoire',
                'cote d''ivoire',
                'costa do marfim',
                'ivory coast'
            ) THEN 'Ivory Coast'

            WHEN LOWER(TRIM(team_name)) IN (
                'dr congo',
                'rd congo',
                'congo dr',
                'república democrática do congo',
                'republica democratica do congo',
                'rep. dem. do congo',
                'democratic republic of the congo'
            ) THEN 'DR Congo'

            WHEN LOWER(TRIM(team_name)) IN (
    'czechia',
    'czech republic',
    'república checa',
    'republica checa',
    'rep. checa',
    'tchéquia',
    'tchequia'
) THEN 'Czech Republic'

WHEN LOWER(TRIM(team_name)) IN (
    'bosnia and herzegovina',
    'bosnia-herzegovina',
    'bósnia-herzegovina',
    'bosnia & herzegovina',
    'bósnia e herzegovina',
    'bosnia e herzegovina',
    'bósnia-herzgovina',
    'bosnia-herzgovina'
) THEN 'Bosnia & Herzegovina'

            WHEN LOWER(TRIM(team_name)) IN (
                'türkiye',
                'turkiye',
                'turquia',
                'turkey'
            ) THEN 'Turkey'

            ELSE TRIM(team_name)
        END AS team_name,
        fifa_rank,
        fifa_points
    FROM raw.team_fifa_ranking
)

SELECT
    dc.country_name AS team_name,
    dc.iso3,
    rm.fifa_rank,
    rm.fifa_points
FROM mart.dim_country dc
LEFT JOIN ranking_mapped rm
    ON dc.country_name = rm.team_name
ORDER BY rm.fifa_rank
"""

df = pd.read_sql(query, engine)

overwrite_table(

    df,
    "team_ranking",
    engine,
    schema="mart",
    index=False
)

print(df)
print(f"{len(df)} seleções carregadas em mart.team_ranking")
print("Sem ranking:")
print(df[df["fifa_rank"].isna()])