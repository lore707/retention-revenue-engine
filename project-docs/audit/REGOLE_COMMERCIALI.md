# Regole commerciali · inventario completo

Fotografia del 15 ottobre 2026: 15 regole, rules.json v28, catalog.json v38, promotions.json v3. Tutte le regole hanno stato `approved_for_manual_pilot`: approvazione commerciale per il pilot, non prova di efficacia storica. Nessuna regola aggiunta o modificata.

## Fonti e livelli di decisione

- **Relazioni prodotto:** `src/rules.json::rules`, dotazioni/varianti e compatibilità in `src/catalog.json::products`.
- **Valutazione singola:** `src/engine.py::_evaluate`, `_evaluate_replenishment`, `_evaluate_replacement`.
- **Composizione e precedenze:** `src/engine.py::evaluate_portfolio`, `_contact_plan_closure`.
- **Contattabilità e UI:** `src/customer_profiles.py::evaluate_day`, `_workable_plan`, `plan_detail`, `filter_retention`; `frontend/retention.js`, `frontend/ui.js`.
- **Promozioni:** `src/promotions.json::campaigns`, `engine.py::_promotions_on`.

Le 13 voci di ogni scheda vanno lette insieme alle politiche comuni seguenti, che si applicano a tutte le regole salvo specifica eccezione documentata.

## Politiche comuni effettive

**Fonti e possesso.** Si considerano acquisti fino alla data valutata. Annullati e resi sono ignorati. La fonte è il primo acquisto valido fra le configurazioni ammesse; se non ci sono fonti valide può essere selezionata una incerta per la diagnostica, ma l’applicazione blocca l’operatività tramite revisione. SKU sconosciuti, righe incerte e consenso incerto richiedono revisione. L’assenza è soltanto nello storico importato. Per ricambi si sceglie il primo dispositivo valido, poi l’ultimo ricambio valido dalla data del dispositivo; non si calcola consumo individuale.

**Esclusioni.** Per regole ordinarie, possesso dello SKU o del componente equivalente incluso in qualsiasi configurazione acquistata esclude. Anche una riga incerta può impedire di presumere assenza. L’esclusione di categoria è applicata dove esplicitamente dichiarata. Le compatibilità del catalogo sono evidenze; l’applicabilità del motore è determinata dalle sorgenti esplicite nelle regole, non da un’inferenza sul nome del modello.

**Contatto.** Storico attivo, consenso subscribed per il canale email e nessun caso di revisione; almeno 15 giorni fra tutti i contatti del cliente. Prezzo, stock, recapito e stato corrente del consenso devono essere ricontrollati dall’operatore. Nessuna sincronizzazione live, nessun invio automatico. Interesse preventivo non richiesto.

**Identità.** Una opportunità per cliente/regola per completamenti, complementi, espansioni e sostituzioni. Per ricambi si aggiunge l’ID acquisto che apre il ciclo. Un ulteriore phon non crea automaticamente una nuova opportunità già esaurita della medesima regola.

**Composizione.** Piano = stesso ordine fonte, commercial_track e data di maturazione; per ricambi ordine del ciclo. Il piano ha una primaria, secondarie e, dopo interesse, altre disponibili non presentate nella scheda principale. I piani di ordine o data diversi restano separati. Le dipendenze sono calcolate sullo stesso ordine. L’intervallo globale continua a valere fra piani indipendenti.

**Priorità.** Primaria interna: interesse, primaria contattata ancora disponibile, poi mirata/test, promozione, valore nominale, rango, ID. Piano cliente: risposte da gestire, contattati aperti, maturi, futuri. Fra maturi: mirata/test, promozione, stagionalità, valore, anzianità maturazione, rango, anzianità fonte, ID. Rango non è il primo criterio. Prezzo minimo delle opzioni rappresenta valore nominale, non somma delle alternative o revenue attesa. La preferenza della variante nel dato grezzo può essere sostituita dal prezzo minimo nel portafoglio.

**Dopo il contatto.** Due tentativi per piano, secondo dopo almeno 15 giorni. Reply/interesse/rifiuto prodotto richiedono gestione fino a conversation_closed; interesse focalizza, rifiuto prodotto elimina solo quel prodotto. Acquisto verificato, rifiuto piano, due contatti o risultato presentato excluded/stopped chiudono il piano. Le altre proposte presentate vengono soppresse senza sequenza autonoma. L’acquisto importato può chiudere il piano senza generare revenue: serve verified_purchase manuale. Solo un nuovo acquisto ricambio apre automaticamente il relativo nuovo ciclo.

**Promozioni.** Intervalli inclusivi, prezzi pianificati. Le campagne influenzano SKU/valore/priorità ma non creano una regola e non anticipano maturazione. Possono superare prerequisiti soltanto da testare e mai contattati; non una mirata o un piano contattato. Una promozione futura non prenota automaticamente il contatto. Elenco delle campagne pertinenti in ogni scheda.

## Indice

- 1. `magnetic_concentrator_completion` · Concentratore magnetico
- 2. `se_lite_diffuser_completion` · Diffusore SE Lite
- 3. `mini_wall_mount_completion` · Supporto Mini
- 4. `neo_wall_mount_completion` · Supporto Neo
- 5. `autocurl_cross_sell` · AutoCurl dopo un phon
- 6. `mini_travel_cross_sell` · Mini da viaggio
- 7. `hair_dryer_to_wave_pro_category_expansion` · Dal phon a Wave Pro
- 8. `hair_dryer_to_shavers_category_expansion` · Dal phon ai rasoi
- 9. `toothbrush_to_neo_category_expansion` · Dallo spazzolino a Neo
- 10. `storage_pouch_cross_sell` · Pochette
- 11. `brush_complement` · Spazzola
- 12. `p3_travel_case_cross_sell` · Astuccio P3 / P3 Pro
- 13. `p3_pro_head_replenishment` · Testina P3 Pro
- 14. `wave_legacy_to_wave_pro_replacement` · Da Wave precedente a Wave Pro
- 15. `wave_pro_heads_replenishment` · Testine Wave e Wave Pro

## 1. Concentratore magnetico

1. **ID e stato:** `magnetic_concentrator_completion`, versione 6, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Completamenti funzionali (`ACCESSORY_COMPLETION`); categoria opportunità **Mirata** quando lavorabile; percorso `hair_care`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Swift Premium · Ugello standard magnetico, diffusore magnetico e custodia da viaggio** (`standard_diffuser_case`): `CP38476`, `CP38473`, `CP38475`

4. **Destinazioni esatte:**

- `CP34473` · Ugello Concentratore Magnetico Laifen · prezzo osservato € 24.99

5. **Motivo commerciale:** Aggiunge il concentratore compatibile, non incluso nelle configurazioni Neo 2 ugelli, Neo Special e Swift Premium.

6. **Compatibilità ed evidenze:**

- Ugello Concentratore Magnetico Laifen: Neo · confermata compatibile (fonte `concentrator_business_confirmation`).
- Ugello Concentratore Magnetico Laifen: SE Special · confermata compatibile (fonte `concentrator_shopify_screenshots`).
- Ugello Concentratore Magnetico Laifen: Gift Edition · confermata compatibile (fonte `concentrator_shopify_screenshots`).
- Ugello Concentratore Magnetico Laifen: Swift Premium · confermata compatibile (fonte `concentrator_shopify_screenshots`).
- Ugello Concentratore Magnetico Laifen: Retro · incompatibile (fonte `concentrator_shopify_screenshots`).
- Ugello Concentratore Magnetico Laifen: SE Lite · incompatibile (fonte `concentrator_shopify_screenshots`).
- Ugello Concentratore Magnetico Laifen: Mini · incompatibile (fonte `concentrator_shopify_screenshots`).
- Ugello Concentratore Magnetico Laifen: Neo Special · confermata compatibile (fonte `neo_special_business_confirmation`).

Stato delle evidenze dichiarate: `compatibility`: `business_confirmed`; `source_configuration_lacks_concentrator`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_magnetic_concentrator` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Mirata; `plan_rank=300` (Completamento funzionale specifico.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Con gli accessori della stessa fonte/ordine che maturano a 15 giorni; combinazione dipendente da dotazioni e possesso.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 2. Diffusore SE Lite

1. **ID e stato:** `se_lite_diffuser_completion`, versione 3, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Completamenti funzionali (`ACCESSORY_COMPLETION`); categoria opportunità **Mirata** quando lavorabile; percorso `hair_care`.

3. **Fonti esatte:**

- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`

4. **Destinazioni esatte:**

- `CP34510` · Ugello Diffusore per Laifen SE Lite · Light Gray · prezzo osservato € 24.99

5. **Motivo commerciale:** Aggiunge il diffusore a incastro compatibile, non incluso in nessuna colorazione SE Lite.

6. **Compatibilità ed evidenze:**

- Ugello Diffusore per Laifen SE Lite: Retro · confermata compatibile (fonte `diffuser_shopify_screenshots`).
- Ugello Diffusore per Laifen SE Lite: SE Lite · confermata compatibile (fonte `diffuser_shopify_screenshots`).
- Ugello Diffusore per Laifen SE Lite: Neo · incompatibile (fonte `diffuser_business_confirmation`).

Stato delle evidenze dichiarate: `compatibility`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`; `source_configuration_lacks_diffuser`: `business_confirmed`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `se_lite_diffuser` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Mirata; `plan_rank=300` (Completamento funzionale specifico.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Con gli accessori della stessa fonte/ordine che maturano a 15 giorni; combinazione dipendente da dotazioni e possesso.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 3. Supporto Mini

1. **ID e stato:** `mini_wall_mount_completion`, versione 3, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Completamenti funzionali (`ACCESSORY_COMPLETION`); categoria opportunità **Mirata** quando lavorabile; percorso `hair_care`.

3. **Fonti esatte:**

- **Laifen Mini · Ugello standard magnetico e custodia da viaggio** (`standard_nozzle_case`): `CP34448`, `CP34447`, `CP34500`, `CR05263`

4. **Destinazioni esatte:**

- `CP34501` · Supporto magnetico da parete Laifen Mini · prezzo osservato € 14.99

5. **Motivo commerciale:** Aggiunge il supporto magnetico da parete compatibile, non incluso in nessuna colorazione Mini.

6. **Compatibilità ed evidenze:**

- Supporto magnetico da parete Laifen Mini: Mini · confermata compatibile (fonte `mini_wall_mount_shopify_screenshots`).

Stato delle evidenze dichiarate: `compatibility`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`; `source_configuration_lacks_wall_mount`: `business_confirmed`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `mini_magnetic_wall_mount` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Mirata; `plan_rank=200` (Accessorio organizzativo specifico.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Con gli accessori della stessa fonte/ordine che maturano a 15 giorni; combinazione dipendente da dotazioni e possesso.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 4. Supporto Neo

1. **ID e stato:** `neo_wall_mount_completion`, versione 3, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Completamenti funzionali (`ACCESSORY_COMPLETION`); categoria opportunità **Mirata** quando lavorabile; percorso `hair_care`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`

4. **Destinazioni esatte:**

- `30101-000092` · Supporto magnetico da parete Laifen · Silver · prezzo osservato € 17.99

5. **Motivo commerciale:** Aggiunge il supporto magnetico da parete compatibile, non incluso nelle configurazioni Neo.

6. **Compatibilità ed evidenze:**

- Supporto magnetico da parete Laifen: Neo · confermata compatibile (fonte `magnetic_wall_mount_business_confirmation`).

Stato delle evidenze dichiarate: `compatibility`: `business_confirmed_for_neo`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`; `source_configuration_lacks_wall_mount`: `business_confirmed`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_magnetic_wall_mount` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Mirata; `plan_rank=200` (Accessorio organizzativo specifico.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Con gli accessori della stessa fonte/ordine che maturano a 15 giorni; combinazione dipendente da dotazioni e possesso.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 5. AutoCurl dopo un phon

1. **ID e stato:** `autocurl_cross_sell`, versione 5, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Complementi d’uso (`USE_CASE_COMPLEMENT`); categoria opportunità **Da testare** quando lavorabile; percorso `category_expansion`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`
- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Swift Premium · Ugello standard magnetico, diffusore magnetico e custodia da viaggio** (`standard_diffuser_case`): `CP38476`, `CP38473`, `CP38475`
- **Laifen Gift Edition · Concentratore magnetico e diffusore magnetico** (`concentrator_diffuser`): `CK8063`, `CK80633`, `CK80632`, `CK80631`
- **Laifen SE Special · Ugello standard, concentratore e diffusore magnetici** (`standard_concentrator_diffuser`): `CL50966`, `CL50970`, `CL50961`, `CL50968`
- **Laifen Mini · Ugello standard magnetico e custodia da viaggio** (`standard_nozzle_case`): `CP34448`, `CP34447`, `CP34500`, `CR05263`
- **Laifen Air · Ugello standard magnetico e manuale utente** (`standard_nozzle_manual`): `1HD20-S-EU-PU-001`, `1HD20-S-EU-WH-001`, `1HD20-S-EU-PK-001`

4. **Destinazioni esatte:**

- `1HC51-P-EU-BL-001` · Laifen AutoCurl - Arricciacapelli Automatico · Black · prezzo osservato € 99.99
- `1HC51-P-EU-WH-002` · Laifen AutoCurl - Arricciacapelli Automatico · White · prezzo osservato € 99.99

5. **Motivo commerciale:** Aggiunge uno strumento automatico per creare ricci e onde alla routine di chi ha acquistato un asciugacapelli Laifen.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `applicability_to_all_laifen_hair_dryers`: `business_confirmed`; `suitability_for_multiple_hair_types`: `official_product_page_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 45 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_autocurl` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** `magnetic_concentrator_completion`, `se_lite_diffuser_completion`, `mini_wall_mount_completion`, `neo_wall_mount_completion`, `storage_pouch_cross_sell`, `brush_complement`

11. **Scelta della primaria:** categoria Da testare; `plan_rank=100` (Complemento di styling ad alto valore nominale.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** AutoCurl ha un piano dedicato a 45 giorni. Wave Pro e rasoi condividono il piano espansioni a 75 giorni; Neo dallo spazzolino matura a 90 giorni. Raggruppamento soltanto con ordine, percorso e data coincidenti.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 6. Mini da viaggio

1. **ID e stato:** `mini_travel_cross_sell`, versione 3, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Complementi d’uso (`USE_CASE_COMPLEMENT`); categoria opportunità **Da testare** quando lavorabile; percorso `seasonal_travel`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`
- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Swift Premium · Ugello standard magnetico, diffusore magnetico e custodia da viaggio** (`standard_diffuser_case`): `CP38476`, `CP38473`, `CP38475`
- **Laifen Gift Edition · Concentratore magnetico e diffusore magnetico** (`concentrator_diffuser`): `CK8063`, `CK80633`, `CK80632`, `CK80631`
- **Laifen SE Special · Ugello standard, concentratore e diffusore magnetici** (`standard_concentrator_diffuser`): `CL50966`, `CL50970`, `CL50961`, `CL50968`
- **Laifen Air · Ugello standard magnetico e manuale utente** (`standard_nozzle_manual`): `1HD20-S-EU-PU-001`, `1HD20-S-EU-WH-001`, `1HD20-S-EU-PK-001`

4. **Destinazioni esatte:**

- `CP34448` · Laifen Mini · Jungle Green · standard_nozzle_case · prezzo osservato € 79.99
- `CP34447` · Laifen Mini · Glacier Blue · standard_nozzle_case · prezzo osservato € 79.99
- `CP34500` · Laifen Mini · Coral Pink · standard_nozzle_case · prezzo osservato € 79.99
- `CR05263` · Laifen Mini · Sand Gold · standard_nozzle_case · prezzo osservato € 79.99

5. **Motivo commerciale:** Propone Mini come secondo asciugacapelli compatto per viaggi, palestra o seconda casa.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `travel_use_case`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** Prima data utile dalla fonte nelle finestre annuali inclusive 15 maggio–5 settembre e 15 dicembre–15 gennaio; nessuna attesa minima aggiuntiva. Anche il secondo contatto deve ricadere in finestra. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_mini` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

Finestre stagionali Mini come al punto 7.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=100` (Secondo dispositivo per un caso d'uso specifico.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Piano Mini distinto dagli accessori e dalle espansioni anche se le date coincidono.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 7. Dal phon a Wave Pro

1. **ID e stato:** `hair_dryer_to_wave_pro_category_expansion`, versione 4, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Espansione di categoria (`CATEGORY_EXPANSION`); categoria opportunità **Da testare** quando lavorabile; percorso `category_expansion`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`
- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Swift Premium · Ugello standard magnetico, diffusore magnetico e custodia da viaggio** (`standard_diffuser_case`): `CP38476`, `CP38473`, `CP38475`
- **Laifen Gift Edition · Concentratore magnetico e diffusore magnetico** (`concentrator_diffuser`): `CK8063`, `CK80633`, `CK80632`, `CK80631`
- **Laifen SE Special · Ugello standard, concentratore e diffusore magnetici** (`standard_concentrator_diffuser`): `CL50966`, `CL50970`, `CL50961`, `CL50968`
- **Laifen Mini · Ugello standard magnetico e custodia da viaggio** (`standard_nozzle_case`): `CP34448`, `CP34447`, `CP34500`, `CR05263`
- **Laifen Air · Ugello standard magnetico e manuale utente** (`standard_nozzle_manual`): `1HD20-S-EU-PU-001`, `1HD20-S-EU-WH-001`, `1HD20-S-EU-PK-001`

4. **Destinazioni esatte:**

- `CR95008` · Laifen Wave Pro - Spazzolino Elettrico · Bianco · ABS · two_heads_case_wireless_charger · prezzo osservato € 99.99
- `CR95009` · Laifen Wave Pro - Spazzolino Elettrico · Nero · ABS · two_heads_case_wireless_charger · prezzo osservato € 99.99
- `CR95024` · Laifen Wave Pro - Spazzolino Elettrico · Rosa · ABS · two_heads_case_wireless_charger · prezzo osservato € 99.99
- `CR95017` · Laifen Wave Pro - Spazzolino Elettrico · Argento Satinato · Alluminio · two_heads_case_wireless_charger · prezzo osservato € 119.99
- `CR95041` · Laifen Wave Pro - Spazzolino Elettrico · Grigio Satinato · Alluminio · two_heads_case_wireless_charger · prezzo osservato € 119.99
- `CR95016` · Laifen Wave Pro - Spazzolino Elettrico · Nero Trasparente · Transparent · two_heads_case_wireless_charger · prezzo osservato € 139.99

5. **Motivo commerciale:** Espande la relazione commerciale dall'asciugatura dei capelli all'igiene orale proponendo Wave Pro.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `category_absence`: `complete_purchase_history_required`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 75 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Esclude qualsiasi acquisto osservato della categoria spazzolini elettrici, non soltanto il modello destinazione. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_wave_pro`; `target_category_in_purchase_history` = `electric_toothbrush` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

- `wave_pro_abs_october_2026`: 2026-10-12 -> 2026-10-18, € 84.99; SKU: `CR95008`, `CR95009`, `CR95024`
- `wave_pro_aluminum_october_2026`: 2026-10-12 -> 2026-10-18, € 99.99; SKU: `CR95017`, `CR95041`
- `wave_pro_transparent_october_2026`: 2026-10-12 -> 2026-10-18, € 118.99; SKU: `CR95016`
- `wave_pro_abs_november_2026`: 2026-11-19 -> 2026-11-30, € 79.99; SKU: `CR95008`, `CR95009`, `CR95024`
- `wave_pro_aluminum_november_2026`: 2026-11-19 -> 2026-11-30, € 94.99; SKU: `CR95017`, `CR95041`
- `wave_pro_transparent_november_2026`: 2026-11-19 -> 2026-11-30, € 109.99; SKU: `CR95016`
- `wave_pro_abs_december_2026`: 2026-12-12 -> 2026-12-25, € 79.99; SKU: `CR95008`, `CR95009`, `CR95024`
- `wave_pro_aluminum_december_2026`: 2026-12-12 -> 2026-12-25, € 94.99; SKU: `CR95017`, `CR95041`
- `wave_pro_transparent_december_2026`: 2026-12-12 -> 2026-12-25, € 109.99; SKU: `CR95016`

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani. Non eredita la dipendenza accessori di AutoCurl: il piano è separato.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=100` (Espansione verso una categoria Laifen non ancora posseduta.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** AutoCurl ha un piano dedicato a 45 giorni. Wave Pro e rasoi condividono il piano espansioni a 75 giorni; Neo dallo spazzolino matura a 90 giorni. Raggruppamento soltanto con ordine, percorso e data coincidenti.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 8. Dal phon ai rasoi

1. **ID e stato:** `hair_dryer_to_shavers_category_expansion`, versione 3, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Espansione di categoria (`CATEGORY_EXPANSION`); categoria opportunità **Da testare** quando lavorabile; percorso `category_expansion`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`
- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Swift Premium · Ugello standard magnetico, diffusore magnetico e custodia da viaggio** (`standard_diffuser_case`): `CP38476`, `CP38473`, `CP38475`
- **Laifen Gift Edition · Concentratore magnetico e diffusore magnetico** (`concentrator_diffuser`): `CK8063`, `CK80633`, `CK80632`, `CK80631`
- **Laifen SE Special · Ugello standard, concentratore e diffusore magnetici** (`standard_concentrator_diffuser`): `CL50966`, `CL50970`, `CL50961`, `CL50968`
- **Laifen Mini · Ugello standard magnetico e custodia da viaggio** (`standard_nozzle_case`): `CP34448`, `CP34447`, `CP34500`, `CR05263`
- **Laifen Air · Ugello standard magnetico e manuale utente** (`standard_nozzle_manual`): `1HD20-S-EU-PU-001`, `1HD20-S-EU-WH-001`, `1HD20-S-EU-PK-001`

4. **Destinazioni esatte:**

- `CP96308` · Laifen P3 Pro - Rasoio Elettrico a 3 Lame · Original Aluminium Alloy · Alluminio CNC · case_cable_manual · prezzo osservato € 199.99
- `CP96436` · Laifen P3 Pro - Rasoio Elettrico a 3 Lame · Space Gray Aluminium Alloy · Alluminio CNC · case_cable_manual · prezzo osservato € 199.99
- `1ER91-P-XX-BL-002` · Laifen P3 - Rasoio Elettrico a 3 Lame · Black · Composito ad alta resistenza · head_case_cable_manual · prezzo osservato € 169.99
- `1ER91-P-XX-WH-002` · Laifen P3 - Rasoio Elettrico a 3 Lame · White · Composito ad alta resistenza · head_case_cable_manual · prezzo osservato € 169.99

5. **Motivo commerciale:** Scoprire la rasatura Laifen: P3 Pro in evidenza, P3 come alternativa.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `category_absence`: `complete_purchase_history_required`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 75 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Esclude qualsiasi acquisto osservato della categoria rasoi elettrici, non soltanto il modello destinazione. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_p3_pro`; `target_category_in_purchase_history` = `electric_shaver` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

- `p3_pro_october_2026`: 2026-10-12 -> 2026-10-18, € 169.99; SKU: `CP96308`, `CP96436`
- `p3_october_2026`: 2026-10-12 -> 2026-10-18, € 139.99; SKU: `1ER91-P-XX-BL-002`, `1ER91-P-XX-WH-002`
- `p3_pro_november_2026`: 2026-11-19 -> 2026-11-30, € 149.99; SKU: `CP96308`, `CP96436`
- `p3_november_2026`: 2026-11-19 -> 2026-11-30, € 129.99; SKU: `1ER91-P-XX-BL-002`, `1ER91-P-XX-WH-002`
- `p3_pro_december_2026`: 2026-12-12 -> 2026-12-25, € 149.99; SKU: `CP96308`, `CP96436`
- `p3_december_2026`: 2026-12-12 -> 2026-12-25, € 129.99; SKU: `1ER91-P-XX-BL-002`, `1ER91-P-XX-WH-002`

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani. Non eredita la dipendenza accessori di AutoCurl: il piano è separato.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=100` (Espansione verso una categoria Laifen non ancora posseduta.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** AutoCurl ha un piano dedicato a 45 giorni. Wave Pro e rasoi condividono il piano espansioni a 75 giorni; Neo dallo spazzolino matura a 90 giorni. Raggruppamento soltanto con ordine, percorso e data coincidenti.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 9. Dallo spazzolino a Neo

1. **ID e stato:** `toothbrush_to_neo_category_expansion`, versione 2, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Espansione di categoria (`CATEGORY_EXPANSION`); categoria opportunità **Da testare** quando lavorabile; percorso `category_expansion`.

3. **Fonti esatte:**

- **Laifen Wave - Spazzolino Elettrico con Travel Box · Travel Box e tre testine specializzate** (`travel_box_three_heads`): `CL97510`, `CL97511`, `CL97508X`, `CP34472X`, `CL97509`, `C027164`, `C027165`
- **Laifen Wave Pro - Spazzolino Elettrico · Due testine, custodia da viaggio e caricatore wireless** (`two_heads_case_wireless_charger`): `CR95008`, `CR95009`, `CR95024`, `CR95017`, `CR95041`, `CR95016`

4. **Destinazioni esatte:**

- `CQ15839` · Laifen Neo · Shadow Black · three_nozzles · prezzo osservato € 149.99
- `CQ15841` · Laifen Neo · Mist White · three_nozzles · prezzo osservato € 149.99
- `CQ15840` · Laifen Neo · Pastel Purple · three_nozzles · prezzo osservato € 149.99
- `CR05272` · Laifen Neo · Shadow Black · two_nozzles · prezzo osservato € 134.99
- `CR05186` · Laifen Neo · Mist White · two_nozzles · prezzo osservato € 134.99
- `CR05227` · Laifen Neo · Pastel Purple · two_nozzles · prezzo osservato € 134.99

5. **Motivo commerciale:** Espande la relazione commerciale dall'igiene orale alla cura dei capelli proponendo la gamma Neo.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `category_absence`: `complete_purchase_history_required`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 90 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Esclude qualsiasi acquisto osservato della categoria asciugacapelli, non soltanto il modello destinazione. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_neo`; `target_category_in_purchase_history` = `hair_dryer` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

- `neo_three_nozzles_october_2026`: 2026-10-01 -> 2026-10-07, € 124.99; SKU: `CQ15839`, `CQ15841`, `CQ15840`
- `neo_three_nozzles_november_2026`: 2026-11-19 -> 2026-11-30, € 113.99; SKU: `CQ15839`, `CQ15841`, `CQ15840`
- `neo_three_nozzles_december_2026`: 2026-12-12 -> 2026-12-25, € 113.99; SKU: `CQ15839`, `CQ15841`, `CQ15840`

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=100` (Espansione verso una categoria Laifen non ancora posseduta.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** AutoCurl ha un piano dedicato a 45 giorni. Wave Pro e rasoi condividono il piano espansioni a 75 giorni; Neo dallo spazzolino matura a 90 giorni. Raggruppamento soltanto con ordine, percorso e data coincidenti.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 10. Pochette

1. **ID e stato:** `storage_pouch_cross_sell`, versione 1, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Complementi d’uso (`USE_CASE_COMPLEMENT`); categoria opportunità **Da testare** quando lavorabile; percorso `hair_care`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`
- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Gift Edition · Concentratore magnetico e diffusore magnetico** (`concentrator_diffuser`): `CK8063`, `CK80633`, `CK80632`, `CK80631`
- **Laifen SE Special · Ugello standard, concentratore e diffusore magnetici** (`standard_concentrator_diffuser`): `CL50966`, `CL50970`, `CL50961`, `CL50968`
- **Laifen Mini · Ugello standard magnetico e custodia da viaggio** (`standard_nozzle_case`): `CP34448`, `CP34447`, `CP34500`, `CR05263`
- **Laifen Air · Ugello standard magnetico e manuale utente** (`standard_nozzle_manual`): `1HD20-S-EU-PU-001`, `1HD20-S-EU-WH-001`, `1HD20-S-EU-PK-001`

4. **Destinazioni esatte:**

- `CL51809` · Pochette Portaoggetti Laifen · prezzo osservato € 29.99

5. **Motivo commerciale:** Aggiunge una pochette per organizzare e trasportare l'asciugacapelli e i suoi accessori quando non è già inclusa nella confezione.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `applicability_to_all_hair_dryers_except_swift_premium`: `business_confirmed`; `swift_premium_already_includes_target`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_storage_pouch` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=200` (Accessorio organizzativo generale ad alto valore nominale.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Con gli accessori della stessa fonte/ordine che maturano a 15 giorni; combinazione dipendente da dotazioni e possesso.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 11. Spazzola

1. **ID e stato:** `brush_complement`, versione 2, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Complementi d’uso (`USE_CASE_COMPLEMENT`); categoria opportunità **Da testare** quando lavorabile; percorso `hair_care`.

3. **Fonti esatte:**

- **Laifen Neo · 2 Ugelli** (`two_nozzles`): `CR05272`, `CR05186`, `CR05227`
- **Laifen Neo · 3 Ugelli** (`three_nozzles`): `CQ15839`, `CQ15841`, `CQ15840`
- **Laifen SE Lite · Ugello classico a scatto, senza diffusore** (`standard_nozzle`): `CQ62986`, `CL50959`, `CL50963`, `CL50964`, `CL50962`
- **Laifen Neo Special · Ugello standard, diffusore, ugello nutriente e tre capsule** (`nourishing_kit`): `CR68941`, `CR68943`, `CR68942`
- **Laifen Swift Premium · Ugello standard magnetico, diffusore magnetico e custodia da viaggio** (`standard_diffuser_case`): `CP38476`, `CP38473`, `CP38475`
- **Laifen Gift Edition · Concentratore magnetico e diffusore magnetico** (`concentrator_diffuser`): `CK8063`, `CK80633`, `CK80632`, `CK80631`
- **Laifen SE Special · Ugello standard, concentratore e diffusore magnetici** (`standard_concentrator_diffuser`): `CL50966`, `CL50970`, `CL50961`, `CL50968`
- **Laifen Mini · Ugello standard magnetico e custodia da viaggio** (`standard_nozzle_case`): `CP34448`, `CP34447`, `CP34500`, `CR05263`
- **Laifen Air · Ugello standard magnetico e manuale utente** (`standard_nozzle_manual`): `1HD20-S-EU-PU-001`, `1HD20-S-EU-WH-001`, `1HD20-S-EU-PK-001`

4. **Destinazioni esatte:**

- `30101-000041` · Spazzola Laifen · Silver · prezzo osservato € 12.99

5. **Motivo commerciale:** Aggiunge una spazzola portatile alla routine di chi ha acquistato un asciugacapelli Laifen.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `applicability_to_all_laifen_hair_dryers`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `laifen_brush` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=100` (Complemento generico della routine capelli.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Con gli accessori della stessa fonte/ordine che maturano a 15 giorni; combinazione dipendente da dotazioni e possesso.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 12. Astuccio P3 / P3 Pro

1. **ID e stato:** `p3_travel_case_cross_sell`, versione 1, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Complementi d’uso (`USE_CASE_COMPLEMENT`); categoria opportunità **Da testare** quando lavorabile; percorso `shaving`.

3. **Fonti esatte:**

- **Laifen P3 - Rasoio Elettrico a 3 Lame · Testina, custodia lama, cavo USB-C e manuale** (`head_case_cable_manual`): `1ER91-P-XX-BL-002`, `1ER91-P-XX-WH-002`
- **Laifen P3 Pro - Rasoio Elettrico a 3 Lame · Custodia lama, cavo USB-C e manuale** (`case_cable_manual`): `CP96308`, `CP96436`

4. **Destinazioni esatte:**

- `30103-000019` · Astuccio da Viaggio per Laifen P3 Pro · White · prezzo osservato € 29.99
- `30103-000021` · Astuccio da Viaggio per Laifen P3 Pro · Gray · prezzo osservato € 29.99

5. **Motivo commerciale:** Aggiunge un astuccio da viaggio compatibile per proteggere e trasportare P3 o P3 Pro.

6. **Compatibilità ed evidenze:**

- Astuccio da Viaggio per Laifen P3 Pro: P3 Pro · confermata compatibile (fonte `p3_travel_case_shopify_screenshots`).
- Astuccio da Viaggio per Laifen P3 Pro: P3 · confermata compatibile (fonte `p3_accessories_business_confirmation`).

Stato delle evidenze dichiarate: `p3_pro_compatibility`: `shopify_product_confirmed`; `p3_compatibility`: `business_confirmed`; `customer_interest`: `unknown`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 15 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Esclude chi ha acquistato uno degli SKU destinazione elencati. Esclude anche chi ha ricevuto il componente equivalente in una dotazione acquistata o tramite un accessorio che lo fornisce, anche da un altro modello ammesso nel catalogo. Parametri canonici: `target_sku_in_purchase_history` = `True`; `target_component_in_known_purchased_configuration` = `p3_travel_case` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=200` (Accessorio organizzativo specifico.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Astuccio a 15 giorni e ricambio a 180 hanno date diverse: piani separati; eventuali coincidenze di ordine/percorso/data seguono la regola generale.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 13. Testina P3 Pro

1. **ID e stato:** `p3_pro_head_replenishment`, versione 1, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate_replenishment`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Ricambi (`REPLENISHMENT`); categoria opportunità **Mirata** quando lavorabile; percorso `shaving`.

3. **Fonti esatte:**

- **Laifen P3 Pro - Rasoio Elettrico a 3 Lame · Custodia lama, cavo USB-C e manuale** (`case_cable_manual`): `CP96308`, `CP96436`

4. **Destinazioni esatte:**

- `30103-000046` · Testina di Ricambio per Laifen P3 Pro · Original Aluminium Alloy · prezzo osservato € 44.99
- `30103-000047` · Testina di Ricambio per Laifen P3 Pro · Space Gray Aluminium Alloy · prezzo osservato € 44.99

5. **Motivo commerciale:** Ricorda il ricambio della testina P3 Pro e propone per prima la finitura coerente con il rasoio acquistato.

6. **Compatibilità ed evidenze:**

- Testina di Ricambio per Laifen P3 Pro: P3 Pro · confermata compatibile (fonte `p3_pro_replacement_head_shopify_screenshots`).
- Testina di Ricambio per Laifen P3 Pro: P3 · incompatibile (fonte `p3_pro_replacement_head_official_product_page`).

Stato delle evidenze dichiarate: `p3_pro_compatibility`: `official_product_page_confirmed`; `p3_incompatibility`: `official_product_page_confirmed`; `replacement_interval`: `business_approved_from_official_planning_benchmark`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** Primo ciclo: 180 giorni dall’acquisto dispositivo. Cicli successivi: 180 giorni dall’ultimo acquisto valido di ricambio successivo o contemporaneo alla fonte; quantità non considerate. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Ricambio: nessuna esclusione permanente per acquisto del ricambio; apre un nuovo ciclo. Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Mirata; `plan_rank=400` (Ricambio funzionale periodico ad alto valore nominale.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Astuccio a 15 giorni e ricambio a 180 hanno date diverse: piani separati; eventuali coincidenze di ordine/percorso/data seguono la regola generale.

13. **Dopo contatto/acquisto/chiusura:** Nuovo ricambio acquistato apre un ciclo con nuovo riferimento acquisto e nuova maturazione; primo e secondo tentativo appartengono al singolo ciclo. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 14. Da Wave precedente a Wave Pro

1. **ID e stato:** `wave_legacy_to_wave_pro_replacement`, versione 1, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate_replacement`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Sostituzioni / upgrade (`REPLACEMENT`); categoria opportunità **Da testare** quando lavorabile; percorso `oral_care`.

3. **Fonti esatte:**

- **Laifen Wave - Spazzolino Elettrico con Travel Box · Travel Box e tre testine specializzate** (`travel_box_three_heads`): `CL97510`, `CL97511`, `CL97508X`, `CP34472X`, `CL97509`, `C027164`, `C027165`

4. **Destinazioni esatte:**

- `CR95008` · Laifen Wave Pro - Spazzolino Elettrico · Bianco · ABS · two_heads_case_wireless_charger · prezzo osservato € 99.99
- `CR95009` · Laifen Wave Pro - Spazzolino Elettrico · Nero · ABS · two_heads_case_wireless_charger · prezzo osservato € 99.99
- `CR95024` · Laifen Wave Pro - Spazzolino Elettrico · Rosa · ABS · two_heads_case_wireless_charger · prezzo osservato € 99.99
- `CR95017` · Laifen Wave Pro - Spazzolino Elettrico · Argento Satinato · Alluminio · two_heads_case_wireless_charger · prezzo osservato € 119.99
- `CR95041` · Laifen Wave Pro - Spazzolino Elettrico · Grigio Satinato · Alluminio · two_heads_case_wireless_charger · prezzo osservato € 119.99
- `CR95016` · Laifen Wave Pro - Spazzolino Elettrico · Nero Trasparente · Transparent · two_heads_case_wireless_charger · prezzo osservato € 139.99

5. **Motivo commerciale:** Propone il modello Wave Pro a chi possiede il precedente Wave, non più vendibile e non destinato al riassortimento.

6. **Compatibilità ed evidenze:**

Non è una compatibilità tecnica da inferire: applicabilità commerciale limitata alle fonti elencate. Per ricambi/sostituzioni valgono modello e configurazione espliciti.

Stato delle evidenze dichiarate: `source_model_discontinued`: `business_confirmed`; `source_model_no_restock`: `business_confirmed`; `replacement_timing`: `business_approved_pilot`; `purchase_probability`: `not_estimated`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** 180 giorni di calendario dall’acquisto fonte; nessuna scadenza massima. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Qualsiasi variante Wave Pro acquistata esclude la sostituzione, indipendentemente dalla finitura. Parametri canonici: `any_wave_pro_variant_in_purchase_history` = `True` Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

- `wave_pro_abs_october_2026`: 2026-10-12 -> 2026-10-18, € 84.99; SKU: `CR95008`, `CR95009`, `CR95024`
- `wave_pro_aluminum_october_2026`: 2026-10-12 -> 2026-10-18, € 99.99; SKU: `CR95017`, `CR95041`
- `wave_pro_transparent_october_2026`: 2026-10-12 -> 2026-10-18, € 118.99; SKU: `CR95016`
- `wave_pro_abs_november_2026`: 2026-11-19 -> 2026-11-30, € 79.99; SKU: `CR95008`, `CR95009`, `CR95024`
- `wave_pro_aluminum_november_2026`: 2026-11-19 -> 2026-11-30, € 94.99; SKU: `CR95017`, `CR95041`
- `wave_pro_transparent_november_2026`: 2026-11-19 -> 2026-11-30, € 109.99; SKU: `CR95016`
- `wave_pro_abs_december_2026`: 2026-12-12 -> 2026-12-25, € 79.99; SKU: `CR95008`, `CR95009`, `CR95024`
- `wave_pro_aluminum_december_2026`: 2026-12-12 -> 2026-12-25, € 94.99; SKU: `CR95017`, `CR95041`
- `wave_pro_transparent_december_2026`: 2026-12-12 -> 2026-12-25, € 109.99; SKU: `CR95016`

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Da testare; `plan_rank=450` (Sostituzione ad alto valore potenziale di un modello non più commercializzato.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Ricambio e sostituzione restano separati quando data o ordine differiscono; il solo fatto di essere igiene orale non li unisce.

13. **Dopo contatto/acquisto/chiusura:** Una sola opportunità cliente/regola; nessuna riapertura automatica dopo esaurimento o chiusura del piano. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## 15. Testine Wave e Wave Pro

1. **ID e stato:** `wave_pro_heads_replenishment`, versione 3, `approved_for_manual_pilot`. Valutazione: `src/engine.py::_evaluate_replenishment`; coordinamento: `evaluate_portfolio`.

2. **Strategia:** Ricambi (`REPLENISHMENT`); categoria opportunità **Mirata** quando lavorabile; percorso `oral_care`.

3. **Fonti esatte:**

- **Laifen Wave precedente con Travel Box** (`travel_box_three_heads`): `CL97510`, `CL97511`, `CL97508X`, `CP34472X`, `CL97509`, `C027164`, `C027165`. Se presente anche Wave Pro valido, conserva la precedenza come fonte dell’unico ciclo.

- **Laifen Wave Pro - Spazzolino Elettrico · Due testine, custodia da viaggio e caricatore wireless** (`two_heads_case_wireless_charger`): `CR95008`, `CR95009`, `CR95024`, `CR95017`, `CR95041`, `CR95016`

4. **Destinazioni esatte:**

- `CR95042` · Testine di Ricambio Laifen Wave Pro · Pro Whitening · prezzo osservato € 19.99
- `CR95032` · Testine di Ricambio Laifen Wave Pro · Pro Plaque Removal · prezzo osservato € 19.99
- `6976973852011` · Testine di Ricambio Laifen Wave Pro · Pro Gum Care · prezzo osservato € 19.99
- `CR94994` · Testine di Ricambio Laifen Wave Pro · Pro Max Brush · prezzo osservato € 19.99

5. **Motivo commerciale:** Ricorda il ricambio delle testine di Wave e Wave Pro e consente di scegliere tra le quattro confezioni compatibili.

6. **Compatibilità ed evidenze:**

- Testine di Ricambio Laifen Wave Pro: Wave e Wave Pro · compatibilità confermata dal business.

Stato delle evidenze dichiarate: `compatibility`: `business_confirmed_wave_and_wave_pro`; `replacement_interval`: `business_approved_shared_wave_and_wave_pro_timing`. Le fonti sono quelle registrate nel catalogo, non una nuova verifica esterna eseguita nell’audit.

7. **Timing:** Primo ciclo: 150 giorni dall’acquisto dispositivo. Cicli successivi: 240 giorni dall’ultimo acquisto valido di ricambio successivo o contemporaneo alla fonte; quantità non considerate. Giorni calendario Europe/Rome; maturazione non autorizza da sola l’invio.

8. **Esclusioni e blocchi specifici:** Ricambio: nessuna esclusione permanente per acquisto del ricambio; apre un nuovo ciclo. Si applicano tutte le politiche comuni sopra.

9. **Promozioni e stagionalità:**

Nessuna campagna destinazione registrata. Restano possibili precedenze di altri piani promozionati.

10. **Dipendenze:** Nessun wait_for_rules proprio. Restano consenso, distanza globale e precedenza degli altri piani.

11. **Scelta della primaria:** categoria Mirata; `plan_rank=400` (Ricambio maturo necessario a mantenere la routine del prodotto.). Si applicano interesse/piano contattato e ordinamento comune: il rango non supera automaticamente categoria, promozione o valore.

12. **Raggruppamento:** Ricambio e sostituzione restano separati quando data o ordine differiscono; il solo fatto di essere igiene orale non li unisce.

13. **Dopo contatto/acquisto/chiusura:** Nuovo ricambio acquistato apre un ciclo con nuovo riferimento acquisto e nuova maturazione; primo e secondo tentativo appartengono al singolo ciclo. Contatti, risposte, acquisto ed esclusioni seguono le politiche comuni; le secondarie condividono i tentativi. L’esito economico richiede registrazione manuale distinta dall’acquisto importato.

## Catalogo completo e limiti di copertura

Ogni riga seguente è un prodotto censito; presenza nel catalogo non significa regola attiva. SKU storici continuano a essere sorgenti/esclusioni anche se non vendibili.

| Prodotto | Categoria | SKU e stato commerciale |
| --- | --- | --- |
| Laifen Neo | hair_dryer | CQ15839 (nessuno stato variante esplicito); CQ15841 (nessuno stato variante esplicito); CQ15840 (nessuno stato variante esplicito); CR05272 (nessuno stato variante esplicito); CR05186 (nessuno stato variante esplicito); CR05227 (nessuno stato variante esplicito) |
| Ugello Concentratore Magnetico Laifen | hair_dryer_accessory | CP34473 (nessuno stato variante esplicito) |
| Ugello Diffusore Magnetico Laifen | hair_dryer_accessory | CP34520 (nessuno stato variante esplicito); CP34449 (nessuno stato variante esplicito) |
| Ugello Diffusore per Laifen SE Lite | hair_dryer_accessory | CP34510 (nessuno stato variante esplicito) |
| Laifen SE Lite | hair_dryer | CQ62986 (sell_until_exhausted); CL50959 (historical_only); CL50963 (historical_only); CL50964 (historical_only); CL50962 (historical_only) |
| Laifen Neo Special | hair_dryer | CR68941 (nessuno stato variante esplicito); CR68943 (nessuno stato variante esplicito); CR68942 (nessuno stato variante esplicito) |
| Laifen Swift Premium | hair_dryer | CP38476 (historical_only); CP38473 (historical_only); CP38475 (sell_until_exhausted) |
| Laifen Gift Edition | hair_dryer | CK8063 (sell_until_exhausted); CK80633 (sell_until_exhausted); CK80632 (historical_only); CK80631 (historical_only) |
| Laifen SE Special | hair_dryer | CL50966 (historical_only); CL50970 (historical_only); CL50961 (sell_until_exhausted); CL50968 (historical_only) |
| Laifen Mini | hair_dryer | CP34448 (nessuno stato variante esplicito); CP34447 (nessuno stato variante esplicito); CP34500 (nessuno stato variante esplicito); CR05263 (nessuno stato variante esplicito) |
| Supporto magnetico da parete Laifen Mini | hair_dryer_accessory | CP34501 (nessuno stato variante esplicito) |
| Laifen Air | hair_dryer | 1HD20-S-EU-PU-001 (nessuno stato variante esplicito); 1HD20-S-EU-WH-001 (nessuno stato variante esplicito); 1HD20-S-EU-PK-001 (nessuno stato variante esplicito) |
| Supporto magnetico da parete Laifen | hair_dryer_accessory | 30101-000092 (nessuno stato variante esplicito); 30101-000249 (nessuno stato variante esplicito); 30101-000248 (nessuno stato variante esplicito) |
| Laifen AutoCurl - Arricciacapelli Automatico | hair_styler | 1HC51-P-EU-BL-001 (nessuno stato variante esplicito); 1HC51-P-EU-WH-002 (nessuno stato variante esplicito) |
| Pochette Portaoggetti Laifen | hair_dryer_accessory | CL51809 (nessuno stato variante esplicito) |
| Spazzola Laifen | hair_care_accessory | 30101-000041 (nessuno stato variante esplicito); CL51811 (nessuno stato variante esplicito) |
| Laifen Wave - Spazzolino Elettrico con Travel Box | electric_toothbrush | CL97510 (historical_only); CL97511 (historical_only); CL97508X (historical_only); CP34472X (historical_only); CL97509 (historical_only); C027164 (historical_only); C027165 (historical_only) |
| Laifen Wave Travel Box | electric_toothbrush_accessory | CM61971 (nessuno stato variante esplicito) |
| Cavo di ricarica magnetico Laifen Wave | electric_toothbrush_accessory | 6973833031630 (nessuno stato variante esplicito) |
| Laifen Wave Pro - Spazzolino Elettrico | electric_toothbrush | CR95008 (nessuno stato variante esplicito); CR95009 (nessuno stato variante esplicito); CR95024 (nessuno stato variante esplicito); CR95017 (nessuno stato variante esplicito); CR95041 (nessuno stato variante esplicito); CR95016 (nessuno stato variante esplicito) |
| Base di Ricarica Laifen Wave Pro | electric_toothbrush_accessory | 30102-000170 (nessuno stato variante esplicito); 30102-000171 (nessuno stato variante esplicito) |
| Testine di Ricambio Laifen Wave Pro | electric_toothbrush_accessory | CR95042 (nessuno stato variante esplicito); CR95032 (nessuno stato variante esplicito); 6976973852011 (nessuno stato variante esplicito); CR94994 (nessuno stato variante esplicito) |
| Laifen P3 - Rasoio Elettrico a 3 Lame | electric_shaver | 1ER91-P-XX-BL-002 (nessuno stato variante esplicito); 1ER91-P-XX-WH-002 (nessuno stato variante esplicito) |
| Laifen P3 Pro - Rasoio Elettrico a 3 Lame | electric_shaver | CP96308 (nessuno stato variante esplicito); CP96436 (nessuno stato variante esplicito) |
| Testina di Ricambio per Laifen P3 Pro | electric_shaver_accessory | 30103-000046 (nessuno stato variante esplicito); 30103-000047 (nessuno stato variante esplicito) |
| Astuccio da Viaggio per Laifen P3 Pro | electric_shaver_accessory | 30103-000019 (nessuno stato variante esplicito); 30103-000021 (nessuno stato variante esplicito) |
| Laifen T1 Pro - Rasoio Elettrico a 1 Lama | electric_shaver | CP96306 (nessuno stato variante esplicito); CP96307 (nessuno stato variante esplicito) |

## Verifiche lasciate in stand-by

- `wave_legacy_travel_box_aluminum_identifiers`: Recuperare SKU e codice a barre della variante Alluminio della Travel Box del precedente Wave. **Effetto:** La variante Alluminio non può essere riconosciuta automaticamente negli acquisti finché mancano gli identificativi.
- `neo_special_magnetic_diffuser_compatibility`: Confermare se il diffusore magnetico venduto separatamente sia compatibile con Neo Special. **Effetto:** Nessuna opportunità diffusore per Neo Special finché la compatibilità non è confermata.
- `air_magnetic_concentrator_compatibility`: Confermare se il concentratore magnetico CP34473 sia compatibile con Air. **Effetto:** Nessuna opportunità concentratore per Air finché la compatibilità non è confermata.
- `air_magnetic_diffuser_compatibility`: Confermare se il diffusore magnetico venduto separatamente sia compatibile con Air. **Effetto:** Nessuna opportunità diffusore per Air finché la compatibilità non è confermata.
- `magnetic_wall_mount_other_models_compatibility`: Confermare quali modelli Laifen diversi da Neo siano compatibili con il supporto 30101-000092. **Effetto:** La regola del supporto resta attiva solo per Neo fino a nuove conferme.
- `se_lite_dark_gray_diffuser_identifiers`: Recuperare SKU ed EAN della variante storica Dark Gray disattivata. **Effetto:** Gli acquisti storici Dark Gray non possono essere riconosciuti automaticamente finché mancano gli identificativi.

Il diffusore magnetico standalone non ha una regola: nei modelli con dotazione confermata il diffusore è già incluso; non estendere a Neo/Neo Special/Air senza evidenza. Travel Box Wave, cavo Wave e base Wave Pro restano senza relazione commerciale. T1 Pro è riconosciuto come rasoio ma non genera percorsi propri. Le campagne Neo Special e Air non creano una destinazione retention. Retro compare nelle compatibilità, ma non è un prodotto sorgente con SKU censiti nelle 15 regole.

## Come usare la matrice Shopify

`REGOLE_DA_VALIDARE_SHOPIFY.csv` ha una riga per regola. I campi numerici vuoti significano **da misurare**, mai zero. `numero_clienti_iniziali_richiesto` è la numerosità da definire per il disegno di validazione; `numero_clienti_iniziali_osservati` è il conteggio estratto. Nessuna numerosità minima è approvata oggi. Dimensione campione clienti e numero eventi/cicli sono distinti. La distribuzione dei giorni riguarda acquirenti successivi; documentare i censurati. Per destinazioni alternative (P3/P3 Pro, finiture) produrre anche sottogruppi, senza sommare clienti duplicati. Per testare il calendario analizzare prima la distribuzione completa, poi confrontare finestre predefinite; non filtrare già a 45/75/90/150 giorni e concludere che quella soglia è confermata.
