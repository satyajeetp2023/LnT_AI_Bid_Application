from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://railway:change-me@localhost:5432/railway_bid"
    environment: str = "development"
    secret_key: str = "development-only-change-me"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    storage_root: Path = Path("storage")
    max_file_size_mb: int = 50
    max_batch_size_mb: int = 250
    max_files_per_batch: int = 100
    allowed_extensions: frozenset[str] = frozenset({"pdf","doc","docx","xls","xlsx","csv","txt","jpg","jpeg","png","zip","xer","xml","mpp"})
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment.strip().lower()=="production" and self.secret_key=="development-only-change-me":
            raise ValueError("Production SECRET_KEY must be explicitly configured")
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()

