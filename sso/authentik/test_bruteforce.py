import requests

BASE = "http://localhost:9000"
FLOW = BASE + "/api/v3/flows/executor/default-authentication-flow/"
USERNAME = "sans-role-1"

print("\n===== TEST BRUTE FORCE AUTHENTIK =====")

for tentative in range(1, 4):
    session = requests.Session()
    session.trust_env = False

    response = session.get(FLOW, timeout=15)
    response.raise_for_status()
    data = response.json()

    for _ in range(5):
        component = data.get("component")

        if component == "ak-stage-identification":
            payload = {
                "component": component,
                "uid_field": USERNAME,
            }
        elif component == "ak-stage-password":
            payload = {
                "component": component,
                "password": "incorrect-test-2026",
            }
        else:
            break

        response = session.post(
            FLOW, json=payload, timeout=15
        )
        response.raise_for_status()
        data = response.json()

    response = session.get(
        BASE + "/api/v3/core/users/me/",
        timeout=15
    )

    utilisateur = None
    if response.status_code == 200:
        utilisateur = response.json().get(
            "user", {}
        ).get("username")

    if utilisateur == USERNAME:
        raise AssertionError(
            "Session authentifiée malgré le mauvais mot de passe"
        )

    print(f"Tentative {tentative}/3 : accès refusé - OK")

print("\n3 tentatives incorrectes refusées.")
print("TEST DE REFUS : RÉUSSI")
print("Protection anti-brute-force : à vérifier séparément")
