import pandas as pd
from sqlalchemy import create_engine

from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

query = """
SELECT *
FROM raw.worldcup_matches
WHERE status = 'Finalizado'
"""

df = pd.read_sql(query, engine)

stats = {}

for _, row in df.iterrows():

    casa = row["time_casa"]
    fora = row["time_fora"]

    gols_casa = row["gols_casa"]
    gols_fora = row["gols_fora"]

    for time in [casa, fora]:

        if time not in stats:
            stats[time] = {
                "selecao": time,
                "jogos": 0,
                "vitorias": 0,
                "empates": 0,
                "derrotas": 0,
                "gols_pro": 0,
                "gols_contra": 0,
                "pontos": 0
            }

    # CASA

    stats[casa]["jogos"] += 1
    stats[casa]["gols_pro"] += gols_casa
    stats[casa]["gols_contra"] += gols_fora

    # FORA

    stats[fora]["jogos"] += 1
    stats[fora]["gols_pro"] += gols_fora
    stats[fora]["gols_contra"] += gols_casa

    if gols_casa > gols_fora:

        stats[casa]["vitorias"] += 1
        stats[casa]["pontos"] += 3

        stats[fora]["derrotas"] += 1

    elif gols_casa < gols_fora:

        stats[fora]["vitorias"] += 1
        stats[fora]["pontos"] += 3

        stats[casa]["derrotas"] += 1

    else:

        stats[casa]["empates"] += 1
        stats[fora]["empates"] += 1

        stats[casa]["pontos"] += 1
        stats[fora]["pontos"] += 1

team_stats = pd.DataFrame(stats.values())

team_stats["saldo"] = (
    team_stats["gols_pro"] -
    team_stats["gols_contra"]
)

team_stats = team_stats.sort_values(
    ["pontos", "saldo"],
    ascending=False
)

overwrite_table(

    team_stats,
    "team_stats",
    engine,
    schema="mart",
    index=False
)

print(team_stats.head())
print("Tabela mart.team_stats criada.")
