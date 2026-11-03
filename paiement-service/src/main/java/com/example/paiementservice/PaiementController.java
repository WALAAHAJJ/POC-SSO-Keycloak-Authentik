package com.example.paiementservice;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
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
@RequestMapping("/paiements")
public class PaiementController {

    /** Règle mockée : au-delà de ce montant, le paiement est refusé. */
    private static final BigDecimal PLAFOND = new BigDecimal("5000.00");

    private final PaiementRepository repository;

    public PaiementController(PaiementRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public List<Paiement> findAll() {
        return repository.findAll();
    }

    @GetMapping("/{id}")
    public Paiement findById(@PathVariable Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Paiement " + id + " introuvable"));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Paiement create(@Valid @RequestBody PaiementRequest request) {
        PaiementStatus status = request.amount().compareTo(PLAFOND) > 0
                ? PaiementStatus.REFUSE
                : PaiementStatus.ACCEPTE;

        // id = null : il est attribué par le repository
        Paiement payment = new Paiement(null, request.commandeId(), request.amount(),
                status, Instant.now());
        return repository.save(payment);
    }
}