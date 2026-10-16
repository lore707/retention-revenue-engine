# Audit della dashboard — comportamento corrente

Data: 15 ottobre 2026. Audit descrittivo, senza modifiche al software. Regole aggiornate v28, catalogo v38, promozioni v3. La documentazione è una fotografia del codice corrente, non una nuova fonte di regole operative.

Documenti collegati: [regole](REGOLE_COMMERCIALI.md), [percorsi](PERCORSI_RIACQUISTO.md), [criticità](CRITICITA_RILEVATE.md), [matrice Shopify](REGOLE_DA_VALIDARE_SHOPIFY.csv).

## Metodo e confini

Il punto di partenza sono le schermate HTML e i loro gestori JavaScript. Il comportamento commerciale effettivo è ricostruito da `src/customer_profiles.py`, `src/engine.py`, catalogo e regole. I percorsi dei file in questo audit sono relativi alla radice del repository. Non sono stati importati nuovi dati, registrati contatti o modificati eventi reali.

Il precedente riscontro API del 15 ottobre, nello stesso audit conversazionale, ha restituito 1.121 profili locali, 715 corrispondenze per completamenti e 955 per espansione. Sono conteggi operativi di quello snapshot, non risultati di conversione Shopify e non una costante del prodotto. Le verifiche su casi sintetici sono distinte dalle evidenze storiche. Nessuna nuova verifica visiva in browser: il controllo di fedeltà è sul contratto dati, sul codice e sui test DOM.

## 1. Superficie realmente disponibile

| Schermata/azione | Frontend | Backend | Stato effettivo |
| --- | --- | --- | --- |
| Overview `/` | `frontend/overview.html`, `overview.js` | `GET /api/overview`, `overview_summary` | Operativa |
| Retention `/retention` | `retention.html`, `retention.js` | `GET /api/retention`, `retention_summary`, `filter_retention` | Operativa |
| Regole `/rules` | `rules.html`, `rules.js` | `GET /api/rules`, `rules_summary` | Consultazione; nessuna modifica delle regole |
| Scheda cliente | `ui.js`: `openPlan`, `customerProposal`, `nextAction`, `customerHistory` | `GET /api/plan`, `plan_detail` | Condivisa fra Overview e Retention |
| Salva contatto/esito | `ui.js`: `eventForm` | `POST /api/events`, `record_event` | Registrazione manuale; non invia email |
| Carica CSV | `overview.js`, dialog di import | `POST /api/import`, `sanitize_export`, `import_into_store` | Solo dati locali, disabilitato in demo |
| Follow-up e Risultati nella sidebar | Pulsanti `disabled` nei tre HTML | Nessuna pagina dedicata collegata | Non disponibili come sezioni autonome; esiti e follow-up si gestiscono nella scheda |

Routing, modalità demo, data di valutazione e controlli HTTP: `src/web.py::make_handler`. La data è quella locale Europe/Rome, salvo `--as-of` esplicito. Il frontend mostra la data ricevuta.

## 2. Dati che alimentano la dashboard

`src/shopify_orders.py::import_orders` normalizza ordini e righe per SKU; `merge_orders` e `Store` persistono acquisti e recapiti separati. L'identità locale collega ordini con la stessa email normalizzata: non è una persona Shopify verificata. Ordini senza email restano separati, non diventano righe cliente.

`engine_snapshot` passa al motore gli acquisti fino alla data di valutazione e gli eventi. Il consenso email deriva dall'insieme dei segnali degli ordini osservati: tutti yes → subscribed; tutti no → unsubscribed; mancanti o discordanti → unknown. Non viene interrogato Shopify in tempo reale. `review_cases` rileva validità incerta, SKU sconosciuti e consenso incerto; `evaluate_day` e `plan_detail` impediscono il contatto operativo finché persistono.

L'attivazione dello storico è gestita da `activate_history`, non da un pulsante della dashboard. Prima dell'attivazione nessun cliente è lavorabile. L'attivazione non dimostra completezza dello storico: le chiamate allo snapshot usano `history_complete=True` per lo storico disponibile, mentre il prodotto dichiara `history_scope=imported_orders_only`.

Un nuovo import aggiorna gli ordini senza cancellare eventi o attivazione. L'ultimo export elaborato prevale per lo stesso ordine; manca un campo Updated at per decidere automaticamente quale copia sia più recente. Date ordini in Europe/Rome; ordini annullati/righe rese vengono esclusi dalle opportunità; rimborsi non attribuibili alla riga e ripetizioni ambigue dello stesso SKU portano a revisione.

## 3. Overview: KPI e grafico

Responsabili: `overview.js::loadOverview`, `renderChart`, `renderRows`; `customer_profiles.py::overview_summary`, `retention_summary`, `revenue_summary`.

| Indicatore | Calcolo effettivo | Interpretazione e limite |
| --- | --- | --- |
| Clienti da contattare | Numero di righe `sections.ready` | Un solo piano lavorabile per cliente; servono storico attivo, nessuna revisione, consenso e timing validi |
| Valore potenziale | Somma `value_minor` delle proposte principali ready | Valore nominale, non somma delle alternative, non probabilità, margine o ricavo atteso |
| Contatti registrati | Eventi di tipo contact fino alla data valutata | Numero di eventi, non clienti distinti, email consegnate o aperture |
| Ricavi attribuiti | Somma degli acquisti verificati manualmente con ultima correzione | Non attribuzione automatica degli ordini importati; non incremento causale |

Il selettore 30d/90d/6m/12m modifica **solo il grafico**, non KPI, categorie o coda. 30/90 giorni includono oggi; 6/12 mesi usano un inizio mobile calcolato sul giorno del mese (con clamp per mesi corti), più un giorno. I dati mensili possono comprendere mesi di bordo parziali. Il grafico usa `purchase_date`, non data di registrazione dell'esito. I giorni senza vendite hanno zero; 6m/12m aggregano per mese. La scala minima grafica non costituisce un ricavo dimostrativo.

`period` è conservato nell'URL; un valore non ammesso torna a 30d. Il popup condiviso `ui.js::createFloatingSelect` non modifica il calcolo economico. La tabella iniziale mostra quattro clienti, poi tutti con “Vedi tutti”. Il bottone Apri apre il piano ricevuto dal backend.

## 4. Tre categorie commerciali: partizione dei clienti

Responsabili: `engine.py::commercial_category`; `customer_profiles.py::_operational_row`, `_operational_views`.

| Categoria cliente | Criterio esatto |
| --- | --- |
| Opportunità mirate | Piano principale lavorabile con almeno una proposta primaria/secondaria di tipo ACCESSORY_COMPLETION o REPLENISHMENT |
| Opportunità da testare | Piano principale lavorabile, nessuna mirata fra le proposte considerate; tipi USE_CASE_COMPLEMENT, CATEGORY_EXPANSION, REPLACEMENT |
| Nessuna azione immediata | Nessun piano lavorabile: futuro, coda, distanza fra contatti, conversazione, consenso, revisione, storico inattivo oppure nessuna proposta |

Ogni cliente osservato appartiene a una sola categoria. “Nessuna azione” non equivale a cliente senza opportunità. Un cliente può avere una proposta mirata futura ed essere oggi da testare o senza azione. I segnali del profilo non cambiano la categoria. La categoria cliente può dipendere anche da una secondaria del piano, non soltanto dall'etichetta della primaria.

Le card Overview sono link a Retention con `view=targeted|test|none`; non sono viste che rivalutano autonomamente le regole.

## 5. Filtri Retention e corrispondenza effettiva

`retention.js::applyRetentionFilters`, `loadRetention` inviano categoria, stato, strategia, profilo e ricerca a `/api/retention`. `filter_retention` applica AND tra filtri. Non c'è una seconda selezione commerciale nel browser.

| Filtro | Semantica backend | Dettaglio frontend |
| --- | --- | --- |
| Categoria | Categoria esclusiva attuale del cliente | Singola; conteggi globali dal backend, prima degli altri filtri |
| Stato | Almeno un piano con lo stato richiesto | Singolo; non è lo stato generale del cliente |
| Strategia | Almeno un'opportunità della strategia fra i piani consultabili | Singola; include primaria, secondarie, altre disponibili e storico rappresentato |
| Stato + strategia | Devono corrispondere sullo stesso piano | Non basta stato in un piano e strategia in un altro |
| Profilo | Presenza del segnale richiesto | Singolo, non multiselezione; segnali fra loro sovrapponibili |
| Ricerca | Sottostringa case-insensitive in ID cliente, numero ordine fonte, prodotto fonte e proposte dei piani corrispondenti | Non cerca l'email, tutti gli ordini storici o tutti gli SKU; 350 ms di debounce |

Profili: primo acquisto = esattamente un ordine interamente valido; ricorrente = almeno due; alta attività recente = almeno tre ordini interamente validi negli ultimi 90 giorni inclusivi; multicategoria = almeno due categorie principali da righe valide. Hair dryer e hair styler confluiscono in cura capelli; spazzolini in igiene orale; rasoi in rasatura. Accessori non creano da soli una categoria principale. Possibile B2B e alto valore storico restano non valutabili, con opzioni disabilitate. Fonte: `customer_signals`, soglie in `rules.json::customer_signals`.

I quattro selettori hanno ricerca locale delle opzioni, tastiera, Escape/Enter, focus, checkmark e chip rimovibili. Il numero di clienti è mostrato solo per categorie quando fornito; non sono inventati conteggi per strategie/stati/profili. URL: `view`, `state`, `strategy`, `profile`, `search`, con lettura del vecchio `category`; reset mantiene parametri estranei e hash. Paginazione client-side a 25 righe; ogni filtro riparte dalla prima pagina. La risposta conserva KPI globali e righe filtrate separate.

### Ambiguità confermata: filtro strategia e proposta visibile

`filter_retention` aggiunge `matching_plans` senza sostituire la raccomandazione principale. `renderRetentionRows` mostra `item.proposal` e `item.strategy_label` globali; soltanto “Corrispondenze / motivo” spiega il match. Anche Apri continua ad aprire il piano globale. Il pannello “piani consultabili” permette invece di ispezionare quello corrispondente.

Nel riscontro locale: completamenti 715; espansione 955; intersezione 715; primi 25 identici. Con stato open: 476 e 17. Questo non dimostra un filtro guasto: mostra che l'interfaccia rende poco evidente l'ambito della ricerca. Nessun numero di questa prova deve essere usato come conversione storica.

## 6. Proposta principale, alternative e stati

Il motore `evaluate_portfolio` restituisce una primaria cliente, una coda e opportunità escluse/soppresse. `plan_detail` espone primaria e secondarie del piano consultato; `ui.js` le mostra con motivazione, immagini, valore e varianti. “Alternative compatibili” è un titolo generico usato anche per espansioni: non significa sempre compatibilità fisica fra dispositivi.

La presentazione dei motivi deriva da `_proposal_presentation`: per completamenti confermati mostra compatibile/non incluso; per altri tipi beneficio e natura della relazione; timing maturo/futuro deriva dalla data di idoneità. Timing maturo non equivale a contatto autorizzato. Verifiche tecniche e controlli operatore sono espandibili. Le varianti sono consultabili, non una selezione SKU salvata nel contatto.

| Stato nel filtro | Derivazione in `_operational_row` | Conseguenza |
| --- | --- | --- |
| open | Piano non contattato e lavorabile | Primo contatto disponibile |
| in_progress | Piano corrente già contattato, salvo chiusura tracciata | Può attendere, richiedere risposta manuale oppure consentire il secondo contatto |
| suspended | Piano corrente non contattato e non lavorabile | Riunisce futuro, coda e altri blocchi; non solo sospensione manuale |
| closed | Piano tracciato concluso | Storico; esiti ancora consultabili/registrabili con un contatto precedente |

“Futuro” non è un quinto valore del filtro: è una motivazione/data. Gli stati del portafoglio (`deferred`, `waiting_for_plan`, `operator_response`, `blocked_consent`, `contact_review`, `queued`) sono più dettagliati e non coincidono uno-a-uno con questi quattro stati UI.

I piani non contattati scomparsi per esclusione non diventano automaticamente uno storico closed. La scheda espone gli acquisti e gli eventi, ma non un registro completo di ogni valutazione/esclusione passata. `explain_order` espone diagnostica ulteriore tramite API/CLI, non una sezione esaustiva della scheda attuale.

## 7. Composizione e priorità: tre responsabilità distinte

Flusso phon aggiornato: accessori a 15 giorni; AutoCurl a 45 in una mail dedicata con i propri prerequisiti accessori; Wave Pro e rasoi insieme a 75 in un piano separato, con esclusioni indipendenti. Mini rimane stagionale.

1. **Regola prodotto**: `_evaluate`, `_evaluate_replenishment`, `_evaluate_replacement` decidono se una singola relazione ha fonte, destinazione non esclusa e timing.
2. **Composizione**: `evaluate_portfolio` raggruppa per ordine fonte (ordine del ciclo per ricambi), percorso commerciale e data di maturazione. La stessa data da sola non basta. `wait_for_rules` introduce dipendenze sullo stesso ordine.
3. **Priorità**: lo stesso portafoglio sceglie primaria interna e piano cliente; le liste dashboard ordinano successivamente i clienti, senza scegliere un altro piano.

Primaria interna: interesse esplicito per un prodotto se disponibile; altrimenti primaria già contattata ancora candidata; altrimenti mirata prima di test, promozione, valore nominale decrescente, plan_rank decrescente, rule_id. Gli SKU rappresentativi sono scelti fra opzioni in promozione oppure disponibili, prendendo il prezzo più basso e SKU come spareggio. L'ordine delle opzioni può suggerire una preferenza diversa dalla variante rappresentativa.

Piano cliente: prima conversazioni in gestione, poi piani già contattati aperti (più vecchio primo contatto), poi nuovi maturi. Fra maturi: mirata, promozione, finestra stagionale, valore, maturazione più vecchia, rango, acquisto fonte più vecchio, rule_id. Se non ci sono maturi, primo futuro per prossima data, rango, fonte, rule_id. I piani `waiting_for_plan` restano in coda. Consenso e intervallo globale possono impedire il contatto anche al piano selezionato.

Ordine delle righe Retention: categoria targeted/test/none, valore della primaria decrescente, ID cliente. Ordine ready Overview: mirata prima, valore decrescente, ID cliente e plan_key. Non è una graduatoria probabilistica e non replica tutta la priorità interna (per esempio la promozione non è un ordinatore autonomo delle righe).

## 8. Contatti, follow-up, esiti

`nextAction` mostra il modulo solo se il backend fornisce `event_templates.contact`. L'operatore invia l'email fuori dal sistema, conferma invio/recapito/consenso/disponibilità/prezzi e salva data e note. Il contatto viene rivalutato dal backend per quella data: stesso cliente, piano, primaria e lista di opportunità, canale email, storico attivo e nessun blocco. Non basta aggirare un bottone disabilitato. La conferma dell'operatore è una checkbox UI, non una prova esterna dell'invio.

Massimo due contatti per piano; secondo dopo almeno 15 giorni; almeno 15 giorni tra contatti di qualsiasi piano dello stesso cliente. Non sono contate newsletter o comunicazioni esterne non registrate. Il secondo contatto Mini deve ricadere nella finestra stagionale, eventualmente nell'anno successivo; non si azzerano i tentativi a ogni stagione.

| Evento | Effetto attuale |
| --- | --- |
| contact | Consuma un tentativo condiviso dal piano; secondo tentativo chiude per esaurimento appena registrato |
| reply | Sospende il normale follow-up, richiede gestione operatore |
| product_interest | Focalizza il prodotto nel piano, senza azzerare i tentativi; risposta da gestire |
| product_rejection | Esclude quel prodotto, mantiene gli altri candidati; risposta da gestire |
| plan_rejection / rejection | Chiude il piano |
| conversation_closed | Segna risposta gestita e rivaluta con gli stessi tentativi; non equivale a rifiuto del piano |
| verified_purchase | Chiude il piano e alimenta revenue manuale |
| revenue_correction | Sostituisce l'importo attribuito della vendita; non aggiunge una seconda vendita |

`_contact_plan_closure`: precedenza acquisto verificato, rifiuto piano, due tentativi, poi almeno un risultato presentato excluded/stopped. Quindi un acquisto rilevato negli import può chiudere commercialmente il piano anche senza ricavo registrato. Altre proposte del piano chiuso vengono soppresse. La chiusura non crea nuove sequenze per le secondarie; un acquisto di ricambio apre il suo nuovo ciclo. La derivazione usa il catalogo/regole correnti, non snapshot immutabili delle valutazioni.

Gli esiti richiedono un contatto precedente dello stesso piano; gli esiti prodotto un prodotto nelle proposte ricostruite. I ricambi richiedono riferimento al ciclo. L'ID evento garantisce idempotenza: stesso ID e contenuto non duplicano; contenuto diverso viene rifiutato. HTTP rifiuta date future; le date non possono precedere l'attivazione. Eventi nello stesso giorno usano la granularità data e spareggio ID, non l'ora: vedi criticità.

## 9. Revenue: cosa viene realmente attribuito

`eventForm` chiede contatto, SKU, ID ordine Shopify, data acquisto, importo e conferma di verifica. `_validate_revenue_event` verifica: importo intero non negativo in centesimi EUR; conferma vera; ordine non già attribuito; contatto esistente dello stesso cliente/piano; data acquisto tra data contatto e data verifica (estremi inclusi); SKU fra quelli offerti ricostruiti.

Non interroga Shopify e non verifica automaticamente che l'ID ordine appartenga al cliente, che l'importo corrisponda alle righe o che il prodotto sia realmente nell'ordine. Sono verifiche affidate all'operatore. Non esiste limite massimo contatto→acquisto. Una vendita può essere registrata successivamente alla chiusura se soddisfa i controlli.

`Store.verified_purchase_for_order` impedisce la doppia attribuzione dello stesso ordine, anche fra piani/clienti. `_verified_sales` applica l'ultima correzione visibile; `revenue_summary` somma gli importi corretti e conta ordini, con data acquisto nel grafico. Una correzione a zero conserva l'ordine verificato nel conteggio. Resi importati non aggiornano automaticamente gli importi manuali: occorre una correzione. L'importo economico da attribuire a un ordine multiprodotto deve essere verificato; il backend non calcola margini, IVA/spedizioni o quota incrementale.

## 10. Aggiornamenti, errori e fedeltà

La Retention aggiorna ogni 60 secondi quando pagina visibile e nessun dettaglio aperto; le risposte obsolete sono ignorate. Dopo salvataggio le viste vengono ricaricate. Se una richiesta filtro fallisce, resta la precedente tabella con avviso: il filtro visibile potrebbe non descrivere i dati ancora mostrati. Il periodo Overview segue lo stesso criterio di ignorare risposte obsolete.

Fedeltà buona: categorie e valori da backend; filtri inviati; priorità non rifatte nel browser; moduli vincolati dal backend. Fedeltà incompleta: presentazione del match strategia, focalizzazione contro opportunità registrate, preferenze varianti non evidenziate, disponibilità/consenso non live. Le motivazioni dettagliate della selezione sono sviluppate soprattutto per `hair_care`; non tutte le altre famiglie espongono lo stesso livello di spiegazione.

## 11. Verifiche e passaggio a Shopify

Suite di riferimento: `tests/test_engine.py`, `test_customer_profiles.py`, `test_shopify_orders.py`, `test_storage.py`, `test_web.py`, `retention_ui.test.cjs`. Rieseguiti durante la produzione di questi documenti: `python -m unittest discover -s tests` (178 passati) e `node --test tests/retention_ui.test.cjs` (13 passati). Provano i casi codificati, non ottimalità commerciale né resa visiva browser. Hash dei file preesistenti confrontati prima/dopo: nessuna modifica a sorgenti, frontend, test o documentazione preesistente. Solo i cinque output richiesti sono stati aggiunti.

La matrice CSV contiene 15 righe e campi numerici intenzionalmente vuoti. Per ciascuna regola estrarre clienti con fonte valida, verificare possesso/dotazioni già presenti alla data fonte, identificare il primo acquisto destinazione successivo in altro ordine e calcolare intervalli. Tenere distinti acquisti nella stessa confezione/ordine, riacquisti organici, sequenze dopo un contatto e acquisti attribuiti manualmente.

Confrontare a parità di tempo osservabile: scegliere prima un orizzonte H, separare clienti non ancora osservabili per H giorni (censura a destra), documentare inizio/fine disponibilità dei dati. Tasso descrittivo = clienti con destinazione successiva entro H / clienti fonte eleggibili e osservabili per H. Non è una probabilità predittiva o una prova di incremento. Mediana e quantili dei tempi si riferiscono ai soli acquirenti successivi e vanno accompagnati da numero di eventi e non acquirenti/censurati.

Per i ricambi distinguere primo ciclo e cicli ripetuti, conteggi clienti e conteggi cicli; quantità e confezioni multiple richiedono segmentazione. Per Mini separare finestre stagionali; per promozioni distinguere prezzo realmente pagato e calendario pianificato. La numerosità minima richiesta non è definita dal prodotto: lasciare il campo vuoto finché non sono fissati precisione attesa, orizzonte e metodo. Non usare una soglia universale inventata.

Con Sidekick chiedere esplicitamente SKU, periodo, deduplicazione cliente/ordine, esclusioni, denominatore osservabile, acquisti same-order separati, P25/P50/P75/P90 dei giorni e limiti. Se uno dei dati non è disponibile, riportare non disponibile anziché stimarlo. Dati identificativi ed export rimangono in `local-data/`, non in questi documenti.
