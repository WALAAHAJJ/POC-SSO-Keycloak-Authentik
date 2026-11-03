package fr.poc.commandeservice;

import java.math.BigDecimal;
import java.time.Instant;

/** Réponse du paiement-service. Le statut vaut "ACCEPTE" ou "REFUSE". */
public record PaiementDto(Long id, Long commandeId, BigDecimal amount,
                          String status, Instant createdAt) {
}