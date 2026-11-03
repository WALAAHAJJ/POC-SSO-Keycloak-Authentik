import base64
import getpass
import hashlib
import json
import secrets
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9000"
AUTH_URL = BASE + "/application/o/authorize/"
TOKEN_URL = BASE + "/application/o/token/"
REDIRECT = "https://oauth.pstmn.io/v1/callback"

USERNAME = "operations-1"


def preparer_autorisation(client_id):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(24)

    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": "openid profile email roles",
        "redirect_uri": REDIRECT,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }

    return (
        AUTH_URL + "?" + urllib.parse.urlencode(params),
        verifier,
        state,
    )


def obtenir_token(callback_url, verifier, state, client_id):
    params = urllib.parse.parse_qs(
        urllib.parse.urlparse(callback_url).query
    )

    if params.get("error"):
        raise RuntimeError(
            "Autorisation refusée : " + params["error"][0]
        )

    if params.get("state", [None])[0] != state:
        raise RuntimeError("State OAuth2 incorrect")

    code = params.get("code", [None])[0]

    if not code:
        raise RuntimeError("Code OAuth2 absent")

    donnees = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": REDIRECT,
        "code_verifier": verifier,
    }).encode()

    requete = urllib.request.Request(
        TOKEN_URL,
        data=donnees,
        method="POST",
    )

    with urllib.request.urlopen(requete, timeout=15) as reponse:
        tokens = json.load(reponse)

    if not tokens.get("access_token"):
        raise RuntimeError("Access Token absent")

    return True


def est_callback(url):
    return url.startswith(REDIRECT + "?")


def tester_sso():
    password = getpass.getpass(
        "Mot de passe operations-1 : "
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Intercepter le callback sans contacter Postman
            def callback_handler(route):
                route.fulfill(
                    status=200,
                    content_type="text/plain",
                    body="Callback OAuth2 reçu",
                )

            page.route(REDIRECT + "*", callback_handler)

            print("\n===== TEST 1 : CATALOGUE =====")

            url, verifier, state = preparer_autorisation(
                "catalogue-client"
            )

            page.goto(url, wait_until="commit")

            champ_username = page.locator(
                'input[name="uid_field"], '
                'input[name="username"], '
                'input[autocomplete="username"]'
            ).first

            champ_username.wait_for(
                state="visible", timeout=30000
            )
            champ_username.fill(USERNAME)

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

            champ_password = page.locator(
                'input[type="password"]'
            ).first

            champ_password.wait_for(
                state="visible", timeout=30000
            )
            champ_password.fill(password)

            page.locator(
                'button[type="submit"], '
                'input[type="submit"]'
            ).first.click()

            page.wait_for_url(
                REDIRECT + "*",
                timeout=30000,
                wait_until="commit",
            )

            obtenir_token(
                page.url,
                verifier,
                state,
                "catalogue-client",
            )

            print("Connexion Catalogue : OK")
            print("JWT Catalogue : OUI")

            # Conserver le même contexte navigateur
            print("\n===== TEST 2 : COMMANDE =====")

            url, verifier, state = preparer_autorisation(
                "commande-client"
            )

            page.goto(url, wait_until="commit")

            try:
                page.wait_for_url(
                    REDIRECT + "*",
                    timeout=15000,
                    wait_until="commit",
                )
            except Exception:
                print(
                    "Commande nécessite une nouvelle "
                    "interaction ou authentification."
                )
                print("SSO automatique : NON VALIDÉ")
                return

            if not est_callback(page.url):
                raise RuntimeError(
                    "Callback Commande non atteint"
                )

            obtenir_token(
                page.url,
                verifier,
                state,
                "commande-client",
            )

            print("Autorisation Commande : OK")
            print("JWT Commande : OUI")
            print("Deuxième mot de passe demandé : NON")

            print("\n===== RÉSULTAT FINAL =====")
            print("SSO Catalogue -> Commande : RÉUSSI")

        finally:
            browser.close()


if __name__ == "__main__":
    tester_sso()
