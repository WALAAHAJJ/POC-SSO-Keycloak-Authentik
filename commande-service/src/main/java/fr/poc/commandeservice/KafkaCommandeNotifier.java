package fr.poc.commandeservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

/**
 * Publie un événement sur Kafka au lieu d'appeler le notification-service en HTTP.
 * La clé du message est l'id de la commande : tous les événements d'une même commande
 * arrivent dans la même partition, donc dans l'ordre.
 */
@Component
@ConditionalOnProperty(name = "poc.messaging.broker", havingValue = "kafka")
public class KafkaCommandeNotifier implements CommandeNotifier {

    private static final Logger log = LoggerFactory.getLogger(KafkaCommandeNotifier.class);

    private final KafkaTemplate<String, CommandeEvent> kafkaTemplate;

    public KafkaCommandeNotifier(KafkaTemplate<String, CommandeEvent> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    @Override
    public void commandeTraitee(CommandeEvent event) {
        try {
            // Envoi asynchrone : on ne bloque pas la réponse HTTP en attendant l'ack du broker
            kafkaTemplate.send(KafkaTopics.COMMANDE_EVENTS, String.valueOf(event.commandeId()), event)
                    .whenComplete((result, error) -> {
                        if (error != null) {
                            log.warn("Événement commande {} non publié : {}",
                                    event.commandeId(), error.getMessage());
                        } else {
                            log.info("Événement commande {} publié : partition {}, offset {}",
                                    event.commandeId(),
                                    result.getRecordMetadata().partition(),
                                    result.getRecordMetadata().offset());
                        }
                    });
        } catch (RuntimeException e) {
            // Ne doit pas empêcher la commande (même règle qu'avec l'appel HTTP)
            log.warn("Événement commande {} non publié : {}", event.commandeId(), e.getMessage());
        }
    }
}
