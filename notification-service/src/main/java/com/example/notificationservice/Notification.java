package com.example.notificationservice;

import java.time.Instant;

/** Notification : simple objet de données, sans lien avec une base. */
public record Notification(
        Long id,
        String recipient,
        String subject,
        String message,
        Instant sentAt) {
}
