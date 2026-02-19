"""Application configuration via Pydantic Settings."""
from pathlib import Path
from pydantic_settings import BaseSettings

# .env is at project root (sns-solution/.env), one level above backend/
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sns_solution"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Meta (Instagram/Facebook)
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""

    # YouTube
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""

    # AI
    AI_PROVIDER: str = "claude"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # S3 / MinIO
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "sns-media"
    S3_REGION: str = "ap-northeast-2"

    # Encryption
    ENCRYPTION_KEY: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # WebSocket
    WS_MAX_CONNECTIONS: int = 1000

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
