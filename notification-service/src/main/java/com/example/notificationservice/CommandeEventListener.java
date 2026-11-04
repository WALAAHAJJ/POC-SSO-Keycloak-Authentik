package com.example.notificationservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.time.Instant;

/**
 * Consomme les événements de commande et produit la même notification que l'appel HTTP
 * POST /notifications. Le groupe de consommateurs vient de spring.kafka.consumer.group-id.
 *
 * Kafka garantit une livraison "au moins une fois" : en cas de rejeu, une notification
 * peut être enregistrée deux fois (acceptable pour ce POC, mais à connaître).
 */
@Component
@ConditionalOnProperty(name = "poc.messaging.broker", havingValue = "kafka")
public class CommandeEventListener {

    private static final Logger log = LoggerFactory.getLogger(CommandeEventListener.class);

    private final NotificationRepository repository;

    public CommandeEventListener(NotificationRepository repository) {
        this.repository = repository;
    }

    @KafkaListener(topics = KafkaTopics.COMMANDE_EVENTS)
    public void onCommandeEvent(CommandeEvent event) {
        boolean paye = "PAYEE".equals(event.status());
        String subject = paye ? "Commande confirmée" : "Paiement refusé";
        String message = "Commande n°%d : %s x%d (%s)".formatted(
                event.commandeId(), event.productName(), event.quantity(), event.status());

        log.info("Événement Kafka reçu -> notification pour {} : [{}] {}",
                event.customerEmail(), subject, message);

        repository.save(new Notification(null, event.customerEmail(), subject, message, Instant.now()));
    }
}
