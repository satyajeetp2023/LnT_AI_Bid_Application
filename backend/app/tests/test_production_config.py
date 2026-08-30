import pytest
from pydantic import ValidationError

from app.core.config import Settings


BASE={
    "environment":"production",
    "secret_key":"0123456789abcdef0123456789abcdef",
    "database_url":"postgresql+psycopg://railway:strong-password@db:5432/railway_bid",
    "cors_origins":"https://bid.example.internal",
    "auth_mode":"oidc",
    "oidc_issuer":"https://identity.example/",
    "oidc_audience":"railway-bid-intelligence",
    "oidc_jwks_url":"https://identity.example/.well-known/jwks.json",
}


def settings(**changes):
    values={**BASE,**changes}
    return Settings(_env_file=None,**values)


def test_valid_production_security_configuration_is_accepted():
    result=settings()
    assert result.environment=="production"
    assert result.auth_mode=="oidc"


@pytest.mark.parametrize("changes",[
    {"secret_key":"short"},
    {"database_url":"postgresql+psycopg://railway:change-me@db:5432/railway_bid"},
    {"cors_origins":"*"},
    {"cors_origins":"http://localhost:3000"},
    {"auth_mode":"development_header"},
    {"oidc_jwks_url":"http://identity.example/jwks"},
])
def test_unsafe_production_configuration_is_rejected(changes):
    with pytest.raises(ValidationError):
        settings(**changes)
