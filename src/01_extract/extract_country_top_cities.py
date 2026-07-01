import zipfile
from io import BytesIO

import pandas as pd
import requests
from sqlalchemy import create_engine
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

countries = pd.read_sql(
    """
    SELECT DISTINCT iso3
    FROM mart.dim_country
    WHERE iso3 IS NOT NULL
    """,
    engine
)

iso3_list = countries["iso3"].dropna().unique().tolist()

url = "https://download.geonames.org/export/dump/cities15000.zip"

response = requests.get(url)
response.raise_for_status()

zip_file = zipfile.ZipFile(BytesIO(response.content))

with zip_file.open("cities15000.txt") as file:
    df = pd.read_csv(
        file,
        sep="\t",
        header=None,
        low_memory=False,
        names=[
            "geonameid",
            "name",
            "asciiname",
            "alternatenames",
            "latitude",
            "longitude",
            "feature_class",
            "feature_code",
            "country_code",
            "cc2",
            "admin1_code",
            "admin2_code",
            "admin3_code",
            "admin4_code",
            "population",
            "elevation",
            "dem",
            "timezone",
            "modification_date"
        ]
    )

# GeoNames usa ISO2, então vamos converter ISO3 -> ISO2 com pycountry
import pycountry

iso3_to_iso2 = {}

for iso3 in iso3_list:
    try:
        country = pycountry.countries.get(alpha_3=iso3)
        if country:
            iso3_to_iso2[iso3] = country.alpha_2
    except Exception:
        pass

iso2_to_iso3 = {v: k for k, v in iso3_to_iso2.items()}

df = df[df["country_code"].isin(iso2_to_iso3.keys())]

df["iso3"] = df["country_code"].map(iso2_to_iso3)

df = df[
    [
        "iso3",
        "name",
        "asciiname",
        "country_code",
        "latitude",
        "longitude",
        "population"
    ]
].copy()

df = df.sort_values(
    ["iso3", "population"],
    ascending=[True, False]
)

df["city_rank"] = df.groupby("iso3").cumcount() + 1

df = df[df["city_rank"] <= 10]

df = df.rename(columns={
    "name": "city_name",
    "asciiname": "city_ascii_name"
})

overwrite_table(

    df,
    "country_top_cities",
    engine,
    schema="raw",
    index=False
)

print(df.head(50))
print(f"{len(df)} cidades carregadas em raw.country_top_cities")
