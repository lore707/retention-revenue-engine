# Contesto del prodotto

## Problema

Shopify registra clienti, ordini, prodotti, importi e date. Retention Revenue Engine deve aiutare un operatore a capire **chi contattare, quando, cosa proporre e perché**. Deve inoltre consentire di registrare cosa è successo dopo il contatto.

## Flusso della prima versione

Export manuale CSV da Shopify → import → analisi dei clienti → applicazione di regole deterministiche → opportunità spiegate → contatto manuale → registrazione del follow-up → nuovo import → verifica degli ordini successivi → misurazione dei risultati.

## Forma di un'opportunità

Per ogni proposta il sistema dovrà distinguere:

- **Cosa proporre** e quale relazione ha con gli acquisti del cliente.
- **Perché quel prodotto**: proprietà, compatibilità, contenuto della confezione, prodotti già posseduti ed esclusioni.
- **Perché ora**: date e condizioni temporali applicabili.
- **Beneficio per il cliente**: funzione o utilità concreta.
- **Evidenza**: dati e regole che hanno portato alla decisione.
- **Valore nominale** dell'opportunità, distinto dalla revenue effettivamente attribuita.

Il sistema dovrà rendere verificabile anche il motivo per cui una proposta è stata esclusa. I numeri presenti negli esempi discussi (per esempio 28 o 30 giorni) non sono regole approvate.

## Confini attuali

La prima implementazione sarà pensata per Laifen Italia. Le informazioni sui prodotti e le regole commerciali verranno definite in fasi successive. Per ora non sono previsti Shopify API, invii automatici, n8n, infrastrutture cloud complesse, LLM o agenti autonomi.
