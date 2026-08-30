from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://railway:change-me@localhost:5432/railway_bid"
    environment: str = "development"
    secret_key: str = "development-only-change-me"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    auth_mode: str = "development_header"
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_email_claim: str = "email"
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
        if self.environment.strip().lower()=="production":
            if self.secret_key=="development-only-change-me" or len(self.secret_key)<32:
                raise ValueError("Production SECRET_KEY must be explicitly configured and at least 32 characters")
            if "change-me" in self.database_url.lower():
                raise ValueError("Production DATABASE_URL cannot use placeholder credentials")
            origins=self.cors_origin_list
            if not origins or "*" in origins:
                raise ValueError("Production CORS_ORIGINS must explicitly list approved origins")
            if any("localhost" in x.lower() or "127.0.0.1" in x for x in origins):
                raise ValueError("Production CORS_ORIGINS cannot use localhost origins")
            if self.auth_mode!="oidc":
                raise ValueError("Production AUTH_MODE must be oidc")
            if not self.oidc_issuer or not self.oidc_audience or not self.oidc_jwks_url:
                raise ValueError("Production OIDC_ISSUER, OIDC_AUDIENCE and OIDC_JWKS_URL are required")
            if not self.oidc_jwks_url.lower().startswith("https://"):
                raise ValueError("Production OIDC_JWKS_URL must use HTTPS")
            if self.max_file_size_mb>200 or self.max_batch_size_mb>1000:
                raise ValueError("Production upload limits exceed the approved safety ceiling")
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()

