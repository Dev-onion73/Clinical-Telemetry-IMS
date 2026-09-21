from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Testing Backend"
    app_version: str = "0.1.0"

    host: str = "127.0.0.1"
    port: int = 8010

    model_config = SettingsConfigDict(
        env_prefix="TESTING_BACKEND_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()