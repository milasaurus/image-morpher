from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LUMAAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    LUMA_MODEL: str = "uni-1"
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    CORS_ORIGINS: list[str] = ["http://localhost:8080"]
    # Set once the spike's weight probe confirms the agents API accepts this field.
    IMAGE_REF_WEIGHT: float | None = None


settings = Settings()
