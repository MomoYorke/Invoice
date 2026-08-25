# -*- coding: utf-8 -*-
"""
Le tre lingue dell'app.

Ci sono DUE lingue, non una, e tenerle separate e' la scelta importante di
questo file:

- la lingua dell'APP e' di chi la usa: menu, pagine, messaggi. Una sola, si
  cambia col tasto in alto.
- la lingua dei DOCUMENTI e' del CLIENTE: la fattura e la mail le legge lui,
  non chi le scrive. Chi lavora a Zurigo ha clienti che parlano tedesco e
  clienti che parlano inglese, e un'impostazione sola non puo' servirli tutti.
  Legarle insieme vorrebbe dire che il giorno che uno mette l'app in italiano
  i suoi clienti ricevono fatture in italiano, senza averlo chiesto.

Le chiavi del dizionario sono le FRASI ITALIANE, non delle sigle. Due motivi:
i template restano leggibili («Nuova fattura», non «menu.nuova.titolo»), e
quando una traduzione manca esce l'italiano. Una pagina con una frase nella
lingua sbagliata si usa lo stesso; una piena di sigle no.
"""

LINGUE = (('it', 'Italiano'), ('en', 'English'), ('de', 'Deutsch'))
CODICI = tuple(c for c, _n in LINGUE)
PREDEFINITA = 'it'


def normalizza(codice):
    """Un codice che non conosciamo non e' un errore: si torna all'italiano."""
    return codice if codice in CODICI else PREDEFINITA


def t(frase, lingua=None):
    """La frase nella lingua chiesta, o in italiano se non c'e'."""
    if not lingua or lingua == PREDEFINITA:
        return frase
    return TESTI.get(lingua, {}).get(frase, frase)


def mancanti(lingua):
    """Le frasi che l'italiano ha e questa lingua no. Serve al collaudo."""
    fatte = set(TESTI.get(lingua, {}))
    return sorted(f for f in TUTTE if f not in fatte)


# ---------------------------------------------------------------------------
# I dizionari. Ogni blocco corrisponde a un pezzo dell'app, cosi' quando se ne
# aggiunge uno si sa dove mettere le frasi nuove.
# ---------------------------------------------------------------------------

TESTI = {
    'en': {
        # --- menu ---
        'Dashboard': 'Dashboard',
        'Performance': 'Performance',
        'Nuova fattura': 'New invoice',
        'Fatture': 'Invoices',
        'Email inviate': 'Sent emails',
        'Clienti': 'Clients',
        'Crediti': 'Credits',
        'Agenda': 'Sessions',
        'Banca': 'Bank',
        'Commercialista': 'Accountant',
        'Controlli': 'Checks',
        'Verifica calcoli': 'Calculation check',
        'Cestino': 'Trash',
        'Impostazioni': 'Settings',
        'Primi passi': 'First steps',
        'Fatturare': 'Invoicing',
        'Chi segui': 'Your clients',
        'Incassi e fisco': 'Payments and tax',
        "L'app": 'The app',
        # --- cornice, presente su ogni pagina ---
        'Indietro': 'Back',
        'Torna alla schermata precedente': 'Back to the previous screen',
        'App locale · dati sul tuo Mac': 'Local app · data on your Mac',
        'Nascondi gli importi (screenshot, luogo pubblico)':
            'Hide amounts (screenshots, public places)',
        'Importi nascosti — clicca per mostrarli': 'Amounts hidden — click to show',
        'Lingua': 'Language',
        # --- Dashboard ---
        'Fatturato {anno} ad oggi': 'Revenue {anno} to date',
        'rispetto allo stesso periodo del {anno}': 'compared with the same period in {anno}',
        'Vedi le performance': 'See performance',
        'Da fare': 'To do',
        'Ultime cose': 'Latest activity',
        'Da incassare': 'To collect',
        'Fatte e non ancora spedite': 'Created but not sent',
        'Pacchetti finiti': 'Packages used up',
        'Estratto conto da aggiornare': 'Bank statement out of date',
        'Niente in sospeso. Tutte le fatture sono partite e non aspetti soldi da nessuno.':
            'Nothing pending. Every invoice has gone out and no one owes you money.',
        'Ancora niente da raccontare.': 'Nothing to report yet.',
        'fatture': 'invoices',
        'clienti': 'clients',
        'fattura': 'invoice',
        'cliente': 'client',
        # --- le voci del «Da fare», composte dal codice ---
        '{tardi} ferme da oltre {giorni} giorni': '{tardi} outstanding for over {giorni} days',
        'nessuna in ritardo, sono tutte recenti': 'none overdue, they are all recent',
        "sono nell'app ma non sono partite per email":
            'they are in the app but have not been emailed',
        '{chi} — va emessa la prossima fattura': '{chi} — the next invoice is due',
        ' e altri': ' and others',
        "non ne hai ancora caricato nessuno: l'app non sa chi ti ha pagato":
            "you haven't loaded one yet: the app cannot tell who has paid you",
        "l'ultimo arriva al {data}, {giorni} giorni fa":
            'the latest one ends on {data}, {giorni} days ago',
        # --- «Ultime cose» ---
        'Fattura #{n} a {cliente}': 'Invoice #{n} for {cliente}',
        'Prova su di te': 'Test to yourself',
        ' — non è partita': ' — it did not go out',
        'Invio fallito della #{n}': 'Sending #{n} failed',
        'Fattura #{n} spedita a {a}': 'Invoice #{n} sent to {a}',
        'Fattura #{n} spedita': 'Invoice #{n} sent',
        'Sessione di {cliente}': 'Session with {cliente}',
        ' (annullata)': ' (cancelled)',
        'Crediti finiti: {pacchetto} ({cliente})': 'Credits used up: {pacchetto} ({cliente})',
        # --- il resto della Dashboard ---
        'gen — dic {anno}': 'Jan — Dec {anno}',
        'Manca ancora una cosa da mettere a posto: {elenco}.':
            'One thing still to set up: {elenco}.',
        'Mancano ancora {n} cose da mettere a posto: {elenco}.':
            '{n} things still to set up: {elenco}.',
        'Vedi i primi passi': 'See the first steps',
        # --- Performance ---
        "Come sta andando l'attività.": 'How the business is doing.',
        'Fatturato {anno}': 'Revenue {anno}',
        ' (ad oggi)': ' (to date)',
        'Proiezione fine {anno}': 'Projection to end of {anno}',
        'al ritmo attuale (media giornaliera)': 'at the current rate (daily average)',
        'Fattura media': 'Average invoice',
        '{n} fatture nel {anno}': '{n} invoices in {anno}',
        'Miglior cliente {anno}': 'Top client {anno}',
        'Andamento mensile {anno}': 'Monthly trend {anno}',
        'Per il {anno} lo storico è per totali annui (da Excel), senza dettaglio mensile.':
            'For {anno} the history is kept as yearly totals (from Excel), with no monthly detail.',
        'valori in CHF': 'values in CHF',
        'Fatturato per anno': 'Revenue by year',
        'da fatture': 'from invoices',
        'da Excel storico (2022–23)': 'from historical Excel (2022–23)',
        'Top clienti {anno}': 'Top clients {anno}',
        'fatt.': 'inv.',
        'Per tipo di servizio {anno}': 'By service {anno}',
        'Totale (coincide col fatturato)': 'Total (matches revenue)',
        "Nessun dettaglio servizi per quest'anno. I servizi si scrivono in":
            'No breakdown by service for this year. Services are defined in',
        'Stato fatture {anno}': 'Invoice status {anno}',
        'Emesse': 'Issued',
        'Pagate': 'Paid',
        'Spedite per email': 'Sent by email',
        "Fatte con l'app, non ancora spedite": 'Created in the app, not yet sent',
        # --- Fatture, l'elenco ---
        '{n} fatture': '{n} invoices',
        'totale': 'total',
        'Tutti gli anni': 'All years',
        'Tutti gli stati': 'All statuses',
        'Cerca cliente o numero…': 'Search client or number…',
        'Cerca': 'Search',
        '+ Nuova': '+ New',
        'Nr.': 'No.',
        'Cliente': 'Client',
        'Email': 'Email',
        'Data': 'Date',
        'Importo': 'Amount',
        'Stato': 'Status',
        'Inviata': 'Sent',
        'Origine': 'Origin',
        'emessa': 'issued',
        'pagata': 'paid',
        'Clicca per cambiare stato': 'Click to change status',
        'storico': 'history',
        # --- Fattura, la singola ---
        'Fattura #{n}': 'Invoice #{n}',
        'Qta': 'Qty',
        'Descrizione': 'Description',
        'Prezzo unit.': 'Unit price',
        'Totale': 'Total',
        'TOTALE': 'TOTAL',
        'Apri PDF': 'Open PDF',
        'Scarica docx': 'Download docx',
        'Mostra nel Finder': 'Show in Finder',
        'Apri file originale (storico)': 'Open the original file (history)',
        'Manda per email': 'Send by email',
        'Segna DA INCASSARE': 'Mark as UNPAID',
        'Segna PAGATA': 'Mark as PAID',
        'Elimina': 'Delete',
        "Eliminare la fattura #{n}? I file finiscono nel Cestino dell'app.":
            "Delete invoice #{n}? The files go to the app's Trash.",
        'Inviata per email il {data}': 'Sent by email on {data}',
        ' alle {ora}': ' at {ora}',
        'Origine:': 'Origin:',
        'creata con questa app': 'created in this app',
        'importata dallo storico ({file})': 'imported from the history ({file})',
        # --- Nuova fattura ---
        "Numero assegnato automaticamente. Il totale lo calcola l'app: zero errori.":
            'The number is assigned automatically. The app does the maths: no slips.',
        '— scegli cliente —': '— choose a client —',
        'Nuovo cliente': 'New client',
        'Nome e cognome': 'First and last name',
        'Mario Rossi': 'John Smith',
        'Indirizzo — riga 1 (via e numero)': 'Address — line 1 (street and number)',
        'Via Roma 1': 'Bahnhofstrasse 1',
        'Indirizzo — riga 2 (CAP e città)': 'Address — line 2 (postcode and town)',
        'Data fattura': 'Invoice date',
        'Numero (auto: {n})': 'Number (auto: {n})',
        'Il #{n} si è liberato: la fattura di {cliente} con questo numero è nel '
        'Cestino. Riusandolo non lasci buchi nella numerazione.':
            'Number {n} is free again: the invoice for {cliente} with that number is in '
            'the Trash. Reusing it leaves no gap in the sequence.',
        'Servizio': 'Service',
        'Righe fattura': 'Invoice lines',
        'Totale riga': 'Line total',
        '+ Aggiungi riga': '+ Add line',
        'Puoi scrivere i prezzi come preferisci:': 'Write the prices however you like:',
        'Se lasci vuoto il totale riga, lo calcolo io (quantità × prezzo).':
            'Leave the line total empty and I work it out (quantity × price).',
        'Crea fattura (docx + PDF)': 'Create invoice (docx + PDF)',
        # --- Nuova fattura: le frasi che scrive il browser ---
        'Descrizione del servizio': 'Description of the service',
        'Rimuovi': 'Remove',
        "Periodo proposto in automatico (mese successivo all'ultima fattura: "
        '{periodo}). Controlla le date e correggi se serve.':
            'Period filled in automatically (the month after the last invoice: '
            '{periodo}). Check the dates and correct them if needed.',
        'La fattura sarà intestata a {chi}, non a {cliente}.':
            'The invoice will be made out to {chi}, not to {cliente}.',
        # --- Clienti ---
        "Il registro clienti dell'app. Le modifiche valgono per le prossime fatture.":
            "The app's client register. Changes apply to the next invoices.",
        'Indirizzo': 'Address',
        'Fatturato tot.': 'Total revenue',
        'Ultima': 'Last',
        '(archiviato)': '(archived)',
        'abbonamento mensile': 'monthly subscription',
        'fattura a {chi}': 'invoiced to {chi}',
        'modifica': 'edit',
        'Nome': 'Name',
        'Indirizzo riga 1': 'Address line 1',
        'Indirizzo riga 2': 'Address line 2',
        'Etichetta nome file': 'Label used in file names',
        'Come ti firmi con lui/lei': 'How you sign off with them',
        'Lingua della fattura e della mail': 'Language of the invoice and the email',
        'È la lingua dei documenti che riceve lui, non quella con cui usi tu l’app.':
            'This is the language of the documents they receive, not the one you use the app in.',
        'Informale': 'Informal',
        'Formale': 'Formal',
        '(non ancora scritto)': '(not written yet)',
        'Abbonamento mensile (ordine permanente)': 'Monthly subscription (standing order)',
        'Intesta la fattura a': 'Make the invoice out to',
        'lascia vuoto: la fattura va intestata a {nome}':
            'leave empty: the invoice goes to {nome}',
        'Quando chi fa le sedute e chi riceve la fattura sono due persone diverse. '
        'Il documento e il registro portano questo nome; il nome del file resta «{file}».':
            'For when the person training and the person paying are not the same. The '
            'document and the register carry this name; the file name stays «{file}».',
        "Sull'estratto conto paga come": 'On the bank statement pays as',
        'lascia vuoto se paga col suo nome': 'leave empty if they pay under their own name',
        "Serve alla pagina Banca quando i soldi arrivano da un'altra persona (marito, "
        'moglie, azienda). Più nomi separati da punto e virgola.':
            'Used by the Bank page when the money comes from someone else (spouse, '
            'company). Several names separated by semicolons.',
        'Note': 'Notes',
        'Archiviato': 'Archived',
        'Salva': 'Save',
        'Aggiungi cliente': 'Add a client',
        'Indirizzo — via e numero': 'Address — street and number',
        'Indirizzo — CAP e città': 'Address — postcode and town',
        'Aggiungi': 'Add',
        'nome@esempio.ch': 'name@example.ch',
        # --- Crediti ---
        'Crediti sessioni': 'Session credits',
        'Ogni sessione svolta consuma un credito. Quando il pacchetto finisce, si rifattura.':
            'Every session done uses up a credit. When the pack runs out, you invoice again.',
        'Registro dal {data}.': 'Register since {data}.',
        'Chi lavora a crediti': 'Who works on credits',
        'Il calendario non è ancora collegato: le sessioni non si registrano da sole.':
            'The calendar is not connected yet: sessions do not record themselves.',
        'Collega il calendario': 'Connect the calendar',
        "Il calendario non risponde — qui sotto vedi l'ultima lettura riuscita.":
            'The calendar is not answering — below is the last successful reading.',
        'Riprova adesso': 'Try again now',
        'Sessioni lette da {calendario}': 'Sessions read from {calendario}',
        ' · ultima lettura {data} alle {ora}': ' · last read {data} at {ora}',
        'Aggiorna adesso': 'Refresh now',
        'Crediti terminati per {n} cliente:': 'Credits used up for {n} client:',
        'Crediti terminati per {n} clienti:': 'Credits used up for {n} clients:',
        'i pacchetti si pagano in anticipo: emetti la prossima fattura per ridare crediti.':
            'packs are paid up front, so issue the next invoice to give the credits back.',
        'Nessun cliente a crediti': 'No clients on credits',
        'I crediti servono a chi vende pacchetti di sessioni prepagate: il cliente compra dieci sedute, ogni incontro ne consuma una, quando finiscono si rifattura.':
            'Credits are for anyone selling prepaid session packs: the client buys ten sessions, each meeting uses one, and when they run out you invoice again.',
        "Perché l'app possa contarle, deve sapere chi sono e quale nome cercare nei titoli del tuo calendario.":
            'For the app to count them, it needs to know who they are and which word to look for in your calendar titles.',
        'Aggiungi il primo': 'Add the first one',
        'Pacchetto': 'Pack',
        'Usati': 'Used',
        'Rimasti': 'Left',
        'Dal': 'Since',
        'Ultima sessione': 'Last session',
        'pacchetto {chi}': 'pack of {chi}',
        'pacchetto': 'pack',
        'Crediti terminati': 'Credits used up',
        'In esaurimento': 'Running low',
        'In corso': 'In progress',
        '✓ incassata': '✓ collected',
        'da incassare': 'to collect',
        'fatturato ({rif}) — numero non registrato':
            'invoiced ({rif}) — number not recorded',
        'Cambia fattura': 'Change invoice',
        'Collega fattura': 'Link an invoice',
        'Numero della fattura che copre {pacchetto}':
            'Number of the invoice that covers {pacchetto}',
        'intestata a {chi}': 'made out to {chi}',
        'es. 84': 'e.g. 84',
        'Collega e chiudi pacchetto': 'Link and close the pack',
        'Prima creo la fattura →': 'Let me create the invoice first →',
        'Registra quale fattura copre questo pacchetto e marca le {n} sessioni. Non sostituisce la prossima fattura: il pacchetto nuovo si apre da solo alla prossima sessione.':
            'Records which invoice covers this pack and marks its {n} sessions. It does not replace the next invoice: the new pack opens by itself at the next session.',
        'Aggiornare i crediti dal calendario': 'Updating credits from the calendar',
        "Non c'è ancora nulla da leggere: la lettura del calendario parte dal {inizio} e oggi è il {oggi}.":
            'Nothing to read yet: the calendar is read from {inizio} onwards and today is {oggi}.',
        'Intervallo da leggere su {calendario}:': 'Range to read on {calendario}:',
        "Il calendario lo legge l'app da sola, ogni volta che apri questa pagina (al massimo una volta ogni quarto d'ora); con «Aggiorna adesso» lo rileggi subito. Le sessioni già registrate non vengono mai duplicate (ogni evento porta il suo ID Google), e lo storico validato non viene mai riscritto.":
            'The app reads the calendar by itself every time you open this page (at most once every quarter of an hour); «Refresh now» reads it again straight away. Sessions already recorded are never duplicated (every event carries its Google ID), and validated history is never rewritten.',
        'Gli appuntamenti futuri non consumano crediti: contano solo le sessioni fino a oggi. Una sessione cancellata consuma comunque il credito.':
            'Future appointments use no credits: only sessions up to today count. A cancelled session still uses its credit.',
        'Ultime fatture': 'Latest invoices',
        # --- Clienti a crediti ---
        'Clienti a crediti': 'Clients on credits',
        "Chi compra un pacchetto di sessioni prepagate. Per ognuno l'app sa quale parola cercare nei titoli del calendario, quante sessioni vale un pacchetto e a che prezzo lo riconosce sulle fatture.":
            'Anyone who buys a prepaid pack of sessions. For each one the app knows which word to look for in the calendar titles, how many sessions a pack is worth and at which price it recognises one on the invoices.',
        'Torna ai crediti': 'Back to credits',
        "Non c'è ancora nessuno": 'Nobody here yet',
        "Finché questo elenco è vuoto, la pagina Crediti resta vuota anche lei: l'app non sa quali nomi cercare nel calendario. Aggiungi qui sotto il primo cliente che lavora a pacchetto.":
            'While this list is empty the Credits page stays empty too: the app does not know which names to look for in the calendar. Add the first client who works on packs below.',
        'Chi paga a sessione singola o a fattura mensile non va messo qui: questa pagina serve solo ai pacchetti prepagati.':
            'Anyone paying per single session or by monthly invoice does not belong here: this page is only for prepaid packs.',
        'Nel calendario': 'In the calendar',
        'Pacchetti': 'Packs',
        'Prezzo': 'Price',
        'supplemento di {chi}': 'add-on to {chi}',
        '({n} nel registro)': '({n} in the register)',
        'Sessioni per pacchetto': 'Sessions per pack',
        'Sigla del pacchetto': 'Pack code',
        'I pacchetti si chiamano {sigla}-01, {sigla}-02 e così via.':
            'The packs are called {sigla}-01, {sigla}-02 and so on.',
        'Prezzo del pacchetto': 'Price of the pack',
        "Quando emetti una fattura di questo importo, l'app capisce da sola che ha comprato un pacchetto e gli ridà i crediti. Più prezzi separati da virgola, se ne hai più di uno.":
            'When you issue an invoice for this amount, the app works out by itself that they bought a pack and gives the credits back. Several prices separated by commas, if you have more than one.',
        'lascia vuoto: la fattura va a {nome}': 'leave empty: the invoice goes to {nome}',
        'È il supplemento di': 'Is the add-on to',
        'lascia vuoto quasi sempre': 'leave empty almost always',
        "Solo per chi fa le sedute in coppia e paga un pacchetto ridotto in aggiunta a quello dell'altro. Scrivi qui la parola-calendario dell'altro. Nei giorni in cui l'altro non c'è, la sessione è piena e scala dal pacchetto dell'altro.":
            'Only for someone who trains as a pair and pays a reduced pack on top of the other person\\u2019s. Write the other person\\u2019s calendar word here. On days when the other one is away, the session counts in full and comes off the other pack.',
        'Archiviato — non è più cliente, ma il suo nome si riconosce ancora nei titoli':
            'Archived — no longer a client, but the name is still recognised in the titles',
        'Tolgo {nome} dai clienti a crediti?': 'Remove {nome} from the clients on credits?',
        "Togli dall'elenco": 'Remove from the list',
        'Aggiungi un cliente a crediti': 'Add a client on credits',
        'Parola da cercare nei titoli del calendario':
            'Word to look for in the calendar titles',
        'lascia vuoto: usa il nome': 'leave empty: the name is used',
        'Un evento che si chiama «Anna», «anna pt» o «Anna - cancelled» conta come una sua sessione. Scegli una parola che non compaia per caso in altri appuntamenti.':
            'An event called «Anna», «anna pt» or «Anna - cancelled» counts as one of their sessions. Pick a word that does not turn up by chance in other appointments.',
        'lascia vuoto: le prime tre lettere': 'leave empty: the first three letters',
        # --- Pacchetto ---
        'Pacchetto {id}': 'Pack {id}',
        '{n} sessioni su {crediti} crediti': '{n} sessions out of {crediti} credits',
        'dal {inizio}': 'from {inizio}',
        ' al {fine}': ' to {fine}',
        ' (aperto)': ' (open)',
        'fatturato:': 'invoiced:',
        'si': 'yes',
        'no': 'no',
        'Titolo sul calendario': 'Title in the calendar',
        'cancellata — credito consumato': 'cancelled — credit used',
        'da calendario': 'from the calendar',
        # --- Agenda ---
        'Le sedute davvero svolte: una per credito consumato. Gli appuntamenti ancora da fare non compaiono.':
            'The sessions actually done: one for each credit used. Appointments still to come do not show up.',
        'sessioni': 'sessions',
        'sessioni nel {anno}': 'sessions in {anno}',
        'di cui con orario:': 'of which with a time:',
        'annullate (credito consumato):': 'cancelled (credit used):',
        'Aggiorna gli orari dal calendario': 'Refresh the times from the calendar',
        'Anno': 'Year',
        'tutti': 'all',
        'Filtra': 'Filter',
        'Azzera': 'Clear',
        "Di {n} sessioni non conosco l'ora. Sono quelle dei calendari vecchi, che «{calendario}» non contiene più. Se incolli in":
            'For {n} sessions I do not know the time. They come from old calendars, which «{calendario}» no longer holds. If you paste into',
        "anche l'indirizzo iCal del calendario storico, si riempiono da sole.":
            'the iCal address of the old calendar too, they fill in by themselves.',
        'Giorno': 'Day',
        'Ora': 'Time',
        'Sul calendario': 'In the calendar',
        'Credito': 'Credit',
        'Fattura': 'Invoice',
        'annullata': 'cancelled',
        'Nessuna sessione con questi filtri.': 'No sessions with these filters.',
        # --- Banca ---
        'Gli accrediti del tuo estratto conto, accostati alle fatture.':
            'The money in on your bank statement, set side by side with your invoices.',
        "L'app non segna niente da sola": 'The app marks nothing by itself',
        ': propone, confermi tu.': ': it suggests, you confirm.',
        'versamenti da decidere': 'payments to decide on',
        'di cui {n} con una proposta chiara': 'of which {n} with a clear match',
        '{n} già sistemati': '{n} already sorted',
        "Nella cartella non c'è ancora nessun estratto conto.":
            'There is no bank statement in the folder yet.',
        "Scarica dall'e-banking i movimenti (CSV, oppure il formato {a} / {b} in XML, che è quello standard svizzero e funziona meglio) e appoggia i file qui:":
            'Download the transactions from your e-banking (CSV, or the {a} / {b} format in XML, which is the Swiss standard and works better) and drop the files here:',
        "Poi ricarica questa pagina. I file restano tuoi e sul tuo Mac: l'app li legge e basta, non li sposta e non li modifica. Legge {sole}: quello che spendi non lo guarda.":
            'Then reload this page. The files stay yours and stay on your Mac: the app only reads them, it does not move or change them. It reads {sole}: what you spend it never looks at.',
        'solo le entrate': 'only the money coming in',
        'arrivati il {data}': 'arrived on {data}',
        '(nessuna causale)': '(no reference text)',
        'il riferimento del pagamento combacia': 'the payment reference matches',
        'importo e nome combaciano': 'amount and name match',
        "combacia solo l'importo": 'only the amount matches',
        '{n} giorni prima': '{n} days earlier',
        'il riferimento del pagamento è quello della fattura':
            'the payment reference is the one on the invoice',
        'importo esatto e la causale cita la data di questa fattura':
            'exact amount, and the reference text quotes the date of this invoice',
        'importo esatto e il nome compare nella causale':
            'exact amount and the name appears in the reference text',
        'importo esatto, ma il nome non compare nella causale':
            'exact amount, but the name does not appear in the reference text',
        ' — già segnata pagata, confermando aggiungo solo la data':
            ' — already marked paid; confirming only adds the date',
        '{quante} fatture dello stesso cliente che insieme fanno esattamente questo importo':
            '{quante} invoices from the same client that together make exactly this amount',
        'Segnare la #{n} pagata il {data}?': 'Mark #{n} as paid on {data}?',
        'Conferma': 'Confirm',
        'È questa': 'This is the one',
        'Nessuna fattura da sola fa questo importo, ma queste insieme sì:':
            'No single invoice makes this amount, but these together do:',
        'Segnare {numeri} pagate il {data}?': 'Mark {numeri} as paid on {data}?',
        'Sono queste': 'These are the ones',
        "Nessuna fattura aperta con questo importo nei giorni intorno. Può essere un rimborso, un giroconto o un pagamento che non c'entra.":
            'No open invoice with this amount in the days around it. It could be a refund, a transfer between your own accounts, or a payment that has nothing to do with this.',
        'Oppure dimmelo tu — numero della fattura:':
            'Or just tell me — invoice number:',
        'es. 53, 58': 'e.g. 53, 58',
        "anche se l'importo non torna": 'even if the amount does not add up',
        'Collega': 'Link',
        'Non è una fattura — metti da parte': 'Not an invoice — set it aside',
        'Già sistemati': 'Already sorted',
        "dall'app": 'by the app',
        'messo da parte': 'set aside',
        'Annulla': 'Undo',
        "Il pallino verde comparirà quando le fatture usciranno come QR-fattura con riferimento: da lì in poi l'accostamento non è più un'ipotesi.":
            'The green dot will appear once invoices go out as QR-invoices with a reference: from then on the match is no longer a guess.',
        'Questa cartella non esiste.': 'This folder does not exist.',
        'Non ho riconosciuto le colonne: manca una intestazione con data e importo.':
            'I did not recognise the columns: there is no header row with a date and an amount.',
        'Per leggere i PDF serve la libreria pypdf.':
            'Reading PDFs needs the pypdf library.',
        # --- Commercialista ---
        'Pacchetto per la commercialista': 'Package for the accountant',
        "Tutto quello che serve a {nome} ({citta}), pronto in un click: Excel col registro fatture, riepilogo PDF e copia di tutte le fatture dell'anno, in un unico zip.":
            'Everything {nome} ({citta}) needs, ready in one click: an Excel invoice register, a PDF summary and a copy of every invoice of the year, in a single zip.',
        'Fatturato': 'Revenue',
        'Incassato': 'Collected',
        'Fonte': 'Source',
        'Excel storico': 'historical Excel',
        'Genera pacchetto {anno}': 'Build the {anno} package',
        'Nota: per 2022–2023 il pacchetto contiene i dati disponibili nelle fatture; i totali ufficiali di quegli anni vengono dai riepiloghi Excel dello storico.':
            'Note: for 2022–2023 the package holds the data available in the invoices; the official totals for those years come from the historical Excel summaries.',
        'Pacchetti generati': 'Packages built',
        'Scarica zip': 'Download zip',
        # --- i messaggi che compaiono in alto dopo un’azione ---
        'Fattura #{n} creata e verificata ✓ — {tot} (importo confermato identico su Word e PDF).':
            'Invoice #{n} created and checked ✓ — {tot} (amount confirmed identical on Word and PDF).',
        ' Il numero #{n} è stato riusato da una fattura nel Cestino.':
            ' Number #{n} was reused from an invoice in the Trash.',
        ' 🎟️ Crediti invariati: questa fattura non compra un pacchetto di sessioni.':
            ' 🎟️ Credits unchanged: this invoice does not buy a pack of sessions.',
        'Collegata al pacchetto {pid} di {nome}, che ha ancora {rimasti} crediti.':
            'Linked to pack {pid} of {nome}, which still has {rimasti} credits.',
        '{nome} ha ancora crediti sul pacchetto {pid}: questa fattura resta in attesa e aprirà il pacchetto successivo alla prima sessione utile.':
            '{nome} still has credits on pack {pid}: this invoice waits and will open the next pack at the first session that comes.',
        'Aperto il pacchetto {pid} per {nome}: {crediti} crediti disponibili.':
            'Opened pack {pid} for {nome}: {crediti} credits available.',
        '⚠️ Crediti NON aggiornati. Questa sembra una fattura-pacchetto per {chi}, ma il totale è {tot} mentre il pacchetto costa {attesi}. Controlla la quantità e il prezzo: per un pacchetto da {crediti} crediti la quantità di solito non è 1. Se invece il prezzo è cambiato davvero, aggiornalo nella scheda del cliente a crediti.':
            '⚠️ Credits NOT updated. This looks like a pack invoice for {chi}, but the total is {tot} while the pack costs {attesi}. Check the quantity and the price: for a pack of {crediti} credits the quantity is usually not 1. If the price really has changed, update it in the card of that client on credits.',
        'Non sono riuscito ad aggiornare i crediti per questa fattura: controlla la pagina Crediti.':
            'I could not update the credits for this invoice: have a look at the Credits page.',
        'La fattura è salvata, ma la copia di sicurezza fuori dal Mac non è riuscita: {guaio} — controlla in Impostazioni.':
            'The invoice is saved, but the backup copy off this Mac did not work: {guaio} — have a look in Settings.',
        'Fattura #{n} spostata nel Cestino. Nulla è andato perso: puoi ripristinarla dalla pagina Cestino.':
            'Invoice #{n} moved to the Trash. Nothing is lost: you can restore it from the Trash page.',
        'Fattura #{n} ripristinata ({quanti} file rimessi al loro posto).':
            'Invoice #{n} restored ({quanti} files put back where they were).',
        'Cliente aggiornato.': 'Client updated.',
        'Cliente «{nome}» aggiunto.': 'Client «{nome}» added.',
        'Pacchetto {anno} pronto: Excel + PDF riepilogo + {quante} fatture PDF. Zip: {zip}':
            '{anno} package ready: Excel + PDF summary + {quante} invoice PDFs. Zip: {zip}',
        ' — PDF non trovati per: {elenco}': ' — no PDF found for: {elenco}',
        '{nome} è ora fra i clienti a crediti.': '{nome} is now one of the clients on credits.',
        'Modifiche salvate per {nome}.': 'Changes saved for {nome}.',
        '{nome} non è più fra i clienti a crediti.':
            '{nome} is no longer one of the clients on credits.',
        'Pacchetto {pid} collegato alla fattura #{n} ({cliente}): {quante} sessioni marcate. Il prossimo pacchetto si apre da solo alla prima sessione nuova.':
            'Pack {pid} linked to invoice #{n} ({cliente}): {quante} sessions marked. The next pack opens by itself at the first new session.',
        'Corretta la fattura #{n} ({cliente}): {cosa}. La correzione resta anche dopo un Reimporta.':
            'Invoice #{n} corrected ({cliente}): {cosa}. The correction stays even after a re-import.',
        'Correzione annullata: il dato è tornato come nel file di origine.':
            'Correction undone: the value is back to what the original file says.',
        'Anomalia archiviata. La trovi in fondo alla pagina se ti serve rivederla.':
            'Issue filed away. You find it at the bottom of the page if you need to see it again.',
        "Anomalia ripristinata: torna nell'elenco dei controlli.":
            'Issue brought back: it returns to the list of checks.',
        'Reimport completato: {dettaglio}': 'Re-import finished: {dettaglio}',
        'Seleziona un cliente.': 'Choose a client.',
        'Inserisci almeno una riga con descrizione e importo.':
            'Put in at least one line with a description and an amount.',
        'Il numero #{n} esiste già. Il prossimo libero è #{libero}.':
            'Number #{n} already exists. The next free one is #{libero}.',
        'Esiste già un file «{file}» — per sicurezza non sovrascrivo.':
            'A file «{file}» already exists — to be safe I am not overwriting it.',
        '⚠️ Fattura NON creata: la verifica automatica ha trovato un problema. {guai} Nessun file è stato salvato: controlla i dati e riprova.':
            '⚠️ Invoice NOT created: the automatic check found a problem. {guai} No file was saved: check the data and try again.',
        'Fattura inviata a {a} il {data} alle {ora}.': 'Invoice sent to {a} on {data} at {ora}.',
        '{quante} fatture inviate a {a} il {data} alle {ora}.':
            '{quante} invoices sent to {a} on {data} at {ora}.',
        'Le fatture importate dallo storico non si possono eliminare da qui.':
            'Invoices imported from the history cannot be deleted from here.',
        'Nome mancante.': 'Name missing.',
        "Manca l'indirizzo iCal del calendario: si incolla in Impostazioni.":
            'The iCal address of the calendar is missing: you paste it in Settings.',
        'Servono almeno il nome e la parola da cercare nel calendario.':
            'At least the name and the word to look for in the calendar are needed.',
        '«{chi}» non è fra i clienti a crediti: aggiungilo prima.':
            '«{chi}» is not among the clients on credits: add them first.',
        "{nome} ha {quanti} pacchetto nel registro: cancellare la scheda perderebbe quella storia. L'ho archiviata — il nome resta riconosciuto nel calendario, ma non si aprono più pacchetti nuovi.":
            '{nome} has {quanti} pack in the register: deleting the card would lose that history. I have archived it — the name is still recognised in the calendar, but no new packs will open.',
        "{nome} ha {quanti} pacchetti nel registro: cancellare la scheda perderebbe quella storia. L'ho archiviata — il nome resta riconosciuto nel calendario, ma non si aprono più pacchetti nuovi.":
            '{nome} has {quanti} packs in the register: deleting the card would lose that history. I have archived it — the name is still recognised in the calendar, but no new packs will open.',
        "Ho collegato da solo {quanti} versamento, quello su cui non c'era niente da decidere: {quali}{extra}. Lo trovi qui sotto marcato «collegato dall'app»: se sbaglio, Annulla.":
            'I linked {quanti} payment by myself, the one where there was nothing to decide: {quali}{extra}. You find it below marked «linked by the app»: if I got it wrong, Undo.',
        "Ho collegato da solo {quanti} versamenti, quelli su cui non c'era niente da decidere: {quali}{extra}. Li trovi qui sotto marcati «collegato dall'app»: se sbaglio, Annulla.":
            'I linked {quanti} payments by myself, the ones where there was nothing to decide: {quali}{extra}. You find them below marked «linked by the app»: if I got it wrong, Undo.',
        'Quel versamento non è più nei file della cartella.':
            'That payment is no longer in the files in the folder.',
        'Versamento messo da parte: non è una fattura.':
            'Payment set aside: it is not an invoice.',
        'Un calendario non ha risposto: {guaio}': 'A calendar did not answer: {guaio}',
        'Orari trovati: {quanti}.': 'Times found: {quanti}.',
        'Indica il numero della fattura.': 'Give the invoice number.',
        'Non esiste una fattura #{n}.': 'There is no invoice #{n}.',
        'Fattura non trovata.': 'Invoice not found.',
        'Non hai inserito nulla da correggere.': 'You have not entered anything to correct.',
        'Impostazioni salvate.': 'Settings saved.',
        'Logo aggiornato. Lo trovi sulle prossime fatture, in PDF e in Word.':
            'Logo updated. You will find it on the next invoices, in PDF and in Word.',
        'Logo rimosso: al suo posto torna il segnaposto.':
            'Logo removed: the placeholder comes back in its place.',
        "Non c'era nessun logo da rimuovere.": 'There was no logo to remove.',
        "Copia creata e verificata: {file} ({kb} KB). Il database dentro l'archivio è integro.":
            'Copy made and checked: {file} ({kb} KB). The database inside the archive is sound.',
        'Copia NON riuscita: {guaio}': 'Copy did NOT work: {guaio}',
        "Storico ({quanti} documenti): invariato dall'ultima copia, non ne serviva una nuova.":
            'History ({quanti} documents): unchanged since the last copy, a new one was not needed.',
        'Storico copiato: {file} — {quanti} documenti.':
            'History copied: {file} — {quanti} documents.',
        'Copia dello storico NON riuscita: {guaio}': 'Copy of the history did NOT work: {guaio}',
        'Nome del nuovo cliente mancante.': 'Name of the new client missing.',
        'Non hai scelto nessun file.': 'You have not chosen a file.',
        'Immagine troppo pesante ({kb} KB): il massimo è 5 MB.':
            'Image too heavy ({kb} KB): the maximum is 5 MB.',
        "Non riesco a leggere questo file: dev'essere un'immagine (PNG, JPG).":
            'I cannot read this file: it has to be an image (PNG, JPG).',
        ' e altri {n}': ' and {n} more',
        'Riga {n}: importo non riconosciuto («{cosa}»).':
            'Line {n}: amount not recognised («{cosa}»).',
        "Non mando niente finché c'è un problema aperto: {guai}":
            'I am sending nothing while a problem is open: {guai}',
        'Non è partita: {guaio}': 'It did not go out: {guaio}',
        'La mail è partita, ma non sono riuscito a metterne una copia in Inviata: {guaio}':
            'The mail went out, but I could not put a copy of it in Sent: {guaio}',
        "Prova inviata a {a}{dove}. Guarda com'è arrivata prima di mandarla al cliente.":
            'Test sent to {a}{dove}. Have a look at how it arrived before sending it to the client.',
        ' e ne trovi la copia in «{cartella}»': ' and you find the copy in «{cartella}»',
        "Il calendario non risponde: {guaio} — i crediti qui sotto sono quelli dell'ultima lettura riuscita.":
            'The calendar is not answering: {guaio} — the credits below are the ones from the last successful read.',
        'I crediti devono essere un numero.': 'The credits have to be a number.',
        'Collegamento annullato. Il versamento torna fra quelli da decidere.':
            'Link undone. The payment goes back among the ones to decide on.',
        'Fattura {quali} segnata pagata il {data}.': 'Invoice {quali} marked paid on {data}.',
        'Fatture {quali} segnate pagate il {data}.': 'Invoices {quali} marked paid on {data}.',
        'Nessun orario nuovo: il calendario non sa altro di quei giorni.':
            'No new times: the calendar knows nothing more about those days.',
        'Pacchetto inesistente.': 'No such pack.',
        'Importo «{cosa}» non riconosciuto. Scrivilo come 1’800.- oppure 1800.00 e riprova.':
            'Amount «{cosa}» not recognised. Write it as 1’800.- or 1800.00 and try again.',
        'Riga {n}: {qty} × {unit} = {calc}, ma il totale riga indicato è {tot}.{suggerimento} Correggi una delle cifre, oppure lascia vuoto il totale e lo calcolo io.':
            'Line {n}: {qty} × {unit} = {calc}, but the line total given is {tot}.{suggerimento} Fix one of the figures, or leave the total empty and I work it out.',
        ' La descrizione parla di {quante} sessioni: forse la quantità è {quante}?':
            ' The description mentions {quante} sessions: maybe the quantity is {quante}?',
        'Sessioni nuove registrate: {dettaglio}': 'New sessions recorded: {dettaglio}',
        'Calendario letto: nessuna sessione nuova.': 'Calendar read: no new sessions.',
        'Data non valida.': 'Date not valid.',
        'Attenzione: {quali} fa {somma} ma il versamento è di {importo} ({differenza}). Non ho collegato niente. Se è giusto lo stesso, rimetti i numeri e spunta la casella.':
            'Careful: {quali} makes {somma} but the payment is {importo} ({differenza}). I have linked nothing. If it is right anyway, put the numbers back and tick the box.',
        'La fattura numero {n} non esiste.': 'Invoice number {n} does not exist.',
        'Il numero {n} è su più di una fattura e dalla causale non capisco quale: {elenco}. Rinumerane una e riprova.':
            'Number {n} is on more than one invoice and the reference text does not tell me which: {elenco}. Renumber one of them and try again.',
        ' È il {n}° rifiuto: non provo più per {minuti} minuti, altrimenti il server blocca il tuo indirizzo IP. Correggi la password in Impostazioni — salvarla toglie la pausa.':
            ' That is refusal number {n}: I stop trying for {minuti} minutes, otherwise the server blocks your IP address. Fix the password in Settings — saving it lifts the pause.',
        # --- i mesi, per il grafico ---
        'Gen': 'Jan',
        'Feb': 'Feb',
        'Mar': 'Mar',
        'Apr': 'Apr',
        'Mag': 'May',
        'Giu': 'Jun',
        'Lug': 'Jul',
        'Ago': 'Aug',
        'Set': 'Sep',
        'Ott': 'Oct',
        'Nov': 'Nov',
        'Dic': 'Dec',
        # --- i giorni, per l’Agenda ---
        'lun': 'Mon',
        'mar': 'Tue',
        'mer': 'Wed',
        'gio': 'Thu',
        'ven': 'Fri',
        'sab': 'Sat',
        'dom': 'Sun',
        # --- Primi passi ---
        'Benvenuto': 'Welcome',
        'Questa è la tua app per le fatture. Gira sul tuo computer e basta: niente account, niente abbonamento, nessun dato che esce di qui. Scrive le fatture in Word e in PDF, tiene il conto di chi ha pagato e prepara il pacchetto per il commercialista.':
            'This is your invoicing app. It runs on your computer and nowhere else: no account, no subscription, no data leaving this machine. It writes invoices in Word and PDF, keeps track of who has paid, and puts together the package for your accountant.',
        '{fatti} di {totali} fatti.': '{fatti} of {totali} done.',
        'Manca ancora qualcosa di essenziale: senza, le fatture escono incomplete.':
            'Something essential is still missing: without it, the invoices come out incomplete.',
        "L'essenziale c'è. Il resto è comodità, quando ti va.":
            'The essentials are there. The rest is convenience, whenever you feel like it.',
        'serve davvero': 'really needed',
        'rivedi': 'review',
        'Vai alla Dashboard': 'Go to the Dashboard',
        "Finché mancano i tuoi dati e l'IBAN, l'app si apre qui. Appena li scrivi, si apre sulla Dashboard.":
            'While your details and your IBAN are missing, the app opens here. As soon as you write them, it opens on the Dashboard.',
        # --- i passi, uno per uno ---
        'Chi emette le fatture': 'Who issues the invoices',
        'Nome, indirizzo e numero IVA/IDI vanno in cima a ogni fattura.':
            'Name, address and VAT/UID number go at the top of every invoice.',
        'Scrivi i tuoi dati': 'Write your details',
        'Dove ti pagano': 'Where you get paid',
        "Senza IBAN la fattura esce senza il conto su cui incassare: è la cosa che si dimentica più facilmente e che costa di più.":
            'Without an IBAN the invoice goes out with no account to be paid into: the easiest thing to forget and the most expensive one.',
        "Scrivi l'IBAN": 'Write the IBAN',
        'Il tuo logo': 'Your logo',
        'Va sulle fatture e qui in alto a sinistra. Finché manca, sulla fattura quello spazio resta vuoto.':
            'It goes on the invoices and up here on the left. While it is missing, that space on the invoice stays empty.',
        'Carica il logo': 'Upload the logo',
        'I tuoi clienti': 'Your clients',
        'Li puoi anche aggiungere al volo mentre fai la prima fattura.':
            'You can also add them on the fly while making the first invoice.',
        'Aggiungi un cliente': 'Add a client',
        'La prima fattura': 'The first invoice',
        "L'app la scrive in Word e in PDF, controlla che i due documenti dicano lo stesso importo, e la mette in archivio.":
            'The app writes it in Word and in PDF, checks that the two documents say the same amount, and files it away.',
        'Fai la prima fattura': 'Make the first invoice',
        'Come si chiamano i tuoi servizi': 'What your services are called',
        "Serve a due cose: la Dashboard raggruppa il fatturato per servizio, e l'email nomina il servizio giusto. Finché è vuoto l'app non prova a indovinare: mette tutto in «Altro» e nell'email non lo nomina.":
            'Good for two things: the Dashboard groups revenue by service, and the email names the right service. While it is empty the app does not try to guess: it puts everything under «Other» and does not name it in the email.',
        'Scrivi i tuoi servizi': 'Write your services',
        'La posta': 'Email',
        "Serve solo se vuoi spedire le fatture dall'app invece di allegarle a mano.":
            'Only needed if you want to send invoices from the app instead of attaching them by hand.',
        'Collega la casella': 'Connect the mailbox',
        'I pacchetti di sessioni': 'Session packs',
        "Se vendi pacchetti prepagati, l'app tiene il conto delle sessioni leggendole dal tuo calendario.":
            'If you sell prepaid packs, the app keeps count of the sessions by reading them from your calendar.',
        # --- Impostazioni ---
        'Questi dati finiscono sulle fatture e negli esporti. Cambiali solo se cambia qualcosa davvero.':
            'These details end up on the invoices and in the exports. Change them only if something really changes.',
        'Nome attività': 'Business name',
        'UID / IDI': 'UID / VAT no.',
        'Indirizzo — riga 1': 'Address — line 1',
        'Indirizzo — riga 2': 'Address — line 2',
        'Telefono': 'Phone',
        'Sito': 'Website',
        'IBAN': 'IBAN',
        'Termini di pagamento': 'Payment terms',
        'Città commercialista': 'Accountant’s town',
        'Servizi proposti sulla nuova fattura': 'Services offered on a new invoice',
        'uno per riga, per esempio:': 'one per line, for example:',
        'Pacchetto 10 sedute': '10-session pack',
        'Abbonamento mensile': 'Monthly subscription',
        "Diventano i pulsanti sopra le righe della fattura. Se lasci vuoto, l'app propone le descrizioni che hai già usato di più. Per gli abbonamenti non scrivere le date: quando scegli il servizio, l'app riprende l'ultima fattura di quel cliente e sposta il periodo avanti di un mese.":
            'They become the buttons above the invoice lines. If you leave this empty, the app offers the descriptions you have used most. For subscriptions do not write the dates: when you pick the service, the app takes the last invoice of that client and moves the period one month forward.',
        "Servizi che l'app deve riconoscere": 'Services the app should recognise',
        "A cosa servono: la Dashboard raggruppa il fatturato per servizio, e l'email nomina il servizio e sceglie il testo giusto. Una riga per servizio, così: {esempio} — le parole sono quelle che compaiono nelle righe delle tue fatture. Senza {uguale}, il nome fa anche da parola. Vince la prima riga che riconosce, e gli abbonamenti si provano per primi. {vuoto}, l'app non prova a indovinare: l'email non nomina il servizio e la Dashboard mette tutto in «Altro».":
            'What they are for: the Dashboard groups revenue by service, and the email names the service and picks the right text. One line per service, like this: {esempio} — the words are the ones that appear in the lines of your invoices. Without {uguale}, the name doubles as the word. The first line that matches wins, and subscriptions are tried first. {vuoto}, the app does not try to guess: the email does not name the service and the Dashboard puts everything under «Other».',
        'Nome del servizio = parola, parola': 'Name of the service = word, word',
        'Se lasci vuoto': 'If you leave this empty',
        'In abbonamento — si rinnova ogni mese': 'By subscription — renews every month',
        'per esempio:': 'for example:',
        'Fisioterapia = fisioterapia, seduta': 'Physiotherapy = physiotherapy, session',
        'Coaching = coaching': 'Coaching = coaching',
        'A pacchetto — si compra una volta e si consuma':
            'By pack — bought once and used up',
        'Pacchetto sedute = pacchetto, sedute, session': 'Session pack = pack, sessions, session',
        'Cartella storico (solo lettura)': 'History folder (read-only)',
        'vuoto: nessuno storico da importare': 'empty: no history to import',
        'Cartella della copia di sicurezza (fuori dal Mac)':
            'Folder for the backup copy (off this Mac)',
        'Logo': 'Logo',
        "Va sulle fatture — in PDF e in Word — e qui nell'app, in alto a sinistra. Meglio un PNG con lo sfondo trasparente. Se è di un'altra forma non viene stirato: lo centriamo nello spazio che c'è.":
            'It goes on the invoices — in PDF and in Word — and here in the app, top left. A PNG with a transparent background works best. If it is a different shape it does not get stretched: we centre it in the space available.',
        'Questo è il tuo logo.': 'This is your logo.',
        'Non hai ancora caricato un logo: sulle fatture compare questo segnaposto.':
            'You have not uploaded a logo yet: this placeholder appears on the invoices.',
        'Carica': 'Upload',
        'Togli': 'Remove',
        'Tolgo il logo? Sulle fatture torna il segnaposto.':
            'Remove the logo? The placeholder comes back on the invoices.',
        'Calendario — sessioni automatiche': 'Calendar — automatic sessions',
        'Su Google Calendar: il calendario delle sessioni → Impostazioni del calendario → {voce}. Copia quell’indirizzo e incollalo qui. L’app leggerà le sessioni da sola ogni volta che apri la pagina Crediti. Un eventuale calendario storico {mai}: raddoppierebbe i crediti.':
            'In Google Calendar: the sessions calendar → Settings for the calendar → {voce}. Copy that address and paste it here. The app will read the sessions by itself every time you open the Credits page. An old calendar, if you have one, {mai}: it would double the credits.',
        'Indirizzo segreto in formato iCal': 'Secret address in iCal format',
        'non va mai messo qui sotto': 'must never go in the box below',
        'Indirizzo iCal segreto del calendario delle sessioni':
            'Secret iCal address of the sessions calendar',
        'Ultima lettura riuscita: {data} alle {ora}.': 'Last successful read: {data} at {ora}.',
        'Non ancora collegato.': 'Not connected yet.',
        'Chi ha questo indirizzo può leggere il calendario: trattalo come una password.':
            'Anyone with this address can read the calendar: treat it like a password.',
        'Indirizzo iCal del calendario storico — facoltativo':
            'iCal address of the old calendar — optional',
        'Serve {solo}, per sapere a che ora sono state fatte le sedute vecchie: da qui i crediti non passano mai, quindi non c’è modo che vengano contati due volte. Senza questo indirizzo l’Agenda funziona lo stesso, ma delle sessioni più vecchie mostra il giorno e non l’ora.':
            'It is needed {solo}, to know at what time the old sessions took place: credits never come through here, so there is no way they get counted twice. Without this address Sessions works all the same, but for the older ones it shows the day and not the time.',
        "solo all'Agenda": 'only for Sessions',
        'Posta — invio delle fatture': 'Email — sending the invoices',
        'Le mail partono dal tuo server, non da Gmail: se il tuo dominio autorizza solo il proprio server a spedire a suo nome (SPF {spf}), quelle mandate da Gmail finiscono in spam. Attenzione al nome del server: spesso il certificato copre {dominio} ma non {sotto}, e allora va scritto il primo.':
            'The mail leaves from your own server, not from Gmail: if your domain only authorises its own server to send in its name (SPF {spf}), anything sent from Gmail lands in spam. Watch the server name: the certificate often covers {dominio} but not {sotto}, and then it is the first one you have to write.',
        'tuodominio.ch': 'yourdomain.ch',
        'mail.tuodominio.ch': 'mail.yourdomain.ch',
        'Server SMTP': 'SMTP server',
        'Porta': 'Port',
        'Casella': 'Mailbox',
        'Password della casella': 'Password of the mailbox',
        '•••••••• (già salvata) — lascia vuoto per non cambiarla':
            '•••••••• (already saved) — leave empty to keep it',
        'non ancora inserita': 'not entered yet',
        'salvata: {n} caratteri': 'saved: {n} characters',
        'Mittente': 'Sender',
        'Indirizzo per le prove': 'Address for test emails',
        'Server IMAP (per la copia in Inviata)': 'IMAP server (for the copy in Sent)',
        'Cartella Inviata': 'Sent folder',
        'vuoto = la cerca da sola sul server': 'empty = it finds it by itself on the server',
        'Mandane una copia nascosta anche a me (arriva nella posta in arrivo, il cliente non la vede)':
            'Send a blind copy to me as well (it lands in my inbox, the client does not see it)',
        'I due oggetti': 'The two subject lines',
        'Uno per modello, scelto insieme al testo. Nell’abbonamento {mese} diventa il mese coperto dall’abbonamento ({a} se il periodo sta a cavallo di due mesi, {b} se no): l’app lo legge dal periodo scritto sulla fattura, e se manca riparte dall’ultima mail mandata a quella persona avanzando di un mese.':
            'One per template, picked together with the text. In the subscription one, {mese} becomes the month the subscription covers ({a} if the period straddles two months, {b} if not): the app reads it from the period written on the invoice, and if that is missing it starts from the last mail sent to that person and moves one month on.',
        'Abbonamento': 'Subscription',
        'Pacchetto di sedute': 'Session pack',
        'I due modelli della frase centrale': 'The two templates for the middle sentence',
        "L'app sceglie da sola quale usare guardando le righe della fattura, e nell'anteprima puoi passare all'altro con un click. Il resto della mail (apertura, frase sull'ordine permanente, firma) resta automatico.":
            'The app picks which one to use by looking at the invoice lines, and in the preview you can switch to the other with one click. The rest of the mail (opening, the standing-order sentence, the sign-off) stays automatic.',
        'Abbonamento — si rinnova ogni mese': 'Subscription — renews every month',
        'Pacchetto di sedute — si compra una volta': 'Session pack — bought once',
        'Come chiudi la mail': 'How you close the mail',
        'Due versioni: nella scheda di ogni cliente scegli quale usare. Vanno al posto di {saluto} nel modello qui sotto. Gli a capo contano.':
            'Two versions: in each client’s card you choose which one to use. They go in place of {saluto} in the template below. Line breaks count.',
        'Con chi ci si dà del tu': 'For people you are on first-name terms with',
        'Con tutti gli altri': 'For everyone else',
        'Modello del testo': 'Template of the text',
        'Sotto {saluto} va la tua firma: scrivila qui com’è in fondo alle mail che mandi davvero.':
            'Your signature goes under {saluto}: write it here exactly as it is at the bottom of the mails you actually send.',
        'Segnaposti:': 'Placeholders:',
        'Banca — collegamento automatico': 'Bank — automatic linking',
        'Quando metti un estratto nuovo nella cartella {cartella}, l’app può collegare da sola i versamenti su cui non c’è niente da decidere: importo esatto, un solo candidato, e il nome (o la data della fattura) nella causale. Tutto il resto continua a chiederlo a te.':
            'When you drop a new statement into the {cartella} folder, the app can link by itself the payments where there is nothing to decide: exact amount, a single candidate, and the name (or the invoice date) in the reference text. Everything else it still asks you about.',
        'Estratti conto': 'Bank statements',
        'Collega da solo i versamenti senza dubbi': 'Link the payments with no doubt by itself',
        'Nel dubbio non decide: se i candidati sono due, o se il nome non compare, la riga resta a te. Ogni riga decisa dall’app resta marcata «dall’app» nella pagina Banca e si annulla con un click.':
            'When in doubt it does not decide: if there are two candidates, or if the name does not appear, the row stays with you. Every row the app decided stays marked «by the app» on the Bank page and can be undone with one click.',
        'Copia di sicurezza fuori dal Mac': 'Backup copy off this Mac',
        'Uno zip con database, registro delle sessioni e tutti i PDF delle fatture. Viene creato all’avvio (una volta al giorno) e dopo ogni fattura nuova. Appena scritto viene riaperto e controllato: se il database dentro non è integro, l’archivio viene buttato e qui lo vedi scritto.':
            'A zip with the database, the sessions register and every invoice PDF. It is made at startup (once a day) and after each new invoice. As soon as it is written it is opened again and checked: if the database inside is not sound, the archive is thrown away and you see it said here.',
        'Ultima copia: {data} alle {ora} — {kb} KB': 'Last copy: {data} at {ora} — {kb} KB',
        'Nessuna copia ancora presente in questa cartella.':
            'No copy in this folder yet.',
        'Fai una copia adesso': 'Make a copy now',
        'Apri la cartella': 'Open the folder',
        'Quando': 'When',
        'Dimensione': 'Size',
        'Mi fermo qui. Il server ha già rifiutato la password due volte e al terzo tentativo blocca il tuo indirizzo IP per un pezzo. Riprova fra {restano} minuti, oppure correggi prima la password in Impostazioni: salvarla azzera questa pausa.':
            'I am stopping here. The server has already refused the password twice, and on the third try it blocks your IP address for a good while. Try again in {restano} minutes, or fix the password in Settings first: saving it clears this pause.',
    },
    'de': {
        # --- Menü ---
        'Dashboard': 'Übersicht',
        'Performance': 'Auswertung',
        'Nuova fattura': 'Neue Rechnung',
        'Fatture': 'Rechnungen',
        'Email inviate': 'Gesendete E-Mails',
        'Clienti': 'Kunden',
        'Crediti': 'Guthaben',
        'Agenda': 'Sitzungen',
        'Banca': 'Bank',
        'Commercialista': 'Treuhänder',
        'Controlli': 'Prüfungen',
        'Verifica calcoli': 'Rechenprüfung',
        'Cestino': 'Papierkorb',
        'Impostazioni': 'Einstellungen',
        'Primi passi': 'Erste Schritte',
        'Fatturare': 'Rechnungen stellen',
        'Chi segui': 'Deine Kunden',
        'Incassi e fisco': 'Zahlungen und Steuern',
        "L'app": 'Die App',
        # --- Rahmen, auf jeder Seite ---
        'Indietro': 'Zurück',
        'Torna alla schermata precedente': 'Zurück zum vorherigen Bildschirm',
        'App locale · dati sul tuo Mac': 'Lokale App · Daten auf deinem Mac',
        'Nascondi gli importi (screenshot, luogo pubblico)':
            'Beträge ausblenden (Screenshots, öffentliche Orte)',
        'Importi nascosti — clicca per mostrarli':
            'Beträge ausgeblendet — zum Anzeigen klicken',
        'Lingua': 'Sprache',
        # --- Übersicht ---
        'Fatturato {anno} ad oggi': 'Umsatz {anno} bis heute',
        'rispetto allo stesso periodo del {anno}':
            'gegenüber dem gleichen Zeitraum {anno}',
        'Vedi le performance': 'Auswertung ansehen',
        'Da fare': 'Zu erledigen',
        'Ultime cose': 'Letzte Aktivitäten',
        'Da incassare': 'Offene Zahlungen',
        'Fatte e non ancora spedite': 'Erstellt, noch nicht versendet',
        'Pacchetti finiti': 'Aufgebrauchte Pakete',
        'Estratto conto da aggiornare': 'Kontoauszug veraltet',
        'Niente in sospeso. Tutte le fatture sono partite e non aspetti soldi da nessuno.':
            'Nichts offen. Alle Rechnungen sind versendet und niemand schuldet dir Geld.',
        'Ancora niente da raccontare.': 'Noch nichts zu berichten.',
        'fatture': 'Rechnungen',
        'clienti': 'Kunden',
        'fattura': 'Rechnung',
        'cliente': 'Kunde',
        # --- die Einträge unter «Zu erledigen», vom Code zusammengesetzt ---
        '{tardi} ferme da oltre {giorni} giorni': '{tardi} seit über {giorni} Tagen offen',
        'nessuna in ritardo, sono tutte recenti': 'keine überfällig, alle sind neu',
        "sono nell'app ma non sono partite per email":
            'in der App vorhanden, aber noch nicht per E-Mail versendet',
        '{chi} — va emessa la prossima fattura': '{chi} — die nächste Rechnung ist fällig',
        ' e altri': ' und weitere',
        "non ne hai ancora caricato nessuno: l'app non sa chi ti ha pagato":
            'noch keiner geladen: die App weiss nicht, wer bezahlt hat',
        "l'ultimo arriva al {data}, {giorni} giorni fa":
            'der letzte reicht bis {data}, vor {giorni} Tagen',
        # --- «Letzte Aktivitäten» ---
        'Fattura #{n} a {cliente}': 'Rechnung #{n} an {cliente}',
        'Prova su di te': 'Test an dich selbst',
        ' — non è partita': ' — nicht versendet',
        'Invio fallito della #{n}': 'Versand von #{n} fehlgeschlagen',
        'Fattura #{n} spedita a {a}': 'Rechnung #{n} an {a} versendet',
        'Fattura #{n} spedita': 'Rechnung #{n} versendet',
        'Sessione di {cliente}': 'Sitzung mit {cliente}',
        ' (annullata)': ' (abgesagt)',
        'Crediti finiti: {pacchetto} ({cliente})':
            'Guthaben aufgebraucht: {pacchetto} ({cliente})',
        # --- Rest der Übersicht ---
        'gen — dic {anno}': 'Jan — Dez {anno}',
        'Manca ancora una cosa da mettere a posto: {elenco}.':
            'Eine Sache fehlt noch: {elenco}.',
        'Mancano ancora {n} cose da mettere a posto: {elenco}.':
            'Es fehlen noch {n} Dinge: {elenco}.',
        'Vedi i primi passi': 'Erste Schritte ansehen',
        # --- Auswertung ---
        "Come sta andando l'attività.": 'Wie das Geschäft läuft.',
        'Fatturato {anno}': 'Umsatz {anno}',
        ' (ad oggi)': ' (bis heute)',
        'Proiezione fine {anno}': 'Hochrechnung Ende {anno}',
        'al ritmo attuale (media giornaliera)': 'beim aktuellen Tempo (Tagesdurchschnitt)',
        'Fattura media': 'Durchschnittliche Rechnung',
        '{n} fatture nel {anno}': '{n} Rechnungen im Jahr {anno}',
        'Miglior cliente {anno}': 'Bester Kunde {anno}',
        'Andamento mensile {anno}': 'Monatsverlauf {anno}',
        'Per il {anno} lo storico è per totali annui (da Excel), senza dettaglio mensile.':
            'Für {anno} liegt die Historie nur als Jahrestotal vor (aus Excel), ohne Monatsdetail.',
        'valori in CHF': 'Werte in CHF',
        'Fatturato per anno': 'Umsatz nach Jahr',
        'da fatture': 'aus Rechnungen',
        'da Excel storico (2022–23)': 'aus historischem Excel (2022–23)',
        'Top clienti {anno}': 'Top-Kunden {anno}',
        'fatt.': 'Rg.',
        'Per tipo di servizio {anno}': 'Nach Dienstleistung {anno}',
        'Totale (coincide col fatturato)': 'Total (stimmt mit dem Umsatz überein)',
        "Nessun dettaglio servizi per quest'anno. I servizi si scrivono in":
            'Keine Aufteilung nach Dienstleistung für dieses Jahr. Dienstleistungen stehen unter',
        'Stato fatture {anno}': 'Rechnungsstatus {anno}',
        'Emesse': 'Ausgestellt',
        'Pagate': 'Bezahlt',
        'Spedite per email': 'Per E-Mail versendet',
        "Fatte con l'app, non ancora spedite": 'In der App erstellt, noch nicht versendet',
        # --- Rechnungen, die Liste ---
        '{n} fatture': '{n} Rechnungen',
        'totale': 'Total',
        'Tutti gli anni': 'Alle Jahre',
        'Tutti gli stati': 'Alle Status',
        'Cerca cliente o numero…': 'Kunde oder Nummer suchen…',
        'Cerca': 'Suchen',
        '+ Nuova': '+ Neu',
        'Nr.': 'Nr.',
        'Cliente': 'Kunde',
        'Email': 'E-Mail',
        'Data': 'Datum',
        'Importo': 'Betrag',
        'Stato': 'Status',
        'Inviata': 'Versendet',
        'Origine': 'Herkunft',
        'emessa': 'ausgestellt',
        'pagata': 'bezahlt',
        'Clicca per cambiare stato': 'Klicken, um den Status zu ändern',
        'storico': 'Historie',
        # --- Rechnung, die einzelne ---
        'Fattura #{n}': 'Rechnung #{n}',
        'Qta': 'Menge',
        'Descrizione': 'Beschreibung',
        'Prezzo unit.': 'Einzelpreis',
        'Totale': 'Total',
        'TOTALE': 'TOTAL',
        'Apri PDF': 'PDF öffnen',
        'Scarica docx': 'docx herunterladen',
        'Mostra nel Finder': 'Im Finder anzeigen',
        'Apri file originale (storico)': 'Originaldatei öffnen (Historie)',
        'Manda per email': 'Per E-Mail senden',
        'Segna DA INCASSARE': 'Als OFFEN markieren',
        'Segna PAGATA': 'Als BEZAHLT markieren',
        'Elimina': 'Löschen',
        "Eliminare la fattura #{n}? I file finiscono nel Cestino dell'app.":
            'Rechnung #{n} löschen? Die Dateien landen im Papierkorb der App.',
        'Inviata per email il {data}': 'Per E-Mail versendet am {data}',
        ' alle {ora}': ' um {ora}',
        'Origine:': 'Herkunft:',
        'creata con questa app': 'in dieser App erstellt',
        'importata dallo storico ({file})': 'aus der Historie importiert ({file})',
        # --- Neue Rechnung ---
        "Numero assegnato automaticamente. Il totale lo calcola l'app: zero errori.":
            'Die Nummer wird automatisch vergeben. Das Total rechnet die App: keine Fehler.',
        '— scegli cliente —': '— Kunde wählen —',
        'Nuovo cliente': 'Neuer Kunde',
        'Nome e cognome': 'Vor- und Nachname',
        'Mario Rossi': 'Hans Müller',
        'Indirizzo — riga 1 (via e numero)': 'Adresse — Zeile 1 (Strasse und Nummer)',
        'Via Roma 1': 'Bahnhofstrasse 1',
        'Indirizzo — riga 2 (CAP e città)': 'Adresse — Zeile 2 (PLZ und Ort)',
        'Data fattura': 'Rechnungsdatum',
        'Numero (auto: {n})': 'Nummer (automatisch: {n})',
        'Il #{n} si è liberato: la fattura di {cliente} con questo numero è nel '
        'Cestino. Riusandolo non lasci buchi nella numerazione.':
            'Die Nummer {n} ist wieder frei: die Rechnung von {cliente} mit dieser Nummer '
            'liegt im Papierkorb. Wenn du sie wiederverwendest, bleibt keine Lücke.',
        'Servizio': 'Dienstleistung',
        'Righe fattura': 'Rechnungszeilen',
        'Totale riga': 'Zeilentotal',
        '+ Aggiungi riga': '+ Zeile hinzufügen',
        'Puoi scrivere i prezzi come preferisci:': 'Schreib die Preise, wie du willst:',
        'Se lasci vuoto il totale riga, lo calcolo io (quantità × prezzo).':
            'Lässt du das Zeilentotal leer, rechne ich es aus (Menge × Preis).',
        'Crea fattura (docx + PDF)': 'Rechnung erstellen (docx + PDF)',
        # --- Neue Rechnung: was der Browser schreibt ---
        'Descrizione del servizio': 'Beschreibung der Dienstleistung',
        'Rimuovi': 'Entfernen',
        "Periodo proposto in automatico (mese successivo all'ultima fattura: "
        '{periodo}). Controlla le date e correggi se serve.':
            'Zeitraum automatisch vorgeschlagen (der Monat nach der letzten Rechnung: '
            '{periodo}). Prüfe die Daten und korrigiere sie bei Bedarf.',
        'La fattura sarà intestata a {chi}, non a {cliente}.':
            'Die Rechnung lautet auf {chi}, nicht auf {cliente}.',
        # --- Kunden ---
        "Il registro clienti dell'app. Le modifiche valgono per le prossime fatture.":
            'Das Kundenregister der App. Änderungen gelten für die nächsten Rechnungen.',
        'Indirizzo': 'Adresse',
        'Fatturato tot.': 'Umsatz total',
        'Ultima': 'Letzte',
        '(archiviato)': '(archiviert)',
        'abbonamento mensile': 'Monatsabo',
        'fattura a {chi}': 'Rechnung an {chi}',
        'modifica': 'bearbeiten',
        'Nome': 'Name',
        'Indirizzo riga 1': 'Adresse Zeile 1',
        'Indirizzo riga 2': 'Adresse Zeile 2',
        'Etichetta nome file': 'Bezeichnung im Dateinamen',
        'Come ti firmi con lui/lei': 'Wie du dich bei ihm/ihr verabschiedest',
        'Lingua della fattura e della mail': 'Sprache der Rechnung und der E-Mail',
        'È la lingua dei documenti che riceve lui, non quella con cui usi tu l’app.':
            'Das ist die Sprache der Dokumente, die er oder sie bekommt, nicht die, in der du die App benutzt.',
        'Informale': 'Informell',
        'Formale': 'Förmlich',
        '(non ancora scritto)': '(noch nicht geschrieben)',
        'Abbonamento mensile (ordine permanente)': 'Monatsabo (Dauerauftrag)',
        'Intesta la fattura a': 'Rechnung ausstellen auf',
        'lascia vuoto: la fattura va intestata a {nome}':
            'leer lassen: die Rechnung lautet auf {nome}',
        'Quando chi fa le sedute e chi riceve la fattura sono due persone diverse. '
        'Il documento e il registro portano questo nome; il nome del file resta «{file}».':
            'Für den Fall, dass die Person, die trainiert, und die Person, die zahlt, '
            'nicht dieselbe ist. Dokument und Register tragen diesen Namen; der Dateiname '
            'bleibt «{file}».',
        "Sull'estratto conto paga come": 'Zahlt auf dem Kontoauszug als',
        'lascia vuoto se paga col suo nome':
            'leer lassen, wenn er oder sie unter dem eigenen Namen zahlt',
        "Serve alla pagina Banca quando i soldi arrivano da un'altra persona (marito, "
        'moglie, azienda). Più nomi separati da punto e virgola.':
            'Wird auf der Seite Bank gebraucht, wenn das Geld von jemand anderem kommt '
            '(Ehepartner, Firma). Mehrere Namen mit Semikolon trennen.',
        'Note': 'Notizen',
        'Archiviato': 'Archiviert',
        'Salva': 'Speichern',
        'Aggiungi cliente': 'Kunde hinzufügen',
        'Indirizzo — via e numero': 'Adresse — Strasse und Nummer',
        'Indirizzo — CAP e città': 'Adresse — PLZ und Ort',
        'Aggiungi': 'Hinzufügen',
        'nome@esempio.ch': 'name@beispiel.ch',
        # --- Guthaben ---
        'Crediti sessioni': 'Sitzungsguthaben',
        'Ogni sessione svolta consuma un credito. Quando il pacchetto finisce, si rifattura.':
            'Jede geleistete Sitzung verbraucht ein Guthaben. Ist das Paket aufgebraucht, stellst du neu Rechnung.',
        'Registro dal {data}.': 'Register seit {data}.',
        'Chi lavora a crediti': 'Wer auf Guthaben arbeitet',
        'Il calendario non è ancora collegato: le sessioni non si registrano da sole.':
            'Der Kalender ist noch nicht verbunden: die Sitzungen tragen sich nicht von selbst ein.',
        'Collega il calendario': 'Kalender verbinden',
        "Il calendario non risponde — qui sotto vedi l'ultima lettura riuscita.":
            'Der Kalender antwortet nicht — unten siehst du die letzte gelungene Abfrage.',
        'Riprova adesso': 'Jetzt nochmals versuchen',
        'Sessioni lette da {calendario}': 'Sitzungen gelesen aus {calendario}',
        ' · ultima lettura {data} alle {ora}': ' · zuletzt gelesen {data} um {ora}',
        'Aggiorna adesso': 'Jetzt aktualisieren',
        'Crediti terminati per {n} cliente:': 'Guthaben aufgebraucht bei {n} Kunden:',
        'Crediti terminati per {n} clienti:': 'Guthaben aufgebraucht bei {n} Kunden:',
        'i pacchetti si pagano in anticipo: emetti la prossima fattura per ridare crediti.':
            'Pakete werden im Voraus bezahlt: stell die nächste Rechnung, damit das Guthaben zurückkommt.',
        'Nessun cliente a crediti': 'Keine Kunden auf Guthaben',
        'I crediti servono a chi vende pacchetti di sessioni prepagate: il cliente compra dieci sedute, ogni incontro ne consuma una, quando finiscono si rifattura.':
            'Guthaben sind für alle, die vorausbezahlte Sitzungspakete verkaufen: der Kunde kauft zehn Sitzungen, jeder Termin verbraucht eine, und wenn sie aufgebraucht sind, stellst du neu Rechnung.',
        "Perché l'app possa contarle, deve sapere chi sono e quale nome cercare nei titoli del tuo calendario.":
            'Damit die App sie zählen kann, muss sie wissen, wer sie sind und welches Wort sie in deinen Kalendertiteln suchen soll.',
        'Aggiungi il primo': 'Den ersten hinzufügen',
        'Pacchetto': 'Paket',
        'Usati': 'Verbraucht',
        'Rimasti': 'Übrig',
        'Dal': 'Seit',
        'Ultima sessione': 'Letzte Sitzung',
        'pacchetto {chi}': 'Paket von {chi}',
        'pacchetto': 'Paket',
        'Crediti terminati': 'Guthaben aufgebraucht',
        'In esaurimento': 'Geht zur Neige',
        'In corso': 'Laufend',
        '✓ incassata': '✓ eingegangen',
        'da incassare': 'offen',
        'fatturato ({rif}) — numero non registrato':
            'fakturiert ({rif}) — Nummer nicht erfasst',
        'Cambia fattura': 'Rechnung ändern',
        'Collega fattura': 'Rechnung verknüpfen',
        'Numero della fattura che copre {pacchetto}':
            'Nummer der Rechnung, die {pacchetto} deckt',
        'intestata a {chi}': 'ausgestellt auf {chi}',
        'es. 84': 'z. B. 84',
        'Collega e chiudi pacchetto': 'Verknüpfen und Paket abschliessen',
        'Prima creo la fattura →': 'Zuerst die Rechnung erstellen →',
        'Registra quale fattura copre questo pacchetto e marca le {n} sessioni. Non sostituisce la prossima fattura: il pacchetto nuovo si apre da solo alla prossima sessione.':
            'Hält fest, welche Rechnung dieses Paket deckt, und markiert seine {n} Sitzungen. Sie ersetzt die nächste Rechnung nicht: das neue Paket öffnet sich bei der nächsten Sitzung von selbst.',
        'Aggiornare i crediti dal calendario': 'Guthaben aus dem Kalender aktualisieren',
        "Non c'è ancora nulla da leggere: la lettura del calendario parte dal {inizio} e oggi è il {oggi}.":
            'Es gibt noch nichts zu lesen: der Kalender wird ab {inizio} gelesen, und heute ist der {oggi}.',
        'Intervallo da leggere su {calendario}:': 'Zu lesender Zeitraum auf {calendario}:',
        "Il calendario lo legge l'app da sola, ogni volta che apri questa pagina (al massimo una volta ogni quarto d'ora); con «Aggiorna adesso» lo rileggi subito. Le sessioni già registrate non vengono mai duplicate (ogni evento porta il suo ID Google), e lo storico validato non viene mai riscritto.":
            'Die App liest den Kalender von selbst, jedes Mal wenn du diese Seite öffnest (höchstens einmal pro Viertelstunde); mit «Jetzt aktualisieren» liest sie ihn sofort neu. Bereits erfasste Sitzungen werden nie doppelt angelegt (jeder Termin trägt seine Google-ID), und geprüfte Historie wird nie überschrieben.',
        'Gli appuntamenti futuri non consumano crediti: contano solo le sessioni fino a oggi. Una sessione cancellata consuma comunque il credito.':
            'Künftige Termine verbrauchen kein Guthaben: es zählen nur Sitzungen bis heute. Eine abgesagte Sitzung verbraucht ihr Guthaben trotzdem.',
        'Ultime fatture': 'Letzte Rechnungen',
        # --- Kunden auf Guthaben ---
        'Clienti a crediti': 'Kunden auf Guthaben',
        "Chi compra un pacchetto di sessioni prepagate. Per ognuno l'app sa quale parola cercare nei titoli del calendario, quante sessioni vale un pacchetto e a che prezzo lo riconosce sulle fatture.":
            'Wer ein vorausbezahltes Sitzungspaket kauft. Für jeden weiss die App, welches Wort sie in den Kalendertiteln suchen soll, wie viele Sitzungen ein Paket wert ist und an welchem Preis sie es auf den Rechnungen erkennt.',
        'Torna ai crediti': 'Zurück zu den Guthaben',
        "Non c'è ancora nessuno": 'Noch niemand da',
        "Finché questo elenco è vuoto, la pagina Crediti resta vuota anche lei: l'app non sa quali nomi cercare nel calendario. Aggiungi qui sotto il primo cliente che lavora a pacchetto.":
            'Solange diese Liste leer ist, bleibt auch die Seite Guthaben leer: die App weiss nicht, welche Namen sie im Kalender suchen soll. Füge unten den ersten Kunden hinzu, der auf Paket arbeitet.',
        'Chi paga a sessione singola o a fattura mensile non va messo qui: questa pagina serve solo ai pacchetti prepagati.':
            'Wer pro Einzelsitzung oder per Monatsrechnung zahlt, gehört nicht hierher: diese Seite ist nur für vorausbezahlte Pakete.',
        'Nel calendario': 'Im Kalender',
        'Pacchetti': 'Pakete',
        'Prezzo': 'Preis',
        'supplemento di {chi}': 'Zusatz zu {chi}',
        '({n} nel registro)': '({n} im Register)',
        'Sessioni per pacchetto': 'Sitzungen pro Paket',
        'Sigla del pacchetto': 'Kürzel des Pakets',
        'I pacchetti si chiamano {sigla}-01, {sigla}-02 e così via.':
            'Die Pakete heissen {sigla}-01, {sigla}-02 und so weiter.',
        'Prezzo del pacchetto': 'Preis des Pakets',
        "Quando emetti una fattura di questo importo, l'app capisce da sola che ha comprato un pacchetto e gli ridà i crediti. Più prezzi separati da virgola, se ne hai più di uno.":
            'Wenn du eine Rechnung über diesen Betrag stellst, erkennt die App von selbst, dass ein Paket gekauft wurde, und gibt das Guthaben zurück. Mehrere Preise mit Komma trennen, falls du mehr als einen hast.',
        'lascia vuoto: la fattura va a {nome}': 'leer lassen: die Rechnung geht an {nome}',
        'È il supplemento di': 'Ist der Zusatz zu',
        'lascia vuoto quasi sempre': 'fast immer leer lassen',
        "Solo per chi fa le sedute in coppia e paga un pacchetto ridotto in aggiunta a quello dell'altro. Scrivi qui la parola-calendario dell'altro. Nei giorni in cui l'altro non c'è, la sessione è piena e scala dal pacchetto dell'altro.":
            'Nur für jemanden, der zu zweit trainiert und zusätzlich zum Paket der anderen Person ein reduziertes Paket bezahlt. Schreib hier das Kalenderwort der anderen Person hin. An Tagen, an denen die andere Person fehlt, zählt die Sitzung voll und geht vom Paket der anderen ab.',
        'Archiviato — non è più cliente, ma il suo nome si riconosce ancora nei titoli':
            'Archiviert — nicht mehr Kunde, aber der Name wird in den Titeln weiterhin erkannt',
        'Tolgo {nome} dai clienti a crediti?': '{nome} aus den Kunden auf Guthaben entfernen?',
        "Togli dall'elenco": 'Aus der Liste entfernen',
        'Aggiungi un cliente a crediti': 'Kunden auf Guthaben hinzufügen',
        'Parola da cercare nei titoli del calendario':
            'Wort, das in den Kalendertiteln gesucht wird',
        'lascia vuoto: usa il nome': 'leer lassen: der Name wird verwendet',
        'Un evento che si chiama «Anna», «anna pt» o «Anna - cancelled» conta come una sua sessione. Scegli una parola che non compaia per caso in altri appuntamenti.':
            'Ein Termin mit dem Titel «Anna», «anna pt» oder «Anna - cancelled» zählt als eine ihrer Sitzungen. Wähl ein Wort, das nicht zufällig in anderen Terminen vorkommt.',
        'lascia vuoto: le prime tre lettere': 'leer lassen: die ersten drei Buchstaben',
        # --- Paket ---
        'Pacchetto {id}': 'Paket {id}',
        '{n} sessioni su {crediti} crediti': '{n} Sitzungen von {crediti} Guthaben',
        'dal {inizio}': 'ab {inizio}',
        ' al {fine}': ' bis {fine}',
        ' (aperto)': ' (offen)',
        'fatturato:': 'fakturiert:',
        'si': 'ja',
        'no': 'nein',
        'Titolo sul calendario': 'Titel im Kalender',
        'cancellata — credito consumato': 'abgesagt — Guthaben verbraucht',
        'da calendario': 'aus dem Kalender',
        # --- Sitzungen ---
        'Le sedute davvero svolte: una per credito consumato. Gli appuntamenti ancora da fare non compaiono.':
            'Die tatsächlich geleisteten Sitzungen: eine pro verbrauchtem Guthaben. Termine, die noch bevorstehen, erscheinen nicht.',
        'sessioni': 'Sitzungen',
        'sessioni nel {anno}': 'Sitzungen im Jahr {anno}',
        'di cui con orario:': 'davon mit Uhrzeit:',
        'annullate (credito consumato):': 'abgesagt (Guthaben verbraucht):',
        'Aggiorna gli orari dal calendario': 'Uhrzeiten aus dem Kalender aktualisieren',
        'Anno': 'Jahr',
        'tutti': 'alle',
        'Filtra': 'Filtern',
        'Azzera': 'Zurücksetzen',
        "Di {n} sessioni non conosco l'ora. Sono quelle dei calendari vecchi, che «{calendario}» non contiene più. Se incolli in":
            'Bei {n} Sitzungen kenne ich die Uhrzeit nicht. Sie stammen aus alten Kalendern, die «{calendario}» nicht mehr enthält. Wenn du unter',
        "anche l'indirizzo iCal del calendario storico, si riempiono da sole.":
            'auch die iCal-Adresse des alten Kalenders einfügst, füllen sie sich von selbst.',
        'Giorno': 'Tag',
        'Ora': 'Uhrzeit',
        'Sul calendario': 'Im Kalender',
        'Credito': 'Guthaben',
        'Fattura': 'Rechnung',
        'annullata': 'abgesagt',
        'Nessuna sessione con questi filtri.': 'Keine Sitzung mit diesen Filtern.',
        # --- Bank ---
        'Gli accrediti del tuo estratto conto, accostati alle fatture.':
            'Die Eingänge auf deinem Kontoauszug, den Rechnungen gegenübergestellt.',
        "L'app non segna niente da sola": 'Die App markiert nichts von selbst',
        ': propone, confermi tu.': ': sie schlägt vor, du bestätigst.',
        'versamenti da decidere': 'Zahlungen zu entscheiden',
        'di cui {n} con una proposta chiara': 'davon {n} mit einem klaren Vorschlag',
        '{n} già sistemati': '{n} bereits erledigt',
        "Nella cartella non c'è ancora nessun estratto conto.":
            'Im Ordner liegt noch kein Kontoauszug.',
        "Scarica dall'e-banking i movimenti (CSV, oppure il formato {a} / {b} in XML, che è quello standard svizzero e funziona meglio) e appoggia i file qui:":
            'Lade die Bewegungen aus dem E-Banking herunter (CSV, oder das Format {a} / {b} in XML, das der Schweizer Standard ist und besser funktioniert) und leg die Dateien hier ab:',
        "Poi ricarica questa pagina. I file restano tuoi e sul tuo Mac: l'app li legge e basta, non li sposta e non li modifica. Legge {sole}: quello che spendi non lo guarda.":
            'Dann lade diese Seite neu. Die Dateien bleiben deine und bleiben auf deinem Mac: die App liest sie nur, sie verschiebt und ändert sie nicht. Sie liest {sole}: was du ausgibst, schaut sie nie an.',
        'solo le entrate': 'nur die Eingänge',
        'arrivati il {data}': 'eingegangen am {data}',
        '(nessuna causale)': '(kein Verwendungszweck)',
        'il riferimento del pagamento combacia': 'die Zahlungsreferenz stimmt überein',
        'importo e nome combaciano': 'Betrag und Name stimmen überein',
        "combacia solo l'importo": 'nur der Betrag stimmt überein',
        '{n} giorni prima': '{n} Tage vorher',
        'il riferimento del pagamento è quello della fattura':
            'die Zahlungsreferenz ist die der Rechnung',
        'importo esatto e la causale cita la data di questa fattura':
            'genauer Betrag, und der Verwendungszweck nennt das Datum dieser Rechnung',
        'importo esatto e il nome compare nella causale':
            'genauer Betrag, und der Name steht im Verwendungszweck',
        'importo esatto, ma il nome non compare nella causale':
            'genauer Betrag, aber der Name steht nicht im Verwendungszweck',
        ' — già segnata pagata, confermando aggiungo solo la data':
            ' — bereits als bezahlt markiert; die Bestätigung ergänzt nur das Datum',
        '{quante} fatture dello stesso cliente che insieme fanno esattamente questo importo':
            '{quante} Rechnungen desselben Kunden, die zusammen genau diesen Betrag ergeben',
        'Segnare la #{n} pagata il {data}?': '#{n} als bezahlt am {data} markieren?',
        'Conferma': 'Bestätigen',
        'È questa': 'Das ist sie',
        'Nessuna fattura da sola fa questo importo, ma queste insieme sì:':
            'Keine einzelne Rechnung ergibt diesen Betrag, diese zusammen aber schon:',
        'Segnare {numeri} pagate il {data}?': '{numeri} als bezahlt am {data} markieren?',
        'Sono queste': 'Das sind sie',
        "Nessuna fattura aperta con questo importo nei giorni intorno. Può essere un rimborso, un giroconto o un pagamento che non c'entra.":
            'Keine offene Rechnung mit diesem Betrag in den Tagen darum herum. Es kann eine Rückerstattung sein, ein Übertrag zwischen deinen Konten oder eine Zahlung, die nichts damit zu tun hat.',
        'Oppure dimmelo tu — numero della fattura:':
            'Oder sag es mir einfach — Rechnungsnummer:',
        'es. 53, 58': 'z. B. 53, 58',
        "anche se l'importo non torna": 'auch wenn der Betrag nicht aufgeht',
        'Collega': 'Verknüpfen',
        'Non è una fattura — metti da parte': 'Keine Rechnung — beiseitelegen',
        'Già sistemati': 'Bereits erledigt',
        "dall'app": 'von der App',
        'messo da parte': 'beiseitegelegt',
        'Annulla': 'Rückgängig',
        "Il pallino verde comparirà quando le fatture usciranno come QR-fattura con riferimento: da lì in poi l'accostamento non è più un'ipotesi.":
            'Der grüne Punkt erscheint, sobald die Rechnungen als QR-Rechnung mit Referenz hinausgehen: ab dann ist die Zuordnung keine Vermutung mehr.',
        'Questa cartella non esiste.': 'Diesen Ordner gibt es nicht.',
        'Non ho riconosciuto le colonne: manca una intestazione con data e importo.':
            'Ich habe die Spalten nicht erkannt: es fehlt eine Kopfzeile mit Datum und Betrag.',
        'Per leggere i PDF serve la libreria pypdf.':
            'Zum Lesen von PDFs wird die Bibliothek pypdf gebraucht.',
        # --- Treuhänder ---
        'Pacchetto per la commercialista': 'Paket für den Treuhänder',
        "Tutto quello che serve a {nome} ({citta}), pronto in un click: Excel col registro fatture, riepilogo PDF e copia di tutte le fatture dell'anno, in un unico zip.":
            'Alles, was {nome} ({citta}) braucht, mit einem Klick bereit: Excel mit dem Rechnungsregister, PDF-Zusammenfassung und eine Kopie aller Rechnungen des Jahres, in einem einzigen Zip.',
        'Fatturato': 'Umsatz',
        'Incassato': 'Eingegangen',
        'Fonte': 'Quelle',
        'Excel storico': 'historisches Excel',
        'Genera pacchetto {anno}': 'Paket {anno} erstellen',
        'Nota: per 2022–2023 il pacchetto contiene i dati disponibili nelle fatture; i totali ufficiali di quegli anni vengono dai riepiloghi Excel dello storico.':
            'Hinweis: für 2022–2023 enthält das Paket die in den Rechnungen verfügbaren Daten; die offiziellen Jahrestotale stammen aus den historischen Excel-Zusammenfassungen.',
        'Pacchetti generati': 'Erstellte Pakete',
        'Scarica zip': 'Zip herunterladen',
        # --- die Meldungen oben nach einer Aktion ---
        'Fattura #{n} creata e verificata ✓ — {tot} (importo confermato identico su Word e PDF).':
            'Rechnung #{n} erstellt und geprüft ✓ — {tot} (Betrag auf Word und PDF bestätigt identisch).',
        ' Il numero #{n} è stato riusato da una fattura nel Cestino.':
            ' Die Nummer #{n} wurde von einer Rechnung im Papierkorb wiederverwendet.',
        ' 🎟️ Crediti invariati: questa fattura non compra un pacchetto di sessioni.':
            ' 🎟️ Guthaben unverändert: diese Rechnung kauft kein Sitzungspaket.',
        'Collegata al pacchetto {pid} di {nome}, che ha ancora {rimasti} crediti.':
            'Mit Paket {pid} von {nome} verknüpft, das noch {rimasti} Guthaben hat.',
        '{nome} ha ancora crediti sul pacchetto {pid}: questa fattura resta in attesa e aprirà il pacchetto successivo alla prima sessione utile.':
            '{nome} hat noch Guthaben auf Paket {pid}: diese Rechnung wartet und öffnet das nächste Paket bei der ersten passenden Sitzung.',
        'Aperto il pacchetto {pid} per {nome}: {crediti} crediti disponibili.':
            'Paket {pid} für {nome} eröffnet: {crediti} Guthaben verfügbar.',
        '⚠️ Crediti NON aggiornati. Questa sembra una fattura-pacchetto per {chi}, ma il totale è {tot} mentre il pacchetto costa {attesi}. Controlla la quantità e il prezzo: per un pacchetto da {crediti} crediti la quantità di solito non è 1. Se invece il prezzo è cambiato davvero, aggiornalo nella scheda del cliente a crediti.':
            '⚠️ Guthaben NICHT aktualisiert. Das sieht nach einer Paketrechnung für {chi} aus, aber das Total ist {tot}, während das Paket {attesi} kostet. Prüf Menge und Preis: bei einem Paket mit {crediti} Guthaben ist die Menge meist nicht 1. Hat sich der Preis wirklich geändert, trag ihn in der Karte des Kunden auf Guthaben nach.',
        'Non sono riuscito ad aggiornare i crediti per questa fattura: controlla la pagina Crediti.':
            'Ich konnte die Guthaben für diese Rechnung nicht aktualisieren: schau auf der Seite Guthaben nach.',
        'La fattura è salvata, ma la copia di sicurezza fuori dal Mac non è riuscita: {guaio} — controlla in Impostazioni.':
            'Die Rechnung ist gespeichert, aber die Sicherungskopie ausserhalb des Macs hat nicht geklappt: {guaio} — schau in den Einstellungen nach.',
        'Fattura #{n} spostata nel Cestino. Nulla è andato perso: puoi ripristinarla dalla pagina Cestino.':
            'Rechnung #{n} in den Papierkorb verschoben. Nichts ist verloren: du kannst sie auf der Seite Papierkorb wiederherstellen.',
        'Fattura #{n} ripristinata ({quanti} file rimessi al loro posto).':
            'Rechnung #{n} wiederhergestellt ({quanti} Dateien zurück an ihrem Platz).',
        'Cliente aggiornato.': 'Kunde aktualisiert.',
        'Cliente «{nome}» aggiunto.': 'Kunde «{nome}» hinzugefügt.',
        'Pacchetto {anno} pronto: Excel + PDF riepilogo + {quante} fatture PDF. Zip: {zip}':
            'Paket {anno} bereit: Excel + PDF-Zusammenfassung + {quante} Rechnungs-PDFs. Zip: {zip}',
        ' — PDF non trovati per: {elenco}': ' — kein PDF gefunden für: {elenco}',
        '{nome} è ora fra i clienti a crediti.': '{nome} gehört jetzt zu den Kunden auf Guthaben.',
        'Modifiche salvate per {nome}.': 'Änderungen für {nome} gespeichert.',
        '{nome} non è più fra i clienti a crediti.':
            '{nome} gehört nicht mehr zu den Kunden auf Guthaben.',
        'Pacchetto {pid} collegato alla fattura #{n} ({cliente}): {quante} sessioni marcate. Il prossimo pacchetto si apre da solo alla prima sessione nuova.':
            'Paket {pid} mit Rechnung #{n} ({cliente}) verknüpft: {quante} Sitzungen markiert. Das nächste Paket öffnet sich bei der ersten neuen Sitzung von selbst.',
        'Corretta la fattura #{n} ({cliente}): {cosa}. La correzione resta anche dopo un Reimporta.':
            'Rechnung #{n} korrigiert ({cliente}): {cosa}. Die Korrektur bleibt auch nach einem neuen Import.',
        'Correzione annullata: il dato è tornato come nel file di origine.':
            'Korrektur rückgängig: der Wert steht wieder so da wie in der Originaldatei.',
        'Anomalia archiviata. La trovi in fondo alla pagina se ti serve rivederla.':
            'Auffälligkeit abgelegt. Du findest sie unten auf der Seite, falls du sie nochmals brauchst.',
        "Anomalia ripristinata: torna nell'elenco dei controlli.":
            'Auffälligkeit zurückgeholt: sie steht wieder in der Liste der Prüfungen.',
        'Reimport completato: {dettaglio}': 'Neuimport fertig: {dettaglio}',
        'Seleziona un cliente.': 'Wähl einen Kunden.',
        'Inserisci almeno una riga con descrizione e importo.':
            'Trag mindestens eine Zeile mit Beschreibung und Betrag ein.',
        'Il numero #{n} esiste già. Il prossimo libero è #{libero}.':
            'Die Nummer #{n} gibt es schon. Die nächste freie ist #{libero}.',
        'Esiste già un file «{file}» — per sicurezza non sovrascrivo.':
            'Eine Datei «{file}» gibt es schon — sicherheitshalber überschreibe ich sie nicht.',
        '⚠️ Fattura NON creata: la verifica automatica ha trovato un problema. {guai} Nessun file è stato salvato: controlla i dati e riprova.':
            '⚠️ Rechnung NICHT erstellt: die automatische Prüfung hat ein Problem gefunden. {guai} Es wurde keine Datei gespeichert: prüf die Angaben und versuch es nochmals.',
        'Fattura inviata a {a} il {data} alle {ora}.': 'Rechnung an {a} gesendet am {data} um {ora}.',
        '{quante} fatture inviate a {a} il {data} alle {ora}.':
            '{quante} Rechnungen an {a} gesendet am {data} um {ora}.',
        'Le fatture importate dallo storico non si possono eliminare da qui.':
            'Aus der Historie importierte Rechnungen lassen sich hier nicht löschen.',
        'Nome mancante.': 'Name fehlt.',
        "Manca l'indirizzo iCal del calendario: si incolla in Impostazioni.":
            'Die iCal-Adresse des Kalenders fehlt: sie wird in den Einstellungen eingefügt.',
        'Servono almeno il nome e la parola da cercare nel calendario.':
            'Mindestens der Name und das im Kalender zu suchende Wort werden gebraucht.',
        '«{chi}» non è fra i clienti a crediti: aggiungilo prima.':
            '«{chi}» gehört nicht zu den Kunden auf Guthaben: füg die Person zuerst hinzu.',
        "{nome} ha {quanti} pacchetto nel registro: cancellare la scheda perderebbe quella storia. L'ho archiviata — il nome resta riconosciuto nel calendario, ma non si aprono più pacchetti nuovi.":
            '{nome} hat {quanti} Paket im Register: die Karte zu löschen würde diese Geschichte verlieren. Ich habe sie archiviert — der Name wird im Kalender weiterhin erkannt, aber es öffnen sich keine neuen Pakete mehr.',
        "{nome} ha {quanti} pacchetti nel registro: cancellare la scheda perderebbe quella storia. L'ho archiviata — il nome resta riconosciuto nel calendario, ma non si aprono più pacchetti nuovi.":
            '{nome} hat {quanti} Pakete im Register: die Karte zu löschen würde diese Geschichte verlieren. Ich habe sie archiviert — der Name wird im Kalender weiterhin erkannt, aber es öffnen sich keine neuen Pakete mehr.',
        "Ho collegato da solo {quanti} versamento, quello su cui non c'era niente da decidere: {quali}{extra}. Lo trovi qui sotto marcato «collegato dall'app»: se sbaglio, Annulla.":
            'Ich habe {quanti} Zahlung von selbst verknüpft, die, bei der es nichts zu entscheiden gab: {quali}{extra}. Du findest sie unten mit «von der App verknüpft» markiert: wenn ich falsch liege, Rückgängig.',
        "Ho collegato da solo {quanti} versamenti, quelli su cui non c'era niente da decidere: {quali}{extra}. Li trovi qui sotto marcati «collegato dall'app»: se sbaglio, Annulla.":
            'Ich habe {quanti} Zahlungen von selbst verknüpft, jene, bei denen es nichts zu entscheiden gab: {quali}{extra}. Du findest sie unten mit «von der App verknüpft» markiert: wenn ich falsch liege, Rückgängig.',
        'Quel versamento non è più nei file della cartella.':
            'Diese Zahlung steht nicht mehr in den Dateien des Ordners.',
        'Versamento messo da parte: non è una fattura.':
            'Zahlung beiseitegelegt: sie ist keine Rechnung.',
        'Un calendario non ha risposto: {guaio}': 'Ein Kalender hat nicht geantwortet: {guaio}',
        'Orari trovati: {quanti}.': 'Gefundene Uhrzeiten: {quanti}.',
        'Indica il numero della fattura.': 'Gib die Rechnungsnummer an.',
        'Non esiste una fattura #{n}.': 'Eine Rechnung #{n} gibt es nicht.',
        'Fattura non trovata.': 'Rechnung nicht gefunden.',
        'Non hai inserito nulla da correggere.': 'Du hast nichts zum Korrigieren eingetragen.',
        'Impostazioni salvate.': 'Einstellungen gespeichert.',
        'Logo aggiornato. Lo trovi sulle prossime fatture, in PDF e in Word.':
            'Logo aktualisiert. Du findest es auf den nächsten Rechnungen, in PDF und in Word.',
        'Logo rimosso: al suo posto torna il segnaposto.':
            'Logo entfernt: an seiner Stelle kommt der Platzhalter zurück.',
        "Non c'era nessun logo da rimuovere.": 'Es gab kein Logo zum Entfernen.',
        "Copia creata e verificata: {file} ({kb} KB). Il database dentro l'archivio è integro.":
            'Kopie erstellt und geprüft: {file} ({kb} KB). Die Datenbank im Archiv ist heil.',
        'Copia NON riuscita: {guaio}': 'Kopie hat NICHT geklappt: {guaio}',
        "Storico ({quanti} documenti): invariato dall'ultima copia, non ne serviva una nuova.":
            'Historie ({quanti} Dokumente): unverändert seit der letzten Kopie, eine neue war nicht nötig.',
        'Storico copiato: {file} — {quanti} documenti.':
            'Historie kopiert: {file} — {quanti} Dokumente.',
        'Copia dello storico NON riuscita: {guaio}':
            'Kopie der Historie hat NICHT geklappt: {guaio}',
        'Nome del nuovo cliente mancante.': 'Name des neuen Kunden fehlt.',
        'Non hai scelto nessun file.': 'Du hast keine Datei gewählt.',
        'Immagine troppo pesante ({kb} KB): il massimo è 5 MB.':
            'Bild zu schwer ({kb} KB): das Maximum sind 5 MB.',
        "Non riesco a leggere questo file: dev'essere un'immagine (PNG, JPG).":
            'Ich kann diese Datei nicht lesen: es muss ein Bild sein (PNG, JPG).',
        ' e altri {n}': ' und {n} weitere',
        'Riga {n}: importo non riconosciuto («{cosa}»).':
            'Zeile {n}: Betrag nicht erkannt («{cosa}»).',
        "Non mando niente finché c'è un problema aperto: {guai}":
            'Ich schicke nichts, solange ein Problem offen ist: {guai}',
        'Non è partita: {guaio}': 'Sie ist nicht hinausgegangen: {guaio}',
        'La mail è partita, ma non sono riuscito a metterne una copia in Inviata: {guaio}':
            'Die Mail ist hinausgegangen, aber ich konnte keine Kopie davon in Gesendet ablegen: {guaio}',
        "Prova inviata a {a}{dove}. Guarda com'è arrivata prima di mandarla al cliente.":
            'Testmail an {a} gesendet{dove}. Schau, wie sie angekommen ist, bevor du sie dem Kunden schickst.',
        ' e ne trovi la copia in «{cartella}»': ' und die Kopie findest du in «{cartella}»',
        "Il calendario non risponde: {guaio} — i crediti qui sotto sono quelli dell'ultima lettura riuscita.":
            'Der Kalender antwortet nicht: {guaio} — die Guthaben unten stammen aus der letzten gelungenen Abfrage.',
        'I crediti devono essere un numero.': 'Die Guthaben müssen eine Zahl sein.',
        'Collegamento annullato. Il versamento torna fra quelli da decidere.':
            'Verknüpfung rückgängig. Die Zahlung geht zurück zu denen, die zu entscheiden sind.',
        'Fattura {quali} segnata pagata il {data}.':
            'Rechnung {quali} als bezahlt am {data} markiert.',
        'Fatture {quali} segnate pagate il {data}.':
            'Rechnungen {quali} als bezahlt am {data} markiert.',
        'Nessun orario nuovo: il calendario non sa altro di quei giorni.':
            'Keine neuen Uhrzeiten: der Kalender weiss nichts weiter über diese Tage.',
        'Pacchetto inesistente.': 'Dieses Paket gibt es nicht.',
        'Importo «{cosa}» non riconosciuto. Scrivilo come 1’800.- oppure 1800.00 e riprova.':
            'Betrag «{cosa}» nicht erkannt. Schreib ihn als 1’800.- oder 1800.00 und versuch es nochmals.',
        'Riga {n}: {qty} × {unit} = {calc}, ma il totale riga indicato è {tot}.{suggerimento} Correggi una delle cifre, oppure lascia vuoto il totale e lo calcolo io.':
            'Zeile {n}: {qty} × {unit} = {calc}, aber als Zeilentotal steht {tot}.{suggerimento} Korrigier eine der Zahlen, oder lass das Total leer und ich rechne es aus.',
        ' La descrizione parla di {quante} sessioni: forse la quantità è {quante}?':
            ' In der Beschreibung stehen {quante} Sitzungen: vielleicht ist die Menge {quante}?',
        'Sessioni nuove registrate: {dettaglio}': 'Neue Sitzungen erfasst: {dettaglio}',
        'Calendario letto: nessuna sessione nuova.': 'Kalender gelesen: keine neuen Sitzungen.',
        'Data non valida.': 'Datum ungültig.',
        'Attenzione: {quali} fa {somma} ma il versamento è di {importo} ({differenza}). Non ho collegato niente. Se è giusto lo stesso, rimetti i numeri e spunta la casella.':
            'Achtung: {quali} ergibt {somma}, die Zahlung beträgt aber {importo} ({differenza}). Ich habe nichts verknüpft. Stimmt es trotzdem, trag die Nummern nochmals ein und setz das Häkchen.',
        'La fattura numero {n} non esiste.': 'Die Rechnung Nummer {n} gibt es nicht.',
        'Il numero {n} è su più di una fattura e dalla causale non capisco quale: {elenco}. Rinumerane una e riprova.':
            'Die Nummer {n} steht auf mehr als einer Rechnung, und aus dem Verwendungszweck geht nicht hervor, welche: {elenco}. Nummerier eine davon um und versuch es nochmals.',
        ' È il {n}° rifiuto: non provo più per {minuti} minuti, altrimenti il server blocca il tuo indirizzo IP. Correggi la password in Impostazioni — salvarla toglie la pausa.':
            ' Das ist die {n}. Ablehnung: ich versuche es {minuti} Minuten lang nicht mehr, sonst sperrt der Server deine IP-Adresse. Korrigier das Passwort in den Einstellungen — das Speichern hebt die Pause auf.',
        # --- die Monate, für die Grafik ---
        'Gen': 'Jan',
        'Feb': 'Feb',
        'Mar': 'Mär',
        'Apr': 'Apr',
        'Mag': 'Mai',
        'Giu': 'Jun',
        'Lug': 'Jul',
        'Ago': 'Aug',
        'Set': 'Sep',
        'Ott': 'Okt',
        'Nov': 'Nov',
        'Dic': 'Dez',
        # --- die Wochentage, für die Sitzungen ---
        'lun': 'Mo',
        'mar': 'Di',
        'mer': 'Mi',
        'gio': 'Do',
        'ven': 'Fr',
        'sab': 'Sa',
        'dom': 'So',
        # --- Erste Schritte ---
        'Benvenuto': 'Willkommen',
        'Questa è la tua app per le fatture. Gira sul tuo computer e basta: niente account, niente abbonamento, nessun dato che esce di qui. Scrive le fatture in Word e in PDF, tiene il conto di chi ha pagato e prepara il pacchetto per il commercialista.':
            'Das ist deine App für die Rechnungen. Sie läuft auf deinem Computer und sonst nirgends: kein Konto, kein Abo, keine Daten, die hier weggehen. Sie schreibt Rechnungen in Word und PDF, behält im Auge, wer bezahlt hat, und stellt das Paket für den Treuhänder zusammen.',
        '{fatti} di {totali} fatti.': '{fatti} von {totali} erledigt.',
        'Manca ancora qualcosa di essenziale: senza, le fatture escono incomplete.':
            'Es fehlt noch etwas Wesentliches: ohne das kommen die Rechnungen unvollständig heraus.',
        "L'essenziale c'è. Il resto è comodità, quando ti va.":
            'Das Wesentliche ist da. Der Rest ist Bequemlichkeit, wann immer du magst.',
        'serve davvero': 'wirklich nötig',
        'rivedi': 'ansehen',
        'Vai alla Dashboard': 'Zur Übersicht',
        "Finché mancano i tuoi dati e l'IBAN, l'app si apre qui. Appena li scrivi, si apre sulla Dashboard.":
            'Solange deine Angaben und die IBAN fehlen, öffnet sich die App hier. Sobald du sie einträgst, öffnet sie sich auf der Übersicht.',
        # --- die Schritte, einer nach dem anderen ---
        'Chi emette le fatture': 'Wer die Rechnungen stellt',
        'Nome, indirizzo e numero IVA/IDI vanno in cima a ogni fattura.':
            'Name, Adresse und MWST-/UID-Nummer stehen zuoberst auf jeder Rechnung.',
        'Scrivi i tuoi dati': 'Deine Angaben eintragen',
        'Dove ti pagano': 'Wohin du bezahlt wirst',
        "Senza IBAN la fattura esce senza il conto su cui incassare: è la cosa che si dimentica più facilmente e che costa di più.":
            'Ohne IBAN geht die Rechnung ohne Konto hinaus, auf das bezahlt werden kann: das wird am leichtesten vergessen und kostet am meisten.',
        "Scrivi l'IBAN": 'IBAN eintragen',
        'Il tuo logo': 'Dein Logo',
        'Va sulle fatture e qui in alto a sinistra. Finché manca, sulla fattura quello spazio resta vuoto.':
            'Es kommt auf die Rechnungen und hier oben links. Solange es fehlt, bleibt dieser Platz auf der Rechnung leer.',
        'Carica il logo': 'Logo hochladen',
        'I tuoi clienti': 'Deine Kunden',
        'Li puoi anche aggiungere al volo mentre fai la prima fattura.':
            'Du kannst sie auch nebenbei erfassen, während du die erste Rechnung machst.',
        'Aggiungi un cliente': 'Kunde hinzufügen',
        'La prima fattura': 'Die erste Rechnung',
        "L'app la scrive in Word e in PDF, controlla che i due documenti dicano lo stesso importo, e la mette in archivio.":
            'Die App schreibt sie in Word und in PDF, prüft, dass beide Dokumente denselben Betrag nennen, und legt sie ab.',
        'Fai la prima fattura': 'Erste Rechnung machen',
        'Come si chiamano i tuoi servizi': 'Wie deine Dienstleistungen heissen',
        "Serve a due cose: la Dashboard raggruppa il fatturato per servizio, e l'email nomina il servizio giusto. Finché è vuoto l'app non prova a indovinare: mette tutto in «Altro» e nell'email non lo nomina.":
            'Gut für zwei Dinge: die Übersicht gruppiert den Umsatz nach Dienstleistung, und die E-Mail nennt die richtige. Solange es leer ist, rät die App nicht: sie legt alles unter «Anderes» und nennt es in der E-Mail nicht.',
        'Scrivi i tuoi servizi': 'Deine Dienstleistungen eintragen',
        'La posta': 'Die Post',
        "Serve solo se vuoi spedire le fatture dall'app invece di allegarle a mano.":
            'Nur nötig, wenn du die Rechnungen aus der App verschicken willst, statt sie von Hand anzuhängen.',
        'Collega la casella': 'Postfach verbinden',
        'I pacchetti di sessioni': 'Die Sitzungspakete',
        "Se vendi pacchetti prepagati, l'app tiene il conto delle sessioni leggendole dal tuo calendario.":
            'Wenn du vorausbezahlte Pakete verkaufst, zählt die App die Sitzungen, indem sie sie aus deinem Kalender liest.',
        # --- Einstellungen ---
        'Questi dati finiscono sulle fatture e negli esporti. Cambiali solo se cambia qualcosa davvero.':
            'Diese Angaben landen auf den Rechnungen und in den Exporten. Ändere sie nur, wenn sich wirklich etwas ändert.',
        'Nome attività': 'Name des Betriebs',
        'UID / IDI': 'UID / MWST-Nr.',
        'Indirizzo — riga 1': 'Adresse — Zeile 1',
        'Indirizzo — riga 2': 'Adresse — Zeile 2',
        'Telefono': 'Telefon',
        'Sito': 'Website',
        'IBAN': 'IBAN',
        'Termini di pagamento': 'Zahlungsfrist',
        'Città commercialista': 'Ort des Treuhänders',
        'Servizi proposti sulla nuova fattura': 'Dienstleistungen auf der neuen Rechnung',
        'uno per riga, per esempio:': 'eine pro Zeile, zum Beispiel:',
        'Pacchetto 10 sedute': '10er-Paket',
        'Abbonamento mensile': 'Monatsabo',
        "Diventano i pulsanti sopra le righe della fattura. Se lasci vuoto, l'app propone le descrizioni che hai già usato di più. Per gli abbonamenti non scrivere le date: quando scegli il servizio, l'app riprende l'ultima fattura di quel cliente e sposta il periodo avanti di un mese.":
            'Daraus werden die Knöpfe über den Rechnungszeilen. Lässt du das leer, schlägt die App die Beschreibungen vor, die du am häufigsten verwendet hast. Bei Abos keine Daten hinschreiben: wenn du die Dienstleistung wählst, nimmt die App die letzte Rechnung dieses Kunden und schiebt den Zeitraum einen Monat weiter.',
        "Servizi che l'app deve riconoscere": 'Dienstleistungen, die die App erkennen soll',
        "A cosa servono: la Dashboard raggruppa il fatturato per servizio, e l'email nomina il servizio e sceglie il testo giusto. Una riga per servizio, così: {esempio} — le parole sono quelle che compaiono nelle righe delle tue fatture. Senza {uguale}, il nome fa anche da parola. Vince la prima riga che riconosce, e gli abbonamenti si provano per primi. {vuoto}, l'app non prova a indovinare: l'email non nomina il servizio e la Dashboard mette tutto in «Altro».":
            'Wozu sie da sind: die Übersicht gruppiert den Umsatz nach Dienstleistung, und die E-Mail nennt die Dienstleistung und wählt den passenden Text. Eine Zeile pro Dienstleistung, so: {esempio} — die Wörter sind jene, die in den Zeilen deiner Rechnungen vorkommen. Ohne {uguale} dient der Name zugleich als Wort. Die erste passende Zeile gewinnt, und Abos werden zuerst geprüft. {vuoto}, rät die App nicht: die E-Mail nennt die Dienstleistung nicht und die Übersicht legt alles unter «Anderes».',
        'Nome del servizio = parola, parola': 'Name der Dienstleistung = Wort, Wort',
        'Se lasci vuoto': 'Wenn du das leer lässt',
        'In abbonamento — si rinnova ogni mese': 'Im Abo — erneuert sich jeden Monat',
        'per esempio:': 'zum Beispiel:',
        'Fisioterapia = fisioterapia, seduta': 'Physiotherapie = physiotherapie, sitzung',
        'Coaching = coaching': 'Coaching = coaching',
        'A pacchetto — si compra una volta e si consuma':
            'Als Paket — einmal gekauft und aufgebraucht',
        'Pacchetto sedute = pacchetto, sedute, session': 'Sitzungspaket = paket, sitzungen, session',
        'Cartella storico (solo lettura)': 'Ordner der Historie (nur lesen)',
        'vuoto: nessuno storico da importare': 'leer: keine Historie zu importieren',
        'Cartella della copia di sicurezza (fuori dal Mac)':
            'Ordner der Sicherungskopie (ausserhalb des Macs)',
        'Logo': 'Logo',
        "Va sulle fatture — in PDF e in Word — e qui nell'app, in alto a sinistra. Meglio un PNG con lo sfondo trasparente. Se è di un'altra forma non viene stirato: lo centriamo nello spazio che c'è.":
            'Es kommt auf die Rechnungen — in PDF und in Word — und hier in der App, oben links. Am besten ein PNG mit durchsichtigem Hintergrund. Hat es eine andere Form, wird es nicht verzerrt: wir zentrieren es im vorhandenen Platz.',
        'Questo è il tuo logo.': 'Das ist dein Logo.',
        'Non hai ancora caricato un logo: sulle fatture compare questo segnaposto.':
            'Du hast noch kein Logo hochgeladen: auf den Rechnungen erscheint dieser Platzhalter.',
        'Carica': 'Hochladen',
        'Togli': 'Entfernen',
        'Tolgo il logo? Sulle fatture torna il segnaposto.':
            'Logo entfernen? Auf den Rechnungen kommt der Platzhalter zurück.',
        'Calendario — sessioni automatiche': 'Kalender — automatische Sitzungen',
        'Su Google Calendar: il calendario delle sessioni → Impostazioni del calendario → {voce}. Copia quell’indirizzo e incollalo qui. L’app leggerà le sessioni da sola ogni volta che apri la pagina Crediti. Un eventuale calendario storico {mai}: raddoppierebbe i crediti.':
            'In Google Kalender: der Sitzungskalender → Einstellungen für den Kalender → {voce}. Kopier diese Adresse und füg sie hier ein. Die App liest die Sitzungen von selbst, jedes Mal wenn du die Seite Guthaben öffnest. Ein allfälliger alter Kalender {mai}: das würde die Guthaben verdoppeln.',
        'Indirizzo segreto in formato iCal': 'Geheime Adresse im iCal-Format',
        'non va mai messo qui sotto': 'darf nie ins Feld unten',
        'Indirizzo iCal segreto del calendario delle sessioni':
            'Geheime iCal-Adresse des Sitzungskalenders',
        'Ultima lettura riuscita: {data} alle {ora}.': 'Zuletzt erfolgreich gelesen: {data} um {ora}.',
        'Non ancora collegato.': 'Noch nicht verbunden.',
        'Chi ha questo indirizzo può leggere il calendario: trattalo come una password.':
            'Wer diese Adresse hat, kann den Kalender lesen: behandle sie wie ein Passwort.',
        'Indirizzo iCal del calendario storico — facoltativo':
            'iCal-Adresse des alten Kalenders — freiwillig',
        'Serve {solo}, per sapere a che ora sono state fatte le sedute vecchie: da qui i crediti non passano mai, quindi non c’è modo che vengano contati due volte. Senza questo indirizzo l’Agenda funziona lo stesso, ma delle sessioni più vecchie mostra il giorno e non l’ora.':
            'Sie wird {solo} gebraucht, um zu wissen, um welche Uhrzeit die alten Sitzungen stattfanden: Guthaben kommen hier nie durch, also können sie auch nicht doppelt gezählt werden. Ohne diese Adresse funktionieren die Sitzungen gleich gut, bei den älteren steht dann aber nur der Tag und nicht die Uhrzeit.',
        "solo all'Agenda": 'nur für die Sitzungen',
        'Posta — invio delle fatture': 'Post — Versand der Rechnungen',
        'Le mail partono dal tuo server, non da Gmail: se il tuo dominio autorizza solo il proprio server a spedire a suo nome (SPF {spf}), quelle mandate da Gmail finiscono in spam. Attenzione al nome del server: spesso il certificato copre {dominio} ma non {sotto}, e allora va scritto il primo.':
            'Die Mails gehen von deinem eigenen Server hinaus, nicht von Gmail: wenn deine Domain nur dem eigenen Server erlaubt, in ihrem Namen zu senden (SPF {spf}), landen die von Gmail verschickten im Spam. Achte auf den Servernamen: oft deckt das Zertifikat {dominio} ab, aber nicht {sotto}, und dann muss der erste hin.',
        'tuodominio.ch': 'deinedomain.ch',
        'mail.tuodominio.ch': 'mail.deinedomain.ch',
        'Server SMTP': 'SMTP-Server',
        'Porta': 'Port',
        'Casella': 'Postfach',
        'Password della casella': 'Passwort des Postfachs',
        '•••••••• (già salvata) — lascia vuoto per non cambiarla':
            '•••••••• (bereits gespeichert) — leer lassen, um es zu behalten',
        'non ancora inserita': 'noch nicht eingetragen',
        'salvata: {n} caratteri': 'gespeichert: {n} Zeichen',
        'Mittente': 'Absender',
        'Indirizzo per le prove': 'Adresse für Testmails',
        'Server IMAP (per la copia in Inviata)': 'IMAP-Server (für die Kopie in Gesendet)',
        'Cartella Inviata': 'Ordner Gesendet',
        'vuoto = la cerca da sola sul server': 'leer = sie wird auf dem Server selbst gesucht',
        'Mandane una copia nascosta anche a me (arriva nella posta in arrivo, il cliente non la vede)':
            'Auch mir eine Blindkopie schicken (sie landet im Posteingang, der Kunde sieht sie nicht)',
        'I due oggetti': 'Die zwei Betreffzeilen',
        'Uno per modello, scelto insieme al testo. Nell’abbonamento {mese} diventa il mese coperto dall’abbonamento ({a} se il periodo sta a cavallo di due mesi, {b} se no): l’app lo legge dal periodo scritto sulla fattura, e se manca riparte dall’ultima mail mandata a quella persona avanzando di un mese.':
            'Eine pro Vorlage, zusammen mit dem Text gewählt. Beim Abo wird {mese} zum Monat, den das Abo deckt ({a}, wenn der Zeitraum über zwei Monate geht, sonst {b}): die App liest ihn aus dem Zeitraum auf der Rechnung, und fehlt der, geht sie von der letzten Mail an diese Person aus und einen Monat weiter.',
        'Abbonamento': 'Abo',
        'Pacchetto di sedute': 'Sitzungspaket',
        'I due modelli della frase centrale': 'Die zwei Vorlagen für den mittleren Satz',
        "L'app sceglie da sola quale usare guardando le righe della fattura, e nell'anteprima puoi passare all'altro con un click. Il resto della mail (apertura, frase sull'ordine permanente, firma) resta automatico.":
            'Die App wählt selbst, welche sie nimmt, indem sie die Rechnungszeilen anschaut, und in der Vorschau wechselst du mit einem Klick zur anderen. Der Rest der Mail (Anrede, Satz zum Dauerauftrag, Grussformel) bleibt automatisch.',
        'Abbonamento — si rinnova ogni mese': 'Abo — erneuert sich jeden Monat',
        'Pacchetto di sedute — si compra una volta': 'Sitzungspaket — einmal gekauft',
        'Come chiudi la mail': 'Wie du die Mail abschliesst',
        'Due versioni: nella scheda di ogni cliente scegli quale usare. Vanno al posto di {saluto} nel modello qui sotto. Gli a capo contano.':
            'Zwei Fassungen: in der Karte jedes Kunden wählst du, welche gilt. Sie kommen anstelle von {saluto} in die Vorlage unten. Zeilenumbrüche zählen.',
        'Con chi ci si dà del tu': 'Bei wem man sich duzt',
        'Con tutti gli altri': 'Bei allen anderen',
        'Modello del testo': 'Vorlage des Textes',
        'Sotto {saluto} va la tua firma: scrivila qui com’è in fondo alle mail che mandi davvero.':
            'Unter {saluto} kommt deine Unterschrift: schreib sie hier genau so hin, wie sie am Ende deiner echten Mails steht.',
        'Segnaposti:': 'Platzhalter:',
        'Banca — collegamento automatico': 'Bank — automatische Verknüpfung',
        'Quando metti un estratto nuovo nella cartella {cartella}, l’app può collegare da sola i versamenti su cui non c’è niente da decidere: importo esatto, un solo candidato, e il nome (o la data della fattura) nella causale. Tutto il resto continua a chiederlo a te.':
            'Wenn du einen neuen Auszug in den Ordner {cartella} legst, kann die App jene Zahlungen von selbst verknüpfen, bei denen es nichts zu entscheiden gibt: genauer Betrag, ein einziger Kandidat, und der Name (oder das Rechnungsdatum) im Verwendungszweck. Alles andere fragt sie weiterhin dich.',
        'Estratti conto': 'Kontoauszüge',
        'Collega da solo i versamenti senza dubbi': 'Zweifelsfreie Zahlungen von selbst verknüpfen',
        'Nel dubbio non decide: se i candidati sono due, o se il nome non compare, la riga resta a te. Ogni riga decisa dall’app resta marcata «dall’app» nella pagina Banca e si annulla con un click.':
            'Im Zweifel entscheidet sie nicht: gibt es zwei Kandidaten, oder fehlt der Name, bleibt die Zeile bei dir. Jede von der App entschiedene Zeile bleibt auf der Seite Bank mit «von der App» markiert und lässt sich mit einem Klick rückgängig machen.',
        'Copia di sicurezza fuori dal Mac': 'Sicherungskopie ausserhalb des Macs',
        'Uno zip con database, registro delle sessioni e tutti i PDF delle fatture. Viene creato all’avvio (una volta al giorno) e dopo ogni fattura nuova. Appena scritto viene riaperto e controllato: se il database dentro non è integro, l’archivio viene buttato e qui lo vedi scritto.':
            'Ein Zip mit der Datenbank, dem Sitzungsregister und allen Rechnungs-PDFs. Es entsteht beim Start (einmal am Tag) und nach jeder neuen Rechnung. Kaum geschrieben, wird es wieder geöffnet und geprüft: ist die Datenbank darin nicht heil, wird das Archiv weggeworfen, und hier steht es dann.',
        'Ultima copia: {data} alle {ora} — {kb} KB': 'Letzte Kopie: {data} um {ora} — {kb} KB',
        'Nessuna copia ancora presente in questa cartella.':
            'In diesem Ordner liegt noch keine Kopie.',
        'Fai una copia adesso': 'Jetzt eine Kopie machen',
        'Apri la cartella': 'Ordner öffnen',
        'Quando': 'Wann',
        'Dimensione': 'Grösse',
        'Mi fermo qui. Il server ha già rifiutato la password due volte e al terzo tentativo blocca il tuo indirizzo IP per un pezzo. Riprova fra {restano} minuti, oppure correggi prima la password in Impostazioni: salvarla azzera questa pausa.':
            'Ich höre hier auf. Der Server hat das Passwort schon zweimal abgelehnt, und beim dritten Versuch sperrt er deine IP-Adresse für eine ganze Weile. Versuch es in {restano} Minuten nochmals, oder korrigier zuerst das Passwort in den Einstellungen: das Speichern hebt diese Pause auf.',
    },
}

# ---------------------------------------------------------------------------
# I DOCUMENTI. Dizionario a parte, non per ordine ma per una differenza vera:
# qui non si parla a chi usa l'app, si parla al suo CLIENTE. Il tedesco della
# fattura da' del Lei; quello dei menu da' del tu. Tenerli insieme vorrebbe
# dire scegliere quale dei due sbagliare.
# ---------------------------------------------------------------------------

DOCUMENTI = {
    'en': {
        # --- la fattura ---
        'QUANTITÀ': 'QUANTITY',
        'DESCRIZIONE': 'DESCRIPTION',
        'PREZZO UNITARIO': 'UNIT PRICE',
        'TOTALE': 'TOTAL',
        'TOTALE DA PAGARE': 'TOTAL DUE',
        'Condizioni': 'Terms',
        'Grazie per aver scelto {nome}!': 'Thanks for choosing {nome}!',
        'Pagabile entro 30 giorni netti a:': 'Payable within 30 days net to:',
        # --- la mail ---
        'In allegato la fattura di questo mese per {servizio}.':
            "Please find attached this month's invoice for {servizio}.",
        'In allegato la Sua fattura per {servizio}.':
            'Please find attached your invoice for {servizio}.',
        'In allegato la fattura di questo mese.':
            "Please find attached this month's invoice.",
        'In allegato la Sua fattura.': 'Please find attached your invoice.',
        'In allegato {quante} fatture.': 'Attached are {quante} invoices.',
        'Se ha già pagato questo mese con l\'ordine permanente, può semplicemente '
        'tenere il documento allegato per i Suoi archivi.\n':
            "If you have already completed this month's payment by standing order, "
            'you can simply keep the attached document for your records.\n',
        'due': 'two', 'tre': 'three', 'quattro': 'four',
        'cinque': 'five', 'sei': 'six',
    },
    'de': {
        # --- die Rechnung ---
        'QUANTITÀ': 'MENGE',
        'DESCRIZIONE': 'BESCHREIBUNG',
        'PREZZO UNITARIO': 'EINZELPREIS',
        'TOTALE': 'TOTAL',
        'TOTALE DA PAGARE': 'ZU BEZAHLEN',
        'Condizioni': 'Bedingungen',
        'Grazie per aver scelto {nome}!':
            'Vielen Dank, dass Sie sich für {nome} entschieden haben!',
        'Pagabile entro 30 giorni netti a:': 'Zahlbar innert 30 Tagen netto an:',
        # --- die E-Mail ---
        'In allegato la fattura di questo mese per {servizio}.':
            'Anbei die Rechnung dieses Monats für {servizio}.',
        'In allegato la Sua fattura per {servizio}.':
            'Anbei Ihre Rechnung für {servizio}.',
        'In allegato la fattura di questo mese.': 'Anbei die Rechnung dieses Monats.',
        'In allegato la Sua fattura.': 'Anbei Ihre Rechnung.',
        'In allegato {quante} fatture.': 'Anbei {quante} Rechnungen.',
        'Se ha già pagato questo mese con l\'ordine permanente, può semplicemente '
        'tenere il documento allegato per i Suoi archivi.\n':
            'Falls Sie die Zahlung dieses Monats bereits per Dauerauftrag geleistet '
            'haben, können Sie das beiliegende Dokument einfach für Ihre Unterlagen '
            'behalten.\n',
        'due': 'zwei', 'tre': 'drei', 'quattro': 'vier',
        'cinque': 'fünf', 'sei': 'sechs',
    },
}

# I mesi come li scrive la mail nell'oggetto. Non passano dal dizionario
# perche' qui conta la POSIZIONE (il mese numero 8), non una frase.
MESI_DOC = {
    'it': ('Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio',
           'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'),
    'en': ('January', 'February', 'March', 'April', 'May', 'June', 'July',
           'August', 'September', 'October', 'November', 'December'),
    'de': ('Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
           'August', 'September', 'Oktober', 'November', 'Dezember'),
}


# Il ripiego dei DOCUMENTI non e' quello dell'app. Chi non ha mai scelto una
# lingua per un cliente riceve documenti in inglese, che e' come sono sempre
# usciti: un ripiego che cambia le fatture gia' spedite non e' un ripiego.
PREDEFINITA_DOC = 'en'


def normalizza_doc(codice):
    """La lingua di un documento. Se non si sa, inglese."""
    return codice if codice in CODICI else PREDEFINITA_DOC


def t_doc(frase, lingua=None):
    """La frase di un documento nella lingua del CLIENTE, non dell'app."""
    lingua = normalizza_doc(lingua)
    if lingua == PREDEFINITA:
        return frase
    return DOCUMENTI.get(lingua, {}).get(frase, frase)


def mesi_doc(lingua=None):
    """I dodici nomi di mese nella lingua del cliente."""
    return MESI_DOC[normalizza_doc(lingua)]


def mancanti_doc(lingua):
    """Le frasi di documento che questa lingua non ha. Serve al collaudo."""
    fatte = set(DOCUMENTI.get(lingua, {}))
    return sorted(f for f in TUTTE_DOC if f not in fatte)


# L'italiano non ha un dizionario: e' lui la chiave. Questo e' l'elenco di
# tutte le frasi note, che serve al collaudo per dire quali mancano altrove.
TUTTE = sorted(set(TESTI['en']) | set(TESTI['de']))

TUTTE_DOC = sorted(set(DOCUMENTI['en']) | set(DOCUMENTI['de']))
