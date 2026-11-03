import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ISSUER = "http://localhost:8080/realms/collector-poc"
CLIENT_ID = "catalogue-client"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
TOKEN_URL = ISSUER + "/protocol/openid-connect/token"

verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()

state = secrets.token_urlsafe(24)


def envoyer_token(parametres):
    donnees = urllib.parse.urlencode(parametres).encode()

    requete = urllib.request.Request(
        TOKEN_URL,
        data=donnees,
        method="POST"
    )

    debut = time.perf_counter()

    with urllib.request.urlopen(requete, timeout=15) as reponse:
        resultat = json.load(reponse)

    duree = (time.perf_counter() - debut) * 1000
    return resultat, duree


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parametres = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )

        self.server.resultat = parametres

        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"Authentification terminee. Retournez au terminal."
        )

    def log_message(self, *args):
        pass


serveur = HTTPServer(("127.0.0.1", 8765), CallbackHandler)
serveur.timeout = 120

params = {
    "client_id": CLIENT_ID,
    "response_type": "code",
    "scope": "openid profile email",
    "redirect_uri": REDIRECT_URI,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "state": state,
}

url = ISSUER + "/protocol/openid-connect/auth?" + urllib.parse.urlencode(params)

print("Ouverture de Keycloak...")
webbrowser.open(url)

serveur.handle_request()
serveur.server_close()

resultat = getattr(serveur, "resultat", {})

if resultat.get("state", [None])[0] != state:
    raise RuntimeError("Etat OAuth2 invalide ou authentification non terminee")

code = resultat.get("code", [None])[0]

if not code:
    raise RuntimeError("Aucun code d'autorisation recu")

tokens, duree = envoyer_token({
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "code_verifier": verifier,
})

print(f"Echange du code : {duree:.2f} ms")

refresh_token = tokens["refresh_token"]

print("\nMESURE DU REFRESH TOKEN")

for numero in range(1, 6):
    tokens, duree = envoyer_token({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    })

    refresh_token = tokens["refresh_token"]

    print(f"Test {numero} : {duree:.2f} ms")

print("\nTests termines.")