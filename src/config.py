import os
import platform
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        if not path.exists():
            return

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

if DB_HOST == "host.docker.internal" and platform.system() == "Windows":
    DB_HOST = "localhost"

os.environ.setdefault("PGCLIENTENCODING", "UTF8")


def database_url():
    from sqlalchemy.engine import URL

    return URL.create(
        "postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT) if DB_PORT else None,
        database=DB_NAME,
    )


def create_engine(*args, **kwargs):
    from sqlalchemy import create_engine as sqlalchemy_create_engine
    from sqlalchemy import text

    if args and isinstance(args[0], str) and args[0].startswith("postgresql+psycopg2://"):
        args = (database_url(), *args[1:])

    connect_args = dict(kwargs.get("connect_args", {}))
    connect_args.setdefault("options", "-c client_encoding=utf8")
    kwargs["connect_args"] = connect_args

    engine = sqlalchemy_create_engine(*args, **kwargs)

    if engine.url.get_backend_name() == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS mart;"))

    return engine


def overwrite_table(df, table_name, engine, schema=None, index=False):
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    table_exists = inspector.has_table(table_name, schema=schema)

    if table_exists:
        qualified_name = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'

        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {qualified_name};"))

        df.to_sql(
            table_name,
            engine,
            schema=schema,
            if_exists="append",
            index=index,
        )
        return

    df.to_sql(
        table_name,
        engine,
        schema=schema,
        if_exists="replace",
        index=index,
    )
