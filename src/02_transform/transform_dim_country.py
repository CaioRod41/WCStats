import pandas as pd
import pycountry
from sqlalchemy import create_engine

from config import *


engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT DISTINCT team_name AS country_name
FROM raw.worldcup_teams
WHERE team_name IS NOT NULL
ORDER BY team_name
"""

df = pd.read_sql(query, engine)

manual_iso3 = {
    "England": "GBR",
    "Scotland": "GBR",
    "Wales": "GBR",
    "Northern Ireland": "GBR",
    "Ivory Coast": "CIV",
    "DR Congo": "COD",
    "South Korea": "KOR",
    "Czechia": "CZE",
    "Czech Republic": "CZE",
    "USA": "USA",
    "United States": "USA",
    "Iran": "IRN",
    "Cape Verde": "CPV",
    "Curacao": "CUW",
    "Curaçao": "CUW",
    "Turkey": "TUR",
    "Bosnia & Herzegovina": "BIH",
}


def get_iso3(country_name):
    if country_name in manual_iso3:
        return manual_iso3[country_name]

    try:
        return pycountry.countries.lookup(country_name).alpha_3
    except LookupError:
        return None


df["iso3"] = df["country_name"].apply(get_iso3)
df["is_world_cup_team"] = True

overwrite_table(

    df,
    "dim_country",
    engine,
    schema="mart",
    index=False,
)

print(df.head(50))
print(f"{len(df)} paises carregados em mart.dim_country")
print("Sem ISO3:")
print(df[df["iso3"].isna()])
