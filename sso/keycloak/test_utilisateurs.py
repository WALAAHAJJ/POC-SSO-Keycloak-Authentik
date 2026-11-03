
import os

import jwt
import pytest
from jwt import PyJWKClient

ISSUER = "http://localhost:8080/realms/collector-poc"
JWKS_URL = ISSUER + "/protocol/openid-connect/certs"
AUDIENCE = "catalogue-api"

# Profils métier attendus
PROFILS = {
    "sales-1": {"SALES"},
    "operation-1": {"OPERATIONS"},
    "sans-role-1": set(),
}

ROLES_METIER = {"SALES", "OPERATIONS"}


@pytest.mark.parametrize(
    "utilisateur,roles_attendus",
    PROFILS.items()
)
def test_roles_utilisateur(utilisateur, roles_attendus):
    nom_variable = (
        "KEYCLOAK_TOKEN_"
        + utilisateur.upper().replace("-", "_")
    )

    token = os.environ.get(nom_variable)

    if not token:
        pytest.skip(
            f"Token absent pour {utilisateur} : {nom_variable}"
        )

    jwks = PyJWKClient(JWKS_URL)
    cle = jwks.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        cle.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        audience=AUDIENCE
    )

    assert claims["preferred_username"] == utilisateur

    roles = set(
        claims.get("realm_access", {}).get("roles", [])
    )

    assert roles & ROLES_METIER == roles_attendus
