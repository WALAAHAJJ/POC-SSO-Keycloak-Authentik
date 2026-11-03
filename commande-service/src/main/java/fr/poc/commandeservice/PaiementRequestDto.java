package fr.poc.commandeservice;

import java.math.BigDecimal;

/** Corps envoyé au paiement-service (POST /paiements). */
public record PaiementRequestDto(Long commandeId, BigDecimal amount) {
}