from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Texora"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://texora_user:texora_pass@localhost:5432/texora_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://texora_user:texora_pass@localhost:5432/texora_db"

    # --- AI Gateway ---
    ARVANCLOUD_API_KEY: str = ""
    AI_GATEWAY_BASE_URL: str = ""
    AI_MODEL_NAME: str = "Gemini-2.5-Flash"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2
    AI_RATE_LIMIT_PER_MINUTE: int = 60

    # --- File Upload ---
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/webp"
    ALLOWED_FILE_TYPES: str = "application/pdf,text/plain,application/zip"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:8000"

    # --- Moderation ---
    MODERATION_ENABLED: bool = True
    MODERATION_MIN_LENGTH: int = 5
    MODERATION_BATCH_SIZE: int = 10

    # --- Properties ---
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_image_types_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_IMAGE_TYPES.split(",") if t.strip()]

    @property
    def allowed_file_types_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_FILE_TYPES.split(",") if t.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()