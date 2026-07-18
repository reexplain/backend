from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    reexplain_allowed_origins: str = "http://localhost:3000"
    reexplain_allowed_hosts: str = "localhost,127.0.0.1,testserver"
    reexplain_api_service_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    reexplain_question_model: str = "gpt-5.4"
    reexplain_embedding_model: str = "text-embedding-3-small"

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.reexplain_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.reexplain_allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()