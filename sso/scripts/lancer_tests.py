
import os
import sys
import tkinter as tk
from tkinter import simpledialog

import pytest

UTILISATEURS = {
    "sales-1": "KEYCLOAK_TOKEN_SALES_1",
    "operation-1": "KEYCLOAK_TOKEN_OPERATION_1",
    "sans-role-1": "KEYCLOAK_TOKEN_SANS_ROLE_1",
}

root = tk.Tk()
root.withdraw()

try:
    for utilisateur, variable in UTILISATEURS.items():
        token = simpledialog.askstring(
            "Tests SSO Keycloak",
            f"Colle l'Access Token de {utilisateur} :",
            show="*",
            parent=root
        )

        if not token:
            print(f"Token manquant pour {utilisateur}.")
            sys.exit(1)

        token = token.strip()

        if token.startswith("Bearer "):
            token = token[7:].strip()

        if len(token.split(".")) != 3:
            print(f"JWT incorrect pour {utilisateur}.")
            sys.exit(1)

        os.environ[variable] = token

    # Compatibilité avec les 4 tests d'intégration précédents
    os.environ["KEYCLOAK_TEST_TOKEN"] = os.environ[
        "KEYCLOAK_TOKEN_SALES_1"
    ]

finally:
    root.destroy()

resultat = pytest.main([
    "sso/keycloak/",
    "-v",
    "-rs",
    "--tb=short"
])

sys.exit(int(resultat))
