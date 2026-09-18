---
name: repository-change
description: Usa questa skill per modificare codice o struttura del Retention Revenue Engine. Non usarla per sola discussione, pianificazione o analisi senza modifiche al repository.
---

# Modificare il repository

Segui `AGENTS.md` come fonte delle regole vincolanti; questo workflow indica l'ordine operativo senza sostituirle.

## Prima

1. Leggi `AGENTS.md` e `project-docs/ARCHITECTURE.md`.
2. Individua il file responsabile della funzione richiesta, cerca implementazioni sovrapposte e leggi i test correlati.
3. Se il task riguarda decisioni di prodotto, dati o regole commerciali, consulta `project-docs/PRODUCT.md`. Non inventare decisioni mancanti.

## Durante

1. Modifica il responsabile esistente; crea un file solo per una responsabilità realmente nuova.
2. Mantieni la modifica nel perimetro richiesto e rimuovi la logica che viene sostituita.

## Dopo

1. Aggiorna i test pertinenti ed esegui le verifiche disponibili.
2. Controlla duplicati, riferimenti obsoleti e file senza scopo.
3. Aggiorna `project-docs/ARCHITECTURE.md` solo se è cambiata la mappa delle responsabilità.
4. Riporta cosa hai cambiato, rimosso e verificato, e le decisioni ancora aperte.
