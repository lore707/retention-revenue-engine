# Criticità rilevate — classificazione e prove

Data: 15 ottobre 2026. Nessuna correzione applicata. “Confermato” significa riscontrato nel codice o riprodotto con dati sintetici/API; non significa danno già avvenuto su clienti reali. Le proposte di miglioramento non sono nuove regole approvate.

## A. Bug tecnici e incoerenze funzionali

### T01 — Prodotti mostrati diversi da opportunità registrate dopo focalizzazione

**Priorità alta; confermato con riproduzione sintetica.** Piano espansione con rasoi e Wave Pro; primo contatto; interesse Wave Pro; conversation_closed; rivalutazione al secondo contatto. `secondary_opportunities=[]`, l’altra opportunità passa in `other_available_opportunities`, ma `included_opportunity_keys` conserva entrambe. `plan_detail` mostra soltanto primaria/secondarie, mentre il template di contatto contiene tutte le chiavi. `record_event` richiede esattamente quell'elenco. L'operatore vede un prodotto e registra anche altri candidati.

Riferimenti: `src/engine.py::evaluate_portfolio` (focused, included_opportunity_keys); `src/customer_profiles.py::plan_detail`, `record_event`; `frontend/ui.js::eventForm`. Conseguenze possibili: storico proposte inesatto, soppressioni e attribuzione basate su prodotti non presentati nel secondo contatto. Il test engine sull'interesse simula un secondo contatto con la sola regola focalizzata, ma la validazione HTTP richiede l'elenco completo: copertura da estendere fra livelli. Proposta: distinguere candidati da prodotti effettivamente presentati, validare e salvare questi ultimi senza modificare autonomamente le regole di contatto.

### T02 — Preferenza variante dei ricambi persa nella selezione di portafoglio/UI

**Confermato dalla catena di codice e riproduzione sintetica.** `_evaluate_replenishment` conserva `preferred_target_sku` per finitura P3 Pro o ultimo ricambio Wave Pro. `evaluate_portfolio` riassegna `target_sku` alla variante più economica fra promozionate/disponibili, con SKU come spareggio. `plan_detail` non espone la preferenza tra i campi delle proposte e `productOptions` non la evidenzia. Prova: P3 Pro Gray CP96436 acquistato il 01/01/2026, valutazione 15/10/2026: preferenza grezza 30103-000047, SKU nel portafoglio 30103-000046. Pertanto “preferire l'ultima variante” non è garantito nella proposta visibile. Fonte: funzioni citate in `src/engine.py`, `src/customer_profiles.py`, `frontend/ui.js`. Proposta: decidere la precedenza tra preferenza, prezzo e promozione e rendere coerente la presentazione; mantenere tutte le alternative ammesse.

### T03 — Storico prodotti offerti ricostruito dalle regole correnti

**Confermato; difetto di fedeltà storica potenziale.** `_offered_skus` legge `rules.json` e `catalog.json` correnti partendo dagli ID delle regole nei contatti. Non conserva gli SKU effettivi al momento del contatto, né una fotografia prezzi/varianti. Una modifica futura delle destinazioni può alterare retroattivamente storico e SKU ammessi per attribuire una vendita. Non è dimostrato un caso reale già alterato. Proposta: snapshot dei prodotti effettivamente offerti e versioni al contatto. Fonte: `src/customer_profiles.py::_offered_skus`, `plan_detail`, `_validate_revenue_event`.

### T04 — Risposte e chiusure nella stessa data

**Confermato dal confronto sulle date e da prova sintetica.** `_commercial_snapshot` scarta reply con data <= ultima conversation_closed del piano; `evaluate_portfolio` considera non risolti solo esiti con giorno > chiusura. Una nuova risposta/interesse nello stesso giorno di una chiusura può essere trattata come già gestita. `_visible_events` ordina eventi per data e ID, non per ora effettiva. Con primo contatto 01/04/2026, chiusura A_CLOSED e risposta Z_REPLY entrambe il 17/04, la rivalutazione restituisce contact_review anziché operator_response. Proposta: semantica esplicita di sequenza/ora o riferimento della chiusura agli eventi gestiti. Nessuna modifica effettuata.

## B. Ambiguità frontend/backend e comportamenti poco visibili

### U01 — Strategia cercata in tutti i piani, primaria sempre globale

**Confermato da API e test.** `filter_retention` filtra `matching_plans`, `renderRetentionRows` conserva primaria globale e stesso ordinamento. Nel riscontro locale 15/10/2026: completion 715, expansion 955, intersezione 715, primi 25 identici; con open rispettivamente 476 e 17. Questi conteggi non sono conversioni. Proposta: rendere espliciti “azioni oggi” e “tutti i piani”, evidenziando proposta corrispondente e suo stato senza cambiare l'autorizzazione al contatto.

### U02 — Stato cliente, piano e opportunità si sovrappongono visivamente

`_operational_row` assegna categoria cliente dalla lavorabilità attuale; stato in_progress da contatti, anche quando secondo contatto disponibile; suspended riunisce futuro, coda e blocchi. “Nessuna azione” può includere un buon cliente con un ricambio futuro. Proposta: mostrare motivo sospensione e distinguere natura dell'opportunità dalla possibilità di agire oggi.

### U03 — Prezzo rappresentativo e varianti

P3 Pro può essere primo nell'elenco opzioni mentre il rappresentativo/minimo è P3; Neo 3 ugelli è evidenziato nell'ordine opzioni mentre valore minimo può riferirsi ai 2 ugelli. `productOptions` elenca varianti senza prezzo per variante. I prezzi promozionali sono pianificati, non confermati live. Proposta: chiarire “da €…” e prezzo associato alla variante, mantenendo distinzione catalogo/promozione. Fonte: `evaluate_portfolio`, `plan_detail`, `productOptions`.

### U04 — Copertura delle spiegazioni non uniforme

`evaluate_portfolio` costruisce `presentation.primary_selection_reason` dettagliata soprattutto per hair_care. Le altre famiglie mostrano rationale e motivo piano ma non sempre perché un'alternativa ha perso la priorità. “Alternative compatibili” è usato anche per prodotti autonomi di altre categorie. Proposta: terminologia aderente alla relazione e spiegazione della selezione per tutte le famiglie.

### U05 — KPI globali, periodo limitato al grafico, conteggi non sfaccettati

Comportamento coerente con backend, ma facilmente frainteso. I KPI Overview non seguono periodo; i conteggi dei selettori categoria non si restringono con gli altri filtri. Fonte: `overview_summary`, `retention_summary`, `filterOption`. Proposta: esplicitare l'ambito di ogni numero, non introdurre conteggi frontend autonomi.

### U06 — Dati precedenti dopo errore filtro; ricerca limitata

`loadRetention` lascia vecchie righe e mostra avviso quando la nuova richiesta fallisce; filtri/chip possono già essere cambiati. La ricerca promessa “cliente, ordine o prodotto” copre soltanto ID cliente, ordine/prodotto fonte e proposte corrispondenti, non ogni acquisto storico. Proposta: stato di errore che renda inequivoca la mancata applicazione e descrizione del campo di ricerca.

### U07 — Funzionalità visibili ma non autonome

Follow-up/Risultati sono pulsanti disabilitati; Regole è sola consultazione; SKU varianti non selezionabili come offerta registrata. UI non offre correzione di SKU/consenso incerto, attivazione storico o esito “stock indisponibile” prima del contatto. Non confondere presenza grafica con funzionalità disponibile. Riferimenti: tre HTML, `eventForm`, `src/web.py`.

## C. Limiti dei dati e della misurazione

| ID | Limite verificato | Impatto e proposta |
| --- | --- | --- |
| D01 | Email come identità locale; storico solo importato; snapshot usa history_complete=True per il disponibile | Non prova persona unica, possesso o assenza di acquisti esterni; esplicitare copertura dati per analisi |
| D02 | Consenso da segnali concordi degli ordini, non stato Shopify live | Discordanze bloccano; stato recente reale può differire. Verifica operatore obbligatoria; nessuna conclusione normativa in questo audit |
| D03 | Nessuno stock live; stato commerciale non è disponibilità | Una primaria valida può non essere vendibile ora; definire gestione temporanea dell'indisponibilità |
| D04 | Resi parziali/SKU sconosciuti bloccano il cliente operativamente | Prudente ma riduce bacino; misurare motivi di revisione e risolvere dati, non ignorarli |
| D05 | Quantità non usata nei cicli ricambio | Prova sintetica: 1 o 3 confezioni Wave Pro acquistate 01/02/2026 dopo dispositivo 01/01 portano entrambe al 29/09/2026. Separare scorte, dispositivi e uso prima di formulare consumo |
| D06 | Newsletter e contatti esterni assenti | Frequenza globale limitata agli eventi registrati; calendario promozionale non è storico invii |
| D07 | Revenue verificata manualmente, ordine non confrontato automaticamente con import | Possibili errori operatore su titolare/importo/prodotto; audit del processo e confronto ordini necessario |
| D08 | Nessuna finestra massima di attribuzione; un ordine una sola volta | Sequenze lontane attribuibili; ordini multiprodotto non suddivisi; decidere orizzonte e base economica |
| D09 | Nessuna misura causale o margine | Ricavo attribuito non prova incremento; costo operatore/sconti/costo prodotto non valutati |
| D10 | SKU e compatibilità mancanti in stand-by | Travel Box Alluminio, diffusore storico Dark Gray, Wave precedente/testine, Air/ugelli, Neo Special/diffusore, supporto altri modelli. Non colmare per analogia |

Fonti: `src/shopify_orders.py::import_orders`, `customer_profiles.py::engine_snapshot`, `review_cases`, `_validate_revenue_event`, `revenue_summary`; `engine.py::_evaluate_replenishment`; `catalog.json::standby_checks`; `project-docs/PRODUCT.md`.

## D. Decisioni commerciali da riesaminare (non bug)

### C01 — Compatibile e assente non significa desiderato

ACCESSORY_COMPLETION e REPLENISHMENT sono mirati. Supporto parete e diffusore hanno utilità dipendente dall'uso; consumo effettivo sconosciuto. Tenere distinti evidenza tecnica, motivo commerciale e interesse osservato. Non dedurre genere, capelli o bisogni personali dall'acquisto di un phon.

### C02 — Rasoio e spazzolino nello stesso piano

Stessa fonte/percorso/data a 75 giorni raggruppa rasoi e Wave Pro, mentre AutoCurl è separato a 45 giorni, ma non prova uno stesso bisogno. Il prodotto più costoso può prevalere senza evidenze di maggiore interesse. Confrontare risultati per singolo bisogno/prodotto e numero di alternative presentate; non assumere efficacia del bundle commerciale.

### C03 — Chiusura piano sopprime bisogni indipendenti

Acquisto di una proposta presentata o due tentativi chiudono il piano. Anche la seconda email chiude subito, senza finestra separata di attesa risposta. Limita pressione commerciale, ma può perdere opportunità diverse. Separare nella decisione futura chiusura della comunicazione e destino delle singole opportunità; definire condizioni esplicite prima di consentire rivalutazioni.


### C05 — Priorità assoluta mirata/test e valore nominale

È una regola approvata, non una stima di conversione. Il valore precede plan_rank; il margine e il costo contatto non sono noti. Valutare le priorità attraverso esiti reali, mantenendo i vincoli tecnici. Non introdurre uno score numerico arbitrario.

### C06 — Tempi pilota e assenza di scadenza

15/45/75/90/150/180/240 giorni sono soglie approvate, non curve validate. Vecchi accessori possono restare proponibili senza scadenza massima; Mini può maturare a T0 nella finestra; sostituire Wave a sei mesi è un'ipotesi di upgrade, non prova di usura. Confrontare distribuzioni di tempi e ragioni di rifiuto.

### C07 — Una opportunità per cliente/regola e categorie larghe

Un nuovo dispositivo non riapre normalmente una regola esaurita; un rasoio T1 Pro esclude espansione P3/P3 Pro perché già categoria rasatura. Ordini regalo e più utilizzatori indistinguibili. Valutare i casi reali prima di cambiare ampiezza delle esclusioni o identità opportunità.

### C08 — Pochette per Mini e ristrettezza varianti

Mini include una custodia diversa dalla pochette proposta: tecnicamente componenti diversi, utilità aggiuntiva da verificare. Spazzola ha Silver/Pink nel catalogo ma regola target Silver; supporto Neo propone solo Silver benché altre finiture siano riconosciute per esclusione. Decisioni da esplicitare, senza aggiungere SKU autonomamente.

### C09 — Dipendenze senza scadenza operativa

Un piano accessori non contattato può mantenere in attesa altri piani; non c'è esito pre-contatto “non lavorabile per stock/canale” che lo risolva. Distinguere impossibilità temporanea, rifiuto e opportunità non prioritaria, con politica approvata.

## E. Incoerenze documentali e manutenzione del catalogo

- AutoCurl: `catalog.json::suitability.commercial_filter` richiama interesse a ricci/onde, mentre `rules.json::shared_policies.customer_interest_required=false` e la valutazione sono proattivi. Il comportamento è quello del motore; riallineare la descrizione solo dopo conferma della semantica desiderata.
- La matrice compatibilità e l'elenco sorgenti nelle regole richiedono coerenza di manutenzione; il motore non usa la prima come validatore generale a runtime. Nessuna sorgente/configurazione o destinazione SKU mancante rilevata nelle 15 regole, nessuna destinazione historical_only nell'inventario attuale. Aggiungere controlli di integrità in un eventuale intervento successivo.
- Alcune dotazioni usano componenti specifici del modello: non uniformarli per somiglianza di nome o foto. Compatibilità di un accessorio e inclusione in confezione sono fatti diversi.

## F. Ordine di lavoro proposto e prove

1. T01, T03: fedeltà dei prodotti presentati e della storia commerciale.
2. T02, T04: preferenze dichiarate e sequenza degli eventi.
3. U01–U03: comprensibilità dei filtri e della proposta corrispondente.
4. C02, C03 e C05: composizione, dipendenze e priorità da discutere con il business.
5. D05, C06–C08: validazione quantitativa delle ipotesi, tramite il CSV.

Prove osservate: 178 test Python e 13 DOM rieseguiti e passati durante la produzione dei documenti; API locali sui filtri nel precedente riscontro; riproduzione sintetica focalizzazione, quantità ricambi e dipendenza AutoCurl, più nuove prove preferenza ricambio e risposta nello stesso giorno. Nessun esito o import reale scritto. I test esistenti non coprono ogni incoerenza elencata: un risultato verde non certifica la completezza del prodotto. Nessuna valutazione di efficacia Shopify è stata calcolata; i campi quantitativi della matrice restano vuoti.
