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
        'Chi segui': 'Ihre Kunden',
        'Incassi e fisco': 'Zahlungen und Steuern',
        "L'app": 'Die App',
        # --- Rahmen, auf jeder Seite ---
        'Indietro': 'Zurück',
        'Torna alla schermata precedente': 'Zurück zum vorherigen Bildschirm',
        'App locale · dati sul tuo Mac': 'Lokale App · Daten auf Ihrem Mac',
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
            'Nichts offen. Alle Rechnungen sind versendet und niemand schuldet Ihnen Geld.',
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
        'Prova su di te': 'Test an Sie selbst',
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
    },
}

# L'italiano non ha un dizionario: e' lui la chiave. Questo e' l'elenco di
# tutte le frasi note, che serve al collaudo per dire quali mancano altrove.
TUTTE = sorted(set(TESTI['en']) | set(TESTI['de']))
