package com.example.paiementservice;

import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Stockage mocké : les paiements sont gardés en mémoire (une Map), aucune base de données.
 * Ils disparaissent à l'arrêt du service.
 */
@Repository
public class PaiementRepository {

    private final ConcurrentHashMap<Long, Paiement> payments = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong();

    public List<Paiement> findAll() {
        return new ArrayList<>(payments.values());
    }

    public Optional<Paiement> findById(Long id) {
        return Optional.ofNullable(payments.get(id));
    }

    /** Attribue un identifiant au paiement puis le range en mémoire. */
    public Paiement save(Paiement payment) {
        Paiement saved = new Paiement(
                sequence.incrementAndGet(),
                payment.commandeId(),
                payment.amount(),
                payment.status(),
                payment.createdAt());
        payments.put(saved.id(), saved);
        return saved;
    }
}
