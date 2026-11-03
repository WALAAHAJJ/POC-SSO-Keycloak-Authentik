package com.example.paiementservice;

import java.math.BigDecimal;
import java.time.Instant;

/** Paiement : simple objet de données, sans lien avec une base. */
public record Paiement(
        Long id,
        Long commandeId,
        BigDecimal amount,
        PaiementStatus status,
        Instant createdAt) {
}
