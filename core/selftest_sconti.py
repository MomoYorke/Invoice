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
