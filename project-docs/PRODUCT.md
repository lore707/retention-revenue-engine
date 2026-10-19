# Retention Revenue Engine: prodotto e decisioni

## Obiettivo

Retention Revenue Engine è un sistema operativo per decidere e monitorare azioni di retention commerciale su clienti già acquisiti o comunque presenti in Shopify e contattabili secondo le regole di marketing applicabili.

Shopify rimane la fonte di riferimento per clienti, ordini, prodotti, varianti e storico degli acquisti. Il software usa quello storico per aiutare un operatore a capire **chi contattare, quando, cosa proporre, perché, quanto vale l'opportunità e cosa è successo dopo il follow-up**.

Il prodotto deve trasformare la storia di acquisto in una **coda operativa di opportunità commerciali spiegabili e monitorabili**:

storia del cliente → stato attuale → opportunità → proposta coerente → follow-up → risultato → valore economico osservato.

Il monitoraggio avviene a livello del singolo cliente; le opportunità e i risultati possono poi essere aggregati per prodotto, strategia e periodo.

## Prima versione

La dashboard può essere utilizzata sul PC oppure come servizio privato su Render. La versione online per un singolo operatore richiede accesso HTTP Basic su HTTPS. Può usare PostgreSQL su Supabase, anche con Render Free, oppure SQLite su disco persistente a pagamento; tutti i dati operativi sono protetti dalle credenziali del backend. Gli export caricati con PostgreSQL sono temporanei: ordini normalizzati, email separate, eventi, attivazione e registro import restano nel database remoto. La versione locale conserva SQLite e l'accesso senza credenziali sul solo loopback. Il trasferimento iniziale preserva tutte le tabelle, crea una copia locale, verifica ogni riga e rifiuta una destinazione non vuota. Non esiste una sincronizzazione automatica fra SQLite e Supabase: dopo il passaggio si usa un solo database operativo. La demo sintetica resta separata e temporanea. Hosting e salvataggio non cambiano consenso, regole, tentativi, priorità o attribuzione economica.

Export CSV manuale da Shopify → pulizia e import locali automatici → analisi dei clienti → regole deterministiche → opportunità spiegate → contatto manuale → follow-up registrato → nuovi ordini importati → verifica degli ordini successivi → misurazione. Lo storico operativo iniziale comprende i soli export disponibili e si amplia con i successivi; il sistema rivaluta i profili, senza considerare dimostrata l'assenza di acquisti non ancora importati.

Il primo caso è Laifen Italia. Informazioni sui prodotti e regole commerciali saranno definite nelle rispettive fasi, senza supposizioni. Per ora non sono previsti Shopify API, invii automatici, n8n, infrastrutture cloud complesse, LLM o agenti autonomi.

## Criteri di validazione operativa

La direzione del prodotto è un'ipotesi da verificare con un ciclo completo di import, decisione, contatto manuale e risultato osservato. La presenza di regole implementate non dimostra da sola l'utilità operativa o economica. Prima di ampliare le automazioni, valutare questi quattro criteri:

1. **Correttezza della selezione.** Confrontare proposte ed esclusioni con gli acquisti disponibili e le regole approvate: compatibilità, dotazioni incluse, prodotti già acquistati, consenso, tempi e coordinamento dei piani. Verificare casi ammessi ed esclusi e la riproducibilità a parità di dati, data e versione delle regole. I controlli esistenti restano nel motore canonico e nei test; la prova operativa deve anche verificare la completezza e l'aggiornamento dei dati reali.
2. **Utilità per l'operatore.** Verificare sul lavoro reale se la vista permette di capire chi contattare, con cosa e perché, chi attende e quale azione segue. Rilevare tempo impiegato, verifiche esterne necessarie e difficoltà incontrate, confrontandoli con la gestione senza il sistema. Metodo di rilevazione e criterio di successo restano da concordare; questa verifica non è oggi automatizzata.
3. **Coordinamento con newsletter e promozioni.** Confrontare le proposte con le comunicazioni effettivamente ricevute e con le offerte in corso. Il calendario promozionale già implementato influenza la priorità, ma non contiene lo storico degli invii delle newsletter. Restano da definire quali newsletter contino come contatto o proposta presentata e come incidano su attese e tentativi; finché mancano dati e politica non dichiarare il coordinamento verificato.
4. **Valore economico.** Valutare gli acquisti e i ricavi secondo la sezione «Misure economiche», insieme al margine e al lavoro necessario per ottenerli. Distinguere risultati attribuiti e vendite aggiuntive: queste ultime richiedono un confronto definito, non si deducono dalla sola successione invio-acquisto. Dati di costo, formula del margine, metodo di confronto, periodo di osservazione e soglie di successo restano da concordare; il sistema corrente non calcola margine o incremento causale delle vendite.

Questi sono criteri di valutazione del prodotto, non nuove regole di idoneità dei clienti né funzionalità già implementate. La prova può portare a proseguire, semplificare o rivedere il sistema; soglie o calcoli mancanti non vengono assunti dal backend.

## Il cuore del prodotto

Il sistema costruisce un'interpretazione commerciale dei fatti disponibili e la usa per creare e monitorare opportunità. Questa capacità si articola in tre responsabilità concettuali:

- **Conoscenza commerciale dei prodotti (knowledge model).** Descrive il significato commerciale del catalogo: contenuto dei precisi SKU, compatibilità, consumabili, accessori, benefici e relazioni tra prodotti. Queste informazioni vengono definite e validate dal business; non si deducono automaticamente dal fatto che due prodotti siano stati acquistati insieme.
- **Stato del cliente (state engine).** Ricostruisce lo stato attuale a partire dallo storico disponibile: acquisti, date, quantità, categorie acquistate, possesso dedotto, consumo stimato e contatti registrati. Viene rivalutato con i nuovi dati e alla data di riferimento della valutazione, secondo i principi della sezione «Come il sistema interpreta e aggiorna le opportunità».
- **Decisione commerciale (decision engine).** Combina conoscenza dei prodotti, regole commerciali, stato del cliente, storico e tempi. Genera proposte candidate, poi applica idoneità al contatto, esclusioni, timing, conflitti e priorità. Restituisce opportunità lavorabili ordinate e motivate, oppure nessuna azione o informazioni insufficienti.

Una relazione tra prodotti descrive una possibilità commerciale. Diventa un'opportunità per un cliente soltanto quando le condizioni della regola sono soddisfatte: compatibilità, dotazione già inclusa, acquisti successivi e tempi possono confermare o escludere la proposta. Le prime definizioni Laifen sono conservate nei file canonici indicati in `ARCHITECTURE.md`, distinguendo conferme del business, soglie sperimentali approvate e decisioni ancora aperte.

### Confine dei dati

Gli export Shopify completi vengono collocati in `local-data/`. Un processo locale avviato dall'operatore elimina le colonne superflue nello stesso file prima dell'import; se fallisce, l'import rifiuta il CSV completo. L'email è ancora necessaria per collegare ordini e rendere possibile il contatto; la riduzione non equivale ad anonimizzazione.

Il sistema conserva i dati importati necessari a ricostruire le decisioni e produce informazioni proprie: stato derivato, opportunità, motivi di esclusione, follow-up e risultati attribuiti. Shopify resta autorevole per i fatti provenienti dallo store; il nostro sistema registra le azioni commerciali svolte al suo interno.

I dati in ingresso vengono trasformati in un formato interno coerente per clienti, ordini e righe d'ordine. Le decisioni lavorano su questo formato, senza dipendere dal modo in cui i dati sono arrivati. I CSV sono il canale della V0; eventuali API o webhook futuri potranno alimentare lo stesso modello, mantenendo esplicite completezza e data di aggiornamento dei dati disponibili.

### Dalla decisione al risultato

Il flusso concettuale completo è:

Shopify → import e dati normalizzati → stato del cliente + conoscenza commerciale + regole → proposte candidate → controlli e priorità → opportunità lavorabili → operatore e follow-up → nuovi ordini osservati → attribuzione e misurazione.

La dashboard rende questo processo consultabile e operativo. Il valore del prodotto comprende l'intero percorso, dalla proposta al risultato per ogni cliente.

La V0 lavora sulla retention dei clienti presenti nello store, principalmente dopo l'acquisto. Carrello, checkout e carrello abbandonato sono possibili estensioni da valutare in seguito, con dati e condizioni propri. La separazione tra ingresso dati e decisioni consente di valutarle senza costruire ora quei flussi.

## Focus commerciale

Le strategie possibili comprendono cross-sell, replenishment, maintenance/replacement, acquisto di un secondo prodotto o espansione di categoria e reactivation quando appropriata. La proposta non dipende soltanto dal tempo trascorso dall'ultimo ordine: contano il prodotto e lo SKU acquistati, ciò che era incluso, ciò che il cliente possiede già, le relazioni tra prodotti, le tempistiche e le regole commerciali definite.

Tutte le proposte commerciali sono proattive: non richiedono una verifica preventiva del bisogno o dell’interesse. Acquisti, compatibilità e regole approvate rendono una proposta pertinente; il bisogno resta un’ipotesi, non un fatto attribuito al cliente. La politica comune è definita in `src/rules.json`, in `shared_policies.customer_interest_required`. L’interesse espresso dopo il contatto orienta la conversazione; rifiuti, consenso, possesso, tempi e coordinamento continuano a determinare quali azioni sono ammesse.

Il sistema deve poter concludere che **oggi non esiste alcuna azione commerciale sensata**. Questa è una decisione valida, non un errore da riempire con una proposta generica.

## Cosa deve spiegare un'opportunità

La vista operatore deve mostrare per ogni ordine un riepilogo breve della decisione: prodotto acquistato, consenso, proposta principale, alternative compatibili, tempi, motivi, eventuali esclusioni e piani successivi. La spiegazione legge l'esito del motore sul profilo cliente aggiornato; l'ordine indica la fonte della proposta, ma gli acquisti di altri ordini possono cambiarne l'idoneità. Finché manca una stima verificata, la probabilità di acquisto viene indicata come non disponibile.

- **Cosa proporre:** il prodotto e la relazione con quanto già acquistato.
- **Perché quel prodotto:** caratteristiche, compatibilità, contenuto del preciso SKU, possesso ed esclusioni.
- **Perché ora:** date e condizioni temporali applicabili.
- **Beneficio per il cliente:** funzione o utilità concreta.
- **Evidenza:** dati e regole che hanno prodotto la decisione.
- **Valore nominale:** potenziale della proposta, distinto dalla revenue attribuita.

Il sistema deve rendere verificabile anche il motivo di un'esclusione. I numeri usati negli esempi diventano regole solo quando esplicitamente approvati e registrati nella definizione pertinente; non si estendono automaticamente ad altre relazioni o condizioni. A parità di dati e regole, la decisione deve essere la stessa.

## Segnali del profilo cliente

Le sei casistiche descrivono il cliente e possono coesistere; non sono nuove relazioni tra prodotti. Le condizioni approvate vivono in `src/rules.json`, in `customer_signals`. Primo acquisto significa un ordine valido osservato, cliente ricorrente almeno due, alta attività recente almeno tre negli ultimi 90 giorni. Il conteggio include soltanto ordini non vuoti con tutte le righe valide; ordini incerti, annullati, resi o futuri non qualificano il conteggio. La finestra comprende 90 date di calendario, inclusa la data di valutazione. Un ordine con più prodotti conta una sola volta.

Multicategoria richiede almeno due categorie principali in righe valide osservate: cura dei capelli (phon e AutoCurl), igiene orale (Wave/Wave Pro), rasatura (rasoi). Accessori e ricambi non aggiungono categorie. I conteggi riguardano soltanto gli acquisti importati: «primo acquisto» non prova che non esistano ordini precedenti fuori dal campione.

La coda Overview e la scheda cliente espongono i segnali calcolati dal backend, con conteggi e categorie. Possibile B2B richiede dati aziendali e criteri di acquisto professionale ancora da definire; alto valore storico richiede spesa netta effettiva e un criterio di top 20% fra i clienti osservati. Entrambi sono indicati come non valutabili, non come assenti. Non si usa il prezzo di catalogo per ricostruire la spesa storica.

Le categorie commerciali sono una partizione dei clienti osservati: Opportunità mirate (almeno un completamento funzionale o ricambio nel piano lavorabile), Opportunità da testare (almeno un complemento, espansione o upgrade lavorabile e nessuna mirata attuabile), Nessuna azione immediata (attese, blocchi, dati incerti o nessuna proposta). Un cliente compare in un solo gruppo; la somma coincide con tutti i clienti analizzati, non soltanto con i contattabili. I segnali cliente restano filtri indipendenti: ricorrenza non crea una proposta e B2B/alto valore restano non valutabili. Le alternative accodate restano visibili senza diventare automaticamente contattabili.

## Monitoraggio delle opportunità

L'Overview organizza il lavoro in tre gruppi esclusivi sul piano attuale: **Da seguire** raccoglie risposte da gestire e follow-up consentiti oggi; **Nuove opportunità** raccoglie i primi contatti del piano maturato da meno di 30 giorni; **Storico da recuperare** raccoglie quelli maturati da almeno 30 giorni. La soglia organizzativa è in `src/rules.json`, `overview_worklist.recent_days`: non fa scadere proposte né anticipa contatti. La maturazione è quella del piano, non la data dell'acquisto. Un cliente già contattato per un piano precedente può rientrare nei primi contatti del piano successivo. Futuri, attese e blocchi restano consultabili in Retention.

I tre pulsanti selezionano una sola lista; senza una scelta esplicita si apre il primo gruppo non vuoto nell'ordine Da seguire, Nuove opportunità, Storico. I conteggi dei gruppi precedono i filtri. Categoria mirata/test, prodotto principale, strategia, profilo e ricerca si combinano sulla proposta principale corrente; altri piani e alternative sono consultabili in Retention e nel dettaglio. I filtri della lista non cambiano KPI o ricavi del grafico. Le categorie commerciali di Retention restano distinte dai gruppi di lavoro dell'Overview.

Nell'ordine consigliato di Nuove opportunità e Storico vengono prima le mirate, poi i test: dentro ogni categoria i prodotti si alternano stabilmente, mantenendo i piani più vecchi prima per ciascun prodotto. Il primo giro parte dal prodotto con la maturazione più vecchia, con nome prodotto e ID cliente come spareggi deterministici. L'alternativa Raggruppa per prodotto mantiene mirate prima dei test, poi prodotto e maturazione. In Da seguire vengono prima le risposte, ordinate dalla prima data di contatto del piano, poi i follow-up dalla data minima consentita dal motore; gli spareggi usano l'ID cliente. Qui il selettore di ordinamento è disabilitato. Nessun ordinamento cambia il piano primario, i prodotti, i tentativi o il valore scelti dal motore.

Le foto fornite dal business sono associate nel catalogo e conservate come asset locali. Quando una foto è assegnata esplicitamente a una variante, prevale sull'immagine rappresentativa del prodotto; il colore non viene dedotto automaticamente dalla foto. Le miniature compaiono accanto alle proposte in tabella, nella scheda cliente (varianti e storico compresi) e nelle regole. Un prodotto senza immagine conserva la presentazione testuale; la foto P3 non viene associata a P3 Pro. Le foto generiche di base e testine Wave Pro rappresentano il prodotto, non distinguono materiali o tipi delle varianti. Le immagini non modificano le decisioni commerciali.

Le foto Neo Black/White/Purple rappresentano il colore per entrambe le configurazioni. Il testo alternativo specifica che la foto mostra tre ugelli; dotazioni, compatibilità ed esclusioni continuano a dipendere dalla configurazione dello SKU, senza deduzioni dall'immagine.

Le foto di diffusore SE Lite, Travel Box ABS, spazzole Silver/Pink, pochette, concentratore, SE Special e Gift Edition sono gli originali corrispondenti agli allegati del business, recuperati dal catalogo ufficiale Laifen perché i percorsi locali indicati non erano disponibili. SE Special è associato ai colori identificati, senza usare l'ordine degli allegati; White usa l'immagine assegnata allo SKU CL50966 e conserva il formato PNG. `GIFT-GRIGIO.jpg` rappresenta White CK8063, come indicato dal business e confermato dall'immagine assegnata alla variante ufficiale. La Travel Box fotografata è associata soltanto a CM61971, per Wave ABS.

La sezione Regole si apre sui tre percorsi Asciugacapelli, Rasoi e Spazzolini. Le fasi sono derivate dal backend dalle sorgenti, dal percorso commerciale e dal timing delle 15 regole: accessori, proposte successive, cicli di ricambio e ramo stagionale parallelo. Ogni fase mostra le proposte per i modelli ammessi in tabella; esclusioni, compatibilità, configurazioni e SKU/prezzi restano espandibili. I modelli riconosciuti senza regole sorgente, come T1 Pro, sono indicati esplicitamente. Un nuovo acquisto comporta rivalutazione, non riavvio automatico dei tentativi. Le date rappresentano maturazione, non invii programmati. I tre pulsanti famiglia selezionano un percorso e azzerano i filtri di consultazione; il filtro di acquisto iniziale porta alla famiglia corrispondente. I selettori flottanti di strategia e prodotto restano disponibili in una sezione espandibile. Le Regole comuni raccolgono filtri/categorie/stati/profili Retention, composizione/priorità dei piani, contatti/esiti e revenue. Tutti i contenuti operativi provengono da rules_summary; nessun secondo motore commerciale nel frontend. Grassetti e colori distinguono mirate, test e attese senza affidare il significato al solo colore. La pagina è di sola consultazione.

La scheda cliente condivisa fra Overview e Retention mette in evidenza la proposta principale, il prezzo e i motivi sintetici restituiti dal backend. Per i completamenti verificati mostra compatibilità, assenza nella dotazione e maturazione; per le altre strategie conserva la motivazione pertinente, senza attribuire gli stessi requisiti a ogni prodotto. Seguono le alternative del piano, le prossime opportunità in righe espandibili e lo storico acquisti. Una sola indicazione riassume le dipendenze dal piano attuale; date future e dettagli delle regole restano secondari. Il profilo e il prossimo passo occupano la colonna destra: prima dell'invio il modulo registra il contatto effettuato, dopo l'invio mostra ultimo contatto, prossima data determinabile ed esiti consentiti. Le emoji 🔁 e 🏷️ accompagnano i segnali di ricorrenza e multicategoria; B2B e alto valore non valutabili restano in «Altri dati». Varianti, dati tecnici e contatti/esiti completi sono consultabili tramite sezioni espandibili. L'operatore presenta le opzioni nella stessa email come prodotti acquistabili singolarmente, senza implicare un bundle obbligatorio. La gerarchia del motore resta invariata e non rappresenta una probabilità di acquisto; la UI non ricostruisce compatibilità, esclusioni o ordinamento. Sidebar e barra superiore conservano la struttura esistente.

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
- **Attributed Revenue:** importo effettivamente pagato che l'operatore verifica in Shopify e collega manualmente a un acquisto successivo a un follow-up pertinente. L'ordine Shopify può essere attribuito una sola volta; correzioni e rimborsi modificano l'importo mantenendo la storia. Attribuzione non equivale a prova di causalità.
- **Follow-up Conversion Rate:** quota delle opportunità lavorate che soddisfa il risultato di conversione definito. Denominatore, finestra temporale e trattamento dei casi ancora aperti vanno stabiliti prima del calcolo.

Queste misure devono consentire di distinguere valore disponibile, attività svolta e risultati osservati, fino alla singola opportunità. Nessun valore di opportunità non lavorata o scaduta va presentato come denaro certamente perso.

## Overview operativa

L'Overview mostra, nell'ordine, i quattro KPI generali, il grafico Ricavi da retention, i tre accessi colorati e la coda clienti. Gli accessi sono Opportunità mirate, Opportunità da testare, Nessuna azione immediata. I conteggi sono esclusivi, calcolati dal backend sui profili osservati con consenso email valido; gli ordini non attribuiti restano separati. I collegamenti aprono Retention con la categoria selezionata. I quattro KPI sono globali e indipendenti dai filtri.

La presentazione segue lo stile della Retention: card leggere, icone e colori semantici sobri, spaziatura e tabella coerenti. Il periodo del grafico usa lo stesso popup ricercabile e accessibile dei filtri Retention, con selezione singola, descrizione dell'aggregazione e conservazione del periodo nell'URL. Gli accessi alle tre categorie mantengono i conteggi backend e aprono Retention; non filtrano i KPI dell'Overview. L'import CSV, la scheda cliente e la navigazione conservano il funzionamento esistente.

- **Clienti da contattare oggi:** profili certi con un piano lavorabile alla data di valutazione; consenso valido e assenza di casi di revisione sono condizioni del backend.
- **Valore potenziale:** somma del valore nominale della sola proposta principale di ciascun piano lavorabile, senza sommare le alternative. Non è un ricavo né una previsione di conversione.
- **Follow-up registrati:** numero cumulativo degli eventi di contatto fino alla data di valutazione.
- **Revenue attribuita:** totale cumulativo degli acquisti verificati manualmente, con le correzioni registrate fino alla data di valutazione.
- **Grafico:** importi verificati per data dell'acquisto, con giorni senza vendite a zero. Le correzioni aggiornano l'importo nel giorno dell'acquisto originale. Il selettore modifica soltanto il grafico: 30/90 giorni inclusivi fino alla valutazione; 6/12 mesi di calendario fino alla valutazione, aggregati per mese e con eventuali mesi parziali ai confini. Non è una curva cumulativa.
- **Coda:** una riga per cliente lavorabile; non essendo stimata la probabilità, non si inventano fasce di priorità. Le righe sono ordinate per valore nominale decrescente e ID cliente a parità di valore. La scelta commerciale del piano resta responsabilità del motore.
- La pagina rivaluta il backend all'apertura, al cambio del periodo, dopo una registrazione e ogni minuto mentre è visibile. L'avvio predefinito legge il database locale degli ordini importati e usa il giorno corrente Europe/Rome. La demo richiede l'opzione esplicita `--demo`, dichiara dati sintetici e una data fissa coerente con Figma. Apri mostra il dettaglio operativo comune con storico e registrazione delle attività; in demo le registrazioni restano nel database sintetico temporaneo.

## Retention operativa

- Retention, aperta dalla barra laterale, mostra una sola volta i clienti con consenso email valido. Consensi negati, mancanti o discordanti sono esclusi da lista, ricerca e conteggi delle categorie di Overview e Retention; gli acquisti e gli eventi non vengono cancellati. I contatti storici restano nel KPI attività; il KPI ricavi, il numero di ordini verificati e il grafico includono solo vendite dei clienti con consenso email valido alla data di valutazione. Le vendite escluse restano conservate nello storico; un consenso tornato valido nei dati importati rende nuovamente visibile il cliente. I quattro filtri sono categoria commerciale attuale, stato del piano, strategia e profilo cliente. La ricerca include ID, numero d'ordine di origine e prodotti. Categoria e profilo riguardano il cliente; stato e strategia devono corrispondere allo stesso piano/opportunità. La strategia comprende anche le secondarie e i piani accodati. Il risultato conserva la raccomandazione globale e mostra separatamente le corrispondenze.

- Il selettore Profilo cliente restringe la lista per un segnale alla volta; i badge mostrano tutti i segnali coesistenti. B2B e alto valore sono disabilitati perché non valutabili. I profili non cambiano la categoria commerciale.
- I quattro filtri usano popup ricercabili con icone, descrizioni, selezione singola, navigazione da tastiera e chip rimovibili. Categoria, stato, strategia, profilo e ricerca si conservano nell’URL insieme agli eventuali parametri estranei ai filtri. I conteggi delle categorie sono globali, prima degli altri filtri, e provengono dal backend; stato, strategia e profilo non mostrano conteggi non disponibili. Il restyling non modifica le decisioni del motore.
- I quattro KPI generali compaiono soltanto in Overview. Retention segue il mockup approvato: titolo e riepilogo, card con quattro filtri, ricerca e reset, indicazione della ricerca attiva e tabella a otto colonne. Clienti analizzati, contattabili oggi, corrispondenze e prezzi nominali sono letti dal backend. Apri porta direttamente alla scheda completa; il numero di piani consultabili apre il pannello rapido con profilo, ordine di origine, proposte e corrispondenze aggiornate. La registrazione di contatti ed esiti resta nella scheda completa; il pannello non invia email. L'aggiornamento della lista chiude il pannello per evitare di lasciare una decisione datata visibile. Le spiegazioni aggiuntive e la data di valutazione rimangono in «Come leggere la lista». Sidebar e barra superiore conservano la struttura attuale.

- Gli stati appartengono ai piani: aperto da lavorare quando attuabile e mai contattato, in corso quando già contattato e ancora aperto, chiuso secondo gli esiti canonici, in attesa/sospeso per piani nuovi non attuabili. Un secondo tentativo resta in corso e può essere contattabile. Un cliente può avere un vecchio piano chiuso e uno nuovo aperto: il filtro conserva lo storico, la categoria dipende dalla situazione attuale.
- Chiusi conserva eventi e risultato: acquisto verificato in verde, rifiuto esplicito del piano in rosso, tentativi esauriti o piano non più proponibile in grigio. Una vendita osservata nei CSV può rendere il piano non più proponibile, ma non attribuisce revenue né una conversione verificata. I nuovi cicli non cancellano la storia dei cicli precedenti.
- Il limite dei tentativi e i criteri di chiusura restano quelli del motore. Non si introduce una scadenza per mancata risposta. Una risposta o il rifiuto di un singolo prodotto non equivale al rifiuto dell'intero piano.
- La lista segue categoria commerciale e valore nominale decrescente, con ID come spareggio. La paginazione mostra 25 clienti per pagina. Il pannello rapido conserva la proposta principale, le alternative, gli stati e le corrispondenze ai filtri. La consultazione di un piano alternativo non lo autorizza al contatto; la scheda completa applica i vincoli del motore.
- I casi incerti compaiono in Nessuna azione immediata e non sono contattabili. Dal dettaglio l'operatore registra contatti manuali ed esiti, con verifica del backend alla data indicata. Il recapito rimane soltanto nel dettaglio operativo. Le email continuano a essere inviate fuori dal sistema.
- Gli acquisti richiedono il contatto di riferimento, l'ID ordine Shopify, lo SKU fra quelli delle proposte registrate, data, importo in euro e conferma della verifica manuale. Le correzioni richiedono la vendita originale, il nuovo importo totale e una motivazione. Un doppio invio della stessa registrazione non duplica l'evento. Al salvataggio vengono rivalutati coda e riepiloghi; lo storico conserva gli eventi. Prezzi storici non conservati nei contatti restano sconosciuti, senza ricostruire sconti o SKU effettivamente presentati. Importi delle vendite verificate usano le stesse correzioni dell'Overview.

## Dati e privacy

La prima versione userà export CSV manuali. Nell'export ordini Shopify esaminato sono disponibili ID ordine, righe con SKU e quantità, timestamp, stato finanziario, evasione, annullamento, importo rimborsato e il campo `Accepts Marketing`. L'EAN viene collegato dal catalogo. Se il campo SKU contiene un EAN univoco del catalogo, l'importatore lo normalizza allo SKU della relativa variante; uno SKU esatto prevale e codici sconosciuti o EAN ambigui non vengono dedotti. Questo riconosce anche Neo Special Black 6942590700097 → CR68943 e Blue 6942590700103 → CR68942. La normalizzazione non attribuisce compatibilità nuove. L'export non contiene un ID della singola riga d'ordine né il dettaglio dei prodotti resi; casi ambigui restano da verificare. Per decisione del business `Accepts Marketing` viene assunto come corretto per il consenso email del profilo quando tutti gli ordini associati mostrano lo stesso valore `yes` o `no`. Valori mancanti o discordanti non abilitano il contatto. Questo campo non abilita SMS o WhatsApp.

Il `Customer ID` Shopify non è richiesto per associare gli ordini: si usa l'email normalizzata come chiave di collegamento e si assegna un ID locale pseudonimo al profilo. I recapiti restano separati dai fatti di acquisto e dallo stato di consenso. Un ordine senza email resta non attribuito. L'email può cambiare o essere condivisa: il profilo raggruppa acquisti dello stesso indirizzo, senza verificare che appartengano alla stessa persona. L'export clienti separato non fa parte del flusso email corrente.

Il programma di retention considera i contatti gestiti dal sistema a partire dalla sua data di attivazione. I contatti commerciali precedenti non sono recuperabili: per i tentativi e gli intervalli si parte da zero, senza affermare che il cliente non abbia ricevuto messaggi in passato. L'attivazione avviene dopo il caricamento e la verifica dello storico ordini; un CSV campione non basta. La vista operativa mostra soltanto proposte mature con consenso email valido e dati d'acquisto non incerti. Gli ordini senza email, gli acquisti ambigui, gli SKU sconosciuti e i consensi discordanti richiedono revisione separata.

Le analisi devono poter usare soprattutto ID pseudonimi, per esempio `CUST_000123`. Nome, email e telefono servono all'operatore per il contatto, ma non per calcolare l'opportunità. Il collegamento concreto tra identità e analisi sarà deciso con il modello dati. Eventuali export reali vanno in `local-data/`, esclusa da Git; non inserire dati personali, credenziali o export reali nei file tracciati.

Opportunità teorica, contatto registrato, ordine successivo e revenue attribuita sono fatti distinti. Nella prima versione l'operatore verifica in Shopify l'acquisto della proposta, ne registra ID ordine, SKU, data e importo effettivamente pagato, collegandolo a un contatto precedente dello stesso piano. Il prezzo di catalogo resta solo valore potenziale. La correzione manuale dell'importo conserva l'evento originale; nessuna importazione CSV attribuisce automaticamente revenue.

## Percorso e stato

La struttura e i principi del repository sono definiti. Il prossimo percorso costruisce e valida il modello commerciale in quattro fasi.

Censiamo il catalogo e documentiamo i fatti verificabili. Per ogni prodotto formuliamo ipotesi commerciali e relazioni direzionali. Definiamo quali condizioni del cliente rendono attivabile ciascuna relazione. Verifichiamo disponibilità dei dati ed evidenze storiche, poi approviamo un primo insieme di regole da implementare e monitorare.

### 1. Mappare il catalogo

Capire cosa esiste e cosa riceve il cliente quando acquista. Raccogliere prodotti, varianti/SKU, bundle, accessori e consumabili; documentare contenuti delle confezioni e compatibilità, indicando fonti e informazioni da verificare.

**Risultato:** una mappa del catalogo che distingue chiaramente le configurazioni acquistabili.

### 2. Analizzare il ruolo commerciale di ogni prodotto

Capire quali bisogni soddisfa il prodotto e quali esigenze possono emergere dopo l'acquisto. Valutare benefici, utilizzi, consumabili, possibili completamenti, upgrade o sostituzioni. Separare sempre i fatti documentati dalle ipotesi commerciali.

**Risultato:** una scheda sintetica per prodotto, con possibilità commerciali, limiti e domande aperte.

### 3. Definire le relazioni tra prodotti

Stabilire quale prodotto potrebbe essere proposto a partire da un altro e perché. Per ogni relazione indicare prodotto di partenza, prodotto proposto, beneficio e tipo: `ACCESSORY_ATTACH`, `ACCESSORY_COMPLETION`, `USE_CASE_COMPLEMENT`, `CATEGORY_EXPANSION`, `REPLENISHMENT`, `UPSELL`, `REPLACEMENT` o `SECOND_UNIT`.

Le relazioni sono direzionali e devono avere una motivazione concreta. Non è necessario trovare una proposta per ogni prodotto. I confini operativi tra i tipi saranno precisati durante l'analisi.

**Risultato:** una tabella delle relazioni commerciali, con motivazioni, vincoli e ipotesi da verificare.

### 4. Definire e verificare le regole di attivazione

Stabilire quando una relazione diventa un'opportunità per uno specifico cliente. Per ogni regola definire quali acquisti e condizioni sono necessari, quando la proposta può avere senso, cosa la esclude o la rimanda e quali dati servono per decidere.

Verificare la disponibilità dei dati e confrontare le ipotesi con lo storico. Approvare quindi un primo insieme di regole da implementare, lasciando espliciti i punti ancora incerti. Una compatibilità verificata non rende automaticamente certi il bisogno del cliente o il timing della proposta.

**Risultato:** regole spiegabili che producono opportunità attive, `NO ACTION` oppure una segnalazione di dati insufficienti.

### Come procedere e primo traguardo

- Controllare presto un campione degli export per verificare quali informazioni sono realmente ricostruibili; l'analisi approfondita dello storico può venire dopo.
- Completare prima la panoramica del catalogo, poi procedere una famiglia di prodotti alla volta. Validare un primo caso completo senza aspettare di analizzare ogni prodotto.
- Il primo traguardo è spiegare, per un cliente e una relazione commerciale, perché l'opportunità è attiva, esclusa, rimandata oppure non valutabile per mancanza di dati. Verificarlo con casi concreti e risultati attesi prima di estendere il modello.

Le quattro fasi costruiscono il modello commerciale. Lo sviluppo partirà dal primo insieme di regole approvate, collegando import CSV, stato del cliente e opportunità spiegabili. Seguiranno gestione delle opportunità, follow-up, risultati, attribuzione economica e dashboard, dopo aver definito i relativi criteri.

Questo percorso non autorizza a costruire in anticipo le fasi successive.

## Punti in stand-by

Le verifiche concrete ancora sospese sono registrate una sola volta in `src/catalog.json`, nel campo `standby_checks`. Ogni voce indica la domanda, i prodotti coinvolti e l'effetto commerciale finché manca la conferma. Una voce in stand-by non autorizza nuove compatibilità o regole commerciali.

## Decisioni prese

- Il flusso iniziale usa CSV manuali e contatti manuali.
- Nella V0 la disponibilità di tutti i prodotti proposti viene verificata dall'operatore prima della proposta. Il motore non richiede dati di magazzino per generare le opportunità.
- I completamenti e accessori degli asciugacapelli formano un piano dal giorno 15 con una proposta in evidenza e tutte le altre compatibili non possedute come alternative o aggiunte. AutoCurl ha una mail dedicata dal giorno 45; le espansioni hanno un piano separato dal giorno 75. Le opportunità restano uniche per cliente/regola e partono dal primo acquisto valido della configurazione interessata.
- Dal giorno 75 dopo il phon, Wave Pro e rasoi P3/P3 Pro condividono una mail di espansione, separata da AutoCurl del giorno 45. Le esclusioni delle categorie sono indipendenti; se entrambe possedute il piano non ha proposte. P3 Pro e P3 sono alternative e la primaria segue le priorità del motore, senza imporre Wave Pro come primo. Wave / Wave Pro → Neo resta a 90 giorni, esclusa con qualsiasi phon già acquistato. Nessuna espansione rasoio → phon/spazzolino o spazzolino → rasoio.
- SE Lite è in esaurimento senza riassortimento: solo Green è attualmente vendibile secondo conferma del business. Le altre colorazioni restano nel catalogo per riconoscere gli acquisti storici e valutare il completamento con diffusore, assente in tutte le dotazioni confermate. Essere fuori vendita non rende irrilevante un acquisto storico.
- Swift Premium è in esaurimento senza riassortimento: solo Golden Pink è attualmente vendibile secondo conferma del business. Golden White e Golden Blue restano nel catalogo per riconoscere gli acquisti storici e valutare il completamento con concentratore, assente dalla dotazione confermata.
- Gift Edition è in esaurimento senza riassortimento: White e Red sono vendibili fino a esaurimento; Green e Black restano nel catalogo per riconoscere gli acquisti storici. Tutte le varianti includono già concentratore e diffusore magnetici, quindi il loro acquisto esclude una proposta di completamento con questi accessori.
- SE Special è in esaurimento senza riassortimento: Matte Pink è vendibile fino a esaurimento; Matte White, Matte Blue e Matte Purple restano nel catalogo per riconoscere gli acquisti storici. Tutte le varianti includono già ugello standard, concentratore e diffusore magnetici, quindi il loro acquisto esclude proposte di completamento con questi accessori.
- Il supporto magnetico da parete 30101-000092 è compatibile con entrambe le configurazioni Neo, non è incluso e viene proposto dopo almeno 15 giorni dall'acquisto. La compatibilità con tutti gli altri modelli resta in stand-by fino a conferma del business.
- Le foto del supporto Neo distinguono Silver, Gray e Star Light. Gray (30101-000249) e Star Light (30101-000248), con i rispettivi EAN, sono censiti dal catalogo pubblico Laifen verificato il 14 ottobre 2026; il possesso di queste varianti esclude il completamento già soddisfatto. La destinazione della regola resta lo SKU Silver storico 30101-000092. Il sito riporta CL51817 per Silver con lo stesso EAN: la riconciliazione del codice corrente resta da verificare, senza sostituire lo SKU storico durante l'aggiunta delle foto.
- Mini è una gamma corrente destinata al riassortimento in tutte e quattro le colorazioni. La confezione include ugello standard magnetico e custodia da viaggio; concentratore e diffusore magnetici venduti separatamente non sono compatibili. Il supporto magnetico da parete CP34501 è compatibile, non incluso e viene proposto secondo la regola approvata dopo almeno 15 giorni dall'acquisto del Mini. A chi ha acquistato qualsiasi altro asciugacapelli Laifen, il Mini viene proposto come secondo phon compatto da viaggio, palestra o seconda casa solo nelle finestre annuali 15 maggio–5 settembre e 15 dicembre–15 gennaio, estremi inclusi, lasciando scegliere fra le quattro colorazioni. Non è richiesta un'attesa di 180 giorni dall'acquisto: se il phon viene acquistato nella finestra, la proposta è subito valutabile, altrimenti attende la prima apertura successiva. Anche un eventuale secondo contatto deve rientrare in una finestra, rispettando almeno 15 giorni dal primo; restano al massimo due tentativi complessivi senza riapertura automatica negli anni successivi. Chi possiede già un Mini è escluso. La proposta è proattiva: non richiede verifica preventiva del bisogno o dell’interesse.
- Neo è la destinazione dell'espansione dalla categoria spazzolini. Vengono mostrate per prime le tre varianti a tre ugelli da 149,99 €, mantenendo disponibili anche le tre varianti a due ugelli da 134,99 €. Il valore nominale prudenziale del piano resta 134,99 €.
- Air è una gamma corrente destinata al riassortimento in tutte e tre le colorazioni. La confezione include soltanto l'ugello standard magnetico e il manuale utente oltre al phon. La compatibilità del concentratore CP34473 e del diffusore magnetico venduto separatamente resta da confermare; fino alla conferma Air non genera opportunità di completamento accessori.
- La Spazzola Laifen Silver/Pink è un complemento d'uso riassortibile per chi ha acquistato qualsiasi asciugacapelli Laifen. Viene proposta dopo almeno 15 giorni; l'acquisto di una delle due varianti esclude l'unica opportunità spazzola del cliente.
- La Pochette Portaoggetti Laifen da 29,99 € è un cross sell per tutti gli asciugacapelli Laifen tranne Swift Premium, che la include già. Viene valutata dopo almeno 15 giorni; un acquisto della pochette esclude l'unica opportunità condivisa del cliente.
- AutoCurl da 99,99 € è valutabile dal giorno 45 dopo qualsiasi phon, in una mail dedicata. Black e White restano opzioni; AutoCurl rimane complemento da testare ed è escluso se già acquistato. Attende i piani accessori applicabili dello stesso ordine; una promozione può precedere soltanto complementi da testare mai contattati. Il piano espansioni a 75 giorni non eredita questa dipendenza; restano priorità globali, piani contattati e almeno 15 giorni fra contatti. Maturazione non significa invio.
- Wave Pro è censito come spazzolino elettrico autonomo nelle sei varianti osservate. È anche la destinazione dell'espansione dalla categoria asciugacapelli, con valore nominale prudenziale di 99,99 € e scelta fra tutte le varianti. La confezione include una testina Pro Whitening, una testina Pro antiplacca, una custodia da viaggio e un caricatore wireless. Le confezioni da tre testine Pro Whitening, Pro Plaque Removal, Pro Gum Care e Pro Max Brush sono accessori compatibili. La prima proposta di ricambio viene valutata 150 giorni dopo l'acquisto del Wave Pro e lascia scegliere tra le quattro varianti. Dopo l'acquisto di una confezione, un nuovo ciclo viene valutato a 240 giorni, evidenziando la variante acquistata e mantenendo disponibili le alternative.
- Il precedente Laifen Wave con Travel Box non è più vendibile e non verrà riassortito. Le sette varianti restano nel catalogo per riconoscere gli acquisti storici. Dopo 180 giorni dall'acquisto, senza scadenza massima, viene proposta la sostituzione con Wave Pro; chi possiede già Wave Pro è escluso. Il cliente può scegliere tra tutte le varianti e il valore nominale usato dal portafoglio è il prezzo minimo osservato, pari a 99,99 €. Le testine sono confermate compatibili sia con Wave sia con Wave Pro. Il precedente Wave non genera comunque un ciclo ricambio: le soglie 150/240 giorni sono approvate soltanto per Wave Pro.
- Il cavo magnetico da 9,99 € è compatibile con il precedente Wave nelle versioni ABS e Alluminio. La base wireless da 29,99 €, disponibile in ABS e Alluminio, è compatibile con Wave Pro. I due accessori restano separati, senza relazione commerciale: il sistema li riconosce nello storico ma non li propone mai.
- La Travel Box da 19,99 € è un accessorio del precedente Wave e non è compatibile con Wave Pro, che include già una custodia propria. Poiché anche il precedente Wave include la Travel Box, resta senza relazione commerciale: il motore di cross-sell non la propone come ricambio. Entrambe le Travel Box sono in ABS: CM61971 è per Wave ABS, CM61972 per Wave Alluminio. Il materiale indicato nel modello riguarda lo spazzolino contenuto, non la custodia. CM61972 è riconosciuto nello storico; il suo EAN e prezzo specifico non sono stati confermati.
- P3 e P3 Pro sono censiti come rasoi elettrici correnti. P3 è il modello più nuovo e più economico, costa 169,99 € e usa un corpo in materiale composito; P3 Pro costa 199,99 € e usa un corpo in alluminio. L'astuccio da viaggio da 29,99 € è compatibile con entrambi e viene proposto dopo almeno 15 giorni, lasciando scegliere tra White e Gray. La testina da 44,99 € è compatibile con P3 Pro e incompatibile con P3. La prima proposta matura dopo 180 giorni e preferisce la finitura del rasoio acquistato; ogni testina acquistata apre un nuovo ciclo di 180 giorni, preferendo l'ultima variante scelta e mantenendo disponibili entrambe le finiture. Non è stata approvata alcuna proposta di upgrade o sostituzione tra i due rasoi.
- Le opportunità di ricambio e sostituzione Wave Pro appartengono al percorso `oral_care`, quelle P3/P3 Pro al percorso `shaving`, le priorità degli accessori per asciugacapelli al percorso `hair_care` e le proposte tra phon, spazzolini e rasoi al percorso `category_expansion`. Rimane comune la distanza minima di 15 giorni tra qualsiasi contatto rivolto allo stesso cliente.
- Resi e annullamenti noti vengono considerati; informazioni mancanti o ambigue, storico incompleto e SKU sconosciuti richiedono una verifica dell'operatore. Non si presume che ciò che manca nello storico non sia mai stato acquistato.
- Massimo due tentativi per piano, distanziati di almeno 15 giorni. Acquisto di qualsiasi proposta presentata, rifiuto dell’intero piano o esaurimento dei tentativi chiudono il piano; le altre proposte presentate non avviano sequenze autonome. Il rifiuto di un singolo prodotto esclude solo quel prodotto. L’interesse per un prodotto concentra la conversazione su di esso, mantenendo lo stesso piano e il conteggio comune dei tentativi. Una risposta o un esito prodotto richiedono gestione manuale fino alla chiusura esplicita della conversazione. Un nuovo acquisto di ricambio apre il relativo ciclo.
- Il motore valuta ogni opportunità singolarmente e poi costruisce piani di contatto. Opportunità dello stesso ordine, dello stesso percorso commerciale e con la stessa data di idoneità confluiscono in una sola comunicazione: una proposta primaria e le altre come suggerimenti secondari. Percorsi o date diverse producono piani separati, senza mappare manualmente le combinazioni di prodotti presenti nell’ordine.
- Un piano già contattato resta primario finché viene chiuso; una risposta blocca gli altri piani in attesa della gestione dell’operatore. Il piano ha al massimo due contatti, condivisi da primaria e secondarie. Alla chiusura, le secondarie già incluse non avviano sequenze separate. Tra contatti di piani diversi trascorrono almeno 15 giorni.
- Fra nuove proposte mature, sia dentro un piano sia fra piani, le mirate precedono sempre i test anche in promozione. All'interno della stessa categoria restano i criteri esistenti: promozione, finestra viaggio fra piani, valore nominale, maturazione e spareggi deterministici. Piani già contattati e conversazioni in gestione mantengono precedenza. Una promozione può superare soltanto prerequisiti da testare mai contattati; non supera un completamento mirato né anticipa la maturazione. Non si usano margini o punteggi probabilistici non disponibili.
- Il calendario promozionale del 2026 registra Neo a tre ugelli a 124,99 € dal 1 al 7 ottobre; P3 Pro a 169,99 €, P3 a 139,99 € e Wave Pro ABS a 84,99 €, Alluminio a 99,99 € e Trasparente a 118,99 € dal 12 al 18 ottobre. Sono prezzi pianificati per i gruppi di varianti mostrati nelle schermate: l'operatore verifica attivazione, disponibilità e prezzo effettivo prima della proposta. Queste finestre non anticipano la maturazione di un'opportunità e non spostano automaticamente i contatti a una campagna futura.
- Dal 19 al 30 novembre 2026 e dal 12 al 25 dicembre 2026 il calendario ripete per entrambe le finestre: Neo 3 ugelli 113,99 €, Neo Special 135,99 €, P3 Pro 149,99 €, Wave Pro ABS 79,99 €, Wave Pro Alluminio 94,99 €, Wave Pro Trasparente 109,99 €, P3 129,99 € e Air 54,99 €. AutoCurl resta al prezzo osservato di 99,99 € senza una promozione di retention pianificata in queste finestre. La campagna non crea relazioni commerciali: Neo Special e Air sono riconosciuti come prodotti promozionati, ma nessuna regola corrente li propone come destinazione di retention.
- Il precedente Wave compare in una promozione continuativa dal 14 settembre al 31 dicembre 2026, ma il business conferma che ne restano circa sette pezzi e chiede di ignorarla per la retention: Wave resta storico e non viene proposto. T1 Pro è censito con identità, varianti Silver/Gray, immagini, SKU/EAN e prezzo osservato nel catalogo pubblico il 14 ottobre 2026. Il suo acquisto viene riconosciuto nella categoria rasatura, ma non sono definite dotazioni o relazioni commerciali: la sua promozione non genera proposte.
- Neo a due ugelli genera concentratore, supporto Neo, pochette e spazzola. Nel nuovo piano il concentratore è principale, seguito dal supporto mirato e dai complementi da testare. Per Neo a tre ugelli il concentratore è escluso perché incluso e il supporto è principale. AutoCurl matura in un piano dedicato al giorno 45; Wave Pro e rasoi condividono il piano del giorno 75. Piani già contattati e interesse esplicito conservano il coordinamento esistente.
- Il consenso marketing valido sul canale selezionato è obbligatorio per ogni contatto commerciale, inclusi i ricambi. Assente, sconosciuto, in attesa o revocato blocca il contatto; il consenso email non vale automaticamente per SMS. Lo snapshot deve essere aggiornato prima del contatto. Il motore legge lo stato del consenso, non lo raccoglie e non lo sincronizza con Shopify. Recapito, disponibilità e prezzo sono verificati dall’operatore.
- La vista operatore espone percorso, stato, proposte, controlli, motivazione, data minima e blocchi. Una data resta indeterminata se dipende dalla chiusura di un altro piano. Le precedenze mirata/test sono regole deterministiche approvate, non stime di conversione.
- Le decisioni commerciali sono deterministiche; un eventuale LLM futuro non decide l'idoneità delle opportunità.
- Il repository contiene la versione corrente; Git conserva la storia.
- Il valore nominale di una proposta non è revenue generata.
- Il prodotto monitora un portafoglio di opportunità a livello di singolo cliente, dalla generazione al risultato osservato.
- Il sistema può decidere che per un cliente non esiste un'azione sensata al momento.

## Da definire nelle fasi pertinenti

- Campi e varianti degli export reali.
- Prodotti, contenuto degli SKU e relazioni commerciali Laifen.
- Significato della confidenza ed eventuali revisioni future di soglie temporali, esclusioni e priorità.
- Eventuale finestra temporale massima per l'attribuzione e trattamento delle vendite con più prodotti nello stesso ordine.
- Definizioni operative degli stati dell'opportunità, della scadenza e del conversion rate.
- Conservazione dei dati; il primo motore usa Python e l'import dei timestamp richiede `tzdata` sui sistemi senza database IANA, come l'ambiente Windows verificato.

Le testine CP38422, CP38423, CP38472, CP38474 e le quattro varianti già censite appartengono allo stesso contenitore commerciale «Testine di Ricambio Laifen Wave / Wave Pro», compatibile con entrambi i modelli per conferma del 16 ottobre 2026. La UI non distingue il tipo di testina; conserva i codici per riconoscere gli acquisti. Ogni codice acquistato aggiorna il ciclo Wave Pro secondo i 240 giorni già approvati. I quattro codici appena identificati sono riconosciuti solo negli acquisti: prezzo, EAN e quantità della confezione non sono forniti, quindi non diventano nuove destinazioni a prezzo inventato. Le quattro destinazioni già confermate rimangono proponibili.
