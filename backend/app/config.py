from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    secret_key: str
    access_token_minutes: int = 480
    storage_dir: Path = ROOT / "storage"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    gmail_refresh_token: str | None = None
    gmail_poll_seconds: int = 60
    gmail_lookback_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()