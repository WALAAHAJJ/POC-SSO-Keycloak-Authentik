package com.example.paiementservice;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/** Corps de la requête POST /paiements. */
public record PaiementRequest(
        @NotNull Long commandeId,
        @NotNull @DecimalMin("0.01") BigDecimal amount) {
}
