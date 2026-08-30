import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_development_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production",secret_key="development-only-change-me")


def test_explicit_production_secret_and_cors_are_accepted():
    settings=Settings(
        environment="production",
        secret_key="a-secure-production-secret",
        cors_origins="https://bid.example.com, https://review.example.com",
    )
    assert settings.cors_origin_list==["https://bid.example.com","https://review.example.com"]


def test_production_blocks_development_identity(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.security import auth

    monkeypatch.setattr(auth,"get_settings",lambda:SimpleNamespace(environment="production"))
    with pytest.raises(HTTPException) as exc:
        auth.current_user(None,1)
    assert exc.value.status_code==503
    assert "enterprise identity provider" in exc.value.detail.lower()
