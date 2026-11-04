package com.example.notificationservice;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Événement publié par le commande-service sur le topic Kafka "commandes.events".
 * Chaque service garde sa propre copie du contrat (pas de classe partagée entre microservices) :
 * seuls les noms de champs JSON comptent.
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
