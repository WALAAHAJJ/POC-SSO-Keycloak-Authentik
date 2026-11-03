package fr.poc.catalogservice;

import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

/**
 * Source de données mockée : la liste est figée en mémoire, aucune base de données.
 * Les données sont rechargées à chaque démarrage du service.
 */
@Repository
public class ProductRepository {

    private final List<Product> products = List.of(
            new Product(1L, "Clavier mécanique", new BigDecimal("89.90"), 25),
            new Product(2L, "Souris sans fil", new BigDecimal("34.50"), 40),
            new Product(3L, "Écran 27 pouces", new BigDecimal("249.00"), 10));

    public List<Product> findAll() {
        return products;
    }

    public Optional<Product> findById(Long id) {
        return products.stream()
                .filter(p -> p.id().equals(id))
                .findFirst();
    }
}
