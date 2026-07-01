import pandas as pd
import requests
from io import StringIO
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

headers = {
    "User-Agent": "Mozilla/5.0"
}

name_mapping = {
    "França": "France",
    "Espanha": "Spain",
    "Argentina": "Argentina",
    "Inglaterra": "England",
    "Portugal": "Portugal",
    "Brasil": "Brazil",
    "Holanda": "Netherlands",
    "Marrocos": "Morocco",
    "Bélgica": "Belgium",
    "Alemanha": "Germany",
    "Croácia": "Croatia",
    "Itália": "Italy",
    "Colômbia": "Colombia",
    "Senegal": "Senegal",
    "México": "Mexico",
    "Estados Unidos": "USA",
    "Uruguai": "Uruguay",
    "Japão": "Japan",
    "Suíça": "Switzerland",
    "Dinamarca": "Denmark",
    "Irã": "Iran",
    "Áustria": "Austria",
    "Coreia do Sul": "South Korea",
    "Equador": "Ecuador",
    "Suécia": "Sweden",
    "Austrália": "Australia",
    "Canadá": "Canada",
    "Catar": "Qatar",
    "Noruega": "Norway",
    "Egito": "Egypt",
    "Argélia": "Algeria",
    "Costa do Marfim": "Ivory Coast",
    "Tunísia": "Tunisia",
    "República Checa": "Czech Republic",
    "África do Sul": "South Africa",
    "Paraguai": "Paraguay",
    "Turquia": "Turkey",
    "Escócia": "Scotland",
    "Arábia Saudita": "Saudi Arabia",
    "Bósnia-Herzegovina": "Bosnia & Herzegovina",
    "Nova Zelândia": "New Zealand",
    "Panamá": "Panama",
    "Haiti": "Haiti",
    "Uzbequistão": "Uzbekistan",
    "Cabo Verde": "Cape Verde",
    "Jordânia": "Jordan",
    "Iraque": "Iraq",
    "Curaçao": "Curaçao",
    "RD Congo": "DR Congo",
    "Gana": "Ghana"
}

all_pages = []

for page in range(1, 12):
    url = (
        "https://www.ogol.com.br/rankings/ranking-fifa"
        f"?pais=0&mes_rank=4&ano_rank=2026&page={page}"
    )

    response = requests.get(url, headers=headers)

    print(f"Página {page} - Status {response.status_code}")

    tables = pd.read_html(StringIO(response.text))

    if not tables:
        print("Sem tabelas. Parando.")
        break

    df_page = tables[0]

    if "P" not in df_page.columns or "Equipe" not in df_page.columns or "Pontos" not in df_page.columns:
        print("Tabela sem colunas esperadas. Parando.")
        break

    df_page = df_page[["P", "Equipe", "Pontos"]].copy()
    df_page = df_page.dropna(subset=["P", "Equipe", "Pontos"])

    if df_page.empty:
        print("Página vazia. Parando.")
        break

    all_pages.append(df_page)

df = pd.concat(all_pages, ignore_index=True)

df = df.rename(columns={
    "P": "fifa_rank",
    "Equipe": "team_name_pt",
    "Pontos": "fifa_points"
})

df["fifa_rank"] = df["fifa_rank"].astype(int)
df["fifa_points"] = df["fifa_points"].astype(float)

df["team_name"] = df["team_name_pt"].replace(name_mapping)

df = df.drop_duplicates(subset=["fifa_rank"])

overwrite_table(

    df,
    "team_fifa_ranking",
    engine,
    schema="raw",
    index=False
)

print(df.head(60))
print(f"{len(df)} seleções carregadas em raw.team_fifa_ranking")