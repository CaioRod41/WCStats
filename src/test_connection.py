from sqlalchemy import create_engine
from sqlalchemy import text
from config import *

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


with engine.connect() as conn:
    result = conn.execute(text("SELECT current_user, current_database();"))

    for row in result:
        print(row)

print("Conexão com PostgreSQL feita com sucesso!")
