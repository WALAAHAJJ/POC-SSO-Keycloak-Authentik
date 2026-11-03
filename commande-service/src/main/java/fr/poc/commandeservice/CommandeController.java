package fr.poc.commandeservice;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/commandes")
public class CommandeController {

    private final CommandeRepository repository;
    private final CatalogClient catalogClient;
    private final PaiementClient paiementClient;
    private final NotificationClient notificationClient;

    public CommandeController(CommandeRepository repository,
                              CatalogClient catalogClient,
                              PaiementClient paiementClient,
                              NotificationClient notificationClient) {
        this.repository = repository;
        this.catalogClient = catalogClient;
        this.paiementClient = paiementClient;
        this.notificationClient = notificationClient;
    }

    @GetMapping
    public List<Commande> findAll() {
        return repository.findAll();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Commande create(@Valid @RequestBody CommandeRequest request) {
        // 1. Appel HTTP vers le catalog-service
        ProductDto product = catalogClient.getProduct(request.productId());

        if (product.stock() < request.quantity()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Stock insuffisant : " + product.stock() + " disponible(s)");
        }

        // 2. Enregistrement de la commande (id = null : attribué par le repository)
        BigDecimal total = product.price().multiply(BigDecimal.valueOf(request.quantity()));
        Commande saved = repository.save(new Commande(null, product.id(), product.name(),
                request.quantity(), total, Instant.now(), "EN_ATTENTE"));

        // 3. Appel HTTP vers le paiement-service
        PaiementDto paiement = paiementClient.payer(saved.id(), total);
        boolean paye = "ACCEPTE".equals(paiement.status());
        Commande result = repository.updateStatus(saved.id(), paye ? "PAYEE" : "PAIEMENT_REFUSE");

        // 4. Appel HTTP vers le notification-service (n'empêche pas la commande si ça échoue)
        String message = "Commande n°%d : %s x%d (%s)".formatted(
                saved.id(), product.name(), request.quantity(), result.status());
        notificationClient.envoyer(
                request.customerEmail(),
                paye ? "Commande confirmée" : "Paiement refusé",
                message);

        return result;
    }
}