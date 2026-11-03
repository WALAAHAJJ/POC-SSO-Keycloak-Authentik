
import jwt
import pytest
from datetime import datetime, timedelta, timezone

# Configuration du POC Keycloak
ISSUER = "http://localhost:8080/realms/collector-poc"
AUDIENCE = "catalogue-api"

# Clés fictives utilisées uniquement pour les tests
TEST_SECRET = "cle-fictive-reservee-aux-tests-jwt-collector-2026"
WRONG_SECRET = "autre-cle-fictive-differente-pour-test-collector-2026"


def creer_token_test(audience=AUDIENCE, expiration=5):
    maintenant = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "iss": ISSUER,
            "sub": "utilisateur-fictif",
            "aud": audience,
            "iat": maintenant,
            "exp": maintenant + timedelta(minutes=expiration),
            "realm_access": {
                "roles": ["SALES"]
            }
        },
        TEST_SECRET,
        algorithm="HS256"
    )


def verifier_token_test(token):
    return jwt.decode(
        token,
        TEST_SECRET,
        algorithms=["HS256"],
        issuer=ISSUER,
        audience=AUDIENCE
    )


def test_jwt_valide():
    token = creer_token_test()
    claims = verifier_token_test(token)

    assert claims["iss"] == ISSUER
    assert claims["aud"] == AUDIENCE
    assert "SALES" in claims["realm_access"]["roles"]


def test_jwt_mauvaise_audience():
    token = creer_token_test(audience="commande-api")

    with pytest.raises(jwt.InvalidAudienceError):
        verifier_token_test(token)


def test_jwt_expire():
    token = creer_token_test(expiration=-5)

    with pytest.raises(jwt.ExpiredSignatureError):
        verifier_token_test(token)


def test_jwt_signature_incorrecte():
    token = creer_token_test()

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            token,
            WRONG_SECRET,
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE
        )
