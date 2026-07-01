import time
import requests
import pandas as pd
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

cities = pd.read_sql(
    """
    SELECT
        iso3,
        city_name,
        city_ascii_name,
        latitude,
        longitude,
        population,
        city_rank
    FROM raw.country_top_cities
    ORDER BY iso3, city_rank
    """,
    engine
)

rows = []

for index, city in cities.iterrows():
    latitude = float(city["latitude"])
    longitude = float(city["longitude"])

    print(f"{index + 1}/{len(cities)} - {city['iso3']} - {city['city_name']}")

    weather_url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&start_date=2023-01-01"
        "&end_date=2023-12-31"
        "&daily=temperature_2m_mean,relative_humidity_2m_mean"
        "&timezone=auto"
    )

    elevation_url = (
        "https://api.open-meteo.com/v1/elevation"
        f"?latitude={latitude}&longitude={longitude}"
    )

    weather_response = requests.get(weather_url)
    elevation_response = requests.get(elevation_url)

    weather_data = weather_response.json()
    elevation_data = elevation_response.json()

    daily = weather_data.get("daily", {})

    avg_temperature = None
    avg_humidity = None

    if daily:
        avg_temperature = pd.Series(
            daily.get("temperature_2m_mean", [])
        ).dropna().mean()

        avg_humidity = pd.Series(
            daily.get("relative_humidity_2m_mean", [])
        ).dropna().mean()

    elevation = None

    if elevation_data.get("elevation"):
        elevation = elevation_data["elevation"][0]

    rows.append({
        "iso3": city["iso3"],
        "city_name": city["city_name"],
        "city_ascii_name": city["city_ascii_name"],
        "city_rank": city["city_rank"],
        "population": city["population"],
        "latitude": latitude,
        "longitude": longitude,
        "avg_temperature_annual": avg_temperature,
        "avg_humidity_annual": avg_humidity,
        "elevation_meters": elevation
    })

    time.sleep(0.2)

df = pd.DataFrame(rows)

overwrite_table(

    df,
    "country_city_environment",
    engine,
    schema="raw",
    index=False
)

print(f"{len(df)} cidades carregadas em raw.country_city_environment")
print(df.head())