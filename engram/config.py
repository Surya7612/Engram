from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # local = file-backed graph + embedded Qdrant (no Docker)
    # docker = Neo4j + Qdrant containers
    store: str = Field(default="local", validation_alias="ENGRAM_STORE")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "engramdev"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "engram_artifacts"

    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    langchain_tracing_v2: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING"),
    )
    langchain_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"),
    )
    langchain_project: str = Field(
        default="engram-v1",
        validation_alias=AliasChoices("LANGCHAIN_PROJECT", "LANGSMITH_PROJECT"),
    )

    github_token: str | None = None

    data_dir: Path = _ROOT / "data" / "sample"
    local_data_dir: Path = _ROOT / ".engram"

    # Hosted Try: tight public scope — not multi-tenant SaaS.
    public_mode: bool = Field(default=False, validation_alias="ENGRAM_PUBLIC_MODE")
    seed_on_boot: bool = Field(default=False, validation_alias="ENGRAM_SEED_ON_BOOT")
    cors_origins: str = Field(
        default="http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="ENGRAM_CORS_ORIGINS",
    )
    public_ingest_limit: int = Field(default=30, validation_alias="ENGRAM_PUBLIC_INGEST_LIMIT")

    @field_validator("public_ingest_limit")
    @classmethod
    def _cap_public_limit(cls, value: int) -> int:
        return max(1, min(int(value), 50))

    def cors_origin_list(self) -> list[str]:
        origins = [part.strip() for part in self.cors_origins.split(",") if part.strip()]
        for origin in (
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "null",
        ):
            if origin not in origins:
                origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
