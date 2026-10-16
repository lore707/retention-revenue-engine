# Percorsi di riacquisto — dispositivi Laifen

Fotografia del 15 ottobre 2026. Queste sono opportunità previste, non acquisti attesi o probabilità. Nessuna nuova regola. Gli SKU esatti per ogni modello/configurazione sono elencati nelle 15 schede di [REGOLE_COMMERCIALI.md](REGOLE_COMMERCIALI.md).

## Come leggere le timeline

`T0` è la data del primo acquisto valido riconosciuto della fonte; giorni calendario Europe/Rome. Le timeline di base assumono un cliente con un solo dispositivo iniziale, nessuna destinazione già acquistata, nessun precedente contatto e dati validi. Acquisti multipli modificano esclusioni, fonti e composizione: non sommare meccanicamente i percorsi.

**Maturazione** = la regola raggiunge la soglia. **Lavorabilità** = il piano ha anche priorità, consenso valido, storico attivo, nessuna revisione, intervallo fra contatti e dipendenze risolte. Un T+45 non promette un contatto al giorno 45.

Un piano raggruppa stesso ordine, percorso e data. Piani indipendenti restano coordinati a livello cliente: un solo piano primario e almeno 15 giorni tra contatti. La sequenza non è un calendario di invii automatici. Fonti: `src/engine.py::evaluate_portfolio`, `_evaluate`, `_evaluate_replenishment`, `_evaluate_replacement`; `src/customer_profiles.py::_workable_plan`.

## 1. Asciugacapelli

### 1.1 Neo — configurazione 2 ugelli

**T0 Neo 2 ugelli → T+15 piano accessori: concentratore + supporto Neo + pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi → Mini nella prima finestra stagionale utile.**

- T+15: concentratore e supporto sono mirati; normalmente concentratore primario (valore prima del rango), supporto e complementi secondari. Sono quattro opportunità, un solo piano `hair_care` quando stessa fonte/ordine/data.
- T+45: AutoCurl, complemento da testare, ha una mail dedicata e attende i piani accessori applicabili. T+75: Wave Pro e rasoi condividono una mail di espansione separata, senza ereditare questa dipendenza. Il rasoio è normalmente rappresentativo per valore, salvo promozioni/interesse o esclusioni; nessun ordine prodotto è imposto.
- Mini: piano separato `seasonal_travel`, fonte non Mini, finestre 15/05–05/09 e 15/12–15/01. Può maturare già a T0 nella finestra; non viene necessariamente dopo T+45.
- Dopo acquisto concentratore: quel completamento è escluso. Se già presentato in un piano contattato, può chiudere anche il piano con le altre proposte; senza precedente contatto, le altre opportunità rimangono candidate.

Regole: `magnetic_concentrator_completion`, `neo_wall_mount_completion`, `storage_pouch_cross_sell`, `brush_complement`, `autocurl_cross_sell`, `hair_dryer_to_wave_pro_category_expansion`, `hair_dryer_to_shavers_category_expansion`, `mini_travel_cross_sell`.

### 1.2 Neo — configurazione 3 ugelli

**T0 Neo 3 ugelli → T+15 supporto Neo + pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; in parallelo Mini stagionale.**

Concentratore già incluso: escluso, non è una proposta da ripetere. Il supporto mirato precede i due complementi. Stessi blocchi e comportamento del Neo 2 ugelli per piani successivi. Le due configurazioni sono lo stesso dispositivo, ma generano dotazioni e completamenti diversi.

### 1.3 Neo Special

**T0 kit nutriente → T+15 concentratore + pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; Mini stagionale indipendente.**

Il kit include ugello standard, diffusore specifico, ugello nutriente e capsule vuote; non il concentratore. Nessuna proposta di supporto Neo: compatibilità non approvata per questa fonte. Nessuna proposta diffusore standalone: compatibilità in stand-by e diffusore specifico già nel kit. Nessuna regola di riacquisto capsule/oli: non dedurre consumabili vendibili dal kit.

### 1.4 Swift Premium

**T0 Swift Premium → T+15 concentratore + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; Mini stagionale indipendente.**

La pochette è inclusa: esclusa anche se un altro acquisto phon la renderebbe altrimenti candidata. Non proporre un ulteriore diffusore per completamento. Le varianti storiche White/Blue restano fonti; Pink è in esaurimento. Nessuna regola propone Swift come destinazione.

### 1.5 SE Lite

**T0 qualsiasi variante SE Lite → T+15 diffusore a incastro + pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; Mini stagionale indipendente.**

Diffusore SE Lite CP34510 è il completamento mirato. Concentratore magnetico e diffusore magnetico non sono destinazioni ammesse. Le varianti storiche rimangono valide come sorgenti; identificativo del diffusore Dark Gray storico mancante può impedire il riconoscimento del suo possesso.

### 1.6 Gift Edition

**T0 Gift Edition → T+15 pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; Mini stagionale indipendente.**

Concentratore e diffusore sono inclusi: nessun completamento di quei prodotti. Primo piano soltanto da testare, normalmente pochette primaria per valore. Il piano T+45 con promozione può superare il prerequisito accessori se interamente da testare e mai contattato. White/Red in esaurimento, Green/Black storiche: tutte riconosciute come fonte.

### 1.7 SE Special

**T0 SE Special → T+15 pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; Mini stagionale indipendente.**

Ugello standard, concentratore e diffusore inclusi. Nessun completamento di questi accessori. Matte Pink in esaurimento, altre varianti storiche. Coordinamento come Gift Edition, incluso possibile superamento promozionale del piano da testare mai contattato.

### 1.8 Mini

**T0 Mini → T+15 supporto Mini + pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi.**

Supporto Mini CP34501 mirato; supporto Neo distinto. Mini include custodia da viaggio, ma la regola pochette resta applicabile perché il componente incluso `mini_travel_case` non è `laifen_storage_pouch`: decisione commerciale da valutare, non prova che manchi una custodia. Concentratore/diffusore magnetici separati incompatibili. Nessuna proposta di un secondo Mini: possesso già osservato. Il piano T+45 attende gli accessori se AutoCurl presente; restano i blocchi comuni.

### 1.9 Air

**T0 Air → T+15 pochette + spazzola → T+45 mail dedicata AutoCurl → T+75 mail Wave Pro + rasoi; Mini stagionale indipendente.**

Nessun completamento concentratore/diffusore finché compatibilità non confermata. Primo piano da testare; promozione T+45 può superare il prerequisito mai contattato. Le promozioni Air non generano proposte Air in retention: Air è soltanto fonte nelle regole attuali.

### Dopo un acquisto successivo proveniente dal percorso phon

| Acquisto osservato | Nuove conseguenze previste |
| --- | --- |
| Mini | Esclude Mini da viaggio; può aprire supporto Mini dopo 15 giorni dal suo ordine; pochette/spazzola restano uniche per cliente/regola, non ripartono automaticamente |
| Wave Pro | Esclude espansione spazzolino; apre primo ciclo testine a +150 giorni dal nuovo acquisto; Neo non proposto se phon già presente |
| P3 | Esclude espansione rasoi; astuccio dopo +15 giorni; nessuna testina P3 Pro |
| P3 Pro | Esclude espansione rasoi; astuccio +15 e testina +180, piani distinti |
| AutoCurl | Esclude AutoCurl; nessuna ulteriore regola ha AutoCurl come fonte autonoma; può cambiare la dipendenza del piano espansione residuo |
| Accessorio | Esclude quella opportunità o chiude piano già presentato; non genera nuove relazioni autonome salvo ricambi previsti |

## 2. Spazzolini elettrici

### 2.1 Wave precedente, con Travel Box

**T0 Wave storico → T+90 Neo se nessun phon osservato → T+180 Wave Pro se non già acquistato → dopo acquisto Wave Pro, testine +150 giorni.**

- Neo: `toothbrush_to_neo_category_expansion`, piano `category_expansion`, tutte sei varianti, tre ugelli in evidenza nell'ordine opzioni; valore prudenziale minimo della gamma, non necessariamente prezzo della variante preferita.
- Wave Pro: `wave_legacy_to_wave_pro_replacement`, piano `oral_care`, separato dal piano Neo per percorso/data. È da testare, non ricambio certo; tutte sei varianti.
- A T+180 non c'è obbligo di proporre prima Neo se entrambi nuovi e maturi: prevalgono criteri globali/promozioni/valore; se Neo già contattato il piano resta prioritario fino a risoluzione.
- Nessuna proposta testine Wave Pro per il Wave precedente: compatibilità in stand-by. Nessun invio per cavo o Travel Box standalone, già senza relazione commerciale.
- L'acquisto Wave Pro esclude la sostituzione e apre percorso Wave Pro. Un phon acquistato esclude l'espansione Neo.

### 2.2 Wave Pro

**T0 Wave Pro → T+90 Neo se nessun phon → T+150 prima confezione testine → dopo acquisto testine, nuovo ciclo a +240 giorni dall'ultima confezione.**

Neo e testine sono piani indipendenti, rispettivamente `category_expansion` e `oral_care`. Quando entrambi nuovi e maturi, il ricambio mirato precede l'espansione da testare anche in promozione; un piano già contattato conserva precedenza. Il primo ricambio offre quattro confezioni da tre testine; non sceglie in base a una diagnosi clinica o al consumo effettivo.

Il ciclo ripetuto preferisce nel dato grezzo l'ultima variante acquistata, ma il portafoglio può riassegnare lo SKU rappresentativo al più economico/spareggio SKU; UI non evidenzia un badge “già acquistata”. Una confezione acquistata insieme al dispositivo può già impostare un ciclo repeat a 240 giorni: il confronto acquisto ricambio ≥ data dispositivo è inclusivo.

Quantità multiple non allungano il ciclo e più spazzolini non hanno contatori indipendenti. Nessuna proposta autonoma per base wireless, già inclusa; nessuna Travel Box Wave precedente per Wave Pro.

### Dopo acquisto Neo da un percorso spazzolino

**Neo acquistato → percorso accessori della configurazione acquistata a +15 → AutoCurl a +45 → espansione rasoi a +75 → Mini stagionale.**

La categoria spazzolini già osservata esclude l'espansione phon→Wave Pro, anche se lo spazzolino posseduto è il Wave precedente. L'eventuale sostituzione Wave→Wave Pro segue la propria regola indipendente a 180 giorni dalla fonte Wave; non viene anticipata dalla regola di espansione.

## 3. Rasoi elettrici

### 3.1 P3

**T0 P3 → T+15 astuccio da viaggio → nessun altro percorso specifico attivo.**

`p3_travel_case_cross_sell`, `shaving`, da testare. La custodia lama inclusa è distinta dall'astuccio viaggio. White/Gray selezionabili come opzioni. Testina P3 Pro esplicitamente incompatibile. Nessuna regola P3→P3 Pro, P3→phon o P3→spazzolino. Possesso P3 esclude l'espansione rasoi proveniente da un phon.

### 3.2 P3 Pro

**T0 P3 Pro → T+15 astuccio → T+180 testina → dopo ogni testina, nuovo ciclo +180 giorni.**

Due regole e normalmente due piani `shaving` con date diverse. Nessuna dipendenza wait_for_rules astuccio→testina: si applica soltanto coordinamento globale. Ricambio mirato precede astuccio da testare se entrambi nuovi e maturi; astuccio già contattato resta prioritario fino alla risoluzione.

Dato grezzo: prima testina con finitura coerente con il rasoio; poi ultima variante acquistata. Entrambe le finiture restano opzioni. La successiva selezione dello SKU rappresentativo nel portafoglio può perdere quella preferenza (vedi criticità). Acquisto testina nello stesso giorno del rasoio apre il repeat. Nessun upgrade automatico P3 Pro→P3.

### 3.3 T1 Pro

**T0 T1 Pro → nessuna opportunità sorgente specifica nelle 15 regole.**

SKU riconosciuti e categoria rasatura presente. Può escludere l'espansione verso rasoi per un cliente che possiede anche un phon, perché l'esclusione riguarda l'intera categoria. Dotazioni e percorsi T1 Pro non sono definiti: nessun astuccio o ricambio dedotto da P3/P3 Pro.

## 4. Comportamento trasversale dopo contatto o acquisto

| Situazione | Effetto sul percorso |
| --- | --- |
| Nessun contatto, acquisto destinazione | Regola esclusa o nuovo ciclo ricambio; gli altri candidati vengono rivalutati |
| Primo contatto registrato | Piano mantiene precedenza; almeno 15 giorni prima del secondo; alternative condividono contatore |
| Risposta/interesse/rifiuto prodotto | Conversazione manuale; altri piani attendono, fino a chiusura conversazione |
| Secondo contatto registrato | Piano chiuso per tentativi esauriti; non esiste un ulteriore periodo automatico di attesa risposta prima di marcarlo closed |
| Acquisto di proposta presentata | Piano contattato può chiudersi e sopprimere le altre proposte; revenue non automatica |
| Rifiuto intero piano | Chiusura; nessuna riapertura annuale o nuovo tentativo autonomo delle secondarie |
| Nuovo acquisto ricambio | Nuovo riferimento ciclo, nuova soglia temporale e contatore ciclo |
| Consenso non valido/dati incerti | Opportunità possono restare consultabili, contatto operativo bloccato |

Due esiti nello stesso giorno non hanno un ordine temporale affidabile basato sull'ora: una chiusura conversazione di quel giorno può assorbire anche una risposta registrata dopo. È una criticità tecnica distinta dalla timeline commerciale.

## 5. Casi in cui non concatenare automaticamente le frecce

- Primo acquisto fonte per regola: un nuovo dispositivo può non cambiare l'origine delle opportunità già esistenti.
- Acquisti di più modelli nello stesso ordine: raggruppamento soltanto se percorso e maturazione coincidono; esclusioni delle dotazioni operano a livello cliente.
- Destinazioni già possedute in categorie ampie: nessuna nuova espansione verso quella categoria, anche quando il modello sarebbe diverso.
- Acquisto regalo o professionale: il sistema non conosce il destinatario finale e non deduce quantità di utilizzatori.
- Newsletter/promozioni ricevute esternamente non sono contatti nel sistema.
- Stock non verificato può rendere una proposta non praticabile pur essendo teoricamente primaria; manca un esito operativo specifico “non proponibile per stock” prima del contatto.

Per validare questi percorsi usare la [matrice Shopify](REGOLE_DA_VALIDARE_SHOPIFY.csv): misurare sequenze reali e tempi, non assumere che la timeline approvata descriva già il comportamento dei clienti.
