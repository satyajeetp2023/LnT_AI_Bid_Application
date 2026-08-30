import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_development_secret():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="development-only-change-me",
            database_url="postgresql+psycopg://railway:strong-password@db:5432/railway_bid",
            cors_origins="https://bid.example.com",
            auth_mode="oidc",
            oidc_issuer="https://identity.example/",
            oidc_audience="railway-bid-intelligence",
            oidc_jwks_url="https://identity.example/.well-known/jwks.json",
        )


def test_explicit_production_security_configuration_is_accepted():
    settings=Settings(
        _env_file=None,
        environment="production",
        secret_key="0123456789abcdef0123456789abcdef",
        database_url="postgresql+psycopg://railway:strong-password@db:5432/railway_bid",
        cors_origins="https://bid.example.com, https://review.example.com",
        auth_mode="oidc",
        oidc_issuer="https://identity.example/",
        oidc_audience="railway-bid-intelligence",
        oidc_jwks_url="https://identity.example/.well-known/jwks.json",
    )
    assert settings.cors_origin_list==["https://bid.example.com","https://review.example.com"]
    assert settings.auth_mode=="oidc"


def test_development_identity_mode_still_requires_explicit_header(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.security import auth

    monkeypatch.setattr(auth,"get_settings",lambda:SimpleNamespace(auth_mode="development_header"))
    with pytest.raises(HTTPException) as exc:
        auth.current_user(None,None)
    assert exc.value.status_code==401


def test_oidc_mode_does_not_accept_development_identity_header(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.security import auth

    monkeypatch.setattr(auth,"get_settings",lambda:SimpleNamespace(
        auth_mode="oidc",
        oidc_jwks_url="https://identity.example/.well-known/jwks.json",
        oidc_audience="railway-bid-intelligence",
        oidc_issuer="https://identity.example/",
        oidc_email_claim="email",
    ))
    with pytest.raises(HTTPException) as exc:
        auth.current_user(None,1,None)
    assert exc.value.status_code==401
    assert "Bearer token" in exc.value.detail
