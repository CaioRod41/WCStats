import requests
import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

cities = pd.read_sql(
    "SELECT city, country, latitude, longitude FROM raw.host_cities",
    engine
)

rows = []

for _, city in cities.iterrows():
    latitude = float(city["latitude"])
    longitude = float(city["longitude"])

    print(f"Buscando dados de {city['city']}...")

    # Clima médio de junho e julho, período da Copa
    weather_url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&start_date=2023-06-01"
        "&end_date=2023-07-31"
        "&daily=temperature_2m_mean,relative_humidity_2m_mean"
        "&timezone=auto"
    )

    weather_response = requests.get(weather_url)
    weather_data = weather_response.json()

    # Altitude
    elevation_url = (
        "https://api.open-meteo.com/v1/elevation"
        f"?latitude={latitude}&longitude={longitude}"
    )

    elevation_response = requests.get(elevation_url)
    elevation_data = elevation_response.json()

    daily = weather_data.get("daily", {})

    avg_temperature = None
    avg_humidity = None

    if daily:
        temperature_values = daily.get("temperature_2m_mean", [])
        humidity_values = daily.get("relative_humidity_2m_mean", [])

        avg_temperature = pd.Series(temperature_values).dropna().mean()
        avg_humidity = pd.Series(humidity_values).dropna().mean()

    elevation = None

    if "elevation" in elevation_data and elevation_data["elevation"]:
        elevation = elevation_data["elevation"][0]

    rows.append({
        "city": city["city"],
        "country": city["country"],
        "latitude": latitude,
        "longitude": longitude,
        "avg_temperature_jun_jul": avg_temperature,
        "avg_humidity_jun_jul": avg_humidity,
        "elevation_meters": elevation
    })

df = pd.DataFrame(rows)

overwrite_table(

    df,
    "host_city_environment",
    engine,
    schema="raw",
    index=False
)

print(df)
print("Tabela raw.host_city_environment criada com sucesso.")