
import os
import time

import jwt
import pytest
import requests

# ==========================================
# Configuration Authentik
# ==========================================

ISSUER = "http://localhost:9000/application/o/catalogue-poc/"
CONFIG_URL = ISSUER + ".well-known/openid-configuration"
AUDIENCE = "catalogue-client"

# ID Token récupéré depuis Postman et chargé localement
TOKEN = os.getenv("AUTHENTIK_TEST_TOKEN")


# ==========================================
# 1. Vérification de la configuration OIDC
# ==========================================

@pytest.fixture(scope="module")
def oidc_config():
    response = requests.get(CONFIG_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def test_configuration_oidc(oidc_config):
    assert oidc_config["issuer"] == ISSUER
    assert "authorization_endpoint" in oidc_config
    assert "token_endpoint" in oidc_config
    assert "jwks_uri" in oidc_config


# ==========================================
# 2. Vérification de RS256
# ==========================================

def test_signature_rs256_disponible(oidc_config):
    assert "RS256" in oidc_config["id_token_signing_alg_values_supported"]


# ==========================================
# 3. Vérification des clés JWKS
# ==========================================

def test_cles_publiques_jwks(oidc_config):
    response = requests.get(oidc_config["jwks_uri"], timeout=10)
    response.raise_for_status()

    keys = response.json()["keys"]

    assert len(keys) > 0
    assert any(key["kty"] == "RSA" for key in keys)


# ==========================================
# Fonction de validation des JWT Authentik
# ==========================================

def verifier_jwt(token, audience=AUDIENCE):
    jwks_client = jwt.PyJWKClient(
        ISSUER + "jwks/"
    )

    signing_key = jwks_client.get_signing_key_from_jwt(token)

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=ISSUER,
        options={
            "require": ["exp", "iss", "aud"]
        },
    )


# ==========================================
# 4. Validation d'un vrai JWT Authentik
# ==========================================

@pytest.mark.skipif(not TOKEN, reason="ID Token Authentik absent")
def test_jwt_valide():
    payload = verifier_jwt(TOKEN)

    assert payload["aud"] == AUDIENCE
    assert payload["iss"] == ISSUER
    assert "exp" in payload


# ==========================================
# 5. Vérification du rôle OPERATIONS
# ==========================================

@pytest.mark.skipif(not TOKEN, reason="ID Token Authentik absent")
def test_role_operations():
    payload = verifier_jwt(TOKEN)

    assert payload["preferred_username"] == "operations-1"
    assert "OPERATIONS" in payload["roles"]


# ==========================================
# 6. Rejet d'une audience incorrecte
# ==========================================

@pytest.mark.skipif(not TOKEN, reason="ID Token Authentik absent")
def test_audience_incorrecte():
    with pytest.raises(jwt.InvalidAudienceError):
        verifier_jwt(
            TOKEN,
            audience="mauvais-client"
        )


# ==========================================
# 7. Rejet d'un JWT falsifié
# ==========================================

@pytest.mark.skipif(not TOKEN, reason="ID Token Authentik absent")
def test_jwt_falsifie():
    parties = TOKEN.split(".")

    assert len(parties) == 3

    # Modification de la signature du JWT
    signature = parties[2]

    premier = "A" if signature[0] != "A" else "B"
    signature_falsifiee = premier + signature[1:]

    token_falsifie = ".".join([
        parties[0],
        parties[1],
        signature_falsifiee
    ])

    with pytest.raises(jwt.InvalidSignatureError):
        verifier_jwt(token_falsifie)


# ==========================================
# 8. Rejet d'un JWT expiré
# ==========================================

def test_jwt_expire():
    """
    Vérifie que PyJWT refuse un token dont
    la date d'expiration est dépassée.

    Test unitaire avec un JWT synthétique.
    """

    secret_test = "cle-locale-test-expiration"

    token_expire = jwt.encode(
        {
            "sub": "utilisateur-test",
            "exp": int(time.time()) - 3600,
        },
        secret_test,
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(
            token_expire,
            secret_test,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )


# ==========================================
# 9. Rejet d'un JWT sans claim exp
# ==========================================

def test_claim_exp_obligatoire():
    """
    Vérifie qu'un JWT sans le claim exp
    est rejeté lors de sa validation.

    Test unitaire avec un JWT synthétique.
    """

    secret_test = "cle-locale-de-test-jwt-expiration-2026-secure"

    token_sans_exp = jwt.encode(
        {
            "sub": "utilisateur-test",
        },
        secret_test,
        algorithm="HS256",
    )

    with pytest.raises(jwt.MissingRequiredClaimError) as erreur:
        jwt.decode(
            token_sans_exp,
            secret_test,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )

    assert erreur.value.claim == "exp"
