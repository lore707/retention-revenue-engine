# Regole vincolanti del repository

**Principio:** Git conserva il passato. Il repository contiene solo l'implementazione corrente del prodotto.

## Prima di modificare

1. **DEVI** limitarti al task e alla fase richiesti. **NON DEVI** creare funzionalità, integrazioni, cartelle, API, astrazioni o placeholder per fasi future.
2. **DEVI** leggere `project-docs/ARCHITECTURE.md`, se esiste, e i file coinvolti. Cerca implementazioni equivalenti o sovrapposte prima di creare codice. Leggi `project-docs/PRODUCT.md` quando il task riguarda prodotto, clienti, privacy, opportunità, regole o misure economiche. Approfondisci altri file solo se servono.
3. **DEVI** individuare il file responsabile della funzione richiesta e modificarlo. Puoi creare un nuovo file solo se la responsabilità è nuova, non appartiene a un file esistente e il nuovo file rende più chiaro dove vive. **NON DEVI** creare una seconda implementazione della stessa responsabilità.

## Durante la modifica

4. **DEVI** mantenere la modifica localizzata. **NON DEVI** fare refactor, rinomini, spostamenti o introdurre pattern estranei al task. Se sono necessari cambiamenti in più responsabilità, spiegane il motivo nel resoconto finale.
5. Una decisione commerciale deve avere un solo punto di implementazione. La UI **NON DEVE** duplicare idoneità, tempi, priorità, compatibilità, relazioni tra prodotti, esclusioni, calcoli economici o attribuzione: deve mostrare il risultato della logica responsabile.
6. Se sostituisci una soluzione, **DEVI** aggiornare i riferimenti ed eliminare vecchia implementazione, import, helper, test e file diventati inutili. **NON DEVI** conservare copie `old`, `backup`, `v2`, `new`, `final`, `temp`, `legacy` o codice commentato come riserva.
7. **NON DEVI** inventare regole Laifen, contenuti degli SKU, compatibilità, tempi, soglie, formule economiche o criteri di attribuzione e conversione. Se manca una decisione necessaria, **FERMATI SU QUEL PUNTO**, segnala cosa va deciso e continua solo le parti indipendenti.
8. I dati identificativi servono solo dove necessari al contatto e devono restare separati dall'analisi. Gli export reali vanno in `local-data/`, esclusa da Git. **NON DEVI** tracciare dati personali reali, export Shopify reali, credenziali, token o segreti. Usa dati sintetici in test ed esempi.

## Dopo la modifica

9. Per ogni decisione deterministica modificata **DEVI** verificare con test pertinenti almeno un caso ammesso e uno escluso. Stessi dati e stessa versione delle regole devono produrre lo stesso risultato. **NON DEVI** dichiarare completa una modifica alla logica commerciale senza questa verifica.
10. Quando nasce il primo codice, **DEVI** creare `project-docs/ARCHITECTURE.md` come breve mappa «responsabilità → file canonico» con soli percorsi reali. In seguito aggiornala solo se nasce, si sposta o scompare una responsabilità. Aggiorna `project-docs/PRODUCT.md` solo se cambia una decisione di prodotto.
11. Prima di concludere **DEVI** controllare il diff, implementazioni duplicate, riferimenti obsoleti, import e funzioni inutilizzati, file senza scopo, TODO e test non più coerenti. Rimuovi ciò che è diventato inutile. Esegui i controlli pertinenti disponibili, come test, typecheck o build; riporta i controlli falliti e non dichiarare eseguiti quelli non svolti.
12. Nel resoconto finale riporta in modo sintetico: cosa hai cambiato, cosa hai rimosso, come l'hai verificato e quali decisioni restano aperte. Se una modifica lascia due posti in cui cercare la stessa responsabilità, **NON È CONCLUSA**.
