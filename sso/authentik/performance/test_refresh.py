import json
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FICHIER = Path.home() / "POC-SSO" / "authentik-refresh-token.json"
NOMBRE_TESTS = 5

if not FICHIER.exists():
    raise RuntimeError("Refresh token introuvable.")

configuration = json.loads(FICHIER.read_text(encoding="utf-8"))

refresh_token = configuration["refresh_token"]
client_id = configuration["client_id"]
token_url = configuration["token_url"]

mesures = []

print("\n===== TEST REFRESH TOKEN AUTHENTIK =====")

for numero in range(1, NOMBRE_TESTS + 1):
    donnees = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }).encode()

    requete = urllib.request.Request(
        token_url,
        data=donnees,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    debut = time.perf_counter()

    try:
        with urllib.request.urlopen(requete, timeout=15) as reponse:
            tokens = json.load(reponse)
    except urllib.error.HTTPError as erreur:
        raise RuntimeError(
            f"Test {numero} refuse : HTTP {erreur.code}"
        ) from None

    duree_ms = (time.perf_counter() - debut) * 1000

    if not tokens.get("access_token"):
        raise RuntimeError("Access token absent.")

    # Prendre en charge la rotation du refresh token
    refresh_token = tokens.get("refresh_token", refresh_token)
    configuration["refresh_token"] = refresh_token

    # Sauvegarde locale atomique avec permissions restreintes
    temporaire = FICHIER.with_suffix(".tmp")
    fd = os.open(
        temporaire,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600
    )

    with os.fdopen(fd, "w", encoding="utf-8") as sortie:
        json.dump(configuration, sortie)

    os.replace(temporaire, FICHIER)

    mesures.append(duree_ms)
    print(f"Test {numero} : {duree_ms:.2f} ms - OK")

print("\n===== RESULTATS AUTHENTIK =====")
print(f"Nombre de tests : {len(mesures)}")
print(f"Minimum : {min(mesures):.2f} ms")
print(f"Maximum : {max(mesures):.2f} ms")
print(f"Moyenne : {statistics.mean(mesures):.2f} ms")
print(f"Mediane : {statistics.median(mesures):.2f} ms")
print(f"Renouvellements reussis : {len(mesures)}/5")
