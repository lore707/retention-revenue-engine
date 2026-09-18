# Istruzioni per chi modifica il repository

## Principio

**Git conserva il passato. Il repository descrive il prodotto presente.**

Segui la richiesta dell'utente e la fase di lavoro indicata in `project-docs/START_HERE.md`. Non anticipare fasi successive e non inventare regole commerciali o dati sui prodotti Laifen.

## Prima di modificare

1. Leggi `project-docs/WHERE_TO_CHANGE_CODE.md` e i documenti pertinenti.
2. Cerca se esiste già un file che svolge la funzione richiesta.
3. Controlla i riferimenti alla logica che stai per cambiare.

## Durante la modifica

1. Modifica il punto responsabile della funzione. Crea un file o una cartella solo per una responsabilità nuova e concreta.
2. Non lasciare due implementazioni della stessa funzione. Rimuovi codice sostituito, riferimenti inutilizzati e file rimasti senza scopo.
3. Non creare copie `old`, `backup`, `v2`, `temp` o strutture riservate a funzionalità future.
4. Usa nomi che descrivano ciò che il file o la funzione fa. Separa dati sui prodotti, regole commerciali, stato del cliente e risultati misurati.
5. Mantieni separati i dati identificativi del cliente dai dati usati per l'analisi. Conserva eventuali export reali in `local-data/`, esclusa da Git; non aggiungere dati personali ai file tracciati.

## Prima di concludere

1. Verifica i casi rilevanti, comprese le esclusioni, quando cambi una decisione deterministica.
2. Controlla i riferimenti dopo rimozioni o rinomini e rivedi i file modificati.
3. Aggiorna `project-docs/WHERE_TO_CHANGE_CODE.md` se è cambiato il posto di una funzione; aggiorna `project-docs/PRODUCT_DECISIONS.md` se è stata presa una decisione di prodotto.
4. Riporta cosa è cambiato, cosa è stato rimosso e come hai verificato il risultato.
