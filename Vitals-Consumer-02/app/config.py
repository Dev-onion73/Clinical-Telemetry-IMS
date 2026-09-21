from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vitals Consumer"
    app_version: str = "0.1.0"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_vitals_topic: str = "clinical.vitals"
    kafka_group_id: str = "vitals-consumer"

    influx_url: str = "http://localhost:8086"
    influx_token: str = "clinical-token"
    influx_org: str = "clinical"
    influx_bucket: str = "vitals"

    model_config = SettingsConfigDict(
        env_prefix="VITALS_CONSUMER_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()