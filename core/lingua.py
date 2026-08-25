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
    },
}

# L'italiano non ha un dizionario: e' lui la chiave. Questo e' l'elenco di
# tutte le frasi note, che serve al collaudo per dire quali mancano altrove.
TUTTE = sorted(set(TESTI['en']) | set(TESTI['de']))
