package fr.poc.commandeservice;

/**
 * Point d'entrée unique pour prévenir le reste du système qu'une commande a été traitée.
 * L'implémentation active se choisit avec la propriété {@code poc.messaging.broker} :
 * {@code http} (défaut), {@code kafka}, et plus tard {@code rabbitmq}.
 */
public interface CommandeNotifier {

    void commandeTraitee(CommandeEvent event);
}
