from sqlalchemy import create_engine, text

from config import *


engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

required_tables = [
    ("raw", "historical_matches"),
    ("raw", "worldcup_teams"),
    ("staging", "team_mapping"),
    ("mart", "dim_country"),
    ("mart", "team_ranking"),
    ("mart", "team_country_indicators"),
    ("mart", "team_hdi"),
    ("mart", "team_environment_profile"),
    ("mart", "team_market_value"),
]

query = text(
    """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = :schema_name
      AND table_name = :table_name
    """
)

missing = []

with engine.connect() as conn:
    for schema_name, table_name in required_tables:
        exists = conn.execute(
            query,
            {"schema_name": schema_name, "table_name": table_name},
        ).first()

        if not exists:
            missing.append(f"{schema_name}.{table_name}")

if missing:
    missing_tables = ", ".join(missing)
    raise RuntimeError(
        "Tabelas de referencia ausentes: "
        f"{missing_tables}. Rode a DAG wcstats_reference_pipeline antes da DAG diaria."
    )

print("Tabelas de referencia encontradas.")
