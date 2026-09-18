# Istruzioni per modificare il repository

**Git conserva il passato. Il repository descrive il prodotto presente.**

1. Rispetta la fase richiesta. Consulta `project-docs/PRODUCT.md` quando il lavoro riguarda significato del prodotto, dati, privacy o decisioni commerciali. Non inventare regole Laifen.
2. Prima di creare un file, cerca quale file svolge già quella funzione. Dai a ogni responsabilità un posto riconoscibile; non creare strutture per funzioni future.
3. Quando sostituisci una logica, elimina quella precedente e aggiorna i suoi riferimenti. Non conservare copie `old`, `backup`, `v2` o `temp`.
4. Tieni separati i dati identificativi dall'analisi. Gli export reali vanno in `local-data/`, esclusa da Git; non tracciare dati personali o segreti.
5. Per ogni decisione deterministica modificata, verifica almeno un caso ammesso e uno escluso. Controlla i riferimenti e i file modificati.
6. Aggiorna la documentazione solo quando cambia una decisione o la posizione di una responsabilità. Quando esisterà codice, crea e mantieni una mappa «funzione → file» con soli percorsi reali.
7. Nella risposta finale spiega cosa hai cambiato, cosa hai rimosso e come l'hai verificato.
