#!/usr/bin/env python3
"""Scénario B : coupure du BROKER (Kafka).

Objectif : mesurer l'effet d'une panne de Kafka sur les commandes ET sur les événements.
Ce scénario met en évidence une limite connue du POC : les événements émis pendant la
panne ne sont PAS rejoués au retour de Kafka (pas d'outbox ni de réessai).

Déroulé :
  1. mesure l'état initial
  2. arrête le conteneur Kafka (docker compose stop kafka) - fait par le script
  3. envoie N commandes -> elles doivent répondre 201 (mais lentement : max.block.ms = 3 s)
  4. redémarre Kafka et attend qu'il soit « healthy » (le script le redémarre même en cas d'erreur)
  5. compare : combien d'événements ont réellement été publiés pendant la panne ?
  6. envoie une commande de contrôle pour vérifier que le système a repris

Pendant ce temps, observe le dashboard Grafana « POC Kafka » (brokers actifs, panneaux vides).

Usage :  python tests/resilience/scenario_b_coupure_broker.py [--count 10] [--interval 1]
"""
import argparse
import sys
import time

import kafka_test_utils as k


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--count", type=int, default=10, help="nombre de commandes (défaut 10)")
    parser.add_argument("--interval", type=float, default=1.0, help="pause entre commandes en s (défaut 1)")
    args = parser.parse_args()

    report = k.Report()
    if not k.preflight(need_notification=True):
        return 2

    k.step("1. État initial")
    offsets_before = k.end_offsets_total()
    lag_before = k.consumer_lag()
    print(f"    messages dans le topic : {offsets_before}   |   lag du groupe : {lag_before}")
    if offsets_before is None or lag_before is None:
        print("Impossible de lire Kafka (docker exec). Vérifie le nom du conteneur (KAFKA_CONTAINER).")
        return 2

    kafka_stopped = False
    ready = False
    try:
        k.step("2. Coupure du broker Kafka")
        res = k.kafka_compose("stop")
        if res.returncode != 0:
            print("Échec de l'arrêt de Kafka :\n" + res.stderr)
            return 2
        kafka_stopped = True
        print("    Kafka est arrêté (les autres conteneurs restent actifs).")

        k.step(f"3. Envoi de {args.count} commandes PENDANT la panne")
        results = k.send_commandes(args.count, args.interval)
        report.check(all(status == 201 for status, _ in results),
                     "toutes les commandes répondent 201 (la panne Kafka ne bloque pas les commandes)")
        slow = sum(1 for _, duration in results if duration >= 2.5)
        print(f"    {slow}/{args.count} requêtes ont attendu ~3 s (délai max.block.ms avant abandon de l'envoi)")
        print("    -> Regarde Grafana maintenant : « Brokers Kafka actifs » tombe.")
    finally:
        # Quoi qu'il arrive (erreur, Ctrl+C), on ne laisse pas Kafka arrêté
        if kafka_stopped:
            k.step("4. Redémarrage de Kafka")
            k.kafka_compose("start")
            ready = k.wait_until(lambda: k.kafka_health() == "healthy", timeout=120, interval=3.0)
    report.check(ready, "Kafka est de nouveau « healthy »")
    if not ready:
        return report.finish()

    k.step("5. Bilan des événements après la panne")
    time.sleep(5)  # laisse les clients se reconnecter
    offsets_after = k.end_offsets_total()
    published = (offsets_after or 0) - offsets_before
    lost = args.count - published
    print(f"    événements réellement publiés pendant la panne : {published} / {args.count}")
    if lost > 0:
        print(f"    CONSTAT : {lost} événement(s) PERDU(S) -> les commandes existent mais "
              "les notifications ne seront jamais envoyées.")
        print("    (limite connue : pas d'outbox pattern ni de réessai ; voir docs/kafka-prometheus-grafana.md)")

    k.step("6. Commande de contrôle : le système a-t-il repris ?")
    recovered = False
    for attempt in range(1, 6):  # le 1er envoi peut échouer le temps que le producer se reconnecte
        status, duration = k.post_commande()
        time.sleep(2)
        now = k.end_offsets_total() or 0
        print(f"    essai {attempt} : HTTP {status} en {duration:.2f}s, nouveaux messages dans Kafka : "
              f"{now - (offsets_after or 0)}")
        if now > (offsets_after or 0):
            recovered = True
            break
    report.check(recovered, "un nouvel événement est bien publié après le retour de Kafka")
    report.check(k.wait_until(lambda: k.consumer_lag() == 0, timeout=60, interval=1.0),
                 "le consommateur a repris et le lag est à 0")

    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
