package fr.poc.commandeservice;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Déclare le topic : Spring (KafkaAdmin) le crée au démarrage s'il n'existe pas.
 * Actif uniquement avec poc.messaging.broker=kafka, pour ne pas solliciter Kafka sinon.
 */
@Configuration
@ConditionalOnProperty(name = "poc.messaging.broker", havingValue = "kafka")
public class KafkaConfig {

    @Bean
    NewTopic commandeEventsTopic() {
        return TopicBuilder.name(KafkaTopics.COMMANDE_EVENTS)
                .partitions(3)
                .replicas(1) // 1 seul broker dans compose.kafka.yml
                .build();
    }
}
