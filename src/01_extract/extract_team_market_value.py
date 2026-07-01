import re
import pandas as pd
import requests
from io import StringIO
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

def money_to_eur(value):
    if pd.isna(value):
        return None

    value = str(value).replace("€", "").strip()

    number = re.findall(r"[\d.]+", value)

    if not number:
        return None

    number = float(number[0])

    if "bn" in value:
        return number * 1_000_000_000

    if "m" in value:
        return number * 1_000_000

    if "k" in value:
        return number * 1_000

    return number

url = "https://www.transfermarkt.com/world-cup/teilnehmer/pokalwettbewerb/FIWC"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

print("Status:", response.status_code)

tables = pd.read_html(StringIO(response.text))

df = tables[1].copy()

df = df.rename(columns={
    "Club": "team_name",
    "Club.1": "players_count",
    "Squad": "avg_age",
    "Market Value": "market_value_text",
    "&oslash-Market Value": "avg_market_value_text"
})

df["market_value_eur"] = df["market_value_text"].apply(money_to_eur)
df["avg_market_value_eur"] = df["market_value_eur"] / df["players_count"]

df = df[
    [
        "team_name",
        "players_count",
        "avg_age",
        "market_value_text",
        "avg_market_value_text",
        "market_value_eur",
        "avg_market_value_eur"
    ]
]

overwrite_table(

    df,
    "team_market_value",
    engine,
    schema="raw",
    index=False
)

print(df.head(20))
print(f"{len(df)} seleções carregadas em raw.team_market_value")