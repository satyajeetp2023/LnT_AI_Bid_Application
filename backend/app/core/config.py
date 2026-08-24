from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://railway:change-me@localhost:5432/railway_bid"
    secret_key: str = "development-only-change-me"
    storage_root: Path = Path("storage")
    max_file_size_mb: int = 50
    max_batch_size_mb: int = 250
    max_files_per_batch: int = 100
    allowed_extensions: frozenset[str] = frozenset({"pdf","doc","docx","xls","xlsx","csv","txt","jpg","jpeg","png","zip","xer","xml"})
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

