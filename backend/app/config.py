from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/lenny_growth_assistant"
    )

    llm_provider: str = "ollama"

    ollama_base_url: str = "http://ollama:11434"
    ollama_chat_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    anthropic_model: str = "claude-3-5-sonnet-latest"
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # RAG
    transcripts_dir: str = "data/raw/lenny_transcripts"
    ingest_limit: int = 0
    chunk_size: int = 1200
    chunk_overlap: int = 150
    top_k: int = 6
    relevance_threshold: float = 0.45

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
