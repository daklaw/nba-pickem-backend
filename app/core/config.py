from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings and configuration.
    Values can be overridden by environment variables.
    """
    # Database Settings
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/nba_pickem"

    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application Settings
    APP_NAME: str = "NBA Pick'em API"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()