# Retention Revenue Engine: prodotto e decisioni

## Obiettivo

Retention Revenue Engine è un sistema operativo per decidere e monitorare azioni di retention commerciale su clienti già acquisiti o comunque presenti in Shopify e contattabili secondo le regole di marketing applicabili.

Shopify rimane la fonte di riferimento per clienti, ordini e prodotti. Il software usa quello storico per aiutare un operatore a capire **chi contattare, quando, cosa proporre, perché, quanto vale l'opportunità e cosa è successo dopo il follow-up**.

Il prodotto deve trasformare la storia di acquisto in una **coda operativa di opportunità commerciali spiegabili e monitorabili**:

storia del cliente → stato attuale → opportunità → proposta coerente → follow-up → risultato → valore economico osservato.

Il monitoraggio avviene a livello del singolo cliente; le opportunità e i risultati possono poi essere aggregati per prodotto, strategia e periodo.

## Prima versione

Export CSV manuale da Shopify → import → analisi dei clienti → regole deterministiche → opportunità spiegate → contatto manuale → follow-up registrato → nuovo import → verifica degli ordini successivi → misurazione.

Il primo caso è Laifen Italia. Informazioni sui prodotti e regole commerciali saranno definite nelle rispettive fasi, senza supposizioni. Per ora non sono previsti Shopify API, invii automatici, n8n, infrastrutture cloud complesse, LLM o agenti autonomi.

## Focus commerciale

Le strategie possibili comprendono cross-sell, replenishment, maintenance/replacement, acquisto di un secondo prodotto o espansione di categoria e reactivation quando appropriata. La proposta non dipende soltanto dal tempo trascorso dall'ultimo ordine: contano il prodotto e lo SKU acquistati, ciò che era incluso, ciò che il cliente possiede già, le relazioni tra prodotti, le tempistiche e le regole commerciali definite.

Il sistema deve poter concludere che **oggi non esiste alcuna azione commerciale sensata**. Questa è una decisione valida, non un errore da riempire con una proposta generica.

## Cosa deve spiegare un'opportunità

- **Cosa proporre:** il prodotto e la relazione con quanto già acquistato.
- **Perché quel prodotto:** caratteristiche, compatibilità, contenuto del preciso SKU, possesso ed esclusioni.
- **Perché ora:** date e condizioni temporali applicabili.
- **Beneficio per il cliente:** funzione o utilità concreta.
- **Evidenza:** dati e regole che hanno prodotto la decisione.
- **Valore nominale:** potenziale della proposta, distinto dalla revenue attribuita.

Il sistema deve rendere verificabile anche il motivo di un'esclusione. I numeri usati negli esempi, come 28 o 30 giorni, non sono regole approvate. A parità di dati e regole, la decisione deve essere la stessa.

## Monitoraggio delle opportunità

Un cliente può avere una o più opportunità nel tempo o contemporaneamente, purché non confliggano tra loro secondo le regole definite. Ognuna è collegata a una proposta e ai dati che la giustificano. Per ciascuna bisogna poter ricostruire se è ancora aperta, se è stata lavorata, quale follow-up è stato effettuato, se si è osservato il risultato definito e quale importo è stato attribuito.

Esempio puramente illustrativo, senza validare la relazione commerciale citata: `CUST_00123` possiede SE Lite; viene valutata una proposta per il Diffusore SE Lite con valore nominale di €24,99. Il sistema registra la motivazione e lo stato dell'opportunità; dopo il contatto, un nuovo import permette di verificare gli ordini successivi secondo regole di attribuzione ancora da definire.

Le viste aggregate dovranno poter rispondere a domande concrete: quante opportunità sono state generate, quante restano aperte, quante sono state lavorate o non lavorate, quante hanno convertito, quale revenue è stata attribuita e quali prodotti, strategie e tempi hanno prodotto i risultati osservati.

## Come il sistema interpreta e aggiorna le opportunità

1. **Distinguere fatti, deduzioni e stime.** Un acquisto registrato è un fatto. Il possesso attuale di un prodotto e il possibile esaurimento di un consumabile sono deduzioni o stime. Le spiegazioni devono dichiarare su quali informazioni e ipotesi si basano. L'assenza di un acquisto nello storico disponibile non dimostra che il cliente non possieda quel prodotto.

2. **Conservare le prove della decisione.** Ogni opportunità deve essere riconducibile ai dati importati, alle informazioni di prodotto e alla versione delle regole utilizzate. La valutazione deve avere una data di riferimento esplicita, così possiamo ricostruire perché una proposta era sensata in quel momento.

3. **Aggiornare lo stato senza perdere la storia.** Nuovi acquisti, follow-up e trascorrere del tempo possono attivare, posticipare o rendere non più valide le opportunità. Il sistema deve conservare la storia delle opportunità già generate e delle azioni effettuate, per poter misurare i risultati.

4. **Distinguere nessuna azione da informazioni insufficienti.** Il sistema deve poter indicare sia «non esiste un'opportunità valida» sia «non ci sono dati sufficienti per decidere». Sono esiti diversi e devono essere comprensibili all'operatore.

5. **Usare i risultati per migliorare regole esplicite.** Lo storico e gli esiti dei follow-up possono suggerire modifiche a strategie e tempistiche. Nella V0, queste modifiche vengono valutate e approvate esplicitamente, mantenendo traccia della versione delle regole. Il motore non modifica autonomamente la propria logica commerciale.

## Misure economiche

- **Opportunity Value:** valore nominale o stimato della proposta; non è una vendita già realizzata.
- **Unworked Opportunity:** opportunità per cui non è stato registrato un follow-up. Il suo valore non è automaticamente revenue persa.
- **Expired Opportunity:** opportunità non più valida secondo criteri da definire. È distinta da un'opportunità lavorata che non ha convertito.
- **Attributed Revenue:** revenue osservata dopo un follow-up e collegata a esso secondo una finestra e un criterio espliciti. Attribuzione non equivale a prova di causalità.
- **Follow-up Conversion Rate:** quota delle opportunità lavorate che soddisfa il risultato di conversione definito. Denominatore, finestra temporale e trattamento dei casi ancora aperti vanno stabiliti prima del calcolo.

Queste misure devono consentire di distinguere valore disponibile, attività svolta e risultati osservati, fino alla singola opportunità. Nessun valore di opportunità non lavorata o scaduta va presentato come denaro certamente perso.

## Dati e privacy

La prima versione userà export CSV manuali. Campi e regole di import saranno definiti dopo aver esaminato il formato effettivo.

Le analisi devono poter usare soprattutto ID pseudonimi, per esempio `CUST_000123`. Nome, email e telefono servono all'operatore per il contatto, ma non per calcolare l'opportunità. Il collegamento concreto tra identità e analisi sarà deciso con il modello dati. Eventuali export reali vanno in `local-data/`, esclusa da Git; non inserire dati personali, credenziali o export reali nei file tracciati.

Opportunità teorica, contatto registrato, ordine successivo e revenue attribuita sono fatti distinti. Il criterio di attribuzione va definito prima di implementare il relativo calcolo.

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
- Il prodotto monitora un portafoglio di opportunità a livello di singolo cliente, dalla generazione al risultato osservato.
- Il sistema può decidere che per un cliente non esiste un'azione sensata al momento.

## Da definire nelle fasi pertinenti

- Campi e varianti degli export reali.
- Prodotti, contenuto degli SKU e relazioni commerciali Laifen.
- Soglie temporali, esclusioni, priorità e significato della confidenza.
- Criterio di attribuzione degli ordini ai follow-up.
- Definizioni operative degli stati dell'opportunità, della scadenza e del conversion rate.
- Tecnologia di implementazione e conservazione dei dati.
