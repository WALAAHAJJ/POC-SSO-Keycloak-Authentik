package fr.poc.commandeservice;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** Comportement historique : appel HTTP direct vers le notification-service. */
@Component
@ConditionalOnProperty(name = "poc.messaging.broker", havingValue = "http", matchIfMissing = true)
public class HttpCommandeNotifier implements CommandeNotifier {

    private final NotificationClient notificationClient;

    public HttpCommandeNotifier(NotificationClient notificationClient) {
        this.notificationClient = notificationClient;
    }

    @Override
    public void commandeTraitee(CommandeEvent event) {
        boolean paye = "PAYEE".equals(event.status());
        String message = "Commande n°%d : %s x%d (%s)".formatted(
                event.commandeId(), event.productName(), event.quantity(), event.status());
        notificationClient.envoyer(
                event.customerEmail(),
                paye ? "Commande confirmée" : "Paiement refusé",
                message);
    }
}
