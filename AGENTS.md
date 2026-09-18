# Regole per modificare il repository

**Principio:** Git conserva il passato. Il repository descrive il prodotto presente.

## Obiettivi e regole

1. **Rispettare il perimetro del task.** Implementa la fase richiesta senza anticipare funzionalità, integrazioni o strutture future. Leggi `project-docs/PRODUCT.md` quando servono significato del prodotto, dati, privacy o decisioni commerciali. Non inventare regole Laifen, compatibilità o criteri economici mancanti; segnala le decisioni ancora aperte.

2. **Avere un responsabile riconoscibile per ogni decisione.** Prima di aggiungere codice, cerca dove vive già quella responsabilità e modifica quel punto. Crea un file solo per una responsabilità nuova e distinta. La UI mostra le decisioni commerciali: non ne conserva una seconda implementazione.

3. **Sostituire senza accumulare.** Quando cambi una soluzione, aggiorna i riferimenti ed elimina implementazioni, import, helper e test superati. Non conservare copie `old`, `backup`, `v2`, `final` o codice commentato come riserva. Controlla che non rimangano duplicati o file senza scopo.

4. **Mantenere la modifica localizzata.** Tocca i file necessari al risultato richiesto. Evita refactor estranei e nuovi livelli di astrazione senza un'esigenza attuale. Se il cambiamento coinvolge più responsabilità, rendi esplicito nel resoconto perché era necessario.

5. **Verificare il comportamento deterministico.** Per una decisione commerciale modificata, verifica almeno un caso ammesso e uno escluso con test pertinenti. A parità di dati e versione delle regole, il risultato deve essere lo stesso. Esegui anche gli altri controlli pertinenti disponibili; dichiara soltanto quelli realmente eseguiti.

6. **Proteggere i dati dei clienti.** Usa dati identificativi solo dove servono al contatto, tenendoli separati dall'analisi. Conserva gli export reali in `local-data/`, esclusa da Git. Non tracciare dati personali reali, credenziali o segreti.

7. **Orientarsi con poco contesto.** Leggi prima la mappa delle responsabilità, se esiste, e i file coinvolti; approfondisci solo ciò che serve al task. Quando nasce il primo codice, crea `project-docs/ARCHITECTURE.md` come mappa breve «funzione → file» dei soli percorsi reali. Aggiornala quando nasce, si sposta o scompare una responsabilità, non per ogni modifica interna.

8. **Lasciare il repository comprensibile.** Prima di concludere, controlla il diff, i riferimenti obsoleti e gli eventuali file inutilizzati. Aggiorna `project-docs/PRODUCT.md` solo se cambia una decisione di prodotto. Riporta sinteticamente cosa hai cambiato, cosa hai rimosso, come hai verificato il lavoro e quali decisioni restano aperte.
