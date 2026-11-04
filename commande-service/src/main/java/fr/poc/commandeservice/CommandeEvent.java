package fr.poc.commandeservice;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Événement métier publié quand une commande a été traitée (payée ou refusée).
 * Il décrit des faits : c'est au consommateur de décider quoi en faire (ici, notifier le client).
 */
public record CommandeEvent(
        Long commandeId,
        String customerEmail,
        String productName,
        int quantity,
        BigDecimal totalPrice,
        String status,
        Instant occurredAt) {
}
