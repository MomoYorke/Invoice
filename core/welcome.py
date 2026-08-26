# -*- coding: utf-8 -*-
"""
I primi passi: cosa manca a un'app appena installata per essere utilizzabile.

Un programma vuoto non e' un problema tecnico, e' un problema di orientamento:
chi lo apre la prima volta non sa da dove cominciare, e le Impostazioni sono
lunghe. Qui si tiene l'elenco delle cose da fare, quali sono davvero
indispensabili e quali no, e come si controlla se sono state fatte.

Indispensabile vuol dire una cosa precisa: senza, la fattura che esce e'
sbagliata o incompleta. Tutto il resto e' comodita'.
"""
from . import branding


def passi(con, settings):
    """L'elenco dei primi passi, ognuno con dentro se e' gia' fatto."""
    def valorizzato(*chiavi):
        return all((settings.get(k) or '').strip() for k in chiavi)

    def quante(sql):
        try:
            return con.execute(sql).fetchone()[0]
        except Exception:                       # pragma: no cover
            return 0

    clienti = quante('SELECT COUNT(*) FROM clients WHERE archived = 0')
    fatture = quante('SELECT COUNT(*) FROM invoices WHERE deleted_at IS NULL')

    elenco = [
        {'chiave': 'attivita', 'obbligatorio': True,
         'titolo': 'Chi emette le fatture',
         'fatto': valorizzato('business_name', 'business_addr1', 'business_addr2'),
         'perche': 'Nome, indirizzo e numero IVA/IDI vanno in cima a ogni fattura.',
         'dove': 'impostazioni', 'bottone': 'Scrivi i tuoi dati'},
        {'chiave': 'iban', 'obbligatorio': True,
         'titolo': 'Dove ti pagano',
         'fatto': valorizzato('business_iban'),
         'perche': "Senza IBAN la fattura esce senza il conto su cui incassare: "
                   'è la cosa che si dimentica più facilmente e che costa di più.',
         'dove': 'impostazioni', 'bottone': "Scrivi l'IBAN"},
        {'chiave': 'logo', 'obbligatorio': False,
         'titolo': 'Il tuo logo',
         'fatto': branding.personalizzato(),
         'perche': "Va sulle fatture e qui in alto a sinistra. Finché manca, sulla "
                   'fattura quello spazio resta vuoto.',
         'dove': 'impostazioni', 'bottone': 'Carica il logo'},
        {'chiave': 'clienti', 'obbligatorio': False,
         'titolo': 'I tuoi clienti',
         'fatto': clienti > 0,
         'perche': 'Li puoi anche aggiungere al volo mentre fai la prima fattura.',
         'dove': 'clienti', 'bottone': 'Aggiungi un cliente'},
        {'chiave': 'fattura', 'obbligatorio': False,
         'titolo': 'La prima fattura',
         'fatto': fatture > 0,
         'perche': "L'app la scrive in Word e in PDF, controlla che i due documenti "
                   "dicano lo stesso importo, e la mette in archivio.",
         'dove': 'nuova', 'bottone': 'Fai la prima fattura'},
        {'chiave': 'servizi', 'obbligatorio': False,
         'titolo': 'Come si chiamano i tuoi servizi',
         'fatto': valorizzato('servizi_abbonamento') or valorizzato('servizi_pacchetto'),
         'perche': 'Serve a due cose: la Dashboard raggruppa il fatturato per servizio, '
                   "e l'email nomina il servizio giusto. Finché è vuoto l'app non prova "
                   "a indovinare: mette tutto in «Altro» e nell'email non lo nomina.",
         'dove': 'impostazioni', 'bottone': 'Scrivi i tuoi servizi'},
        {'chiave': 'posta', 'obbligatorio': False,
         'titolo': 'La posta',
         'fatto': valorizzato('smtp_host', 'smtp_user', 'smtp_pass'),
         'perche': "Serve solo se vuoi spedire le fatture dall'app invece di "
                   'allegarle a mano.',
         'dove': 'impostazioni', 'bottone': 'Collega la casella'},
        {'chiave': 'crediti', 'obbligatorio': False,
         'titolo': 'I pacchetti di sessioni',
         'fatto': quante('SELECT COUNT(*) FROM crediti_clienti') > 0,
         'perche': 'Se vendi pacchetti prepagati, l\'app tiene il conto delle sessioni '
                   'leggendole dal tuo calendario.',
         'dove': 'crediti_clienti', 'bottone': 'Chi lavora a crediti'},
    ]
    return elenco


def da_fare(elenco):
    return [p for p in elenco if not p['fatto']]


def manca_l_essenziale(elenco):
    """True se l'app non è ancora in grado di produrre una fattura completa."""
    return any(p['obbligatorio'] and not p['fatto'] for p in elenco)


def avanzamento(elenco):
    fatti = sum(1 for p in elenco if p['fatto'])
    return fatti, len(elenco)
