# -*- coding: utf-8 -*-
"""
Collaudi nati dalla revisione del 4 ottobre: difetti che nessuna prova copriva
perche' le prove guardavano i pezzi e non il percorso intero, dal modulo del
browser alla fattura salvata.

Le prove sull'app girano in un processo a parte, con database, cartelle e
registro di prova (variabili INVOICE_*): niente di quello che fanno puo' toccare
i dati veri, e un guasto dentro l'app non porta via la batteria.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARCA = '@@FATTI@@'


def _scenario():
    """Gira nel processo di prova. Stampa i fatti osservati, uno JSON."""
    import time
    from html.parser import HTMLParser

    import app as APP
    from core import bank, db as D, exports

    fatti = {}
    con = D.init()
    for cid, chiave, nome, ind1, ind2 in (
            (1, 'giulia', 'Giulia Ferrari', 'Musterstrasse 1', '8000 Zürich'),
            (2, 'j-rg-meier', 'Jürg Meier', 'Bahnhofstrasse 2', '8001 Zürich'),
            (3, 'peter', 'Peter Müller', 'Seeweg 3', '8002 Zürich'),
            (4, 'zo-keller', 'Zoë Keller', 'Hauptgasse 4', '3000 Bern')):
        con.execute('INSERT INTO clients(id, key, name, address1, address2, file_label) '
                    'VALUES(?,?,?,?,?,?)', (cid, chiave, nome, ind1, ind2, nome))
    con.commit()
    con.close()
    c = APP.app.test_client()

    def fattura_di(numero):
        k = D.connect()
        inv = k.execute('SELECT * FROM invoices WHERE number=?', (numero,)).fetchone()
        righe = (k.execute('SELECT description, total_cents FROM items WHERE invoice_id=? '
                           'ORDER BY pos', (inv['id'],)).fetchall() if inv else [])
        k.close()
        return inv, righe

    # --- A1: righe con numeri «bucati» e oltre l'ottava -------------------
    # Il modulo numera le righe senza mai riutilizzare un numero: aggiungi,
    # togli, aggiungi, e la riga sullo schermo e' la nona, la decima.
    c.post('/nuova', data={'client_id': '1', 'data': '2026-10-04',
                           'desc_0': 'Uno', 'tot_0': '10', 'desc_3': 'Due', 'tot_3': '20',
                           'desc_9': 'Dieci', 'tot_9': '30'})
    inv, righe = fattura_di(1)
    fatti['righe'] = [r['description'] for r in righe]
    fatti['totale_fattura'] = inv['total_cents'] if inv else None

    # --- C2: la domanda «Eliminare?» deve poter partire ---------------------
    class Cerca(HTMLParser):
        def __init__(self):
            super().__init__()
            self.valori = []

        def handle_starttag(self, tag, attrs):
            for nome, valore in attrs:
                if nome == 'onsubmit' and valore and 'confirm' in valore:
                    self.valori.append(valore)
    if inv:
        pagina = c.get('/fattura/%d' % inv['id']).get_data(as_text=True)
        p = Cerca()
        p.feed(pagina)
        fatti['onsubmit'] = p.valori

    # --- B1: un cliente nuovo non deve riscrivere uno che c'e' gia' ----------
    c.post('/nuova', data={'nuovo_cliente': '1', 'nc_nome': 'Jörg Meier',
                           'nc_indirizzo1': 'Via Nuova 5', 'nc_indirizzo2': '6900 Lugano',
                           'data': '2026-10-04', 'desc_0': 'Seduta', 'tot_0': '10'})
    k = D.connect()
    fatti['jurg'] = [k.execute('SELECT name, address1 FROM clients WHERE id=2').fetchone()[i]
                     for i in (0, 1)]
    fatti['jorg'] = [tuple(x) for x in k.execute(
        "SELECT name, address1 FROM clients WHERE name LIKE 'J%rg Meier' ORDER BY id")]
    fatti['fatture_jorg'] = [r['client_address'] for r in k.execute(
        "SELECT client_address FROM invoices WHERE client_name='Jörg Meier'")]
    k.close()
    # lo stesso nome identico, scritto una seconda volta: non si raddoppia
    c.post('/cliente/nuovo', data={'name': 'Giulia Ferrari', 'address1': 'Altrove 9'})
    k = D.connect()
    fatti['giulia_righe'] = k.execute("SELECT COUNT(*) FROM clients WHERE name='Giulia Ferrari'"
                                      ).fetchone()[0]
    k.close()
    # due nomi che sulla chiave si somigliano, dalla pagina Clienti
    c.post('/cliente/nuovo', data={'name': 'Zoé Keller', 'address1': 'Dorfstrasse 1'})
    k = D.connect()
    fatti['zoe_da_clienti'] = [tuple(x) for x in k.execute(
        "SELECT name, address1 FROM clients WHERE key LIKE 'zo-keller%' ORDER BY id")]
    k.close()

    # --- C1: cliente nuovo + riga sbagliata = errore subito, non dopo 10 s ---
    t0 = time.time()
    r = c.post('/nuova', data={'nuovo_cliente': '1', 'nc_nome': 'Marco Neri',
                               'nc_indirizzo1': 'Via 1', 'nc_indirizzo2': '6900 Lugano',
                               'data': '2026-10-04', 'desc_0': 'Consulenza', 'tot_0': 'abc'})
    fatti['blocco'] = [r.status_code, round(time.time() - t0, 1),
                       b'database is locked' in r.data]

    # --- D1: una richiesta che arriva da un altro sito non si esegue ----------
    r = c.post('/impostazioni', data={'business_iban': 'CH00 0000 0000 0000 0000 0'},
               headers={'Origin': 'https://sito-qualunque.example'})
    k = D.connect()
    fatti['origine_estranea'] = [r.status_code, k.execute(
        "SELECT value FROM settings WHERE key='business_iban'").fetchone()[0]
        == 'CH00 0000 0000 0000 0000 0']
    k.close()
    r = c.post('/impostazioni', data={'business_iban': 'CH11 1111 1111 1111 1111 1'},
               headers={'Origin': 'http://localhost'})
    fatti['origine_nostra'] = r.status_code
    r = c.post('/impostazioni', data={'business_iban': 'CH11 1111 1111 1111 1111 1'})
    fatti['senza_origine'] = r.status_code
    fatti['host_estraneo'] = c.get('/', headers={'Host': 'sito-qualunque.example'}).status_code
    fatti['host_nostro'] = [c.get('/', headers={'Host': '127.0.0.1:8000'}).status_code,
                            c.get('/').status_code]

    # --- D2: /esporti serve solo la cartella degli export --------------------
    cartella = tempfile.mkdtemp(prefix='esporti-')
    exports.EXPORT_DIR = os.path.join(cartella, 'Exports')
    os.makedirs(exports.EXPORT_DIR)
    with io.open(os.path.join(exports.EXPORT_DIR, 'a.zip'), 'w') as f:
        f.write('zip finto')
    with io.open(os.path.join(cartella, 'segreto.txt'), 'w') as f:
        f.write('non si deve leggere')
    fatti['esporti_buono'] = c.get('/esporti/a.zip').status_code
    fatti['esporti_fuori'] = [c.get('/esporti/..%2Fsegreto.txt').status_code,
                              c.get('/esporti/../segreto.txt').status_code]

    # --- A2: un versamento non si lega da solo a meta' nome -------------------
    k = D.connect()
    k.execute("INSERT INTO invoices(number, client_id, client_name, client_address, date, year, "
              "total_cents, status, source, created_at) VALUES(50, 3, 'Peter Müller', 'x', "
              "'2026-09-20', 2026, 12000, 'emessa', 'app', '2026-09-20T10:00:00')")
    k.commit()

    def mov(testo, n):
        return {'data': '2026-09-25', 'importo_cents': 12000, 'descrizione': testo,
                'nome': '', 'riferimento': '', 'file': 'f', 'impronta': 'imp%d' % n}

    def prova(testo, n):
        k.execute('UPDATE invoices SET paid_at=NULL, status="emessa" WHERE number=50')
        k.execute('DELETE FROM movimenti')
        k.commit()
        return len(bank.collega_automatico(k, [mov(testo, n)]))
    fatti['banca'] = {
        'solo_nome': prova('Zahlung Peter Schmid', 1),            # stesso nome di battesimo
        'solo_cognome': prova('Gutschrift Sandra Mueller', 2),     # stesso cognome
        'tutto_il_nome': prova('Zahlung Peter Mueller', 3),
        'cognome_prima': prova('MUELLER PETER Seeweg 3', 4),
        'data_citata': prova('Rechnung vom 20.09.2026 Sandra', 5),
    }
    k.close()
    print(MARCA + json.dumps(fatti))


def _fatti():
    tmp = tempfile.mkdtemp(prefix='prova-revisione-')
    env = dict(os.environ)
    for chiave in [k for k in env if k.startswith('INVOICE_') or k.startswith('FATTURE_')]:
        del env[chiave]
    dati = os.path.join(tmp, 'dati')
    for sotto in ('Invoices', 'estratti', 'backup'):
        os.makedirs(os.path.join(dati, sotto))
    env.update(INVOICE_DB=os.path.join(dati, 'fatture.db'),
               INVOICE_DIR=os.path.join(dati, 'Invoices'),
               INVOICE_SESSIONS=os.path.join(dati, 'sessions.json'),
               INVOICE_STATEMENTS=os.path.join(dati, 'estratti'),
               INVOICE_BACKUP=os.path.join(dati, 'backup'),
               INVOICE_LOGO=os.path.join(dati, 'logo.png'), INVOICE_PORT='8498')
    esito = subprocess.run(
        [sys.executable, '-c', 'from core import selftest_revisione as X; X._scenario()'],
        cwd=BASE, env=env, capture_output=True, text=True, timeout=240)
    for riga in esito.stdout.splitlines():
        if riga.startswith(MARCA):
            return json.loads(riga[len(MARCA):])
    raise RuntimeError('la prova non ha restituito niente: ' + (esito.stderr or '')[-600:])


def _attributi_con_virgolette_doppie():
    """Template con confirm(...) scritto fra virgolette doppie e tojson dentro.

    tojson non scrive mai \\u0022 al posto delle virgolette: dentro un
    attributo a virgolette doppie la chiude a meta' e la domanda non parte."""
    guai = []
    cartella = os.path.join(BASE, 'templates')
    for nome in sorted(os.listdir(cartella)):
        with io.open(os.path.join(cartella, nome), encoding='utf-8') as f:
            testo = f.read()
        for m in re.finditer(r'on\w+="[^"]*confirm\([^"]*tojson', testo):
            guai.append(nome)
    return guai


def _test_revisione(r):
    from .selftest import _check
    f = _fatti()

    # A1
    _check(r, 'Revisione', 'righe fuori posto o oltre l’ottava: nessuna si perde',
           (f['righe'], f['totale_fattura']), (['Uno', 'Due', 'Dieci'], 6000))

    # C2
    _check(r, 'Revisione', 'Elimina chiede conferma: la domanda arriva intera nella pagina',
           [v.startswith('return confirm(') and v.endswith(')') and v.count('"') == 2
            for v in f.get('onsubmit', [])], [True])
    _check(r, 'Revisione', 'nessun modulo scrive la domanda fra virgolette doppie sbagliate',
           _attributi_con_virgolette_doppie(), [])

    # B1
    _check(r, 'Revisione', 'un cliente nuovo con nome simile non riscrive quello che c’è',
           f['jurg'], ['Jürg Meier', 'Bahnhofstrasse 2'])
    _check(r, 'Revisione', 'il cliente nuovo c’è, col suo indirizzo, e la fattura va a lui',
           (f['jorg'], f['fatture_jorg']),
           ([('Jürg Meier', 'Bahnhofstrasse 2'), ('Jörg Meier', 'Via Nuova 5')],
            ['Via Nuova 5\n6900 Lugano']))
    _check(r, 'Revisione', 'lo stesso nome due volte non fa un secondo cliente',
           f['giulia_righe'], 1)
    _check(r, 'Revisione', 'da Clienti, un nome che sulla chiave coincide con un altro viene aggiunto davvero',
           f['zoe_da_clienti'], [('Zoë Keller', 'Hauptgasse 4'), ('Zoé Keller', 'Dorfstrasse 1')])

    # C1
    status, secondi, bloccato = f['blocco']
    _check(r, 'Revisione', 'cliente nuovo e riga sbagliata: errore subito, senza «database is locked»',
           (status, secondi < 3, bloccato), (302, True, False))

    # D1
    _check(r, 'Revisione', 'una richiesta con Origin di un altro sito viene rifiutata',
           f['origine_estranea'], [403, False])
    _check(r, 'Revisione', 'le richieste dell’app (Origin nostro, o nessuno) passano',
           (f['origine_nostra'] != 403, f['senza_origine'] != 403), (True, True))
    _check(r, 'Revisione', 'un nome di host estraneo non viene servito',
           (f['host_estraneo'] in (400, 403), f['host_nostro'][0] == f['host_nostro'][1]),
           (True, True))

    # D2
    _check(r, 'Revisione', 'Esporti serve i file della sua cartella e solo quelli',
           (f['esporti_buono'], f['esporti_fuori']), (200, [404, 404]))

    # A2
    b = f['banca']
    _check(r, 'Revisione', 'Banca non lega da sola un versamento con mezzo nome uguale',
           (b['solo_nome'], b['solo_cognome']), (0, 0))
    _check(r, 'Revisione', 'Banca lega da sola quando c’è il nome intero, in qualunque ordine, o la data',
           (b['tutto_il_nome'], b['cognome_prima'], b['data_citata']), (1, 1, 1))
