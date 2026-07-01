from sqlalchemy import inspect, text

from config import create_engine, database_url


engine = create_engine(database_url())

REQUIRED_TABLES = [
    ("staging", "matches_clean"),
    ("mart", "team_strength_score"),
    ("mart", "team_goal_profile"),
]


def table_row_count(schema, table_name):
    with engine.connect() as conn:
        return conn.execute(
            text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"')
        ).scalar()


def main():
    inspector = inspect(engine)
    missing = []
    empty = []

    for schema, table_name in REQUIRED_TABLES:
        if not inspector.has_table(table_name, schema=schema):
            missing.append(f"{schema}.{table_name}")
            continue

        if table_row_count(schema, table_name) == 0:
            empty.append(f"{schema}.{table_name}")

    if missing or empty:
        message_parts = []

        if missing:
            message_parts.append(f"tabelas ausentes: {', '.join(missing)}")

        if empty:
            message_parts.append(f"tabelas vazias: {', '.join(empty)}")

        raise RuntimeError(
            "Dependencias dos experimentos invalidas. "
            + "; ".join(message_parts)
            + ". Rode primeiro wcstats_reference_pipeline e wcstats_pipeline."
        )

    print("Dependencias dos experimentos validadas.")


if __name__ == "__main__":
    main()
