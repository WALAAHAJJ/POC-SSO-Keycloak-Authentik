package fr.poc.commandeservice;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;

/** Client HTTP vers le paiement-service. */
@Component
public class PaiementClient {

    private final RestClient restClient;

    public PaiementClient(RestClient paiementRestClient) {
        this.restClient = paiementRestClient;
    }

    public PaiementDto payer(Long commandeId, BigDecimal amount) {
        try {
            return restClient.post()
                    .uri("/paiements")
                    .body(new PaiementRequestDto(commandeId, amount))
                    .retrieve()
                    .body(PaiementDto.class);
        } catch (HttpClientErrorException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "Requête rejetée par le service de paiement (" + e.getStatusCode() + ")");
        } catch (ResourceAccessException e) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Le service de paiement est indisponible");
        }
    }
}