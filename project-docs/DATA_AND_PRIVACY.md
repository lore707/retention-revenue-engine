# Dati e privacy

## Origine dei dati

La prima versione userà export CSV manuali di Shopify. Il modello dei dati, i campi richiesti e le regole di import saranno definiti nella fase 2, dopo aver esaminato gli export effettivi.

## Separazione delle identità

Le analisi e le decisioni commerciali devono poter lavorare principalmente con identificativi pseudonimi, per esempio `CUST_000123`. Nome, email e telefono servono all'operatore per il contatto, ma non devono essere necessari per calcolare le opportunità. Il modo concreto di conservare e collegare queste informazioni verrà deciso insieme al modello dati.

Conserva eventuali export reali in `local-data/`, esclusa da Git tramite `.gitignore`. Non inserire nei file tracciati export reali, credenziali o dati identificativi dei clienti. I controlli sui dati e sull'accesso saranno definiti con l'implementazione dell'import.

## Misurazione

Tieni distinti opportunità teorica, contatto registrato, ordine successivo e revenue attribuita. Un ordine dopo il contatto non dimostra da solo che il contatto lo abbia causato. I criteri di attribuzione saranno definiti prima di implementare il relativo calcolo.
