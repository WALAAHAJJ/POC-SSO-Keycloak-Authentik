
import base64
import getpass
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

# ==========================================
# Configuration Authentik
# ==========================================

BASE_URL = "http://localhost:9000"
ISSUER = BASE_URL + "/application/o/catalogue-poc/"
CLIENT_ID = "catalogue-client"

AUTH_URL = BASE_URL + "/application/o/authorize/"
TOKEN_URL = BASE_URL + "/application/o/token/"
REDIRECT_URI = "https://oauth.pstmn.io/v1/callback"

username = input("Utilisateur Authentik : ").strip()
password = getpass.getpass("Mot de passe : ")

# ==========================================
# Configuration OAuth2 + PKCE
# ==========================================

verifier = secrets.token_urlsafe(64)

challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()

state = secrets.token_urlsafe(24)

params = {
    "client_id": CLIENT_ID,
    "response_type": "code",
    "scope": "openid profile email roles offline_access",
    "redirect_uri": REDIRECT_URI,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "state": state,
}

url = AUTH_URL + "?" + urllib.parse.urlencode(params)

callback = {}
evenements = []
debut = None
fin_clic = None
fin_attente = None


# ==========================================
# Enregistrement des événements HTTP
# ==========================================

def tracer_evenement(nom, adresse="", statut=None):
    if debut is None:
        return

    temps_ms = (time.perf_counter() - debut) * 1000

    # Ne jamais afficher les paramètres OAuth2
    chemin = urllib.parse.urlparse(adresse).path if adresse else ""

    if statut is not None:
        description = f"{nom} HTTP {statut} {chemin}"
    else:
        description = f"{nom} {chemin}"

    evenements.append((temps_ms, description))


# ==========================================
# Authentification avec Playwright
# ==========================================

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context()
    page = context.new_page()

    def recevoir_callback(route):
        callback["url"] = route.request.url
        callback["temps"] = time.perf_counter()

        tracer_evenement(
            "Callback OAuth2",
            route.request.url
        )

        route.fulfill(
            status=200,
            content_type="text/plain",
            body="Authentification Authentik terminee."
        )

    def suivre_reponse(response):
        if response.url.startswith(BASE_URL):
            tracer_evenement(
                "Réponse Authentik",
                response.url,
                response.status
            )

    def suivre_navigation(frame):
        if frame == page.main_frame:
            tracer_evenement(
                "Navigation",
                frame.url
            )

    page.route(REDIRECT_URI + "*", recevoir_callback)

    page.on("response", suivre_reponse)
    page.on("framenavigated", suivre_navigation)

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        # ==================================
        # Étape 1 : nom d'utilisateur
        # ==================================

        champ_username = page.locator(
            'input[name="uid_field"], '
            'input[name="username"], '
            'input[autocomplete="username"]'
        ).first

        if (
            champ_username.count() > 0
            and champ_username.is_visible()
        ):
            champ_username.fill(username)

            champ_password = page.locator(
                'input[type="password"]'
            )

            if (
                champ_password.count() == 0
                or not champ_password.first.is_visible()
            ):
                page.locator(
                    'button[type="submit"], '
                    'input[type="submit"]'
                ).first.click()

        # ==================================
        # Étape 2 : mot de passe
        # ==================================

        champ_password = page.locator(
            'input[type="password"]'
        ).first

        champ_password.wait_for(
            state="visible",
            timeout=30000
        )

        champ_password.fill(password)

        print("\nDébut de la mesure Authentik...")

        # Début de la mesure :
        # soumission du mot de passe
        debut = time.perf_counter()

        page.locator(
            'button[type="submit"], '
            'input[type="submit"]'
        ).first.click()

        fin_clic = time.perf_counter()

        # Callback OAuth2
        page.wait_for_url(
            REDIRECT_URI + "*",
            timeout=30000,
            wait_until="commit"
        )

        fin_attente = time.perf_counter()

        if "temps" in callback:
            fin_auth = callback["temps"]
        else:
            fin_auth = fin_attente

        duree_auth = (fin_auth - debut) * 1000

        # Récupération sécurisée de l'URL
        callback["url"] = page.url

    finally:
        browser.close()

password = None

# ==========================================
# Résultats du parcours navigateur
# ==========================================

print("\n===== DÉTAILS AUTHENTIFICATION =====")

print(
    "Durée de l'action Playwright : "
    f"{(fin_clic - debut) * 1000:.2f} ms"
)

print(
    "Temps jusqu'au callback : "
    f"{duree_auth:.2f} ms"
)

print(
    "Durée totale jusqu'à la fin de l'attente : "
    f"{(fin_attente - debut) * 1000:.2f} ms"
)

print("\n===== CHRONOLOGIE HTTP =====")

for temps_ms, description in evenements:
    print(f"+{temps_ms:.2f} ms : {description}")

# ==========================================
# Vérification OAuth2
# ==========================================

if "url" not in callback:
    raise RuntimeError("Callback OAuth2 non reçu")

retour = urllib.parse.parse_qs(
    urllib.parse.urlparse(callback["url"]).query
)

if retour.get("error"):
    raise RuntimeError(
        "Authentification refusée : "
        + retour["error"][0]
    )

if retour.get("state", [None])[0] != state:
    raise RuntimeError("État OAuth2 invalide")

code = retour.get("code", [None])[0]

if not code:
    raise RuntimeError("Aucun code OAuth2 reçu")

# ==========================================
# Échange du code contre JWT
# ==========================================

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
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    method="POST"
)

debut_token = time.perf_counter()

with urllib.request.urlopen(
    requete,
    timeout=15
) as reponse:
    tokens = json.load(reponse)

duree_token = (
    time.perf_counter() - debut_token
) * 1000

if not tokens.get("access_token"):
    raise RuntimeError("Access Token absent")

# Enregistrer le refresh token en dehors de Git
from pathlib import Path
import os

refresh_token = tokens.get("refresh_token")

if not refresh_token:
    raise RuntimeError(
        "Refresh token absent : verifier la configuration offline_access."
    )

fichier_refresh = (
    Path.home() / "POC-SSO" / "authentik-refresh-token.json"
)

configuration = {
    "refresh_token": refresh_token,
    "client_id": CLIENT_ID,
    "token_url": TOKEN_URL
}

fichier_refresh.parent.mkdir(parents=True, exist_ok=True)

fd = os.open(
    fichier_refresh,
    os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
    0o600
)

with os.fdopen(fd, "w", encoding="utf-8") as sortie:
    json.dump(configuration, sortie)

fichier_refresh.chmod(0o600)

print("Refresh token enregistre localement : OUI")

# ==========================================
# Résultats finaux
# ==========================================

print("\n===== RÉSULTATS AUTHENTIK =====")

print(
    f"Authentification navigateur : "
    f"{duree_auth:.2f} ms"
)

print(
    f"Échange du code contre JWT : "
    f"{duree_token:.2f} ms"
)

print(
    f"Total mesuré : "
    f"{duree_auth + duree_token:.2f} ms"
)

print("JWT reçu : OUI")
