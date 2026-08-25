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
    },
}

# L'italiano non ha un dizionario: e' lui la chiave. Questo e' l'elenco di
# tutte le frasi note, che serve al collaudo per dire quali mancano altrove.
TUTTE = sorted(set(TESTI['en']) | set(TESTI['de']))
