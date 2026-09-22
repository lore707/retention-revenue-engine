# Retention Revenue Engine: prodotto e decisioni

## Obiettivo

Retention Revenue Engine è un sistema operativo per decidere e monitorare azioni di retention commerciale su clienti già acquisiti o comunque presenti in Shopify e contattabili secondo le regole di marketing applicabili.

Shopify rimane la fonte di riferimento per clienti, ordini, prodotti, varianti e storico degli acquisti. Il software usa quello storico per aiutare un operatore a capire **chi contattare, quando, cosa proporre, perché, quanto vale l'opportunità e cosa è successo dopo il follow-up**.

Il prodotto deve trasformare la storia di acquisto in una **coda operativa di opportunità commerciali spiegabili e monitorabili**:

storia del cliente → stato attuale → opportunità → proposta coerente → follow-up → risultato → valore economico osservato.

Il monitoraggio avviene a livello del singolo cliente; le opportunità e i risultati possono poi essere aggregati per prodotto, strategia e periodo.

## Prima versione

Export CSV manuale da Shopify → import → analisi dei clienti → regole deterministiche → opportunità spiegate → contatto manuale → follow-up registrato → nuovo import → verifica degli ordini successivi → misurazione.

Il primo caso è Laifen Italia. Informazioni sui prodotti e regole commerciali saranno definite nelle rispettive fasi, senza supposizioni. Per ora non sono previsti Shopify API, invii automatici, n8n, infrastrutture cloud complesse, LLM o agenti autonomi.

## Il cuore del prodotto

Il sistema costruisce un'interpretazione commerciale dei fatti disponibili e la usa per creare e monitorare opportunità. Questa capacità si articola in tre responsabilità concettuali:

- **Conoscenza commerciale dei prodotti (knowledge model).** Descrive il significato commerciale del catalogo: contenuto dei precisi SKU, compatibilità, consumabili, accessori, benefici e relazioni tra prodotti. Queste informazioni vengono definite e validate dal business; non si deducono automaticamente dal fatto che due prodotti siano stati acquistati insieme.
- **Stato del cliente (state engine).** Ricostruisce lo stato attuale a partire dallo storico disponibile: acquisti, date, quantità, categorie acquistate, possesso dedotto, consumo stimato e contatti registrati. Viene rivalutato con i nuovi dati e alla data di riferimento della valutazione, secondo i principi della sezione «Come il sistema interpreta e aggiorna le opportunità».
- **Decisione commerciale (decision engine).** Combina conoscenza dei prodotti, regole commerciali, stato del cliente, storico e tempi. Genera proposte candidate, poi applica idoneità al contatto, esclusioni, timing, conflitti e priorità. Restituisce opportunità lavorabili ordinate e motivate, oppure nessuna azione o informazioni insufficienti.

Una relazione tra prodotti descrive una possibilità commerciale. Diventa un'opportunità per un cliente soltanto quando le condizioni della regola sono soddisfatte: compatibilità, dotazione già inclusa, acquisti successivi e tempi possono confermare o escludere la proposta. Le relazioni Laifen e le soglie degli esempi discussi devono ancora essere validate.

### Confine dei dati

Il sistema conserva i dati importati necessari a ricostruire le decisioni e produce informazioni proprie: stato derivato, opportunità, motivi di esclusione, follow-up e risultati attribuiti. Shopify resta autorevole per i fatti provenienti dallo store; il nostro sistema registra le azioni commerciali svolte al suo interno.

I dati in ingresso vengono trasformati in un formato interno coerente per clienti, ordini e righe d'ordine. Le decisioni lavorano su questo formato, senza dipendere dal modo in cui i dati sono arrivati. I CSV sono il canale della V0; eventuali API o webhook futuri potranno alimentare lo stesso modello, mantenendo esplicite completezza e data di aggiornamento dei dati disponibili.

### Dalla decisione al risultato

Il flusso concettuale completo è:

Shopify → import e dati normalizzati → stato del cliente + conoscenza commerciale + regole → proposte candidate → controlli e priorità → opportunità lavorabili → operatore e follow-up → nuovi ordini osservati → attribuzione e misurazione.

La dashboard rende questo processo consultabile e operativo. Il valore del prodotto comprende l'intero percorso, dalla proposta al risultato per ogni cliente.

La V0 lavora sulla retention dei clienti presenti nello store, principalmente dopo l'acquisto. Carrello, checkout e carrello abbandonato sono possibili estensioni da valutare in seguito, con dati e condizioni propri. La separazione tra ingresso dati e decisioni consente di valutarle senza costruire ora quei flussi.

## Focus commerciale

Le strategie possibili comprendono cross-sell, replenishment, maintenance/replacement, acquisto di un secondo prodotto o espansione di categoria e reactivation quando appropriata. La proposta non dipende soltanto dal tempo trascorso dall'ultimo ordine: contano il prodotto e lo SKU acquistati, ciò che era incluso, ciò che il cliente possiede già, le relazioni tra prodotti, le tempistiche e le regole commerciali definite.

Il sistema deve poter concludere che **oggi non esiste alcuna azione commerciale sensata**. Questa è una decisione valida, non un errore da riempire con una proposta generica.

## Formalizzare catalogo, relazioni e attivazione

La strategia parte dalla conoscenza complessiva del catalogo, prosegue prodotto per prodotto e collega ogni proposta alle condizioni del cliente che la rendono sensata. Ogni relazione viene studiata insieme a una bozza della sua regola di attivazione. La disponibilità delle prove necessarie deve poi essere verificata sugli export Shopify prima di considerare la regola implementabile.

### Catalogo e schede dei prodotti

Il censimento identifica categorie, prodotti principali, varianti/SKU, accessori, consumabili, confezioni e bundle. Include i prodotti storici quando compaiono negli acquisti dei clienti, distinguendoli da quelli attualmente proponibili. Ogni informazione riporta fonte, data di verifica e stato: verificata, ipotesi o da chiarire.

La scheda di ciascun prodotto raccoglie identità e SKU, caratteristiche, casi d'uso, benefici, contenuto della confezione, quantità incluse, compatibilità e incompatibilità, consumabili, prezzo e disponibilità rilevati. Se dotazione o compatibilità sono cambiate nel tempo, occorre distinguere le versioni pertinenti agli acquisti storici. Un dato sconosciuto resta esplicitamente tale.

### Tipi di relazione commerciale

La tassonomia richiesta comprende otto tipi di opportunità. Le descrizioni seguenti sono convenzioni di lavoro da validare nella mappatura del catalogo; non assegnano ancora relazioni a prodotti Laifen. Comprendono anche riacquisto, sostituzione e upgrade, oltre al cross-sell.

| Tipo | Significato operativo proposto |
| --- | --- |
| `ACCESSORY_ATTACH` | Aggiungere un accessorio compatibile che offre un beneficio al prodotto acquistato. |
| `ACCESSORY_COMPLETION` | Completare una dotazione utile definita dal business con un accessorio compatibile mancante, verificando quanto era incluso nello SKU e gli acquisti successivi. |
| `USE_CASE_COMPLEMENT` | Aggiungere un prodotto che completa un caso d'uso o una routine del cliente. |
| `CATEGORY_EXPANSION` | Introdurre una categoria senza acquisti osservati per quel cliente, con un beneficio motivato. |
| `REPLENISHMENT` | Riacquistare un consumabile sulla base delle quantità disponibili stimate e di ipotesi d'uso esplicite. |
| `UPSELL` | Proporre un prodotto di livello superiore per un miglioramento concreto rispetto a quello acquistato. |
| `REPLACEMENT` | Sostituire un prodotto o componente sulla base di un bisogno supportato da evidenze o da una regola approvata. |
| `SECOND_UNIT` | Proporre un'unità aggiuntiva per un'esigenza distinta, senza presumere che l'unità precedente debba essere sostituita. |

`ACCESSORY_COMPLETION` è un caso più specifico dell'aggiunta di un accessorio: prima dell'attivazione va stabilito il confine rispetto a `ACCESSORY_ATTACH`. Anche altri tipi possono sovrapporsi. La stessa proposta non deve diventare due opportunità conteggiate separatamente soltanto perché soddisfa più etichette; classificazione primaria e gestione dei conflitti saranno esplicite. La reactivation descrive il contesto di ricontatto del cliente e può accompagnare una relazione, senza sostituire la motivazione del prodotto proposto.

### Dalla relazione alla regola del cliente

Per ogni relazione si documentano prodotto/SKU di partenza e prodotto proposto, direzione della proposta, tipo, beneficio, prove di compatibilità ed eventuali esclusioni. Una relazione non è automaticamente reciproca. Una stessa relazione può richiedere condizioni diverse per clienti con storie diverse.

La regola associata deve specificare:

- **Identità e stato:** identificativo, versione, fonti, stato di bozza o approvata e decisioni ancora aperte.
- **Prerequisiti:** acquisti e SKU interessati, quantità, dotazione inclusa, stato del cliente e dati necessari a provarli.
- **Evento e timing:** che cosa fa rivalutare la proposta, da quale data si conta, quando si apre la finestra e quando termina; soglie da approvare, mai ricavate arbitrariamente.
- **Esclusioni e rinvii:** acquisti successivi, resi o annullamenti, compatibilità, disponibilità del prodotto proposto, contattabilità e contatti precedenti, secondo criteri da definire per la regola.
- **Dati mancanti:** quali informazioni impediscono la decisione e quali stime sono consentite, con ipotesi visibili.
- **Conflitti e priorità:** proposte che possono coesistere, proposte alternative, precedenze e condizioni di riattivazione.
- **Output ed evidenza:** cosa proporre, perché quel prodotto, perché ora, beneficio, valore nominale e dati che sostengono la decisione.
- **Verifica e misurazione:** casi sintetici ammessi, esclusi e con dati insufficienti; risultato osservabile e criteri di attribuzione da definire prima del relativo calcolo.

Il controllo di nuovi ordini e follow-up aggiorna la validità della proposta conservandone la storia. Un import ripetuto o una rivalutazione della stessa situazione non deve moltiplicare la medesima opportunità; il confine tra aggiornamento e nuova occasione commerciale va esplicitato per le regole ricorrenti.

Una regola è pronta per lo sviluppo quando relazione e condizioni sono approvate, i dati richiesti sono disponibili o le loro assenze hanno un trattamento definito, e gli esempi hanno risultati attesi espliciti. Le regole incomplete restano bozze. I dati storici aiutano a valutare e correggere queste ipotesi secondo il processo di approvazione descritto sotto.

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

5. **Usare i risultati per migliorare regole esplicite.** La conoscenza del prodotto stabilisce quali proposte possono avere senso; lo storico mostra quali acquisti sono stati osservati, con quale frequenza, dopo quanto tempo e per quali clienti. Queste evidenze e gli esiti dei follow-up possono suggerire nuove relazioni o modifiche a strategie e tempistiche. Nella V0, queste modifiche vengono valutate e approvate esplicitamente, mantenendo traccia della versione delle regole. Il motore non modifica autonomamente la propria logica commerciale.

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

La struttura e i principi del repository sono definiti. Il percorso concordato parte ora dal catalogo; ogni fase produrrà un risultato verificabile prima della successiva:

1. **Censimento generale del catalogo:** mappa dei prodotti, categorie, SKU, accessori, consumabili e bundle; fonti e lacune esplicite.
2. **Analisi prodotto per prodotto:** schede con caratteristiche, benefici, dotazione e compatibilità verificate.
3. **Relazioni e attivazioni in bozza:** mappa direzionale tra prodotti con gli otto tipi concordati e, per ciascuna relazione, condizioni del cliente, tempi e dati richiesti. L'analisi delle relazioni può procedere mentre si completano le schede.
4. **Confronto con gli export reali:** verificare i campi disponibili, il collegamento agli SKU, la ricostruzione dello storico e la separazione delle identità; definire il modello dati e rivedere le regole non supportate dai dati.
5. **Approvazione delle prime regole:** definire soglie, esclusioni, conflitti, priorità e casi attesi per un primo insieme circoscritto e completo.
6. **Prima implementazione verificabile:** import CSV, stato del cliente e prime regole approvate fino a opportunità spiegate; poi estendere ai successivi casi approvati con lo stesso metodo.
7. **Follow-up e misurazione:** registrazione delle azioni, nuovi import, risultati osservati e attribuzione secondo criteri espliciti.
8. **Dashboard:** costruire la vista operativa sui dati e risultati già verificati.

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
