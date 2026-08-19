from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    voyage_api_key: str = ""
    voyage_model: str = "voyage-3-lite"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "pleaseletmein"
    neo4j_database: str = "neo4j"
    neo4j_index_name: str = "vector"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    default_top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
