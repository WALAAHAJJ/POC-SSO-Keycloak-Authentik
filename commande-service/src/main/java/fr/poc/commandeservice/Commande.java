package fr.poc.commandeservice;

import java.math.BigDecimal;
import java.time.Instant;

/** Commande : simple objet de données, sans lien avec une base. */
public record Commande(
        Long id,
        Long productId,
        String productName,
        int quantity,
        BigDecimal totalPrice,
        Instant createdAt,
        String status) {
}
