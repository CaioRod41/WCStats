import pandas as pd
from sqlalchemy import create_engine, text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

teams = [
    # Grupo A
    ("Mexico", "México", "mx", "MEX", "A"),
    ("South Africa", "África do Sul", "za", "ZAF", "A"),
    ("South Korea", "Coreia do Sul", "kr", "KOR", "A"),
    ("Czech Republic", "República Tcheca", "cz", "CZE", "A"),

    # Grupo B
    ("Canada", "Canadá", "ca", "CAN", "B"),
    ("Bosnia & Herzegovina", "Bósnia e Herzegovina", "ba", "BIH", "B"),
    ("Qatar", "Catar", "qa", "QAT", "B"),
    ("Switzerland", "Suíça", "ch", "CHE", "B"),

    # Grupo C
    ("Brazil", "Brasil", "br", "BRA", "C"),
    ("Morocco", "Marrocos", "ma", "MAR", "C"),
    ("Haiti", "Haiti", "ht", "HTI", "C"),
    ("Scotland", "Escócia", "gb-sct", "SCO", "C"),

    # Grupo D
    ("USA", "Estados Unidos", "us", "USA", "D"),
    ("Paraguay", "Paraguai", "py", "PRY", "D"),
    ("Australia", "Austrália", "au", "AUS", "D"),
    ("Turkey", "Turquia", "tr", "TUR", "D"),

    # Grupo E
    ("Germany", "Alemanha", "de", "DEU", "E"),
    ("Curaçao", "Curaçao", "cw", "CUW", "E"),
    ("Ivory Coast", "Costa do Marfim", "ci", "CIV", "E"),
    ("Ecuador", "Equador", "ec", "ECU", "E"),

    # Grupo F
    ("Netherlands", "Holanda", "nl", "NLD", "F"),
    ("Japan", "Japão", "jp", "JPN", "F"),
    ("Sweden", "Suécia", "se", "SWE", "F"),
    ("Tunisia", "Tunísia", "tn", "TUN", "F"),

    # Grupo G
    ("Belgium", "Bélgica", "be", "BEL", "G"),
    ("Egypt", "Egito", "eg", "EGY", "G"),
    ("Iran", "Irã", "ir", "IRN", "G"),
    ("New Zealand", "Nova Zelândia", "nz", "NZL", "G"),

    # Grupo H
    ("Spain", "Espanha", "es", "ESP", "H"),
    ("Cape Verde", "Cabo Verde", "cv", "CPV", "H"),
    ("Saudi Arabia", "Arábia Saudita", "sa", "SAU", "H"),
    ("Uruguay", "Uruguai", "uy", "URY", "H"),

    # Grupo I
    ("France", "França", "fr", "FRA", "I"),
    ("Senegal", "Senegal", "sn", "SEN", "I"),
    ("Iraq", "Iraque", "iq", "IRQ", "I"),
    ("Norway", "Noruega", "no", "NOR", "I"),

    # Grupo J
    ("Argentina", "Argentina", "ar", "ARG", "J"),
    ("Algeria", "Argélia", "dz", "DZA", "J"),
    ("Austria", "Áustria", "at", "AUT", "J"),
    ("Jordan", "Jordânia", "jo", "JOR", "J"),

    # Grupo K
    ("Portugal", "Portugal", "pt", "PRT", "K"),
    ("DR Congo", "República Democrática do Congo", "cd", "COD", "K"),
    ("Uzbekistan", "Uzbequistão", "uz", "UZB", "K"),
    ("Colombia", "Colômbia", "co", "COL", "K"),

    # Grupo L
    ("England", "Inglaterra", "gb-eng", "ENG", "L"),
    ("Croatia", "Croácia", "hr", "HRV", "L"),
    ("Ghana", "Gana", "gh", "GHA", "L"),
    ("Panama", "Panamá", "pa", "PAN", "L"),
]

df = pd.DataFrame(
    teams,
    columns=["team_name", "team_name_pt", "iso2", "iso3", "group_name"]
)

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS raw.worldcup_teams (
            team_name TEXT PRIMARY KEY,
            team_name_pt TEXT,
            iso2 TEXT,
            iso3 TEXT,
            group_name TEXT
        );
    """))

    conn.execute(text("TRUNCATE TABLE raw.worldcup_teams;"))

df.to_sql(
    "worldcup_teams",
    engine,
    schema="raw",
    if_exists="append",
    index=False
)

print(df.head(48))
print(f"{len(df)} seleções carregadas em raw.worldcup_teams")