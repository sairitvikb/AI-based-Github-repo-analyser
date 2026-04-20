from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CodeLens AI API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./codelens.db"
    chroma_persist_directory: str = "./chroma_db"

    github_api_base_url: str = "https://api.github.com"
    github_token: str = ""

    # LLM Provider
    llm_provider: str = "groq"

    # OpenAI (optional fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    # Embeddings / analysis
    embedding_model: str = "text-embedding-3-small"
    max_file_bytes: int = 150000
    max_files_to_analyze: int = 150
    chunk_size: int = 1200
    chunk_overlap: int = 200

    log_level: str = "INFO"

    cors_origins: list[str] = [
    "http://localhost:5173",
    "https://codelens-frontend.onrender.com",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
