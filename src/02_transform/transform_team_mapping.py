import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

historical_query = """
SELECT DISTINCT home_team AS team_name
FROM raw.historical_matches

UNION

SELECT DISTINCT away_team AS team_name
FROM raw.historical_matches
"""

worldcup_query = """
SELECT DISTINCT time_casa AS team_name
FROM raw.worldcup_matches

UNION

SELECT DISTINCT time_fora AS team_name
FROM raw.worldcup_matches
"""

historical_teams = pd.read_sql(historical_query, engine)
worldcup_teams = pd.read_sql(worldcup_query, engine)

all_teams = pd.concat(
    [historical_teams, worldcup_teams],
    ignore_index=True
).drop_duplicates()

all_teams["canonical_name"] = all_teams["team_name"]

manual_mapping = {
    "USA": "United States",
    "United States": "United States",
    "South Korea": "South Korea",
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Czech Republic": "Czechia",
    "Czechia": "Czechia",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Türkiye": "Turkey",
    "Turkey": "Turkey"
}

all_teams["canonical_name"] = all_teams["team_name"].replace(manual_mapping)

all_teams = all_teams.sort_values("canonical_name")

overwrite_table(
    all_teams,
    "team_mapping",
    engine,
    schema="staging",
    index=False
)

print(all_teams.head(30))
print(f"{len(all_teams)} seleções carregadas em staging.team_mapping")
