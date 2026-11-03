package com.example.notificationservice;

import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Stockage mocké : les notifications envoyées sont gardées en mémoire (une Map),
 * aucune base de données. Elles disparaissent à l'arrêt du service.
 */
@Repository
public class NotificationRepository {

    private final ConcurrentHashMap<Long, Notification> notifications = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong();

    public List<Notification> findAll() {
        return new ArrayList<>(notifications.values());
    }

    /** Attribue un identifiant à la notification puis la range en mémoire. */
    public Notification save(Notification notification) {
        Notification saved = new Notification(
                sequence.incrementAndGet(),
                notification.recipient(),
                notification.subject(),
                notification.message(),
                notification.sentAt());
        notifications.put(saved.id(), saved);
        return saved;
    }
}
