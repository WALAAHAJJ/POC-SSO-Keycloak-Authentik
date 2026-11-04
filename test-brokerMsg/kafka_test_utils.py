"""Utilitaires partagés par les scénarios de coupure Kafka.

Python 3.8+, bibliothèque standard uniquement (rien à installer).
Les mesures Kafka passent par `docker exec` dans le conteneur du broker : elles sont
instantanées et ne dépendent pas du délai de scrape de Prometheus.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- Configuration (surchargeable par variables d'environnement) -------------
REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDE_URL = os.getenv("COMMANDE_URL", "http://localhost:8082")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8084")
KAFKA_CONTAINER = os.getenv("KAFKA_CONTAINER", "poc-kafka")
KAFKA_COMPOSE_FILE = os.getenv("KAFKA_COMPOSE_FILE", "compose.kafka.yml")
TOPIC = os.getenv("KAFKA_TOPIC", "commandes.events")
GROUP = os.getenv("KAFKA_GROUP", "notification-service")
KAFKA_BIN = "/opt/kafka/bin"  # dans l'image apache/kafka

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, errors="replace")


# --- Affichage ----------------------------------------------------------------
def info(msg):
    print(f"[..] {msg}")


def step(msg):
    print(f"\n=== {msg}")


def action(msg):
    """Action à faire à la main dans l'IDE."""
    print(f"\n>>> ACTION : {msg}")


class Report:
    """Collecte les vérifications et calcule le code de sortie."""

    def __init__(self):
        self.failed = 0

    def check(self, ok, label):
        print(f"[{'OK' if ok else 'KO'}] {label}")
        if not ok:
            self.failed += 1
        return ok

    def finish(self):
        print("\n" + "=" * 60)
        if self.failed:
            print(f"RESULTAT : {self.failed} vérification(s) en échec")
        else:
            print("RESULTAT : toutes les vérifications sont OK")
        return 1 if self.failed else 0


# --- HTTP ---------------------------------------------------------------------
def http_get(url, timeout=3):
    """Renvoie (statut, corps) ou None si le service est injoignable."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, OSError):
        return None


def service_up(base_url):
    res = http_get(base_url + "/actuator/health")
    return res is not None and res[0] == 200


def post_commande(product_id=1, quantity=1, email="test-resilience@example.com"):
    """Crée une commande. Renvoie (statut HTTP ou None, durée en secondes)."""
    body = json.dumps({"productId": product_id, "quantity": quantity,
                       "customerEmail": email}).encode()
    req = urllib.request.Request(COMMANDE_URL + "/commandes", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except (urllib.error.URLError, OSError):
        status = None
    return status, time.monotonic() - start


def send_commandes(count, interval):
    """Envoie `count` commandes espacées de `interval` s. Renvoie la liste des (statut, durée)."""
    results = []
    for i in range(1, count + 1):
        status, duration = post_commande()
        print(f"    commande {i:>2}/{count} -> HTTP {status} en {duration:.2f}s")
        results.append((status, duration))
        if i < count:
            time.sleep(interval)
    return results


def wait_until(predicate, timeout, interval=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


# --- Docker / Kafka -------------------------------------------------------------
def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def kafka_health():
    res = run(["docker", "inspect", "-f", "{{.State.Health.Status}}", KAFKA_CONTAINER])
    return res.stdout.strip() if res.returncode == 0 else "absent"


def kafka_compose(action_name):
    """`docker compose -f compose.kafka.yml stop|start kafka` depuis la racine du dépôt."""
    return run(["docker", "compose", "-f", KAFKA_COMPOSE_FILE, action_name, "kafka"],
               cwd=REPO_ROOT)


def _kafka_exec(script, *args):
    return run(["docker", "exec", KAFKA_CONTAINER, f"{KAFKA_BIN}/{script}",
                "--bootstrap-server", "localhost:9092", *args])


def end_offsets_total():
    """Nombre total de messages écrits dans le topic (somme des offsets de fin). None si erreur."""
    res = _kafka_exec("kafka-get-offsets.sh", "--topic", TOPIC, "--time", "-1")
    if res.returncode != 0:
        return None
    total = 0
    for line in res.stdout.splitlines():
        parts = line.strip().split(":")          # topic:partition:offset
        if len(parts) == 3 and parts[2].isdigit():
            total += int(parts[2])
    return total


def consumer_lag():
    """Lag total du groupe de consommateurs (messages non lus). 0 si le groupe n'existe pas encore,
    None si Kafka est injoignable."""
    res = _kafka_exec("kafka-consumer-groups.sh", "--describe", "--group", GROUP)
    if res.returncode != 0:
        return None
    lag_idx = None
    total = 0
    for line in res.stdout.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == "GROUP" and "LAG" in tokens:
            lag_idx = tokens.index("LAG")
        elif lag_idx is not None and tokens[0] == GROUP and len(tokens) > lag_idx:
            if tokens[lag_idx].isdigit():
                total += int(tokens[lag_idx])
    return total


def preflight(need_notification=True):
    """Vérifie que tout tourne avant de commencer. Renvoie True si OK."""
    step("Vérifications préalables")
    ok = True
    health = kafka_health()
    print(f"    Kafka ({KAFKA_CONTAINER}) : {health}")
    ok &= health == "healthy"
    up = service_up(COMMANDE_URL)
    print(f"    commande-service  ({COMMANDE_URL}) : {'UP' if up else 'INJOIGNABLE'}")
    ok &= up
    if need_notification:
        up = service_up(NOTIFICATION_URL)
        print(f"    notification-service ({NOTIFICATION_URL}) : {'UP' if up else 'INJOIGNABLE'}")
        ok &= up
    if not ok:
        print("\nPré-requis manquants : lancer l'infra (docker compose up -d) et les deux services "
              "avec le mode kafka, puis relancer ce script.")
    return ok


def count_notifications():
    res = http_get(NOTIFICATION_URL + "/notifications", timeout=5)
    if res is None or res[0] != 200:
        return None
    try:
        return len(json.loads(res[1]))
    except ValueError:
        return None
