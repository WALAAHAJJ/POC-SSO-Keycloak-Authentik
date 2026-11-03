package fr.poc.commandeservice;

import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Stockage mocké : les commandes sont gardées en mémoire (une Map), aucune base de données.
 * Elles disparaissent à l'arrêt du service.
 */
@Repository
public class CommandeRepository {

    private final ConcurrentHashMap<Long, Commande> orders = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong();

    public List<Commande> findAll() {
        return new ArrayList<>(orders.values());
    }

    /** Attribue un identifiant à la commande puis la range en mémoire. */
    public Commande save(Commande order) {
        Commande saved = new Commande(
                sequence.incrementAndGet(),
                order.productId(),
                order.productName(),
                order.quantity(),
                order.totalPrice(),
                order.createdAt());
        orders.put(saved.id(), saved);
        return saved;
    }
}
