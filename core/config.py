from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:Kkrishna%402005@localhost:5432/financial_agent"
    groq_api_key: str = ""
    voyage_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "voyage-3-lite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
