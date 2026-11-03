package fr.poc.commandeservice;

import java.math.BigDecimal;

/**
 * Représentation locale d'un produit du catalogue.
 * On ne partage pas la classe Product du catalog-service : chaque service garde son propre modèle.
 */
public record ProductDto(Long id, String name, BigDecimal price, int stock) {
}

