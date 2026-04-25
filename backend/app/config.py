from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    ACCESS_TOKEN: str
    VK_API_URL_GET: str = "https://api.vk.com/method/wall.get"
    VK_API_URL_POST: str = "https://api.vk.com/method/wall.post"
    VK_API_VERSION: str = "5.199"
    GROUP_ID: int

    GOOGLE_SHEET_ID: str
    GOOGLE_SHEET_GID: int = 0
    GOOGLE_WORKSHEET_NAME: str = "0"
    GOOGLE_CREDENTIALS_PATH: Path = Field(default=Path("service_account.json"))

    EVENTS_OUTPUT_FILE: Path = Field(default=Path("events.csv"))

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    @property
    def DATABASE_URL(self) -> str:
        """Async URL для SQLAlchemy + asyncpg."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync URL — пригодится для Alembic / psycopg."""
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def OWNER_ID(self) -> int:
        """owner_id для VK API — для сообществ это -GROUP_ID."""
        return -self.GROUP_ID

    @property
    def google_credentials_abs(self) -> Path:
        """Абсолютный путь к JSON-ключу сервисного аккаунта Google."""
        path = self.GOOGLE_CREDENTIALS_PATH
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def events_output_abs(self) -> Path:
        """Абсолютный путь к CSV с выгрузкой событий."""
        path = self.EVENTS_OUTPUT_FILE
        return path if path.is_absolute() else PROJECT_ROOT / path


settings = Settings()
