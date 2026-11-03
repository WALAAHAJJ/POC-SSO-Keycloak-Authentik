
import json
from urllib.request import urlopen

ISSUER = "http://localhost:8080/realms/collector-poc"


def test_decouverte_oidc():
    with urlopen(
        ISSUER + "/.well-known/openid-configuration",
        timeout=5
    ) as response:
        assert response.status == 200
        data = json.load(response)

    assert data["issuer"] == ISSUER
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data


def test_cle_signature_rs256():
    with urlopen(
        ISSUER + "/protocol/openid-connect/certs",
        timeout=5
    ) as response:
        assert response.status == 200
        data = json.load(response)

    assert any(
        key.get("alg") == "RS256"
        and key.get("kty") == "RSA"
        and key.get("use") == "sig"
        for key in data["keys"]
    )
