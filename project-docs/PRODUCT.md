# Retention Revenue Engine: prodotto e decisioni

## Obiettivo

Shopify registra clienti, ordini, prodotti, importi e date. Il software deve aiutare un operatore a decidere **chi contattare, quando, cosa proporre e perché**, poi registrare il follow-up e misurare gli eventuali risultati.

## Prima versione

Export CSV manuale da Shopify → import → analisi dei clienti → regole deterministiche → opportunità spiegate → contatto manuale → follow-up registrato → nuovo import → verifica degli ordini successivi → misurazione.

Il primo caso è Laifen Italia. Informazioni sui prodotti e regole commerciali saranno definite nelle rispettive fasi, senza supposizioni. Per ora non sono previsti Shopify API, invii automatici, n8n, infrastrutture cloud complesse, LLM o agenti autonomi.

## Cosa deve spiegare un'opportunità

- **Cosa proporre:** il prodotto e la relazione con quanto già acquistato.
- **Perché quel prodotto:** caratteristiche, compatibilità, contenuto del preciso SKU, possesso ed esclusioni.
- **Perché ora:** date e condizioni temporali applicabili.
- **Beneficio per il cliente:** funzione o utilità concreta.
- **Evidenza:** dati e regole che hanno prodotto la decisione.
- **Valore nominale:** potenziale della proposta, distinto dalla revenue attribuita.

Il sistema deve rendere verificabile anche il motivo di un'esclusione. I numeri usati negli esempi, come 28 o 30 giorni, non sono regole approvate. A parità di dati e regole, la decisione deve essere la stessa.

## Dati e privacy

La prima versione userà export CSV manuali. Campi e regole di import saranno definiti dopo aver esaminato il formato effettivo.

Le analisi devono poter usare soprattutto ID pseudonimi, per esempio `CUST_000123`. Nome, email e telefono servono all'operatore per il contatto, ma non per calcolare l'opportunità. Il collegamento concreto tra identità e analisi sarà deciso con il modello dati. Eventuali export reali vanno in `local-data/`, esclusa da Git; non inserire dati personali, credenziali o export reali nei file tracciati.

Opportunità teorica, contatto registrato, ordine successivo e revenue attribuita sono fatti distinti. Un ordine dopo un contatto non prova da solo che il contatto lo abbia causato. Il criterio di attribuzione va definito prima di implementare il calcolo.

## Percorso e stato

La fase 1, struttura e principi del repository, è completata. Le fasi successive saranno specificate separatamente:

1. Modello dati e import CSV Shopify.
2. Knowledge base dei prodotti Laifen.
3. Regole commerciali deterministiche.
4. Stato del cliente.
5. Idoneità e generazione delle opportunità.
6. Insight e spiegazioni.
7. Follow-up e misurazione economica.
8. Dashboard, dopo aver chiarito quali decisioni e risultati mostrare.

Questo elenco non autorizza a costruire in anticipo le fasi successive.

## Decisioni prese

- Il flusso iniziale usa CSV manuali e contatti manuali.
- Le decisioni commerciali sono deterministiche; un eventuale LLM futuro non decide l'idoneità delle opportunità.
- Il repository contiene la versione corrente; Git conserva la storia.
- Il valore nominale di una proposta non è revenue generata.

## Da definire nelle fasi pertinenti

- Campi e varianti degli export reali.
- Prodotti, contenuto degli SKU e relazioni commerciali Laifen.
- Soglie temporali, esclusioni, priorità e significato della confidenza.
- Criterio di attribuzione degli ordini ai follow-up.
- Tecnologia di implementazione e conservazione dei dati.
