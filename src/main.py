import requests
import pandas as pd

url = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

response = requests.get(url)

print("Status:", response.status_code)

if response.status_code != 200:
    print("Erro ao buscar dados.")
    exit()

data = response.json()

rows = []

for match in data.get("matches", []):
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

print(df.head())
print("Total de jogos:", len(df))

df.to_csv("data/jogos.csv", index=False, encoding="utf-8-sig")

print("Arquivo data/jogos.csv criado com sucesso!")