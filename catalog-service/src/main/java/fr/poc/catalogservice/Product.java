package fr.poc.catalogservice;

import java.math.BigDecimal;

/** Produit du catalogue : simple objet de données, sans lien avec une base. */
public record Product(Long id, String name, BigDecimal price, int stock) {
}
