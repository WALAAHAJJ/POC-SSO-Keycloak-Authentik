import requests

BASE = "http://localhost:9000"
FLOW = BASE + "/api/v3/flows/executor/default-authentication-flow/"

session = requests.Session()
session.trust_env = False

response = session.get(FLOW, timeout=10)
response.raise_for_status()
data = response.json()

print("Étape initiale :", data.get("component"))

assert data.get("component") == "ak-stage-identification"

response = session.post(
    FLOW,
    json={
        "component": "ak-stage-identification",
        "uid_field": "operations-1",
    },
    timeout=10,
)
response.raise_for_status()
data = response.json()

print("Étape suivante :", data.get("component"))

assert data.get("component") == "ak-stage-password"

response = session.post(
    FLOW,
    json={
        "component": "ak-stage-password",
        "password": "mot-de-passe-volontairement-incorrect-2026",
    },
    timeout=10,
)

response.raise_for_status()
data = response.json()

print("Étape après tentative :", data.get("component"))

assert data.get("component") != "xak-flow-redirect", (
    "Vérifier le parcours : redirection inattendue"
)

user_response = session.get(
    BASE + "/api/v3/core/users/me/",
    timeout=10,
)

utilisateur = None

if user_response.status_code == 200:
    utilisateur = user_response.json().get("user", {}).get("username")

assert utilisateur != "operations-1", (
    "ERREUR : session authentifiée malgré le mauvais mot de passe"
)

print("\n===== TEST SÉCURITÉ AUTHENTIK =====")
print("Mauvais mot de passe refusé : OUI")
print("Session operations-1 non authentifiée : OUI")
print("TEST RÉUSSI")
