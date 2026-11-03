package fr.poc.commandeservice;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/** Corps de la requête POST /commandes. */
public record CommandeRequest(
        @NotNull Long productId,
        @Min(1) int quantity) {
}
