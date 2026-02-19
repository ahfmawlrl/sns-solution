"""Configuration tests."""
from app.config import Settings


def test_default_settings():
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret",
    )
    assert s.JWT_ALGORITHM == "HS256"
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert s.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert s.APP_ENV == "development"
    assert s.S3_BUCKET_NAME == "sns-media"


def test_cors_origins_parsing():
    s = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret",
        CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173",
    )
    origins = s.CORS_ALLOWED_ORIGINS.split(",")
    assert len(origins) == 2
    assert "http://localhost:3000" in origins
