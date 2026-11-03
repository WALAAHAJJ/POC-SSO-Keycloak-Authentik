package fr.poc.commandeservice;

/** Corps envoyé au notification-service (POST /notifications). */
public record NotificationRequestDto(String recipient, String subject, String message) {
}