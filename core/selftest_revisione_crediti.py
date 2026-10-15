# -*- coding: utf-8 -*-
"""
Collaudi dei crediti nati dalla revisione del 4 ottobre. Dati inventati, nessun
database vero e nessun registro vero: tutto in memoria, o in cartelle di prova.
"""
import datetime
import io
import os
import shutil
import tempfile

D = datetime.date

GIULIA = {'id': 1, 'name': 'Giulia Ferrari', 'nome_calendario': '', 'chiave_sedute': 'giulia',
          'archived': 0, 'intestatario': '', 'compagno': ''}
MARCO = {'id': 2, 'name': 'Marco Neri', 'nome_calendario': '', 'chiave_sedute': 'marco',
         'archived': 0, 'intestatario': '', 'compagno': ''}
PACK10 = {'id': 7, 'nome': '12 Sessions Pack', 'prezzo_cents': 200000, 'sedute': 10, 'ogni_mese': 0,
          'scadenza_mesi': 0, 'passano': 0, 'massimo': 0}
ABO4 = {'id': 8, 'nome': 'Monthly abo', 'prezzo_cents': 40000, 'sedute': 4, 'ogni_mese': 1,
        'scadenza_mesi': 0, 'passano': 1, 'massimo': 6}


def _vuoto():
    return {'generato': '2026-08-18', 'pacchetti': [], 'esclusi': [], 'prepagate': {}}


def _ev(uid, data, titolo='Giulia pt', stato='confirmed'):
    return {'id': '%s::%s' % (uid, data), 'titolo': titolo, 'data': data, 'ora': '08:00',
            'stato_google': stato}


def _test_revisione_crediti(r):
    from . import sessions as S, mensili as M, conferme as C, calendar_feed as F
    from . import schedule as AG
    from .selftest import _check, _senza_scoppiare
    import sync_sessions as SY

    S.configura([GIULIA, MARCO])
    try:
        _spostata_e_calendario(r, S, C, F, SY, _check, _senza_scoppiare)
        _mesi_e_agenda(r, S, M, C, AG, _check)
        _fattura_su_pacchetto(r, S, _check)
        _inizio_lettura(r, S, SY, _check)
        _fattura_rifatta(r, S, _check, _senza_scoppiare)
        _pacchetto_tolto(r, S, _check)
    finally:
        S.ricarica()
    _togli_dalla_pagina(r, _check, _senza_scoppiare)


def _spostata_e_calendario(r, S, C, F, SY, _check, _senza_scoppiare):
    # --- A4: una seduta spostata di giorno e' UNA seduta ----------------------
    oggi = D(2026, 10, 2)
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-09-20', 10, PACK10)
    SY.sincronizza(reg, [_ev('u1', '2026-10-01')], oggi)
    spostato = [_ev('u1', '2026-10-02')]               # stesso evento, il giorno dopo
    esito = _senza_scoppiare(lambda: SY.aggiorna_dal_calendario(reg, spostato, oggi))
    p = S.pacchetto_aperto_di(reg, 'giulia')
    _check(r, 'Revisione crediti', 'una seduta spostata di giorno resta una seduta, senza domande',
           (len(S.contate(p)), esito[1:] if isinstance(esito, tuple) else esito,
            len(reg.get('da_confermare') or [])), (1, (1, 0), 0))

    # --- A5: un file che non e' un calendario non e' «niente sedute» -----------
    def con_risposta(testo):
        class Finta:
            def __init__(self, t):
                self.t = t

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n=-1):
                return self.t.encode('utf-8')
        vero = F.urllib.request.urlopen
        F.urllib.request.urlopen = lambda *a, **k: Finta(testo)
        try:
            return F.scarica('https://esempio.invalid/c.ics')
        except Exception as e:
            return 'errore'
        finally:
            F.urllib.request.urlopen = vero
    buono = 'BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n'
    _check(r, 'Revisione crediti', 'una pagina web al posto del calendario si rifiuta',
           con_risposta('<html><body>Sign in to continue</body></html>'), 'errore')
    _check(r, 'Revisione crediti', 'un calendario tagliato a meta\' si rifiuta',
           con_risposta('BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:x\n'), 'errore')
    _check(r, 'Revisione crediti', 'un calendario intero, anche vuoto, si legge',
           con_risposta(buono), buono)

    # --- A8: l'occorrenza annullata dopo essere stata contata fa una domanda ----
    ics = ('BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:serie1\nDTSTART;TZID=Europe/Zurich:20260901T080000\n'
           'RRULE:FREQ=WEEKLY\nSUMMARY:Giulia pt\nEND:VEVENT\nBEGIN:VEVENT\nUID:serie1\n'
           'RECURRENCE-ID;TZID=Europe/Zurich:20260929T080000\n'
           'DTSTART;TZID=Europe/Zurich:20260929T080000\nSTATUS:CANCELLED\nSUMMARY:Giulia pt\n'
           'END:VEVENT\nEND:VCALENDAR')
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-08-25', 10, PACK10)
    oggi = D(2026, 9, 30)
    for giorno in (1, 8, 15, 22, 29):               # le ripetizioni gia' lette, come nella vita vera
        S.aggiungi_sessione(reg, 'giulia', '2026-09-%02d' % giorno, 'Giulia pt',
                            'serie1::2026-09-%02d' % giorno)
    voci = F.leggi(ics, D(2026, 9, 16), oggi, e_testo=True)
    esiti = C.confronta(reg, voci, oggi)
    _check(r, 'Revisione crediti', 'una seduta contata e poi annullata nel calendario fa una domanda',
           (len(esiti['sparite']), len(esiti['spostate'])), (1, 0))


def _mesi_e_agenda(r, S, M, C, AG, _check):
    # --- A8: «non fatta» su un mese: «in piu'» e mese dopo ----------------------
    reg = _vuoto()
    m = M.da_fattura(reg, 'marco', 'Marco', 5, '2026-09-01', dict(ABO4, passano=0), '2026-09', 1)
    for g in (2, 9, 16, 23, 28):
        S.aggiungi_sessione(reg, 'marco', '2026-09-%02d' % g, 'Marco pt', 'n%d::2026-09-%02d' % (g, g))
    C.segna(reg, ['n9::2026-09-09'], 'non_fatta', D(2026, 9, 29))
    vista = S._mese_in_vista(reg, M.di(reg, 'marco'), '2026-09-29')
    M.ricalcola(reg, m)
    _check(r, 'Revisione crediti', 'Crediti non conta «in piu» una seduta segnata non fatta',
           (vista['in_piu'], m['in_piu']), (0, 0))

    reg = _vuoto()
    M.da_fattura(reg, 'marco', 'Marco', 5, '2026-09-01', ABO4, '2026-09', 1)
    for g in (2, 9, 16, 23):
        S.aggiungi_sessione(reg, 'marco', '2026-09-%02d' % g, 'Marco pt', 'q%d::2026-09-%02d' % (g, g))
    m2 = M.da_fattura(reg, 'marco', 'Marco', 6, '2026-09-25', ABO4, '2026-10', 1)
    C.segna(reg, ['q23::2026-09-23'], 'non_fatta', D(2026, 9, 28))
    _check(r, 'Revisione crediti', 'restituire una seduta aggiorna anche il mese dopo',
           (m2['disponibili'], M.disponibili(reg, m2)), (5, 5))

    # --- A8: il mese e' chiuso: lo si dice, e l'Agenda non offre il pulsante ----
    reg = _vuoto()
    m = M.da_fattura(reg, 'marco', 'Marco', 5, '2026-09-01', ABO4, '2026-09', 1)
    S.aggiungi_sessione(reg, 'marco', '2026-09-29', 'Marco pt', 'm29::2026-09-29')
    riga = next(x for x in AG.elenco(reg, orari={}, oggi=D(2026, 10, 1)) if x['data'] == '2026-09-29')
    riga_aperta = next(x for x in AG.elenco(reg, orari={}, oggi=D(2026, 9, 30))
                       if x['data'] == '2026-09-29')
    _check(r, 'Revisione crediti', 'Agenda: il pulsante «non l’ho fatta» c’è solo se il mese è aperto',
           (riga['aperto'], riga_aperta['aperto']), (False, True))


def _fattura_su_pacchetto(r, S, _check):
    # --- A6: una seduta «non fatta» non e' una seduta pagata -------------------
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-08-01', 10, PACK10)
    for g in range(1, 11):
        S.aggiungi_sessione(reg, 'giulia', '2026-08-%02d' % g, 'Giulia pt', 'a%d::2026-08-%02d' % (g, g))
    for g in range(1, 11):
        S.aggiungi_sessione(reg, 'giulia', '2026-09-%02d' % g, 'Giulia pt', 'b%d::2026-09-%02d' % (g, g))
    p = S.pacchetto_aperto_di(reg, 'giulia')
    p['sessioni'][2]['non_fatta'] = '2026-09-11'
    S.ricalcola(p)
    S.aggiungi_sessione(reg, 'giulia', '2026-09-11', 'Giulia pt', 'b11::2026-09-11')
    S.aggancia_pacchetto(reg, 'giulia', 2, '2026-09-12', 10, PACK10)
    _check(r, 'Revisione crediti', 'fattura su pacchetto con una seduta non fatta: 10 pagate su 10, niente passa al nuovo',
           [(len(S.contate(q)), S.e_saldato(q)) for q in reg['pacchetti']],
           [(10, True), (10, True)])


def _inizio_lettura(r, S, SY, _check):
    # --- A7: la prima lettura parte dal primo pacchetto, non da una data fissa --
    reg = _vuoto()
    oggi = D(2027, 1, 12)
    S.aggancia_pacchetto(reg, 'giulia', 1, '2027-01-10', 10, PACK10)
    eventi = [_ev('v%d' % g, '2026-%02d-%02d' % (9 + g // 28, 1 + g % 28)) for g in range(0, 40)]
    eventi.append(_ev('nuova', '2027-01-11'))
    eventi.append(_ev('tardi', '2027-01-03'))      # una settimana prima: la fattura e' arrivata dopo
    SY.sincronizza(reg, eventi, oggi)
    p = S.pacchetto_aperto_di(reg, 'giulia')
    _check(r, 'Revisione crediti', 'un pacchetto nuovo non si mangia le sedute di mesi prima, ma sì quelle di pochi giorni prima',
           len(S.contate(p)) if p else None, 2)
    # chi non ha comprato niente non e' toccato: le sue sedute restano fra gli esclusi
    vuoto = _vuoto()
    rap = SY.sincronizza(vuoto, [_ev('w1', '2027-01-05', 'Marco pt')], oggi)
    _check(r, 'Revisione crediti', 'senza nessun acquisto la seduta va fra gli esclusi, non si perde',
           (len(rap['esclusi_nuovi']), rap['fuori_finestra']), (1, 0))


def _fattura_rifatta(r, S, _check, _senza_scoppiare):
    # --- A3: buttare nel Cestino e rifare la fattura non raddoppia i crediti ----
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-10-01', 10, PACK10)
    esito = _senza_scoppiare(lambda: S.aggancia_pacchetto(
        reg, 'giulia', 2, '2026-10-04', 10, PACK10, sostituisce=[1]))
    _check(r, 'Revisione crediti', 'la fattura rifatta prende il posto di quella nel Cestino: stessi 10 crediti',
           ([(q['fattura_numero'], q['crediti']) for q in reg['pacchetti']], reg.get('prepagate')),
           ([(2, 10)], {}))
    # ma un acquisto vero resta un acquisto: altre sedute, o pacchetto gia' finito
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-10-01', 10, PACK10)
    S.aggancia_pacchetto(reg, 'giulia', 2, '2026-10-04', 12, dict(PACK10, sedute=12), sostituisce=[1])
    _check(r, 'Revisione crediti', 'con un numero di sedute diverso è un acquisto nuovo: aspetta in coda',
           (len(reg['pacchetti']), len((reg.get('prepagate') or {}).get('giulia') or [])), (1, 1))
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-08-01', 10, PACK10)
    for g in range(1, 11):
        S.aggiungi_sessione(reg, 'giulia', '2026-08-%02d' % g, 'Giulia pt', 'c%d::2026-08-%02d' % (g, g))
    S.aggancia_pacchetto(reg, 'giulia', 2, '2026-10-04', 10, PACK10, sostituisce=[1])
    _check(r, 'Revisione crediti', 'se il pacchetto della fattura cestinata è già finito, la nuova apre il suo',
           [(q['fattura_numero'], len(S.contate(q))) for q in reg['pacchetti']], [(1, 10), (2, 0)])


def _pacchetto_tolto(r, S, _check):
    # --- fattura nel Cestino che non si rifa': il pacchetto si toglie ---------
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-10-01', 10, PACK10)
    S.aggiungi_sessione(reg, 'giulia', '2026-10-02', 'Giulia pt', 'g1::2026-10-02')
    S.aggancia_pacchetto(reg, 'marco', 2, '2026-10-01', 10, PACK10)
    tolto = S.togli_pacchetto(reg, 'GIU-01', '2026-10-05')
    _check(r, 'Revisione crediti', 'un pacchetto tolto non compare più fra i crediti, gli altri sì',
           [x['cliente'] for x in S.vista_crediti(reg, D(2026, 10, 5)) if x['pacchetto']], ['Marco'])
    _check(r, 'Revisione crediti', 'un pacchetto tolto non si cancella: resta da parte, con la data',
           [(q['id'], q['tolto_il'], len(q['sessioni'])) for q in reg['pacchetti_tolti']],
           [('GIU-01', '2026-10-05', 1)])
    _check(r, 'Revisione crediti', 'la seduta già fatta non si perde: torna fra le sedute senza pacchetto',
           ([(e['data'], e['chiave']) for e in reg['esclusi']], tolto[1]), ([('2026-10-02', 'giulia')], 1))
    _check(r, 'Revisione crediti', 'e la lettura dopo non la rilegge come nuova',
           'g1::2026-10-02' in S.id_evento_gia_presente(reg), True)
    # la fattura nuova apre un pacchetto nuovo, non riusa il nome di quello tolto
    S.aggancia_pacchetto(reg, 'giulia', 3, '2026-10-06', 10, PACK10)
    _check(r, 'Revisione crediti', 'il pacchetto dopo non riusa il nome di quello tolto',
           [q['id'] for q in reg['pacchetti'] if 'giulia' in q.get('chiavi', [])], ['GIU-02'])
    # chi aveva gia' un pacchetto finito prima: la seduta torna da fatturare
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-08-01', 10, PACK10)
    for g in range(1, 11):
        S.aggiungi_sessione(reg, 'giulia', '2026-08-%02d' % g, 'Giulia pt', 'c%d::2026-08-%02d' % (g, g))
    S.aggancia_pacchetto(reg, 'giulia', 2, '2026-09-01', 10, PACK10)
    S.aggiungi_sessione(reg, 'giulia', '2026-09-02', 'Giulia pt', 'd1::2026-09-02')
    S.togli_pacchetto(reg, 'GIU-02', '2026-09-05')
    _check(r, 'Revisione crediti', 'con un pacchetto finito prima, la seduta torna in un pacchetto da fatturare',
           [(q['id'], len(S.contate(q)), S.e_saldato(q)) for q in reg['pacchetti']],
           [('GIU-01', 10, True), ('GIU-03', 1, False)])


def _togli_dalla_pagina(r, _check, _senza_scoppiare):
    # --- il pulsante «Togli pacchetto»: solo per una fattura nel Cestino ------
    import json
    import sqlite3
    from . import db as D, sessions as S
    import app as APP
    vero_db, vero_registro = D.DB_PATH, S.REGISTRY
    tmp = tempfile.mkdtemp(prefix='prova-togli-')
    try:
        D.DB_PATH = os.path.join(tmp, 'fatture.db')
        S.REGISTRY = os.path.join(tmp, 'sessions.json')
        con = D.init()
        con.execute("INSERT INTO clients(id, key, name, chiave_sedute) VALUES(1, 'giulia', 'Giulia Ferrari', 'giulia')")
        con.execute("INSERT INTO clients(id, name, key, chiave_sedute) VALUES(2, 'Marco', 'marco', 'marco')")
        con.execute("INSERT INTO invoices(number, client_id, client_name, date, year, status, deleted_at) "
                    "VALUES(1, 1, 'Giulia Ferrari', '2026-10-01', 2026, 'emessa', '2026-10-02 10:00:00')")
        con.execute("INSERT INTO invoices(number, client_id, client_name, date, year, status) "
                    "VALUES(2, 2, 'Marco Neri', '2026-10-01', 2026, 'emessa')")
        con.commit()
        con.close()
        S.ricarica()
        reg = _vuoto()
        S.aggancia_pacchetto(reg, 'giulia', 1, '2026-10-01', 10, PACK10)
        S.aggancia_pacchetto(reg, 'marco', 2, '2026-10-01', 10, PACK10)
        S.salva(reg)
        cliente = APP.app.test_client()

        def premi(pid):
            risposta = cliente.post('/crediti/togli', data={'pacchetto': pid})
            with open(S.REGISTRY, encoding='utf-8') as f:
                dopo = json.load(f)
            return risposta.status_code, sorted(q['id'] for q in dopo['pacchetti'])

        _check(r, 'Revisione crediti', 'il pacchetto di una fattura valida non si toglie',
               _senza_scoppiare(premi, 'MAR-01'), (302, ['GIU-01', 'MAR-01']))
        _check(r, 'Revisione crediti', 'quello di una fattura nel Cestino sì',
               _senza_scoppiare(premi, 'GIU-01'), (302, ['MAR-01']))
    finally:
        D.DB_PATH, S.REGISTRY = vero_db, vero_registro
        S.ricarica()
        shutil.rmtree(tmp, ignore_errors=True)
