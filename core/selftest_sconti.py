# -*- coding: utf-8 -*-
"""
Collaudi degli sconti: una riga con il meno davanti toglie dal totale.

Prima il segno meno si perdeva nella lettura dell'importo: «Pacchetto 500» piu'
«Sconto -50» diventava una fattura da 550 franchi, senza nessun avviso.

Le prove sull'app girano in un processo a parte, con dati di prova.
"""
import io
import json
import os

MARCA = '@@FATTI@@'


def _scenario_sconti():
    import app as APP
    from core import db as D, services as SR

    fatti = {}
    con = D.init()
    con.execute("INSERT INTO clients(id, key, name, address1, address2, file_label) "
                "VALUES(1, 'giulia', 'Giulia Ferrari', 'Musterstrasse 1', '8000 Zürich', "
                "'Giulia Ferrari')")
    pacco = SR.salva(con, SR.dal_modulo(dict(nome='Pacchetto 10 sedute', prezzo='1000',
                                             ogni_mese='0', con_sedute='1', sedute='10')))
    con.commit()
    con.close()
    c = APP.app.test_client()

    def fattura(numero):
        k = D.connect()
        inv = k.execute('SELECT * FROM invoices WHERE number=?', (numero,)).fetchone()
        righe = (k.execute('SELECT total_cents FROM items WHERE invoice_id=? ORDER BY pos',
                           (inv['id'],)).fetchall() if inv else [])
        k.close()
        return [inv['total_cents'] if inv else None, [x['total_cents'] for x in righe]]

    base = {'client_id': '1', 'data': '2026-10-04'}

    # lo sconto scritto nel totale della riga
    c.post('/nuova', data=dict(base, numero='1', desc_0='Pacchetto', tot_0='500',
                               desc_1='Sconto', tot_1='-50'))
    fatti['sconto_nel_totale'] = fattura(1)

    # lo sconto scritto come quantita' -1 per il prezzo
    c.post('/nuova', data=dict(base, numero='2', desc_0='Pacchetto', tot_0='500',
                               desc_1='Sconto', qty_1='-1', unit_1='50'))
    fatti['sconto_con_quantita'] = fattura(2)

    # una fattura che andrebbe sotto zero non si salva, e non lascia file
    pagina = c.post('/nuova', data=dict(base, numero='3', desc_0='Storno', tot_0='-100'),
                    follow_redirects=True).get_data(as_text=True)
    cartella = os.path.join(APP.INVOICE_DIR, '2026')
    fatti['sotto_zero'] = {
        'fattura': fattura(3)[0],
        'file': sorted(n for n in os.listdir(cartella) if '#3' in n) if os.path.isdir(cartella) else [],
        'lo_dice': 'negativo' in pagina}

    # uno sconto collegato al servizio del pacchetto non compra altre sedute
    c.post('/nuova', data=dict(base, numero='4',
                               desc_0='Pacchetto 10 sedute', tot_0='1000', servizio_0=str(pacco),
                               desc_1='Pacchetto 10 sedute, sconto', tot_1='-100',
                               servizio_1=str(pacco)))
    fatti['sconto_sul_pacchetto'] = fattura(4)
    with io.open(os.environ['INVOICE_SESSIONS'], encoding='utf-8') as f:
        reg = json.load(f)
    fatti['crediti'] = sorted(p.get('crediti') for p in reg.get('pacchetti', [])
                              if p.get('fattura_numero') == 4)
    fatti['in_coda'] = reg.get('prepagate', {})

    print(MARCA + json.dumps(fatti))


def _scenario_sconto_cliente():
    """Lo sconto fisso o in percentuale scritto nella scheda del cliente."""
    import app as APP
    from core import db as D, services as SR

    fatti = {}
    con = D.init()
    for cid, nome in ((1, 'Giulia Ferrari'), (2, 'Marco Bianchi'), (3, 'Sofia Rossi')):
        con.execute("INSERT INTO clients(id, key, name, address1, address2, file_label, lingua) "
                    "VALUES(?, ?, ?, 'Musterstrasse 1', '8000 Zürich', ?, 'en')",
                    (cid, nome.split()[0].lower(), nome, nome))
    pacco = SR.salva(con, SR.dal_modulo(dict(nome='10 Sessions Pack', prezzo="2'000",
                                             ogni_mese='0', con_sedute='1', sedute='10')))
    abo = SR.salva(con, SR.dal_modulo(dict(nome='Monthly abo', prezzo='110', ogni_mese='1')))
    con.commit()
    con.close()
    c = APP.app.test_client()

    def scheda(cid, **campi):
        dati = dict(name={1: 'Giulia Ferrari', 2: 'Marco Bianchi', 3: 'Sofia Rossi'}[cid])
        dati.update(campi)
        pagina = c.post('/cliente/%d' % cid, data=dati, follow_redirects=True)
        k = D.connect()
        riga = k.execute('SELECT sconto_tipo, sconto_valore, sconto_nome FROM clients '
                         'WHERE id=?', (cid,)).fetchone()
        k.close()
        return [riga['sconto_tipo'], riga['sconto_valore'], riga['sconto_nome'],
                'sconto' in pagina.get_data(as_text=True).lower()]

    fatti['fisso'] = scheda(1, sconto_tipo='fisso', sconto_valore='50.-',
                            sconto_nome='Loyalty discount')
    fatti['percento'] = scheda(2, sconto_tipo='percento', sconto_valore='10',
                               sconto_nome='Student discount')
    # una percentuale impossibile non si salva: resta quello di prima, e lo dice
    fatti['percento_sbagliato'] = scheda(2, sconto_tipo='percento', sconto_valore='150',
                                         sconto_nome='Student discount')
    fatti['nessuno'] = scheda(3)

    # la prima fattura: il prezzo pieno (2050) lo scrivi tu una volta
    c.post('/nuova', data=dict(client_id='1', data='2026-10-04', numero='1',
                               desc_0='10 Sessions Pack', qty_0='1', unit_0="2'050",
                               servizio_0=str(pacco),
                               desc_1='Loyalty discount', qty_1='1', unit_1='-50'))

    def pulsante(cid, sid):
        return c.get('/api/periodo-successivo?servizio_id=%d&client_id=%d'
                     % (sid, cid)).get_json()

    p = pulsante(1, pacco)
    fatti['pulsante_fisso'] = [p['unit'], p.get('sconto')]
    p = pulsante(2, pacco)
    fatti['pulsante_percento'] = [p['unit'], p.get('sconto')]
    fatti['pulsante_senza'] = pulsante(3, pacco).get('sconto')
    fatti['pulsante_abbonamento'] = pulsante(1, abo).get('sconto')

    k = D.connect()
    inv = k.execute('SELECT * FROM invoices WHERE number=1').fetchone()
    fatti['fattura'] = [inv['total_cents'] if inv else None,
                        [[x['total_cents'], x['servizio_id']] for x in k.execute(
                            'SELECT total_cents, servizio_id FROM items WHERE invoice_id=? '
                            'ORDER BY pos', (inv['id'] if inv else 0,))]]
    k.close()
    with io.open(os.environ['INVOICE_SESSIONS'], encoding='utf-8') as f:
        reg = json.load(f)
    fatti['crediti'] = sorted(x.get('crediti') for x in reg.get('pacchetti', [])
                              if x.get('fattura_numero') == 1)
    print(MARCA + json.dumps(fatti))


def _test_sconto_cliente(r):
    from .selftest import _check
    from .selftest_revisione import _fatti
    from . import sconti as SC

    # --- leggere quello che scrivi nella scheda -------------------------------
    _check(r, 'Sconto cliente', '«10» in percentuale: dieci per cento',
           SC.leggi('percento', '10'), ('percento', 1000, ''))
    _check(r, 'Sconto cliente', '«7,5%» in percentuale: sette e mezzo',
           SC.leggi('percento', '7,5%'), ('percento', 750, ''))
    _check(r, 'Sconto cliente', '«50.-» fisso: cinquanta franchi',
           SC.leggi('fisso', '50.-'), ('fisso', 5000, ''))
    _check(r, 'Sconto cliente', '«-50» fisso: il meno non lo trasforma in un aumento',
           SC.leggi('fisso', '-50'), ('fisso', 5000, ''))
    _check(r, 'Sconto cliente', 'nessuno sconto: niente da leggere',
           SC.leggi('', '30'), ('', 0, ''))
    for tipo, testo in (('percento', '150'), ('percento', '0'), ('percento', 'abc'),
                        ('fisso', '0'), ('fisso', 'abc'), ('fisso', '')):
        _check(r, 'Sconto cliente', '«%s» (%s) non si salva e dice perché' % (testo, tipo),
               bool(SC.leggi(tipo, testo)[2]), True)

    # --- la riga che si aggiunge ----------------------------------------------
    pacco = {'id': 7, 'sedute': 10, 'ogni_mese': 0}
    abo = {'id': 8, 'sedute': 0, 'ogni_mese': 1}
    abo_sedute = {'id': 9, 'sedute': 4, 'ogni_mese': 1}
    consulenza = {'id': 10, 'sedute': 0, 'ogni_mese': 0}
    fisso = {'sconto_tipo': 'fisso', 'sconto_valore': 5000, 'sconto_nome': 'Loyalty discount'}
    dieci = {'sconto_tipo': 'percento', 'sconto_valore': 1000, 'sconto_nome': 'Student discount'}
    _check(r, 'Sconto cliente', 'fisso su un pacchetto da 2050: una riga da -50',
           SC.importo(fisso, pacco, 205000), -5000)
    _check(r, 'Sconto cliente', '10% su un pacchetto da 2050: -205',
           SC.importo(dieci, pacco, 205000), -20500)
    _check(r, 'Sconto cliente', '10% su 123.45: -12.35 (mezzo centesimo per eccesso)',
           SC.importo(dieci, pacco, 12345), -1235)
    _check(r, 'Sconto cliente', 'uno sconto fisso più grande del pacchetto non va sotto zero',
           SC.importo(dict(fisso, sconto_valore=300000), pacco, 205000), -205000)
    _check(r, 'Sconto cliente', 'solo sui pacchetti: non sugli abbonamenti né sul resto',
           [SC.importo(fisso, s, 11000) for s in (abo, abo_sedute, consulenza)],
           [None, None, None])
    _check(r, 'Sconto cliente', 'senza sconto nella scheda, niente riga',
           SC.importo({'sconto_tipo': '', 'sconto_valore': 0}, pacco, 205000), None)
    _check(r, 'Sconto cliente', 'il nome della riga: quello scritto, la percentuale in fondo',
           [SC.descrizione(fisso, 'en'), SC.descrizione(dieci, 'en'),
            SC.descrizione(dict(dieci, sconto_valore=750), 'en')],
           ['Loyalty discount', 'Student discount 10%', 'Student discount 7.5%'])
    _check(r, 'Sconto cliente', 'senza nome: «Discount»/«Rabatt» nella lingua del cliente',
           [SC.descrizione(dict(fisso, sconto_nome=''), lg) for lg in ('en', 'de', 'it')],
           ['Discount', 'Rabatt', 'Sconto'])

    # --- dall'app -------------------------------------------------------------
    f = _fatti('selftest_sconti', '_scenario_sconto_cliente')
    _check(r, 'Sconto cliente', 'la scheda salva uno sconto fisso',
           f['fisso'][:3], ['fisso', 5000, 'Loyalty discount'])
    _check(r, 'Sconto cliente', 'la scheda salva uno sconto in percentuale',
           f['percento'][:3], ['percento', 1000, 'Student discount'])
    _check(r, 'Sconto cliente', 'una percentuale da 150 non si salva, resta il 10%, e lo dice',
           [f['percento_sbagliato'][:3], f['percento_sbagliato'][3]],
           [['percento', 1000, 'Student discount'], True])
    _check(r, 'Sconto cliente', 'chi non ha sconto resta senza',
           f['nessuno'][:2], ['', 0])
    _check(r, 'Sconto cliente', 'il pulsante propone 2050 e la riga «Loyalty discount» -50',
           f['pulsante_fisso'],
           ["2'050.-", {'description': 'Loyalty discount', 'qty': '1', 'unit': '-50.-',
                        'percento': None}])
    _check(r, 'Sconto cliente', 'in percentuale: -200 su 2000, con la percentuale per ricalcolare',
           f['pulsante_percento'],
           ["2'000.-", {'description': 'Student discount 10%', 'qty': '1', 'unit': '-200.-',
                        'percento': 1000}])
    _check(r, 'Sconto cliente', 'senza sconto o su un abbonamento il pulsante non aggiunge niente',
           [f['pulsante_senza'], f['pulsante_abbonamento']], [None, None])
    _check(r, 'Sconto cliente', 'la fattura fa 2000: lo sconto è una riga a parte, senza servizio',
           [f['fattura'][0], [x[0] for x in f['fattura'][1]]], [200000, [205000, -5000]])
    _check(r, 'Sconto cliente', 'la riga dello sconto non è collegata a nessun servizio',
           f['fattura'][1][1][1] in (None, 0), True)
    _check(r, 'Sconto cliente', 'il pacchetto a 2050 scontato apre comunque 10 sedute',
           f['crediti'], [10])


def _test_sconti(r):
    from .selftest import _check
    from .selftest_revisione import _fatti
    f = _fatti('selftest_sconti', '_scenario_sconti')
    _check(r, 'Sconti', '«Pacchetto 500» e «Sconto -50»: la fattura è di 450, non di 550',
           f['sconto_nel_totale'], [45000, [50000, -5000]])
    _check(r, 'Sconti', 'lo sconto scritto come «-1 × 50» fa lo stesso: 450',
           f['sconto_con_quantita'], [45000, [50000, -5000]])
    _check(r, 'Sconti', 'una fattura sotto zero non si salva, non lascia file e lo dice',
           f['sotto_zero'], {'fattura': None, 'file': [], 'lo_dice': True})
    _check(r, 'Sconti', 'il pacchetto scontato costa 900',
           f['sconto_sul_pacchetto'], [90000, [100000, -10000]])
    _check(r, 'Sconti', 'uno sconto collegato al pacchetto non apre altre sedute',
           (f['crediti'], f['in_coda']), ([10], {}))
    _test_sconto_cliente(r)
