import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

url = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"

df = pd.read_csv(url)

df["date"] = pd.to_datetime(df["date"])

df = df[
    (df["date"] >= "2018-01-01") &
    (df["date"] <= "2026-12-31")
]

overwrite_table(

    df,
    "historical_matches",
    engine,
    schema="raw",
    index=False
)

print(f"{len(df)} jogos históricos carregados em raw.historical_matches")