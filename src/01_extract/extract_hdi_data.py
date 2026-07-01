import requests
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

url = "https://ourworldindata.org/grapher/human-development-index.csv"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

print("Status:", response.status_code)

if response.status_code != 200:
    print(response.text[:500])
    exit()

df = pd.read_csv(StringIO(response.text))

print(df.columns)

df = df.rename(columns={
    "Entity": "country_name_api",
    "Code": "iso3",
    "Year": "year",
    "Human Development Index": "hdi"
})

df = df[df["iso3"].notna()]
df = df[df["hdi"].notna()]

overwrite_table(

    df,
    "hdi_indicators",
    engine,
    schema="raw",
    index=False
)

print(f"{len(df)} registros carregados em raw.hdi_indicators")
print(df.head())