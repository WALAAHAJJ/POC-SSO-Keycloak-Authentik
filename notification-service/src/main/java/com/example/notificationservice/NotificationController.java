package com.example.notificationservice;

import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/notifications")
public class NotificationController {

    private static final Logger log = LoggerFactory.getLogger(NotificationController.class);

    private final NotificationRepository repository;

    public NotificationController(NotificationRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public List<Notification> findAll() {
        return repository.findAll();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Notification send(@Valid @RequestBody NotificationRequest request) {
        // Envoi mocké : on se contente de tracer dans les logs (pas de vrai mail/SMS)
        log.info("Notification pour {} : [{}] {}",
                request.recipient(), request.subject(), request.message());

        // id = null : il est attribué par le repository
        Notification notification = new Notification(null, request.recipient(),
                request.subject(), request.message(), Instant.now());
        return repository.save(notification);
    }
}
