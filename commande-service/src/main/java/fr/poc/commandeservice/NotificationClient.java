package fr.poc.commandeservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** Client HTTP vers le notification-service. */
@Component
public class NotificationClient {

    private static final Logger log = LoggerFactory.getLogger(NotificationClient.class);

    private final RestClient restClient;

    public NotificationClient(RestClient notificationRestClient) {
        this.restClient = notificationRestClient;
    }

    public void envoyer(String recipient, String subject, String message) {
        try {
            restClient.post()
                    .uri("/notifications")
                    .body(new NotificationRequestDto(recipient, subject, message))
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientException e) {
            log.warn("Notification non envoyée : {}", e.getMessage());
        }
    }
}