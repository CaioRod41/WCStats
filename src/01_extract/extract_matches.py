import requests
import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ===== API =====

url = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

response = requests.get(url, timeout=30)
response.raise_for_status()
data = response.json()

rows = []

for match in data["matches"]:

    score = match.get("score", {})
    ft = score.get("ft", [None, None])

    rows.append({
        "rodada": match.get("round"),
        "data": match.get("date"),
        "hora": match.get("time"),
        "time_casa": match.get("team1"),
        "time_fora": match.get("team2"),
        "gols_casa": ft[0],
        "gols_fora": ft[1],
        "status": "Finalizado" if ft[0] is not None else "Agendado"
    })

df = pd.DataFrame(rows)

print(f"{len(df)} jogos encontrados")

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS raw.worldcup_matches (
            rodada TEXT,
            data TEXT,
            hora TEXT,
            time_casa TEXT,
            time_fora TEXT,
            gols_casa FLOAT,
            gols_fora FLOAT,
            status TEXT
        );
    """))
    conn.execute(text("TRUNCATE TABLE raw.worldcup_matches;"))

df.to_sql(
    "worldcup_matches",
    engine,
    schema="raw",
    if_exists="append",
    index=False
)

print("Tabela raw.worldcup_matches carregada")
