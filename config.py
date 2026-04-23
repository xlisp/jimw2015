import os


class Config:
    SECRET_KEY = os.environ.get("JIMW_SECRET", "jimw-black-berry-tunnel-dev")

    DB_USER = "postgres"
    DB_PASSWORD = "123456"
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "jimw"

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
