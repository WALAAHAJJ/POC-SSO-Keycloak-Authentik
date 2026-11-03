
import tkinter as tk
from tkinter import simpledialog
import jwt
from jwt import PyJWKClient
from datetime import datetime, timezone

# Configuration Keycloak
ISSUER = "http://localhost:8080/realms/collector-poc"
JWKS_URL = ISSUER + "/protocol/openid-connect/certs"

# Audiences attendues selon le client OIDC
CLIENTS = {
    "catalogue-client": "catalogue-api",
    "commande-client": "commande-api"
}

# Fenêtre pour saisir le JWT
root = tk.Tk()
root.withdraw()

token = simpledialog.askstring(
    "Analyse JWT Keycloak",
    "Colle ton Access Token Keycloak :",
    show="*",
    parent=root
)

root.destroy()

if not token:
    print("Aucun token fourni.")
    raise SystemExit(1)

try:
    token = token.strip()

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if len(token.split(".")) != 3:
        print("ECHEC : Format JWT incorrect.")
        raise SystemExit(1)

    # Lecture des informations pour le diagnostic.
    # Ces informations ne sont pas encore fiables
    # tant que la signature n'est pas vérifiée.
    informations = jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False
        },
        algorithms=["RS256"]
    )

    client = informations.get("azp")

    if client not in CLIENTS:
        print("ECHEC : Client OIDC inconnu :", client)
        raise SystemExit(1)

    audience_attendue = CLIENTS[client]

    # Diagnostic avant validation
    print("\n=== DIAGNOSTIC JWT ===")
    print("Client :", client)
    print("Audience recue :", informations.get("aud"))
    print("Audience attendue :", audience_attendue)

    # Récupération de la clé publique Keycloak
    jwks_client = PyJWKClient(JWKS_URL)
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    # Vérification réelle du JWT
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        audience=audience_attendue,
        options={
            "require": ["exp", "iss", "aud", "azp"]
        }
    )

    # Contrôle du client après vérification de signature
    if claims.get("azp") != client:
        raise jwt.InvalidTokenError(
            "Client OIDC incorrect"
        )

    # Résultats
    print("\n=== VERIFICATION JWT KEYCLOAK ===")
    print("Signature RS256 : VALIDE")
    print("Issuer :", claims.get("iss"))
    print("Utilisateur :", claims.get("preferred_username"))
    print("Client :", claims.get("azp"))
    print("Audience :", claims.get("aud"))

    roles = claims.get(
        "realm_access", {}
    ).get("roles", [])

    print("Roles :", roles)
    print(
        "Role SALES :",
        "PRESENT" if "SALES" in roles else "ABSENT"
    )
    print(
        "Role OPERATIONS :",
        "PRESENT" if "OPERATIONS" in roles else "ABSENT"
    )

    expiration = datetime.fromtimestamp(
        claims["exp"],
        timezone.utc
    )

    print("Expiration UTC :", expiration)
    print("Token non expire : OUI")
    print("Audience : VALIDE")

    print("\nRESULTAT : JWT VALIDE")

except jwt.ExpiredSignatureError:
    print("\nECHEC : Token expire.")

except jwt.InvalidAudienceError:
    print("\nECHEC : Audience incorrecte.")
    print(
        "Verifier le Client scope et son Audience Mapper "
        "dans Keycloak."
    )

except jwt.InvalidIssuerError:
    print("\nECHEC : Emetteur incorrect.")

except jwt.InvalidSignatureError:
    print("\nECHEC : Signature JWT invalide.")

except jwt.InvalidTokenError as e:
    print("\nECHEC : JWT invalide :", e)

except Exception as e:
    print("\nERREUR :", type(e).__name__, str(e))
