package com.example.notificationservice;

import jakarta.validation.constraints.NotBlank;

/** Corps de la requête POST /notifications. */
public record NotificationRequest(
        @NotBlank String recipient,
        @NotBlank String subject,
        @NotBlank String message) {
}