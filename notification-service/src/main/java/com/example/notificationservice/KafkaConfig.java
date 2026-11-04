package com.example.notificationservice;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Déclare aussi le topic côté consommateur : la création est idempotente, et le service
 * démarre correctement même si le commande-service n'a pas encore été lancé.
 */
@Configuration
@ConditionalOnProperty(name = "poc.messaging.broker", havingValue = "kafka")
public class KafkaConfig {

    @Bean
    NewTopic commandeEventsTopic() {
        return TopicBuilder.name(KafkaTopics.COMMANDE_EVENTS)
                .partitions(3)
                .replicas(1)
                .build();
    }
}
