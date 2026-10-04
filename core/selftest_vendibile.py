# -*- coding: utf-8 -*-
"""
Collaudi di cio' che serve per mettere l'app in mano a un estraneo: ripristino
delle copie di sicurezza, pagine che non mentono su un'app appena nata, email
che non si possono spedire senza posta, lingue e piattaforme.

Le prove sull'app girano in un processo a parte, con dati di prova.
"""
import json
import os
import sqlite3
import tempfile
import time
import zipfile

MARCA = '@@FATTI@@'


def _scenario_ripristino():
    import app as APP
    from core import backup, db as D

    fatti = {}
    con = D.init()
    con.execute("INSERT INTO clients(id, key, name, address1, address2, file_label) "
                "VALUES(1, 'giulia', 'Giulia Ferrari', 'Musterstrasse 1', '8000 Zürich', "
                "'Giulia Ferrari')")
    con.commit()
    con.close()
    c = APP.app.test_client()
    dest = APP._cartella_backup()

    def fattura(n):
        c.post('/nuova', data={'client_id': '1', 'data': '2026-10-04', 'numero': str(n),
                               'desc_0': 'Seduta %d' % n, 'tot_0': '100'})

    def quante():
        k = sqlite3.connect(D.DB_PATH)
        n = k.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
        k.close()
        return n

    fattura(1)
    fattura(2)
    time.sleep(1.2)                                   # i nomi delle copie hanno i secondi
    z1 = backup.archivia_fuori(dest, motivo='prova')
    fatti['copia_ok'] = z1['ok']
    time.sleep(1.2)
    fattura(3)
    k = sqlite3.connect(D.DB_PATH)
    pdf1 = k.execute('SELECT pdf_path FROM invoices WHERE number=1').fetchone()[0]
    k.close()
    os.remove(pdf1)                                   # un file che sparisce
    fatti['prima'] = [quante(), os.path.exists(pdf1)]
    time.sleep(1.2)

    # un nome che non e' fra le copie non si apre: niente cambia
    c.post('/impostazioni/ripristina', data={'copia': '../../fatture.db'})
    c.post('/impostazioni/ripristina', data={'copia': 'fatture-app-inesistente.zip'})
    fatti['nome_falso'] = quante()

    pagina = c.post('/impostazioni/ripristina', data={'copia': os.path.basename(z1['path'])},
                    follow_redirects=True).get_data(as_text=True)
    fatti['dopo'] = [quante(), os.path.exists(pdf1)]
    fatti['messaggio'] = 'ripristinat' in pagina.lower()

    # lo stato di prima del ripristino e' in una copia: si puo' tornare indietro
    prima = [x for x in backup.elenco_esterni(dest)
             if 'prima-del-ripristino' in zipfile.ZipFile(x['path']).read('manifest.txt').decode()]
    n_dentro = None
    if prima:
        with tempfile.TemporaryDirectory() as tmp:
            zipfile.ZipFile(prima[0]['path']).extract('fatture.db', tmp)
            k = sqlite3.connect(os.path.join(tmp, 'fatture.db'))
            n_dentro = k.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
            k.close()
    fatti['copia_di_prima'] = [len(prima), n_dentro]

    # uno zip rotto non cambia niente
    rotto = os.path.join(dest, 'fatture-app-20000101-000000.zip')
    with open(rotto, 'w') as f:
        f.write('non e uno zip')
    c.post('/impostazioni/ripristina', data={'copia': os.path.basename(rotto)})
    fatti['zip_rotto'] = quante()
    print(MARCA + json.dumps(fatti))


def _scenario_lingua_clienti():
    """Un cliente nuovo riceve i documenti nella lingua dell'app, non per forza in inglese."""
    import app as APP
    from core import db as D
    con = D.init()
    D.set_setting(con, 'lingua', 'de')
    con.commit()
    con.close()
    c = APP.app.test_client()
    c.post('/cliente/nuovo', data={'name': 'Giulia Ferrari', 'address1': 'Musterstrasse 1'})
    c.post('/nuova', data={'nuovo_cliente': '1', 'nc_nome': 'Marco Neri', 'nc_indirizzo1': 'Musterweg 3',
                           'nc_indirizzo2': '8000 Zürich', 'data': '2026-10-04',
                           'desc_0': 'Seduta', 'tot_0': '100'})
    k = D.connect()
    fatti = {r['name']: r['lingua'] for r in k.execute('SELECT name, lingua FROM clients')}
    k.close()
    print(MARCA + json.dumps(fatti))


def _scenario_email():
    from html.parser import HTMLParser
    import app as APP
    from core import db as D

    fatti = {}
    con = D.init()
    for cid, nome, mail in ((1, 'Giulia Ferrari', 'giulia@esempio.invalid'),
                            (2, 'Marco Neri', 'marco@esempio.invalid')):
        con.execute("INSERT INTO clients(id, key, name, address1, address2, file_label, email) "
                    "VALUES(?,?,?,?,?,?,?)", (cid, nome.split()[0].lower(), nome,
                                              'Musterstrasse 1', '8000 Zürich', nome, mail))
    con.commit()
    con.close()
    c = APP.app.test_client()
    for n, cid in ((1, 1), (2, 1), (3, 2)):
        c.post('/nuova', data={'client_id': str(cid), 'data': '2026-10-04', 'numero': str(n),
                               'desc_0': 'Seduta %d' % n, 'tot_0': '100'})
    k = D.connect()
    ids = {r['number']: r['id'] for r in k.execute('SELECT id, number FROM invoices')}
    k.close()

    class Pagina(HTMLParser):
        def __init__(self):
            super().__init__()
            self.pulsanti, self.allega, self.dentro = {}, [], 0

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == 'details':
                self.dentro += 1
            if tag == 'button' and a.get('name') == 'azione':
                self.pulsanti[a.get('value')] = 'disabled' in a
            if tag == 'input' and a.get('name') == 'allega':
                self.allega.append((a.get('value'), self.dentro > 0))

        def handle_endtag(self, tag):
            if tag == 'details':
                self.dentro -= 1

    # senza posta configurata (e' cosi' su un'app appena nata)
    html = c.get('/fattura/%d/email' % ids[1]).get_data(as_text=True)
    p = Pagina()
    p.feed(html)
    fatti['senza_posta'] = {'invia_spento': p.pulsanti.get('invia'),
                            'prova_assente_o_spenta': ('prova' not in p.pulsanti) or p.pulsanti['prova'],
                            'pezzi_vuoti': 'su di me ()' in html or 'Invia a  ' in html}
    pagina = c.post('/fattura/%d/email' % ids[1], data={'azione': 'invia', 'subject': 'x', 'body': 'y'}
                    ).get_data(as_text=True)
    k = D.connect()
    fatti['registro_email'] = k.execute('SELECT COUNT(*) FROM email_log').fetchone()[0]
    k.close()
    fatti['dice_la_posta'] = 'posta' in pagina.lower()

    # allegati: le fatture dello stesso cliente a vista, quelle di altri in un riquadro che si apre
    scelte = {v: dentro for v, dentro in p.allega}
    fatti['allegati'] = {'stesso_cliente_a_vista': scelte.get(str(ids[2])) is False,
                         'altro_cliente_nel_riquadro': scelte.get(str(ids[3])) is True}
    print(MARCA + json.dumps(fatti))


def _prove_pagine_vuote(r):
    """Un'app appena nata non deve chiedere cose che non ha senso chiedere."""
    import datetime
    from . import db as D, overview
    from .selftest import _check
    import shutil
    vero_db = D.DB_PATH
    tmp = tempfile.mkdtemp(prefix='prova-vuota-')
    try:
        D.DB_PATH = os.path.join(tmp, 'fatture.db')
        con = D.init()
        s = D.get_settings(con)
        # chi non ha mai letto un estratto conto non usa la Banca: niente da aggiornare
        _check(r, 'Vendibile', 'estratto conto mai letto: nessun promemoria «da aggiornare»',
               overview._estratto_vecchio(''), '')
        _check(r, 'Vendibile', 'estratto mai letto ma con fatture da incassare: il promemoria c’è',
               bool(overview._estratto_vecchio('', None, True)), True)
        vecchio = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
        _check(r, 'Vendibile', 'estratto conto letto 120 giorni fa: il promemoria c’è',
               bool(overview._estratto_vecchio(vecchio)), True)
        stato = {v['nome']: v['stato'] for v in overview.salute(con, s, os.path.join(tmp, 'bk'))['voci']}
        _check(r, 'Vendibile', 'nei Controlli «estratto conto mai letto» non è un allarme',
               stato.get('Estratto conto'), overview.VERDE)
        con.close()
    finally:
        D.DB_PATH = vero_db
        shutil.rmtree(tmp, ignore_errors=True)


def _prove_lingue(r):
    """Il tedesco e la piattaforma: quello che legge chi non ha un Mac."""
    import re
    from . import language as L
    from .selftest import _check
    _check(r, 'Vendibile', 'in tedesco la posta elettronica non è «Die Post» (la posta svizzera)',
           (L.TESTI['de']['La posta'], L.TESTI['de']['Posta']), ('Die E-Mail', 'E-Mail'))
    _check(r, 'Vendibile', 'sul Mac «Finder» e «Mac» restano come sono',
           (L.t('Mostra nel Finder', 'it', 'darwin'), L.t('Mostra nel Finder', 'de', 'darwin')),
           ('Mostra nel Finder', 'Im Finder anzeigen'))
    _check(r, 'Vendibile', 'su Windows il Finder diventa Esplora file, in tutte e tre le lingue',
           (L.t('Mostra nel Finder', 'it', 'win32'), L.t('Mostra nel Finder', 'en', 'win32'),
            L.t('Mostra nel Finder', 'de', 'win32')),
           ('Mostra in Esplora file', 'Show in File Explorer', 'Im Explorer anzeigen'))
    rimasti = []
    for lingua in ('it', 'en', 'de'):
        for chiave in L.TESTI['en']:
            fuori = L.t(chiave, lingua, 'win32')
            if re.search(r'\bMacs?\b|Finder', fuori):
                rimasti.append((lingua, fuori[:50]))
    _check(r, 'Vendibile', 'su Windows nessuna frase parla di Mac o di Finder', rimasti, [])


def _test_vendibile(r):
    from .selftest import _check
    from .selftest_revisione import _fatti
    _prove_pagine_vuote(r)
    _prove_lingue(r)
    f = _fatti('selftest_vendibile', '_scenario_ripristino')
    lc = _fatti('selftest_vendibile', '_scenario_lingua_clienti')
    _check(r, 'Vendibile', 'un cliente nuovo riceve i documenti nella lingua dell’app (qui tedesco)',
           (lc.get('Giulia Ferrari'), lc.get('Marco Neri')), ('de', 'de'))
    e = _fatti('selftest_vendibile', '_scenario_email')
    _check(r, 'Vendibile', 'senza posta configurata Invia è spento, e niente «()» vuoto',
           e['senza_posta'], {'invia_spento': True, 'prova_assente_o_spenta': True,
                              'pezzi_vuoti': False})
    _check(r, 'Vendibile', 'senza posta, premere Invia non scrive nel registro dei guasti e lo spiega',
           (e['registro_email'], e['dice_la_posta']), (0, True))
    _check(r, 'Vendibile', 'allegati: le fatture di altri clienti stanno in un riquadro a parte',
           e['allegati'], {'stesso_cliente_a_vista': True, 'altro_cliente_nel_riquadro': True})
    _check(r, 'Vendibile', 'la copia esterna si fa e si riapre', f['copia_ok'], True)
    _check(r, 'Vendibile', 'un nome di copia che non è nell’elenco non si apre',
           f['nome_falso'], 3)
    _check(r, 'Vendibile', 'Ripristina riporta le fatture e i file com’erano nella copia',
           (f['prima'], f['dopo']), ([3, False], [2, True]))
    _check(r, 'Vendibile', 'dopo il ripristino la pagina lo dice',
           f['messaggio'], True)
    _check(r, 'Vendibile', 'lo stato di prima resta in una copia: si può tornare indietro',
           f['copia_di_prima'], [1, 3])
    _check(r, 'Vendibile', 'uno zip rotto non cambia niente', f['zip_rotto'], 2)
