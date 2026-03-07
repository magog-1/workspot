from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # База данных
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/workspot"

    # JWT
    secret_key: str = "change-me-in-production-min-32-chars!!"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Администратор
    admin_email: str = "admin@workspot.ru"
    admin_password: str = "adminpass123"

    # Яндекс Карты
    yandex_maps_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
