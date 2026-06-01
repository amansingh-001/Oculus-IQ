from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/shipments.db"
    open_meteo_base: str = "https://api.open-meteo.com/v1"
    nominatim_base: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "OculusIQ/0.1 (local demo)"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
