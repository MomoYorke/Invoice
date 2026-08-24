# Fatture

App locale per creare fatture, tenerle in un database e produrre documenti
per la commercialista e statistiche sulla tua attività. Tutto resta sul tuo Mac.

Il nome dell'attività, l'indirizzo, l'UID, l'IBAN e il logo si mettono in
**Impostazioni**: nel programma non c'è niente di personale, e quello che
scrivi lì finisce sulle fatture — in PDF e in Word — e in cima all'app.

## La prima volta

L'app si apre su **Primi passi**: sette cose, in ordine, con scritto a cosa
servono e un pulsante che ti porta dove si fanno.

Due sono indispensabili — i dati di chi emette la fattura e l'IBAN — e finché
mancano l'app continua ad aprirsi lì, perché senza quelli le fatture escono
incomplete. Le altre cinque sono comodità: il logo, i clienti, la prima
fattura, la posta, i pacchetti di sessioni. Quando l'essenziale c'è, l'app si
apre sulla Dashboard e i passi rimasti diventano un promemoria discreto in
cima, che sparisce da solo quando finisci.

Ci si torna quando si vuole, da quel promemoria.

## Come si avvia
Doppio click su **`Avvia Fatture.command`**. Si apre il browser su
`http://127.0.0.1:8471`. Lascia aperta la finestra del Terminale mentre usi l'app
(per chiudere: Ctrl+C o chiudi la finestra).

> La prima volta macOS potrebbe chiedere conferma: tasto destro sul file →
> "Apri" → "Apri".

Se l'app è già accesa, il doppio click apre solo il browser senza far ripartire
niente — **tranne quando il programma è stato aggiornato**: in quel caso la
riavvia da sola, perché le pagine restano in memoria da quando è partita e
altrimenti continueresti a vedere la versione vecchia.

## Quando esce una versione nuova
Se hai ricevuto l'app da un repository, l'avviatore controlla da solo se ne è
uscita una versione più recente — non più di una volta ogni sei ore, e senza
bloccare l'avvio se la rete non c'è. Quando ne trova una **mostra cos'è
cambiato e chiede il permesso**: non aggiorna mai di nascosto.

Dicendo di sì, prima fa una copia di sicurezza dei dati, poi sostituisce i file
del programma, e se servono librerie nuove le installa. **I tuoi dati non
vengono toccati**: database, fatture, estratti conto, backup e logo stanno
fuori dal repository, quindi l'aggiornamento non li vede nemmeno.

Per tornare alla versione precedente, il numero è in `data/.versione-precedente`:

    git reset --hard $(cat data/.versione-precedente)

La finestra del Terminale resta quasi vuota: due righe all'avvio e basta.
Non scorre niente mentre usi l'app, e non c'è nessun avviso rosso da
interpretare. Se qualcosa va storto lo dice la pagina, e la traccia completa
finisce in `data/error.log`.

## Il menu
Le voci sono divise in gruppi, nell'ordine in cui le cose capitano davvero:

| Gruppo | Voci | Quando lo apri |
|---|---|---|
| — | Dashboard | ogni volta |
| **Fatturare** | Nuova fattura · Fatture · Email inviate | tutte le settimane |
| **Chi alleni** | Clienti · Crediti · Agenda | tutte le settimane |
| **Incassi e fisco** | Banca · Commercialista | ogni tanto |
| **L'app** | Controlli · Verifica calcoli · Cestino · Impostazioni | quando serve |

Finché resta qualcosa dei **primi passi**, in cima al menu compare la voce
*Primi passi* con quante cose mancano; quando non ne manca più nessuna sparisce
da sola.

Aprendo un dettaglio la voce del suo elenco resta accesa: la scheda di una
fattura tiene acceso *Fatture*, un pacchetto tiene acceso *Crediti*.

**Se stringi la finestra** — per tenere l'app a metà schermo accanto a
qualcos'altro — sotto i 1040px il menu si riduce a una colonnina di sole icone
(passandoci sopra col mouse leggi il nome). Fino a 900px tutte le pagine ci
stanno intere; più stretto di così sono le singole tabelle a scorrere dentro il
loro riquadro, e la pagina non si sposta mai di lato.

## Cosa fa
- **Dashboard** — fatturato dell'anno, confronto con l'anno prima, proiezione a
  fine anno, incassato vs da incassare, top clienti, tipi di servizio, grafici.
  Più tre riquadri di controllo: **Stato fatture** (quante emesse, pagate, da
  incassare, spedite e — solo per quelle fatte con l'app — non ancora spedite,
  ognuna cliccabile), **Salute dell'app** (ultima copia su iCloud e sua
  dimensione, quante copie conservate, ultima lettura del calendario, esito
  dell'ultima verifica dei calcoli, stato della posta, spazio occupato: verde,
  giallo o rosso) e **È successo questo** (fatture create e spedite, sessioni
  registrate, pacchetti arrivati a zero, in un'unica lista in ordine di tempo;
  dove l'ora non si conosce compare solo il giorno).
- **Nuova fattura** — scegli cliente e servizio, l'app assegna il numero
  progressivo, calcola i totali (matematica in centesimi: zero errori di
  arrotondamento) e genera **docx + PDF** in `Fatture/ANNO/`.
  Per il *running coaching* propone da sola il mese successivo all'ultima fattura.
- **Fatture** — elenco completo (storico incluso), ricerca, segna pagata /
  da incassare con un click. La colonna *Inviata* mostra giorno e ora in cui la
  fattura è partita per email.
- **Clienti** — registro clienti con fatturato totale per ciascuno.
- **Commercialista** — un click e prepara il pacchetto per il commercialista:
  Excel (registro + riepilogo mensile/trimestrale + per cliente), PDF di
  riepilogo e copia di tutte le fatture PDF dell'anno, già zippato.
  Lo trovi in `Esporti/`.
- **Agenda** — gli allenamenti svolti, con giorno e ora, dal più recente.
- **Email inviate** — il diario di tutto quello che l'app ha spedito, prove e
  tentativi falliti compresi.
- **Banca** — legge gli estratti conto e propone quale fattura è stata pagata.
- **Crediti** — tracking delle sessioni di personal training. Ogni cliente ha un
  pacchetto di crediti (12 o 10 sessioni); ogni sessione svolta ne consuma uno.
  La pagina mostra quanti crediti restano a ciascuno e segnala con **"Crediti terminati"**
  chi ha finito il pacchetto e va rifatturato. Le sessioni arrivano dal tuo calendario Google.
  Per aggiornare, chiedi a Claude: *«aggiorna i crediti dal calendario»*.
  Quando emetti la fattura di un pacchetto, la colleghi dalla stessa pagina: le
  sessioni coperte vengono marcate col numero fattura e il pacchetto si chiude.
  Accanto al pacchetto vedi **quale fattura lo copre** e se quella fattura è
  *da incassare* (ambra) o *✓ incassata* (verde): lo stato si aggiorna da solo
  quando segni la fattura come pagata.
- **Nascondi importi** — il pulsante con l'**occhio** in alto nella Dashboard (e lo stesso
  occhio in fondo al menu) sfoca tutti gli importi: utile per screenshot o quando sei in
  un luogo pubblico. Occhio aperto = importi visibili, occhio barrato = importi nascosti.
  Resta attivo su tutte le pagine finché non lo rispegni.
- **Controlli** — verifica numerazione (duplicati, buchi) e importi.
- **Impostazioni** — dati aziendali che finiscono in fattura (IBAN, indirizzo…).

## Il logo

Si carica in **Impostazioni → Logo**. Vale ovunque: sulle fatture PDF, su
quelle Word e in alto a sinistra nell'app. Meglio un PNG con lo sfondo
trasparente; va bene anche un JPG.

Non serve che sia della misura giusta. Nella fattura Word lo spazio del logo
ha una forma fissa e piuttosto larga: se il tuo logo è quadrato non viene
stirato, gli si lascia dell'aria ai lati.

Finché non ne carichi uno, nell'app vedi un segnaposto grigio — ma **sulle
fatture quello spazio resta vuoto**, così non parte mai un documento con
scritto «caricalo dalle Impostazioni» sopra.

Il file finisce in `data/logo.png`, insieme agli altri tuoi dati. Se passi
l'app a qualcun altro, il tuo logo non lo segue.

## Da dove vengono i dati
Al primo avvio, se in Impostazioni indichi una **cartella dello storico**,
l'app importa quello che c'è dentro: fatture in Word e PDF, un `clients.json`,
i riepiloghi Excel degli anni passati.
Quella cartella **non viene mai modificata**: l'app la legge soltanto.
Le nuove fatture nascono qui dentro, in `Fatture/ANNO/`.

Per gli anni precedenti all'app, i totali ufficiali vengono dai riepiloghi Excel
(più completi delle singole fatture Word di quegli anni).

## Crediti sessioni — regole

**Chi lavora a crediti si dichiara nell'app**, in *Crediti → Chi lavora a crediti*.
Per ogni persona servono quattro cose:

| Campo | A cosa serve |
|---|---|
| Nome | come compare nell'app e nel registro |
| Parola nel calendario | l'app conta come sua sessione ogni evento che contiene questa parola. Scegline una che non compaia per caso altrove |
| Sessioni per pacchetto | quanti crediti dà un pacchetto |
| Prezzo | quando emetti una fattura di quell'importo, l'app capisce da sola che ha comprato un pacchetto e gli ridà i crediti |

Due campi si usano di rado:

- **Intesta la fattura a** — quando chi si allena e chi paga sono due persone diverse.
- **È il supplemento di** — per chi si allena in coppia e paga un pacchetto ridotto in
  aggiunta a quello dell'altro. Nei giorni in cui l'altro non c'è, la sessione è piena
  e scala dal pacchetto dell'altro.

Chi smette si **archivia**, non si cancella: il suo nome resta riconoscibile nei titoli
del calendario (serve se un pacchetto condiviso è ancora aperto) ma non gli si aprono
più pacchetti. L'app rifiuta di cancellare chi ha già dei pacchetti nel registro.

Chi paga a sessione singola o a fattura mensile qui non va messo.

- **Le fatture si agganciano da sole.** Quando emetti una fattura-pacchetto, l'app
  riconosce di chi è dall'importo e dall'intestatario, e: apre il pacchetto nuovo
  se quello vecchio è finito; oppure lo collega a quello in corso se non risultava
  ancora pagato; oppure la tiene **in attesa** e la usa al prossimo pacchetto.
  Le fatture del running coaching (110.-) non toccano i crediti.
- Gli importi riconosciuti sono quelli scritti nella scheda di ogni cliente.
- Puoi sempre collegare **a mano** una fattura passata a qualsiasi pacchetto dal
  pulsante nella pagina Crediti. Collegare non chiude mai un pacchetto che ha
  ancora crediti.
- Una sessione **cancellata consuma comunque il credito**.
- Gli **appuntamenti futuri non contano**: solo le sessioni fino a oggi.
- Lo storico delle sessioni (fino al 19.08.2026) è **congelato e validato** contro le
  fatture reali: la sincronizzazione aggiunge in coda, non riscrive mai il passato.
- Ogni sessione porta l'ID dell'evento Google: rilanciare la sincronizzazione dieci
  volte non crea duplicati.
- Il calendario storico, se ne colleghi uno, non viene mai letto dai crediti.
- Stati: *In corso* · *In esaurimento* (2 o meno rimasti) · **Crediti terminati**
  (pacchetto finito: emetti la prossima fattura).
- Il registro è `sessions.json` (copia di sicurezza a ogni salvataggio in `data/backups/`).

## Come leggere "per tipo di servizio"
La somma delle voci coincide sempre col fatturato dell'anno:
- gli **sconti** (es. uno sconto fedeltà) non fanno voce a sé: vengono
  **sottratti dal servizio della stessa fattura**, anche se sul documento compaiono
  con importo positivo (2'050 − 50 = 2'000);
- le fatture **senza righe di dettaglio** (importate da un PDF) vengono ricondotte al
  loro servizio quando è deducibile senza ambiguità — stesso cliente, stesso importo
  esatto, un solo servizio possibile — altrimenti finiscono in *Non dettagliato*,
  così non spariscono mai dal conteggio.

## Sessioni dal calendario

L'app legge il calendario delle sessioni da sola e scala i crediti. Si collega
una volta: Google Calendar → il tuo calendario → Impostazioni del calendario →
*Indirizzo segreto in formato iCal*, e quell'indirizzo si incolla in
Impostazioni. Un eventuale calendario storico non va mai collegato qui.

Il nome del calendario l'app non te lo chiede: se lo fa dire dal calendario
stesso, e da quel momento lo chiama per nome nelle sue pagine.

La lettura avviene quando apri la pagina Crediti, non più di una volta ogni 15
minuti; il pulsante *Aggiorna adesso* la forza. Se il calendario non risponde
vedi i crediti dell'ultima lettura riuscita con un avviso, mai una pagina di
errore al posto dei tuoi dati.

**Perché l'iCal e non l'API di Google.** Nessun progetto Google Cloud, nessuna
autorizzazione da rinnovare, nessuna password: un indirizzo da incollare. In
compenso l'iCal descrive una serie ricorrente come una voce sola più le sue
eccezioni, mentre l'API dava un evento già pronto per ogni ripetizione. Le
ripetizioni si espandono quindi in `core/calendario.py`, e l'identificativo che
impedisce di contare due volte la stessa sessione è **UID + data**.

Restano valide tutte le regole di prima: finestra dal 20.08.2026, le sessioni
future non consumano crediti, quelle disdette su Google non si contano, vale la
regola della coppia. Due sessioni dello stesso cliente nello stesso giorno
sono legittime (capita coi pacchetti condivisi) e vengono contate entrambe.

## Agenda

La voce **Agenda** nel menu elenca gli allenamenti **davvero svolti**, uno per
credito consumato, dal più recente. Gli appuntamenti ancora da fare non
compaiono; quelli annullati sì, marcati, perché il credito l'hanno consumato.

Le due fonti sono separate di proposito:

- **quali** sessioni: il registro crediti (`sessions.json`), l'unico elenco
  completo e già verificato contro le fatture. Il calendario di Google non lo è
  più: quando una serie ripetuta finisce, sparisce anche il suo passato.
- **a che ora**: il calendario, tenuto in un indice a parte
  (`data/orari.json`). Si può cancellare e ricostruire quando si vuole senza
  toccare i crediti.

Il pulsante *Aggiorna gli orari dal calendario* riempie gli orari mancanti.
Delle sessioni più vecchie l'ora non si conosce, perché il calendario delle
sessioni non le contiene più: si riempiono da sole incollando in Impostazioni
anche l'indirizzo iCal di un **calendario storico**. Quel secondo indirizzo serve
soltanto all'Agenda — i crediti non ci passano mai, quindi non c'è modo che una
sessione venga contata due volte.

## Mandare la fattura per email

Dal dettaglio di una fattura, **✉️ Manda per email**.

La mail parte dal tuo server (porta 587), non da Gmail: se il tuo dominio
autorizza solo il proprio server a spedire a suo nome (SPF `-all`), quelle
mandate da Gmail finiscono in spam. Attenzione al nome dell'host: spesso il
certificato copre `tuodominio.ch` ma **non** `mail.tuodominio.ch`, e allora va
scritto il primo — l'app te lo dice, se sbagli.
La password della casella si mette in Impostazioni una volta sola.

**Come funziona la pagina di invio**

1. Il testo arriva già scritto, ricalcato sulle email che mandi davvero, e puoi
   riscriverlo per intero prima di spedire.
2. *Prova su di me* manda la mail identica al tuo indirizzo: la vedi arrivare
   come la vedrà il cliente.
3. *Invia* la manda al cliente e segna la data. Se riprovi, la pagina ti avvisa
   che risulta già inviata.

**I due modelli di testo.** La frase centrale — quella che cambia da mail a
mail — ha due versioni salvate in Impostazioni: una per *Running / Online
coaching*, una per *Personal training*. L'app sceglie quale usare guardando le
righe della fattura, e nella pagina di invio due pulsanti ti fanno passare
all'altra con *Riscrivi con questo modello*. Riscrivere ricostruisce il testo da
capo, quindi fallo prima di ritoccarlo a mano. Il resto della mail (apertura,
frase sull'ordine permanente, firma) resta automatico come prima.

**Quando la fattura va intestata a un altro.** Chi si allena e chi riceve la
fattura non sono sempre la stessa persona: un genitore, un coniuge, un'azienda.
Nella scheda del cliente c'è il campo
**Intesta la fattura a**: se compilato, il documento e il registro portano quel
nome, mentre il **nome del file resta quello del cliente** (`Anna #88.pdf`),
così i documenti nuovi restano in fila con i vecchi. Nella pagina *Nuova
fattura*, scelto il cliente, l'app te lo ricorda prima che tu generi il
documento. L'indirizzo resta quello della scheda.

**Cosa cambia da cliente a cliente** (si imposta nella pagina Clienti)

- *Email*: senza indirizzo il pulsante Invia resta spento.
- *Come ti firmi*: i due saluti si scrivono in Impostazioni, qui si sceglie quale
  usare con questa persona.
- *Abbonamento mensile*: aggiunge la frase sull'ordine permanente e fa dire
  «this month's invoice» invece di «your invoice» — perché un pacchetto da dieci
  sessioni non è mensile.

**Il registro.** La voce **Email inviate** nel menu elenca tutto quello che è
partito dall'app: giorno e ora, destinatario, oggetto, allegati, in quale
cartella è finita la copia. Cliccando *leggi* si riapre **la mail intera**, con
mittente, copia nascosta e il testo esatto che ha letto il cliente — un
messaggio pesa circa 250 byte, quindi dieci anni di fatture stanno in poco più
di cento kilobyte. Ci finiscono anche le prove su di te e i tentativi
falliti, con il motivo — un elenco che mostra solo i successi non serve proprio
quando ne hai bisogno. Le righe delle fatture spedite prima che il registro
esistesse sono state ricostruite dalla data segnata sulla fattura e dicono di
esserlo. Questo elenco è il diario dell'app: le mail vere restano dove sono
sempre state.

**La copia a te stesso.** Ogni fattura spedita arriva anche nella tua posta in
arrivo, in **copia nascosta**: il cliente non la vede (è Ccn, non Cc — e
l'intestazione non viaggia nemmeno nel messaggio che riceve). Serve perché
un account POP in Mail non mostra la cartella Inviata del server: così la
fattura spedita la ritrovi comunque in Mail, cercandola.
Si disattiva in Impostazioni con una spunta.

**La copia in «Inviata».** SMTP serve solo a consegnare la posta: la copia nella
cartella Inviata la scrive chi spedisce, ed è per questo che le mail partite
dall'iPhone si vedono anche sul Mac. L'app fa lo stesso, depositando il
messaggio via IMAP subito dopo l'invio. Ritrovi quindi le fatture spedite in
Inviata come tutte le altre mail, da Mail, dal telefono e dal webmail.
La cartella la trova da sola (il server marca `INBOX.Sent` come Inviata). Se la
copia non riesce la mail è comunque partita, e l'app te lo dice invece di far
finta di niente. Anche *Prova su di me* deposita la sua copia: una prova che
salta il deposito non proverebbe la cosa che interessa. Le prove restano quindi
in Inviata come le altre, e le cancelli tu quando non ti servono più.

**Due fatture in una mail.** Nella pagina di invio puoi allegare anche un'altra
fattura recente, anche di un altro cliente: il caso tipico è chi riceve la sua
più quella del coniuge. L'apertura diventa «Attached are two
invoices». Vengono proposte solo le fatture fatte con l'app negli ultimi 90
giorni e non ancora spedite: quelle vecchie dello storico esistono solo in Word
e non si possono allegare come PDF.

## Sapere quando sei stato pagato

Scarica dall'e-banking i movimenti e appoggia i file in **`Estratti conto/`**.
L'app legge tre formati: **camt.053 / camt.054** (XML), i **CSV** e gli
**estratti in PDF**. Del CSV riconosce le colonne dal nome dell'intestazione,
perché ogni banca lo scrive a modo suo. Poi apri la pagina **Banca**.

Il PDF merita una spiegazione. Quando il testo viene estratto, le colonne
*Addebito* e *Accredito* collassano in una sola e non si vedrebbe più se un
importo è entrato o uscito. Il segno si ricava dal **saldo**, che non può
mentire: i movimenti sono in ordine dal più recente e il saldo della riga sotto,
più o meno l'importo, deve ridare quello della riga sopra. Se torna col più è un
accredito, se torna col meno è un addebito, e se non torna con nessuno dei due
la riga si scarta invece di indovinarla. Se i conti non tornano su più di una
riga su dieci, l'app rifiuta tutto il file e ti dice di scaricare il CSV: meglio
niente che un elenco inventato.

**Il collegamento automatico.** All'avvio dell'app e ogni volta che apri la
pagina Banca, i versamenti su cui non c'è niente da decidere vengono collegati
da soli: importo esatto, **un solo** candidato forte, e il nome del cliente (o
la data della fattura) nella causale. Tutto il resto continua a chiederlo a te.
Provato sui 18 mesi di estratti veri prima di attivarlo: **30 collegamenti
automatici, 30 corretti, nessuno sbagliato**, e i 19 casi dubbi sono rimasti
dubbi. Ogni riga decisa dall'app resta marcata «dall'app» e si annulla con un
click. Si spegne in Impostazioni.

Regole che non cambiano:

- **L'app non segna niente da sola.** Propone e aspetta la conferma. Un
  accostamento sbagliato fatto in silenzio è peggio di nessun accostamento:
  ti farebbe credere di essere stato pagato quando non lo sei.
- Legge **solo le entrate**. Quello che spendi non lo guarda.
- I file non vengono spostati né modificati, e lo stesso mese riscaricato due
  volte non produce doppioni (ogni versamento ha la sua impronta).
- *Annulla* riporta la fattura esattamente com'era, stato compreso.

Come vengono accostati: importo esatto, finestra di **60 giorni** prima del
versamento (5 dopo, per chi paga in anticipo) e nome del cliente cercato nella
causale — anche scritto senza dieresi, come fanno le banche («Mueller» o
«Muller» per Müller). La finestra è stretta di proposito: gli
abbonamenti mensili sono tutti da 110.00, e con sei mesi di margine ogni
versamento troverebbe sei fatture identiche.

Altri tre casi che capitano davvero e che l'app gestisce:

- **La data nella causale.** Qualche cliente non scrive il numero della fattura
  ma la sua data («INVOICE 21-04-26»). È l'indizio più preciso che esista senza
  QR-fattura, e distingue due mensilità identiche dello stesso cliente.
- **Chi paga non è l'intestatario.** Sul conto arriva il nome del marito, della
  moglie, di un'azienda. Il nome di
  chi versa si scrive nella scheda del cliente, campo *Sull'estratto conto paga
  come* (più nomi separati da punto e virgola).
- **Un bonifico, due fatture.** Due fatture della stessa famiglia pagate con un
  versamento solo. Se nessuna fattura da sola fa quell'importo, l'app cerca
  combinazioni di due o tre fatture **dello stesso cliente** che insieme lo
  facciano esattamente. Solo dello stesso cliente: senza quel vincolo si
  troverebbero somme che tornano per caso.

Le fatture già spuntate *pagata* a mano restano proponibili: confermarle non
cambia lo stato, aggiunge la data vera del versamento, e la riga lo dice.
Conviene lavorare dall'alto verso il basso (l'elenco è già in ordine di tempo):
ogni conferma toglie quella fattura dai candidati delle successive, e le
ambiguità fra mensilità uguali si sciolgono da sole.

- 🔵 importo e nome combaciano → un pulsante *Conferma*
- ⚪️ combacia solo l'importo → l'app mostra i candidati e ti fa scegliere
- 🟢 il riferimento del pagamento combacia → comparirà con le QR-fatture, e da
  lì l'accostamento non sarà più un'ipotesi

Il riferimento **non** viene dedotto dal numero di fattura: un riferimento di un
altro creditore può finire con le stesse cifre, e l'app direbbe «certo» su una
fattura sbagliata. Vale solo un riferimento che l'app ha stampato lei.

Quando confermi, la fattura prende la data vera del versamento (`paid_at`) oltre
allo stato *pagata*: la spunta messa a mano e il giorno in cui i soldi sono
arrivati restano due informazioni diverse.

**Chi non ha ancora pagato.** In Dashboard, sotto *Stato fatture*, l'app separa
due cose che sembrano uguali e non lo sono: le fatture **davvero scoperte** —
emesse da abbastanza tempo che il versamento sarebbe già dovuto comparire
nell'estratto che hai — e quelle **troppo recenti per saperlo**, il cui
pagamento finirà in un estratto che non hai ancora scaricato. Il confine sono 45
giorni prima dell'ultimo movimento letto, perché i tuoi clienti pagano fra i 4 e
i 47 giorni dalla fattura. Senza questa distinzione l'elenco dei ritardi sarebbe
pieno di falsi allarmi e smetteresti di guardarlo.

Il riquadro *Salute dell'app* mostra fino a che data arrivano gli estratti e
diventa giallo dopo 40 giorni: è il promemoria per scaricarne uno nuovo.

## Copie di sicurezza

Due reti, non una.

**Dentro l'app** (`data/backups/`): copia del solo database, a ogni avvio e prima
di ogni operazione che può distruggere dati. Serve a tornare indietro di
mezz'ora, non a sopravvivere a un disco rotto — sta sullo stesso disco.

**Fuori dal Mac** (iCloud Drive, cartella *Fatture App - Backup*): due archivi.

- `fatture-app-AAAAMMGG-hhmmss.zip` — database, registro delle sessioni e i PDF
  della cartella `Fatture/`. Creato all'avvio (una volta al giorno) e **dopo ogni
  fattura nuova**. Circa 140 KB. Si tengono le ultime 30 copie più la prima di
  ogni mese, che non viene mai cancellata.
- `storico-AAAAMMGG-hhmmss.zip` — i documenti della cartella dello storico, dove
  vivono le fatture più vecchie dell'app. Qualche MB, quindi viene rifatto **solo
  quando quella cartella cambia davvero**: l'app ne confronta l'impronta e se è
  identica non riscrive niente. Se ne tengono 3. La cartella viene solo letta,
  mai modificata.

Appena scritto, ogni archivio viene riaperto: il database dentro deve passare
`PRAGMA integrity_check` e contenere lo stesso numero di fatture dell'originale.
Se non passa, l'archivio viene buttato e l'errore compare in Impostazioni. Un
backup che non si riapre non è un backup.

In Impostazioni trovi data dell'ultima copia, le ultime dieci, il pulsante
*Fai una copia adesso* e la cartella di destinazione, che puoi cambiare.

## Note pratiche
- Prezzi: scrivi come sei abituato (`110.-`, `1'800.00`, `150,00 CHF`).
- Il numero fattura è automatico (max esistente + 1) e l'app rifiuta duplicati
  e non sovrascrive mai file esistenti.
- Le fatture eliminate finiscono in `Cestino/` dentro questa cartella.
- Backup: basta copiare questa cartella (il database è `data/fatture.db`).

## Provare l'app senza toccare i dati veri

Queste variabili d'ambiente deviano l'app su una copia. Servono a chi mette le
mani nel codice: si fanno prove vere, con dati veri, senza rischiare i propri.

| Variabile | Devia |
|---|---|
| `FATTURE_DB` | il database |
| `FATTURE_DIR` | la cartella dove finiscono i documenti |
| `FATTURE_SESSIONS` | il registro delle sessioni |
| `FATTURE_ESTRATTI` | gli estratti conto |
| `FATTURE_ORARI` | gli orari dell'Agenda |
| `FATTURE_LOGO` | il logo |
| `FATTURE_BACKUP` | le copie di sicurezza |
| `FATTURE_PORT` | la porta (di serie 8471) |

`FATTURE_BACKUP` passa davanti anche all'impostazione salvata: un'app di prova
parte quasi sempre da una copia del database vero, e senza questo depositerebbe
le sue copie in mezzo a quelle buone — dove, col ricambio delle ultime 30,
finirebbero per spingere fuori le vere.
