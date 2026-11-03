package fr.poc.commandeservice;

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

    public CommandeController(CommandeRepository repository, CatalogClient catalogClient) {
        this.repository = repository;
        this.catalogClient = catalogClient;
    }

    @GetMapping
    public List<Commande> findAll() {
        return repository.findAll();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Commande create(@RequestBody CommandeRequest request) {
        // Appel HTTP vers le catalog-service
        ProductDto product = catalogClient.getProduct(request.productId());

        if (product.stock() < request.quantity()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Stock insuffisant : " + product.stock() + " disponible(s)");
        }

        BigDecimal total = product.price().multiply(BigDecimal.valueOf(request.quantity()));
        // id = null : il est attribué par le repository
        Commande order = new Commande(null, product.id(), product.name(),
                request.quantity(), total, Instant.now());
        return repository.save(order);
    }
}
