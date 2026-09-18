# Retention Revenue Engine

Sistema operativo per identificare, monitorare e misurare opportunità di retention commerciale sui clienti Shopify.

## Stato

Progetto in sviluppo. La V0 utilizzerà export CSV manuali da Shopify e logica deterministica.

## Documentazione

- [project-docs/PRODUCT.md](project-docs/PRODUCT.md) — visione, obiettivi e decisioni di prodotto.
- [project-docs/ARCHITECTURE.md](project-docs/ARCHITECTURE.md) — mappa delle responsabilità del codice; oggi indica che non esiste ancora codice applicativo.
- [AGENTS.md](AGENTS.md) — regole vincolanti per modificare il repository.

## Sviluppo

Le istruzioni per installazione, avvio, test e build verranno aggiunte quando esisterà la prima implementazione funzionante.

## Dati locali

Gli export Shopify reali devono essere salvati in `local-data/` e non devono essere tracciati da Git.

## Recap del 18 settembre 2026

- **Codice applicativo:** non ancora avviato. Oggi è stata definita la base documentale del repository.
- **Prodotto:** `project-docs/PRODUCT.md` chiarisce il monitoraggio delle opportunità per singolo cliente e distingue valore nominale, follow-up e revenue attribuita.
- **Lavoro degli agenti:** `AGENTS.md` contiene regole verificabili contro logiche duplicate, codice superato e regole commerciali inventate.
- **Mappa e workflow:** `project-docs/ARCHITECTURE.md` attende responsabilità di codice reali; `.agents/skills/repository-change/SKILL.md` descrive come modificare il repo e ricordare procedure candidate.
- **Pulizia:** cinque documenti iniziali sono stati riuniti in `PRODUCT.md` per evitare duplicazioni. `.gitignore` esclude gli export locali.
- **Verifiche:** controllati i diff e l'esclusione di `local-data/` da Git. Non esistono ancora test applicativi da eseguire.
