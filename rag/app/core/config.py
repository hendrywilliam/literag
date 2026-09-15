from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    voyage_api_key: str = ""
    voyage_model: str = "voyage-4"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    redis_url: str = "redis://localhost:6379/0"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "pleaseletmein"
    neo4j_database: str = "neo4j"
    neo4j_index_name: str = "vector"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    default_top_k: int = 4
    min_score: float = 0.65

    relation_enabled: bool = True
    relation_candidates: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
