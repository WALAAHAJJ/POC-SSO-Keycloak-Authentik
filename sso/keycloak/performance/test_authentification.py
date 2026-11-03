import base64
import getpass
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

ISSUER = "http://localhost:8080/realms/collector-poc"
CLIENT_ID = "catalogue-client"
REDIRECT_URI = "http://127.0.0.1:8765/callback"

AUTH_URL = ISSUER + "/protocol/openid-connect/auth"
TOKEN_URL = ISSUER + "/protocol/openid-connect/token"

username = input("Utilisateur Keycloak : ")
password = getpass.getpass("Mot de passe : ")

verifier = secrets.token_urlsafe(64)

challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()

state = secrets.token_urlsafe(24)

params = {
    "client_id": CLIENT_ID,
    "response_type": "code",
    "scope": "openid profile email",
    "redirect_uri": REDIRECT_URI,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "state": state,
}

url = AUTH_URL + "?" + urllib.parse.urlencode(params)

callback = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def recevoir_callback(route):
        callback["url"] = route.request.url
        callback["temps"] = time.perf_counter()

        route.fulfill(
            status=200,
            content_type="text/plain",
            body="Authentification terminee."
        )

    page.route(REDIRECT_URI + "*", recevoir_callback)

    page.goto(url)

    page.locator('input[name="username"]').fill(username)
    page.locator('input[name="password"]').fill(password)

    print("\nDebut de la mesure...")

    debut = time.perf_counter()

    page.locator(
        'input[type="submit"], button[type="submit"]'
    ).first.click()

    page.wait_for_url(REDIRECT_URI + "*", timeout=30000)

    duree_auth = (callback["temps"] - debut) * 1000

    browser.close()

password = None

retour = urllib.parse.parse_qs(
    urllib.parse.urlparse(callback["url"]).query
)

if retour.get("state", [None])[0] != state:
    raise RuntimeError("Etat OAuth2 invalide")

code = retour.get("code", [None])[0]

if not code:
    raise RuntimeError("Authentification echouee")

donnees = urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "code_verifier": verifier,
}).encode()

requete = urllib.request.Request(
    TOKEN_URL,
    data=donnees,
    method="POST"
)

debut_token = time.perf_counter()

with urllib.request.urlopen(requete, timeout=15) as reponse:
    tokens = json.load(reponse)

duree_token = (time.perf_counter() - debut_token) * 1000

assert tokens.get("access_token")

print("\n===== RESULTATS KEYCLOAK =====")
print(f"Authentification navigateur : {duree_auth:.2f} ms")
print(f"Echange du code contre JWT : {duree_token:.2f} ms")
print(f"Total mesure : {duree_auth + duree_token:.2f} ms")
print("JWT recu : OUI")