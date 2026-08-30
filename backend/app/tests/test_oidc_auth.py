from types import SimpleNamespace

import pytest

from app.security import auth


class FakeSigningKey:
    key="fake-public-key"


class FakeJWKClient:
    def __init__(self,url):
        self.url=url
    def get_signing_key_from_jwt(self,token):
        assert token=="token-value"
        return FakeSigningKey()


def oidc_settings():
    return SimpleNamespace(
        auth_mode="oidc",
        oidc_jwks_url="https://identity.example/.well-known/jwks.json",
        oidc_audience="railway-bid-intelligence",
        oidc_issuer="https://identity.example/",
        oidc_email_claim="email",
    )


def test_oidc_identity_maps_verified_email_to_active_user(testing_session,monkeypatch):
    monkeypatch.setattr(auth,"get_settings",oidc_settings)
    monkeypatch.setattr(auth,"PyJWKClient",FakeJWKClient)
    monkeypatch.setattr(auth.jwt,"decode",lambda *args,**kwargs:{"email":"admin@test"})
    with testing_session() as db:
        user=auth.current_user(db,None,"Bearer token-value")
        assert user.email=="admin@test"
        assert user.is_active is True


def test_oidc_identity_requires_bearer_token(testing_session,monkeypatch):
    monkeypatch.setattr(auth,"get_settings",oidc_settings)
    with testing_session() as db:
        with pytest.raises(Exception) as exc:
            auth.current_user(db,None,None)
        assert getattr(exc.value,"status_code",None)==401


def test_oidc_identity_rejects_unprovisioned_verified_user(testing_session,monkeypatch):
    monkeypatch.setattr(auth,"get_settings",oidc_settings)
    monkeypatch.setattr(auth,"PyJWKClient",FakeJWKClient)
    monkeypatch.setattr(auth.jwt,"decode",lambda *args,**kwargs:{"email":"unknown@example.com"})
    with testing_session() as db:
        with pytest.raises(Exception) as exc:
            auth.current_user(db,None,"Bearer token-value")
        assert getattr(exc.value,"status_code",None)==403
