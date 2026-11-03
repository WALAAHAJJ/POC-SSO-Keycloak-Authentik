package fr.poc.commandeservice;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class ServicesClientConfig {

    @Bean
    RestClient paiementRestClient(@Value("${paiement.service.url}") String baseUrl) {
        return RestClient.builder().baseUrl(baseUrl).build();
    }

    @Bean
    RestClient notificationRestClient(@Value("${notification.service.url}") String baseUrl) {
        return RestClient.builder().baseUrl(baseUrl).build();
    }
}
