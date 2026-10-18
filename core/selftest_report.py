# -*- coding: utf-8 -*-
"""
Collaudi del report del mese: chi ha fatto quante sedute, quanti crediti
restano, chi va fatturato presto e cosa non torna. Dati inventati, nessun
database vero e nessun registro vero.
"""
import datetime
import json
import os
import shutil
import tempfile

from .selftest_revisione_crediti import GIULIA, MARCO, PACK10, _vuoto, _ev

D = datetime.date


def _test_report(r):
    from . import sessions as S
    from .selftest import _check, _senza_scoppiare

    S.configura([GIULIA, MARCO])
    try:
        _conteggi(r, S, _check, _senza_scoppiare)
        _quando_si_manda(r, _check)
    finally:
        S.ricarica()
    _pagina_e_invio(r, _check, _senza_scoppiare)


def _registro_di_prova(S):
    """Giulia: pacchetto da 5, una seduta ad agosto e tre a settembre -> ne
    resta 1. Marco: pacchetto da 10, due sedute a settembre -> ne restano 8."""
    import sync_sessions as SY
    reg = _vuoto()
    S.aggancia_pacchetto(reg, 'giulia', 1, '2026-08-25', 5, PACK10)
    S.aggancia_pacchetto(reg, 'marco', 2, '2026-08-25', 10, PACK10)
    eventi = [
        _ev('g0', '2026-08-28'),
        _ev('g1', '2026-09-02'), _ev('g2', '2026-09-14'), _ev('g3', '2026-09-28'),
        _ev('m1', '2026-09-03', 'Marco pt'), _ev('m2', '2026-09-17', 'Marco pt'),
    ]
    SY.sincronizza(reg, eventi, D(2026, 10, 1))
    return reg


def _conteggi(r, S, _check, _senza_scoppiare):
    from . import report_mese as R
    oggi = D(2026, 10, 1)
    reg = _registro_di_prova(S)
    # quello che c'e' nel calendario del mese, letto per le anomalie
    calendario = [
        _ev('g1', '2026-09-02'),
        _ev('x1', '2026-09-15', 'Gulia pt'),          # nome scritto storto
        _ev('x2', '2026-09-16', 'no Marco'),           # annullata apposta: non e' un'anomalia
        _ev('x3', '2026-08-30', 'Sconosciuto pt'),     # mese prima: non c'entra
        _ev('x4', '2026-10-05', 'Futuro pt'),          # futura: non c'entra
        _ev('x5', '2026-09-20', 'Altro pt', stato='cancelled'),   # cancellato su Google
    ]
    rep = _senza_scoppiare(R.costruisci, reg, '2026-09', calendario, oggi)
    if not isinstance(rep, dict):
        _check(r, 'Report del mese', 'il report si costruisce', rep, 'un report')
        return
    righe = {x['cliente']: (x['sedute_mese'], x['rimasti'], x['ultima_seduta'])
             for x in rep['righe']}
    _check(r, 'Report del mese', 'sedute del mese, crediti rimasti e ultima seduta per cliente',
           righe, {'Giulia': (3, 1, '2026-09-28'), 'Marco': (2, 8, '2026-09-17')})
    _check(r, 'Report del mese', 'da fatturare presto: chi ha 2 crediti o meno',
           [x['cliente'] for x in rep['da_fatturare']], ['Giulia'])
    _check(r, 'Report del mese', 'anomalie: solo gli eventi del mese senza cliente',
           [(a['tipo'], a['data'], a['testo']) for a in rep['anomalie']],
           [('sconosciuto', '2026-09-15', 'Gulia pt')])

    # un pacchetto con piu' sedute fatte che crediti e' un'anomalia
    p = S.pacchetto_aperto_di(reg, 'marco')
    p['crediti'] = 1
    rep = _senza_scoppiare(R.costruisci, reg, '2026-09', [], oggi)
    _check(r, 'Report del mese', 'crediti negativi finiscono fra le anomalie',
           [a['tipo'] for a in rep['anomalie']] if isinstance(rep, dict) else rep,
           ['negativi'])
    _check(r, 'Report del mese', 'e chi e\' sotto zero va fatturato presto',
           sorted(x['cliente'] for x in rep['da_fatturare']) if isinstance(rep, dict) else rep,
           ['Giulia', 'Marco'])

    # il report non cambia il registro: e' solo lettura
    reg = _registro_di_prova(S)
    prima = json.dumps(reg, sort_keys=True)
    _senza_scoppiare(R.costruisci, reg, '2026-09', calendario, oggi)
    _check(r, 'Report del mese', 'costruire il report non tocca il registro',
           json.dumps(reg, sort_keys=True) == prima, True)

    # l'email: in cima chi va fatturato, poi le anomalie, poi tutti
    rep = R.costruisci(reg, '2026-09', calendario, oggi)
    msg = _senza_scoppiare(R.componi, rep, 'io@example.com', 'it')
    if not isinstance(msg, dict):
        _check(r, 'Report del mese', 'l\'email si compone', msg, 'un messaggio')
        return
    corpo = msg['body']
    _check(r, 'Report del mese', 'oggetto col mese, destinatario giusto',
           (msg['subject'], msg['to']), ('Report crediti: Settembre 2026', 'io@example.com'))
    ordine = [corpo.find('Da fatturare presto'), corpo.find('Anomalie'), corpo.find('Tutti i clienti')]
    _check(r, 'Report del mese', 'nell\'email prima da fatturare, poi anomalie, poi tutti',
           (min(ordine) >= 0, ordine == sorted(ordine)), (True, True))
    _check(r, 'Report del mese', 'nell\'email ci sono i nomi e il titolo che non torna',
           ('Giulia' in corpo, 'Marco' in corpo, 'Gulia pt' in corpo), (True, True, True))
    _check(r, 'Report del mese', 'l\'email si scrive anche in tedesco',
           R.componi(rep, 'io@example.com', 'de')['subject'], 'Guthaben-Bericht: September 2026')

    # la nota per la cartella (per esempio un vault di Obsidian): Markdown
    nota = _senza_scoppiare(R.markdown, rep, 'it')
    _check(r, 'Report del mese', 'la nota in Markdown ha titolo, sezioni e tabella',
           [x in str(nota) for x in ('# Report crediti: Settembre 2026', '## Da fatturare presto',
                                     '## Anomalie', '| Giulia | 3 | 1 | 28.09.2026 |')],
           [True, True, True, True])


def _quando_si_manda(r, _check):
    from . import report_mese as R
    # il percorso incollato dal Mac arriva spesso fra apici o con «\ » al
    # posto degli spazi: e' la stessa cartella
    for incollato in ("'/Users/io/Second Brain/Inbox'", '"/Users/io/Second Brain/Inbox"',
                      '/Users/io/Second\\ Brain/Inbox', '  /Users/io/Second Brain/Inbox  '):
        _check(r, 'Report del mese', 'il percorso incollato %s si pulisce' % incollato,
               R.percorso_pulito(incollato), '/Users/io/Second Brain/Inbox')
    acceso = {'report_mese_auto': '1', 'report_mese_ultimo': '2026-08'}
    _check(r, 'Report del mese', 'il primo del mese tocca al mese scorso',
           R.da_mandare(acceso, D(2026, 10, 1)), '2026-09')
    _check(r, 'Report del mese', 'anche aprendo l\'app qualche giorno dopo',
           R.da_mandare(acceso, D(2026, 10, 9)), '2026-09')
    _check(r, 'Report del mese', 'a gennaio tocca a dicembre',
           R.da_mandare(acceso, D(2027, 1, 1)), '2026-12')
    _check(r, 'Report del mese', 'gia\' mandato: non si manda due volte',
           R.da_mandare(dict(acceso, report_mese_ultimo='2026-09'), D(2026, 10, 1)), None)
    _check(r, 'Report del mese', 'spento: non si manda',
           R.da_mandare(dict(acceso, report_mese_auto='0'), D(2026, 10, 1)), None)
    _check(r, 'Report del mese', 'mai mandato prima: si comincia dal mese scorso',
           R.da_mandare({'report_mese_auto': '1'}, D(2026, 10, 1)), '2026-09')
    fallito = dict(acceso, report_mese_tentato='2026-10-01')
    _check(r, 'Report del mese', 'se oggi non e\' partito, si riprova domani e non subito',
           (R.da_mandare(fallito, D(2026, 10, 1)), R.da_mandare(fallito, D(2026, 10, 2))),
           (None, '2026-09'))


def _in_app(APP, f, *args):
    with APP.app.app_context():
        return f(*args)


def _pagina_e_invio(r, _check, _senza_scoppiare):
    import sqlite3
    from . import db as Db, sessions as S, report_mese as R
    import app as APP
    vero_db, vero_registro = Db.DB_PATH, S.REGISTRY
    tmp = tempfile.mkdtemp(prefix='prova-report-')
    try:
        Db.DB_PATH = os.path.join(tmp, 'fatture.db')
        S.REGISTRY = os.path.join(tmp, 'sessions.json')
        con = Db.init()
        con.execute("INSERT INTO clients(id, key, name, chiave_sedute) VALUES(1, 'giulia', 'Giulia Ferrari', 'giulia')")
        con.execute("INSERT INTO clients(id, name, key, chiave_sedute) VALUES(2, 'Marco', 'marco', 'marco')")
        con.commit()
        con.close()
        S.ricarica()
        S.salva(_registro_di_prova(S))
        cliente = APP.app.test_client()

        pagina = _senza_scoppiare(
            lambda: cliente.get('/crediti/report?mese=2026-09').get_data(as_text=True))
        _check(r, 'Report del mese', 'la pagina mostra il mese con chi va fatturato',
               all(x in pagina for x in ('Settembre 2026', 'Da fatturare presto', 'Giulia')), True)

        def impostazione(k):
            c = sqlite3.connect(Db.DB_PATH)
            v = c.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone()
            c.close()
            return v[0] if v else None

        cliente.post('/crediti/report/automatico', data={'report_mese_auto': '1'})
        _check(r, 'Report del mese', 'dalla pagina si accende l\'invio ogni mese, dal prossimo',
               (impostazione('report_mese_auto'), impostazione('report_mese_ultimo')),
               ('1', R.mese_scorso(D.today())))
        c = sqlite3.connect(Db.DB_PATH)
        c.execute("UPDATE settings SET value='2026-08' WHERE key='report_mese_ultimo'")
        c.commit()
        c.close()

        # senza posta configurata non si prova nemmeno a mandare
        partite = []

        def finta(msg, settings, destinatario=None):
            partite.append(msg)
            return True, '', 'ok'

        esito = _senza_scoppiare(_in_app, APP, APP._report_automatico, D(2026, 10, 1), finta)
        _check(r, 'Report del mese', 'senza posta configurata non parte niente',
               (esito, len(partite)), ('posta', 0))

        c = sqlite3.connect(Db.DB_PATH)
        for k, v in (('smtp_host', 'example.com'), ('smtp_user', 'io@example.com'),
                     ('smtp_pass', 'segreta')):
            c.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)', (k, v))
        c.commit()
        c.close()

        def guasta(msg, settings, destinatario=None):
            partite.append(msg)
            return False, 'il server non risponde', 'timeout'

        esito = _senza_scoppiare(_in_app, APP, APP._report_automatico, D(2026, 10, 1), guasta)
        _check(r, 'Report del mese', 'se l\'invio fallisce il mese resta da mandare',
               (esito, impostazione('report_mese_ultimo'), impostazione('report_mese_tentato')),
               ('errore', '2026-08', '2026-10-01'))
        _check(r, 'Report del mese', 'e lo stesso giorno non si riprova',
               _senza_scoppiare(_in_app, APP, APP._report_automatico, D(2026, 10, 1), finta), 'niente')

        partite[:] = []
        esito = _senza_scoppiare(_in_app, APP, APP._report_automatico, D(2026, 10, 2), finta)
        _check(r, 'Report del mese', 'il giorno dopo parte, a se stessi, per il mese scorso',
               (esito, [(m['to'], m['subject']) for m in partite], impostazione('report_mese_ultimo')),
               ('fatto', [('io@example.com', 'Report crediti: Settembre 2026')], '2026-09'))
        _check(r, 'Report del mese', 'una volta partito non riparte',
               _senza_scoppiare(_in_app, APP, APP._report_automatico, D(2026, 10, 3), finta), 'niente')

        # la cartella: una che non esiste non si salva, una vera si'
        cartella = os.path.join(tmp, 'vault', 'Inbox')
        cliente.post('/crediti/report/cartella', data={'report_cartella': cartella})
        _check(r, 'Report del mese', 'una cartella che non esiste non si salva',
               impostazione('report_cartella'), None)
        os.makedirs(cartella)
        cliente.post('/crediti/report/cartella', data={'report_cartella': "'%s'" % cartella})
        _check(r, 'Report del mese', 'una cartella vera si salva, anche incollata fra apici',
               impostazione('report_cartella'), cartella)

        c = sqlite3.connect(Db.DB_PATH)
        c.execute("UPDATE settings SET value='2026-08' WHERE key='report_mese_ultimo'")
        c.commit()
        c.close()
        partite[:] = []
        esito = _senza_scoppiare(_in_app, APP, APP._report_automatico, D(2026, 10, 4), finta)
        nota = os.path.join(cartella, 'Report crediti 2026-09.md')
        _check(r, 'Report del mese', 'ogni mese la nota finisce nella cartella, e parte anche l\'email',
               (esito, os.path.exists(nota), len(partite), impostazione('report_mese_ultimo')),
               ('fatto', True, 1, '2026-09'))
    finally:
        Db.DB_PATH, S.REGISTRY = vero_db, vero_registro
        S.ricarica()
        shutil.rmtree(tmp, ignore_errors=True)
