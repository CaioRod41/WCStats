import requests
import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

countries = pd.read_sql(
    "SELECT DISTINCT iso3 FROM mart.dim_country WHERE iso3 IS NOT NULL",
    engine
)

iso3_list = countries["iso3"].tolist()
country_param = ";".join(iso3_list)

indicators = {
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "NY.GDP.PCAP.CD": "gdp_per_capita_current_usd",
    "SP.POP.TOTL": "population_total",
    "SP.DYN.LE00.IN": "life_expectancy"
}

rows = []

for indicator_code, indicator_name in indicators.items():
    url = (
        f"https://api.worldbank.org/v2/country/{country_param}"
        f"/indicator/{indicator_code}?format=json&per_page=20000"
    )

    response = requests.get(url)
    data = response.json()

    if len(data) < 2:
        print(f"Sem dados para {indicator_code}")
        continue

    for item in data[1]:
        rows.append({
            "iso3": item.get("countryiso3code"),
            "country_name_api": item.get("country", {}).get("value"),
            "indicator_code": indicator_code,
            "indicator_name": indicator_name,
            "year": item.get("date"),
            "value": item.get("value")
        })

df = pd.DataFrame(rows)

df = df[df["value"].notna()]

overwrite_table(

    df,
    "country_indicators",
    engine,
    schema="raw",
    index=False
)

print(f"{len(df)} registros carregados em raw.country_indicators")
print(df.head())
