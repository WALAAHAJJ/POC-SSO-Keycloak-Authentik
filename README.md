# POC SSO — Keycloak vs Authentik

## Objectif
Comparer Keycloak et Authentik pour sécuriser l'authentification des microservices Catalogue et Commande du projet Collector.

## Technologies
Docker, Keycloak, Authentik, OAuth2, OpenID Connect, JWT, PKCE, Postman, Python et pytest.

## Tests réalisés — Keycloak
- Authentification multi-utilisateurs et gestion des rôles SALES et OPERATIONS.
- Validation JWT : signature RS256, expiration et audiences.
- Rejet des JWT falsifiés, expirés et avec audience incorrecte.
- Refus des mots de passe incorrects et des comptes désactivés.
- Gestion des sessions et déconnexion.
- Configuration MFA et protection contre les attaques par force brute.
- SSO validé entre deux clients OIDC : Catalogue et Commande.
- Tests automatisés avec pytest.

## Exécution des tests
Installer les dépendances :

    python3 -m pip install -r sso/requirements.txt

Lancer les tests :

    python3 -m pytest sso/keycloak/ -v

Les tests d'intégration nécessitent un Keycloak local configuré et des tokens de test. Certains tests sont ignorés si les tokens sont absents.

## Prochaines étapes
- Réaliser les mêmes tests avec Authentik.
- Comparer les deux solutions SSO.
- Tester les autorisations HTTP 401/403 sur les microservices Spring Boot.

## Sécurité
Ne jamais publier de mots de passe, Access Tokens ou secrets.

