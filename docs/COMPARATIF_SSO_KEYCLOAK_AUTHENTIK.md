# POC Collector — Comparatif SSO Keycloak / Authentik

**Projet :** CESI MAALSI — Bloc 3, POC Collector  
**Périmètre de ce document :** installation, configuration et tests des fournisseurs d'identité (SSO) ; **les microservices Spring Boot et les API gateways sont hors périmètre**.  
**Date des essais :** 3 novembre 2026  
**Environnement :** macOS (Apple Silicon), Docker, Python 3.13, pytest, Playwright, Grafana k6, Postman.

## 1. Objectif et méthode

Comparer deux solutions de gestion des identités et des accès, **Keycloak** et **Authentik**, pour le POC Collector. Les critères étudiés sont : configuration OIDC, authentification, émission et vérification de jetons, rôles, SSO entre applications, protections de sécurité, temps de réponse et tenue en charge.

Deux clients OIDC sont prévus : **Catalogue** (`catalogue-client`) et **Commande** (`commande-client`). Les rôles métiers de test sont `SALES` et `OPERATIONS` ; un utilisateur sans rôle sert aux vérifications d'autorisation.

Les tests de charge ont été réalisés localement, avec montée progressive jusqu'à 20 utilisateurs virtuels. **Ils ne constituent ni un benchmark de production ni une mesure de capacité maximale.** Les environnements, les jeux de comptes, les parcours HTTP et les paramètres diffèrent encore entre les deux scénarios ; il faut donc interpréter prudemment les écarts.

## 2. Architecture du POC SSO

```text
                       Utilisateur / navigateur / Postman
                                      |
                            OAuth2 / OIDC + PKCE
                                      |
                    +-----------------+-----------------+
                    |                                   |
                 Keycloak                            Authentik
             (localhost:8080)                     (localhost:9000)
                    |                                   |
          Realm collector-poc              Applications Catalogue / Commande
                    |                                   |
             Clients OIDC                      Fournisseurs OIDC publics
                    +-----------------+-----------------+
                                      |
                           Access Token / ID Token
                                      |
                        API Catalogue / Commande (*)
```

(*) **L'intégration effective aux microservices Spring Boot et les retours HTTP 200/401/403 ne sont pas validés dans ce document** : ce travail dépend de l'intégration avec le groupe.

## 3. Technologies et configuration

| Élément | Keycloak | Authentik |
|---|---|---|
| Image utilisée | `quay.io/keycloak/keycloak:26.8.1` | `ghcr.io/goauthentik/server:2026.8.5` |
| Démarrage | Docker (mode `start-dev`) | Docker Compose (server, worker, PostgreSQL et dépendances de l'installation) |
| Adresse locale du POC | `http://localhost:8080` | `http://localhost:9000` |
| Configuration logique | Realm `collector-poc` | Applications + providers OIDC |
| Clients | `catalogue-client`, `commande-client` | `catalogue-client`, `commande-client` |
| Protocole | OAuth2 / OpenID Connect | OAuth2 / OpenID Connect |
| Flux utilisé | Authorization Code + PKCE S256 | Authorization Code + PKCE S256 |
| JWT / signature | Validation RS256/JWKS vérifiée | Validation RS256/JWKS vérifiée |
| Rôles métiers | `SALES`, `OPERATIONS` | Groupes `SALES`, `OPERATIONS`, exposés dans le claim `roles` |

Sur Authentik, le mapping de scope **Collector - Roles** a été configuré pour renvoyer les groupes métiers dans le claim `roles`. Une propriété obsolète `request.user.ak_groups` a été remplacée par `request.user.groups` après lecture des logs d'avertissement.

### Configurations et précautions

- Authentik possède un provider public pour chacun des clients Catalogue et Commande ; les URI de callback utilisées pour les essais sont celles de Postman (`https://oauth.pstmn.io/v1/callback`).
- Les scripts de performance peuvent utiliser une URI de callback de test et un hôte Docker différent de l'URL visible par le navigateur.
- Les mots de passe, jetons, fichiers `.env`, fichiers de credentials et éventuelles sauvegardes sensibles **ne doivent pas être publiés sur GitHub**.
- Les résultats obtenus avec un ID Token ne prouvent pas, à eux seuls, que les API Spring Boot valident les Access Tokens et appliquent des règles de rôles.

## 4. Résultats fonctionnels et sécurité

| Contrôle | Keycloak | Authentik | Observation / limite |
|---|---|---|---|
| Découverte OIDC et JWKS | Validé | Validé | Endpoints et clés publiques vérifiés |
| Signature JWT RS256 / claims | Validé | Validé | Vérification locale avec PyJWT |
| Rejet audience incorrecte | Validé | Validé | Test négatif |
| Rejet signature altérée | Validé | Validé | Test négatif |
| Rejet expiration / absence de `exp` | Validé | Tests locaux réussis | Sur Authentik, les deux tests supplémentaires utilisent des JWT synthétiques HS256 : ils vérifient le comportement de la bibliothèque, pas directement la signature RS256 d'Authentik |
| Mappings rôles `SALES` / `OPERATIONS` | Configurés | Configurés et vérifiés | Authentik : claim `roles` visible dans les jetons / UserInfo |
| Refus d'un mot de passe erroné | Validé | Validé | Authentik : test automatisé réussi |
| Compte désactivé | Testé | Déclaré réalisé | Conserver sortie du test pour une preuve complète |
| MFA | Testé côté Keycloak | Présent mais non imposé | Authentik : 0 dispositif TOTP / WebAuthn ; `not_configured_action=skip` |
| Tentatives erronées / brute force | Verrouillage temporaire observé après 3 erreurs | 3 tentatives erronées refusées | Sur Authentik, **un verrouillage automatique n'a pas été démontré** |
| SSO entre Catalogue et Commande | Configuré / à confirmer par preuve de test identique | **Validé** | Même session navigateur, deux clients, deux jetons, pas de second mot de passe |
| API protégées — 200 / 401 / 403 | À intégrer | À intégrer | Dépend des microservices Spring Boot, non testé ici |

### Tests automatisés Authentik

Le fichier `sso/authentik/test_integration_jwt.py` a obtenu **9 tests pytest réussis sur 9**. Les scénarios incluent découverte OIDC, RS256, JWKS, JWT valide, rôle `OPERATIONS`, audience incorrecte, JWT falsifié et deux vérifications locales de la gestion du claim `exp`.

Le test `sso/authentik/test_sso.py` a produit :

```text
Connexion Catalogue : OK
JWT Catalogue : OUI
Autorisation Commande : OK
JWT Commande : OUI
Deuxième mot de passe demandé : NON
SSO Catalogue -> Commande : RÉUSSI
```

## 5. Mesures de performance

### 5.1 Temps de connexion navigateur et échange du token

| Mesure | Keycloak | Authentik |
|---|---:|---:|
| Authentification navigateur (essai de référence) | 1 675,60 ms | 10 987,11 ms |
| Échange du code contre JWT (même essai) | 34,85 ms | 99,37 ms |
| Temps total (même essai) | **1 710,45 ms** | **11 086,48 ms** |

Authentik a également produit d'autres résultats de parcours navigateur : **15 944,94 ms**, **11 850,52 ms**, **19 266,06 ms**, **10 427,86 ms** et **15 025,06 ms**. Une répétition du flux avec `/flows/-/cancel/` a été observée lors de certains essais ; ce phénomène n'est pas visible dans tous les essais. **Ces temps navigateur, variables, ne permettent pas à eux seuls d'attribuer la différence au moteur SSO.** Les temps de saisie du nom d'utilisateur ne sont pas comptés de manière uniforme.

Le test OAuth2 Authentik réalisé directement avec k6, **sans navigateur**, a réussi une authentification complète en **594 ms** sur un essai isolé. Ce chiffre ne doit pas être comparé directement aux temps Playwright.

### 5.2 Refresh token — 5 renouvellements

| Indicateur | Keycloak | Authentik |
|---|---:|---:|
| Renouvellements réussis | 5/5 | 5/5 |
| Temps moyen | **5,93 ms** | **53,15 ms** |
| Minimum | Non conservé dans le présent relevé | 44,75 ms |
| Médiane | Non conservée dans le présent relevé | 46,07 ms |
| Maximum | Non conservé dans le présent relevé | 79,06 ms |

Authentik — valeurs observées : **79,06 ; 50,24 ; 46,07 ; 45,63 ; 44,75 ms**. La rotation éventuelle du refresh token est gérée par le script.

### 5.3 Charge k6 — montée progressive 1 → 5 → 10 → 20 VUs

**Profil pour chaque solution :** 15 s vers 5 VUs, 15 s vers 10, 15 s vers 20, puis 15 s de diminution vers 0 ; durée d'environ 60 s.

| Indicateur | Keycloak | Authentik |
|---|---:|---:|
| Authentifications OAuth2 réussies | **6 301** | **261** |
| Requêtes HTTP | 18 903 | 2 349 |
| Échecs HTTP | **0 %** | **0 %** |
| Latence moyenne par requête HTTP | **46,43 ms** | **230,15 ms** |
| P95 par requête HTTP | **96 ms** | **641,77 ms** |
| Temps moyen d'authentification complète | Non disponible dans le relevé retenu | **2,07 s** |
| P95 d'authentification complète | Non disponible | **4,19 s** |
| Débit moyen d'authentifications, sur 60 s (approximatif) | 105/s | 4,35/s |

**Important — comparabilité limitée :** le scénario Keycloak utilisait un fichier de plusieurs comptes de test ; le scénario Authentik réutilisait le même compte `operations-1`. De plus, le parcours de requêtes et les méthodes internes des deux plateformes ne sont pas identiques. Ces mesures démontrent surtout que **les deux scénarios ont terminé sans erreurs HTTP sur cet environnement local** et documentent les performances observées ; **elles ne suffisent pas à déclarer une supériorité intrinsèque ou une capacité maximale**.

## 6. Analyse comparative

**Keycloak — points forts constatés :** scénario OAuth2 fonctionnel, gestion des clients / rôles, tests de validation JWT, MFA et protection contre les tentatives répétées testés ; faible latence moyenne observée dans notre scénario de charge local. Le realm exporté permet de reconstruire une partie de la configuration.

**Authentik — points forts constatés :** intégration OIDC/PKCE validée, mapping de rôles personnalisable, parcours SSO entre deux applications validé, renouvellement de token réussi, tests négatifs de jetons réussis, scénario complet OAuth2 sous k6 réussi jusqu'à 20 VUs sans erreurs HTTP.

**Points de vigilance :** sous Authentik, le MFA existe mais reste facultatif pour les utilisateurs sans dispositif (`skip`), et la protection anti-brute-force n'a pas été démontrée. Le test de charge actuel réutilise le même compte. Les premiers essais Playwright ont révélé des réinitialisations possibles du flux d'authentification. Les endpoints métiers sécurisés n'ont pas encore été intégrés et testés de bout en bout.

## 7. Conclusion et recommandation provisoire

**Les deux solutions répondent aux besoins SSO de base démontrés par ce POC** : OAuth2/OIDC, émission et validation de jetons et gestion des identités. Authentik a en plus fait l'objet d'une preuve automatisée de SSO entre les applications Catalogue et Commande.

**Keycloak est provisoirement favorisé pour ce POC** lorsque l'on privilégie la maturité des scénarios de sécurité effectivement testés et les résultats de latence obtenus localement. Cette préférence **n'est pas une conclusion définitive de performance**, puisque les scénarios de charge ne sont pas encore parfaitement alignés. Authentik reste une alternative techniquement viable, particulièrement si la personnalisation des parcours d'authentification et des mappings est prioritaire.

Avant une recommandation de production, il faudrait au minimum : (1) refaire des benchmarks sur jeux de comptes, matériel et flux comparables, (2) imposer et tester le MFA dans les deux environnements, (3) vérifier effectivement les politiques anti-brute-force et (4) valider les réponses 200/401/403 des microservices lors de l'intégration de groupe.

## 8. Reproductibilité et confidentialité

Scripts connus dans le dépôt :

```text
sso/keycloak/performance/test_authentification.py
sso/keycloak/performance/test_refresh_token.py
sso/keycloak/performance/test_charge.js
sso/keycloak/performance/test_charge_auth.js
sso/authentik/test_integration_jwt.py
sso/authentik/test_mauvais_mot_de_passe.py
sso/authentik/test_bruteforce.py
sso/authentik/test_sso.py
sso/authentik/performance/test_authentification.py
sso/authentik/performance/test_refresh.py
sso/authentik/performance/test_charge_auth.js
```

Les scripts de charge k6 s'exécutent via Docker (`grafana/k6:latest`). Les tests Python utilisent un environnement virtuel et des bibliothèques telles que `pytest`, `requests`, `PyJWT` et `playwright`. Les fichiers contenant les mots de passe, tokens, secrets OIDC et environnements locaux ne doivent jamais être versionnés.

**Statut :** POC SSO et comparaison documentés ; validation des microservices hors périmètre de cette livraison.
