# Decisioni di prodotto

Questo file registra decisioni effettivamente prese. Se una scelta è ancora aperta, resta nella sezione dedicata; non trasformarla in una regola nel codice.

## Decisioni attuali

- **Sviluppo per fasi.** Ogni blocco viene specificato separatamente; non si anticipano funzionalità future.
- **Prima versione con CSV manuali.** Il flusso inizia da export Shopify caricati nel software; il contatto è manuale.
- **Decisioni deterministiche.** A parità di dati e regole, il risultato commerciale deve essere lo stesso. Un eventuale LLM futuro non decide l'idoneità delle opportunità.
- **Primo caso: Laifen Italia.** Conoscenza dei prodotti e regole specifiche saranno definite in seguito, senza supposizioni.
- **Opportunità distinta dai risultati.** Valore nominale e revenue attribuita non sono la stessa misura.
- **Repository aderente al presente.** Si modifica la responsabilità esistente e si rimuove la logica sostituita; Git conserva la storia.

## Questioni da definire nelle fasi pertinenti

- Campi e varianti degli export CSV reali.
- Dati dei prodotti, contenuto degli SKU e relazioni commerciali.
- Soglie temporali, esclusioni, priorità e significato della confidenza.
- Criterio di attribuzione degli ordini ai follow-up.
- Tecnologia di implementazione e modalità concreta di conservazione dei dati.
