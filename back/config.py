import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> None:
        return None


load_dotenv()


class Config:
    ENV = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).strip().lower()
    DATABASE_URL = os.environ.get("DATABASE_URL")
    API_KEY = os.environ.get("API_KEY", "demo-api-key")
    SECRET_KEY = os.environ.get("SECRET_KEY", "demo-secret-key")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///revenda_argamassa.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 64 * 1024

    @classmethod
    def validate(cls) -> None:
        if cls.ENV == "production" and (not cls.DATABASE_URL or not cls.SECRET_KEY or not cls.API_KEY):
            raise RuntimeError("DATABASE_URL, SECRET_KEY e API_KEY são obrigatórios em produção.")
