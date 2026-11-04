# Tests de résilience Kafka

Deux scénarios de coupure à lancer pendant que le dashboard Grafana **POC Kafka** est ouvert
(plage *Last 5 minutes*, rafraîchissement 5 s).

Python 3.8+, **aucune dépendance à installer** (bibliothèque standard uniquement).

## Pré-requis

- l'infra tourne : `docker compose -f compose.kafka.yml -f compose.monitoring.yml up -d`
- `catalog-service` et `paiement-service` démarrés
- `commande-service` et `notification-service` démarrés en **mode kafka** (`poc.messaging.broker=kafka`)
- les commandes `docker` et `python` sont disponibles dans le terminal

## Lancer (terminal de l'IDE, à la racine du dépôt)

    python test-brokerMsg/scenario_a_coupure_consommateur.py
    python test-brokerMsg/scenario_b_coupure_broker.py

Dans IntelliJ : clic droit sur le fichier > *Run* (ou configuration « Python » avec le dossier de travail
à la racine du dépôt). Options : `--count 10` (nombre de commandes), `--interval 2` (pause en secondes).
Code de sortie : `0` = toutes les vérifications OK, `1` = au moins un échec, `2` = pré-requis manquants.

## Scénario A — coupure du consommateur (`notification-service`)

Le script te demande d'**arrêter** `notification-service` dans l'IDE (il détecte l'arrêt tout seul), envoie
10 commandes, puis te demande de le **relancer**.

| Ce que le script vérifie | Attendu |
|---|---|
| Les 10 commandes répondent `201` | oui, la commande ne dépend pas du consommateur |
| 10 événements présents dans Kafka | oui |
| Le lag augmente de 10 | oui, les messages attendent |
| Le lag retombe à 0 après redémarrage | oui |
| Notifications créées | 10 (le service garde ses données en mémoire : il a perdu les anciennes au redémarrage) |

Dans Grafana : « Lag » monte à 10 puis retombe, « Records consommés / s » s'arrête puis repart,
« Cibles Prometheus DOWN » passe à 1 pendant la coupure.

## Scénario B — coupure du broker (Kafka)

Le script arrête lui-même Kafka (`docker compose stop kafka`), envoie 10 commandes, **redémarre Kafka
même en cas d'erreur**, puis fait le bilan.

| Constat | Attendu avec la configuration actuelle |
|---|---|
| Les commandes répondent `201` | oui, mais ~3 s chacune (`max.block.ms=3000`) |
| Événements publiés pendant la panne | **0** : ils sont perdus (pas d'outbox ni de réessai) |
| Reprise après redémarrage | un nouvel événement est publié et le lag revient à 0 |

Dans Grafana : « Brokers Kafka actifs » tombe, les panneaux Kafka se vident, puis tout revient.

## Variables d'environnement (si ta config diffère)

`COMMANDE_URL` (défaut `http://localhost:8082`), `NOTIFICATION_URL` (`http://localhost:8084`),
`KAFKA_CONTAINER` (`poc-kafka`), `KAFKA_COMPOSE_FILE` (`compose.kafka.yml`), `KAFKA_TOPIC`
(`commandes.events`), `KAFKA_GROUP` (`notification-service`).

## Comment les mesures sont faites

Le script interroge Kafka avec `docker exec poc-kafka kafka-get-offsets.sh` (messages dans le topic) et
`kafka-consumer-groups.sh --describe` (lag). Ces valeurs sont instantanées, contrairement à Prometheus
qui a un délai de scrape ; Grafana sert ici à **observer** et le script à **vérifier**.
