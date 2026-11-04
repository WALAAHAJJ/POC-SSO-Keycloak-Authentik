#!/usr/bin/env python3
"""Scénario A : coupure du CONSOMMATEUR (notification-service).

Objectif : montrer que Kafka garde les messages pendant que le consommateur est arrêté,
puis les livre tous à son retour (aucune perte).

Déroulé :
  1. mesure l'état initial (messages dans le topic, lag)
  2. te demande d'ARRÊTER notification-service dans l'IDE (le script détecte l'arrêt tout seul)
  3. envoie N commandes -> elles doivent toutes répondre 201
  4. vérifie que N messages sont dans Kafka et que le lag a augmenté de N
  5. te demande de RELANCER notification-service, puis attend que le lag retombe à 0

Pendant ce temps, observe le dashboard Grafana « POC Kafka » (lag, records consommés, cibles DOWN).

Usage :  python tests/resilience/scenario_a_coupure_consommateur.py [--count 10] [--interval 2]
"""
import argparse
import sys
import time

import kafka_test_utils as k


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--count", type=int, default=10, help="nombre de commandes (défaut 10)")
    parser.add_argument("--interval", type=float, default=2.0, help="pause entre commandes en s (défaut 2)")
    parser.add_argument("--wait", type=int, default=180, help="attente max des actions manuelles en s")
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

    k.step("2. Coupure du consommateur")
    k.action("ARRÊTE notification-service dans ton IDE (bouton Stop). Le script attend...")
    if not k.wait_until(lambda: not k.service_up(k.NOTIFICATION_URL), timeout=args.wait):
        print("notification-service est toujours actif : abandon.")
        return 2
    print("    notification-service est arrêté.")

    k.step(f"3. Envoi de {args.count} commandes pendant la coupure")
    results = k.send_commandes(args.count, args.interval)
    report.check(all(status == 201 for status, _ in results),
                 "toutes les commandes répondent 201 (la commande ne dépend pas du consommateur)")

    k.step("4. Contenu de Kafka pendant la coupure")
    offsets_during = k.end_offsets_total()
    lag_during = k.consumer_lag()
    published = (offsets_during or 0) - offsets_before
    print(f"    messages publiés : {published}   |   lag : {lag_during}")
    report.check(published == args.count, f"{args.count} événements publiés dans Kafka")
    report.check(lag_during is not None and lag_during - lag_before == args.count,
                 f"le lag a augmenté de {args.count} (messages en attente, non perdus)")
    print("    -> Regarde Grafana maintenant : lag = {}, cible 8084 DOWN.".format(lag_during))

    k.step("5. Retour du consommateur")
    k.action("RELANCE notification-service dans ton IDE (avec le mode kafka). Le script attend...")
    if not k.wait_until(lambda: k.service_up(k.NOTIFICATION_URL), timeout=args.wait):
        print("notification-service n'a pas redémarré à temps : abandon.")
        return 2
    started = time.monotonic()
    print("    notification-service est reparti, attente de la consommation du retard...")
    drained = k.wait_until(lambda: k.consumer_lag() == 0, timeout=90, interval=1.0)
    report.check(drained, f"le lag retombe à 0 (en {time.monotonic() - started:.1f}s après le redémarrage)")

    notifications = k.count_notifications()
    print(f"    notifications enregistrées par le service : {notifications}")
    report.check(notifications is not None and notifications >= args.count,
                 f"au moins {args.count} notifications créées à partir des messages en attente")

    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
