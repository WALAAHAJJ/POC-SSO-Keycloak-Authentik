
import os

import jwt
import pytest
from jwt import PyJWKClient

ISSUER = "http://localhost:8080/realms/collector-poc"
JWKS_URL = ISSUER + "/protocol/openid-connect/certs"
AUDIENCE = "catalogue-api"


@pytest.fixture
def access_token():
    token = os.environ.get("KEYCLOAK_TEST_TOKEN")

    if not token:
        pytest.skip(
            "Aucun token fourni : définir KEYCLOAK_TEST_TOKEN"
        )

    return token.strip()


def verifier_jwt(token, audience=AUDIENCE):
    jwks = PyJWKClient(JWKS_URL)
    cle = jwks.get_signing_key_from_jwt(token)

    return jwt.decode(
        token,
        cle.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        audience=audience
    )


def test_signature_rs256_et_audience(access_token):
    claims = verifier_jwt(access_token)

    assert claims["iss"] == ISSUER
    assert AUDIENCE in claims["aud"]


def test_role_sales(access_token):
    claims = verifier_jwt(access_token)

    assert "SALES" in claims["realm_access"]["roles"]


def test_rejet_mauvaise_audience(access_token):
    with pytest.raises(jwt.InvalidAudienceError):
        verifier_jwt(access_token, audience="commande-api")


def test_rejet_signature_modifiee(access_token):
    parties = access_token.split(".")
    assert len(parties) == 3

    signature = parties[2]
    assert signature

    # Modifier un caractère de la signature
    caractere = "A" if signature[0] != "A" else "B"
    parties[2] = caractere + signature[1:]

    token_modifie = ".".join(parties)

    with pytest.raises(jwt.InvalidSignatureError):
        verifier_jwt(token_modifie)
