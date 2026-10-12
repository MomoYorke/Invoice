# -*- coding: utf-8 -*-
"""
Collaudi del numero di fattura: due richieste insieme non devono dare lo stesso
numero, e un doppio click non deve fare due fatture.

Prima il numero si calcolava e poi si scriveva senza nessun blocco in mezzo:
quattro salvataggi contemporanei davano quattro fatture #1, e un doppio click
su «Crea fattura» due fatture uguali con lo stesso file PDF.

Le prove sull'app girano in un processo a parte, con dati di prova.
"""
import json
import os
import threading

MARCA = '@@FATTI@@'


def _scenario_numeri():
    import app as APP
    from core import db as D

    fatti = {}
    con = D.init()
    nomi = ('Anna Rossi', 'Bruno Verdi', 'Carla Neri', 'Dino Bianchi', 'Elisa Gallo')
    for i, nome in enumerate(nomi, 1):
        con.execute('INSERT INTO clients(id, key, name, address1, address2, file_label) '
                    'VALUES(?,?,?,?,?,?)',
                    (i, nome.split()[0].lower(), nome, 'Musterstrasse 1', '8000 Zürich', nome))
    con.execute("INSERT INTO ricorrenti(id, client_id, descrizione, importo_cents, giorno, dal, "
                "attiva) VALUES(1, 5, 'Abbonamento', 10000, 1, '2026-09', 1)")
    con.commit()
    con.close()
    APP.app.config['TESTING'] = True

    def righe():
        k = D.connect()
        out = [tuple(r) for r in k.execute(
            'SELECT id, number, client_id, pdf_path FROM invoices ORDER BY id')]
        k.close()
        return out

    def insieme(lavori):
        """Fa partire tutte le richieste nello stesso istante."""
        via = threading.Barrier(len(lavori))
        esiti = [None] * len(lavori)

        def vai(i, dati):
            c = APP.app.test_client()
            via.wait()
            r = c.post('/nuova', data=dati)
            esiti[i] = [r.status_code, r.headers.get('Location')]

        ts = [threading.Thread(target=vai, args=(i, d)) for i, d in enumerate(lavori)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        return esiti

    def modulo(cliente, **altro):
        return dict({'client_id': str(cliente), 'data': '2026-10-04', 'desc_0': 'Seduta',
                     'tot_0': '100'}, **altro)

    # --- quattro clienti salvano nello stesso istante -----------------------
    insieme([modulo(i) for i in (1, 2, 3, 4)])
    r = righe()
    fatti['numeri'] = sorted(x[1] for x in r)
    fatti['file_diversi'] = len({x[3] for x in r}) == len(r)
    fatti['file_ci_sono'] = all(os.path.exists(x[3]) for x in r)

    # --- doppio click: lo stesso modulo, lo stesso gettone, due volte -------
    prima = len(righe())
    esiti = insieme([modulo(5, gettone='gettone-uno')] * 2)
    dopo = righe()
    nuove = [x for x in dopo if x[2] == 5]
    fatti['doppio_click'] = {
        'fatture_nuove': len(nuove),
        'file_diversi': len({x[3] for x in nuove}) == len(nuove),
        'tutte_a_posto': all(e[0] == 302 for e in esiti),
        'vanno_alla_stessa': (len({e[1] for e in esiti}) == 1),
    }
    fatti['totale_dopo_doppio_click'] = len(dopo) - prima

    # lo stesso gettone un'altra volta (indietro e ripremere Crea): niente di nuovo
    c = APP.app.test_client()
    c.post('/nuova', data=modulo(5, gettone='gettone-uno'))
    fatti['stesso_gettone_ancora'] = len(righe()) - len(dopo)
    # un gettone nuovo e' un'altra fattura, e va fatta
    c.post('/nuova', data=modulo(5, gettone='gettone-due'))
    fatti['gettone_nuovo'] = len(righe()) - len(dopo)

    # --- un mese di abbonamento gia' fatturato non lascia file per strada ---
    cartella = os.path.join(APP.INVOICE_DIR, '2026')
    c.post('/nuova', data=modulo(5, ricorrente_id='1', periodo='2026-09'))
    prima_file = sorted(os.listdir(cartella))
    c.post('/nuova', data=modulo(5, ricorrente_id='1', periodo='2026-09'))
    fatti['file_orfani'] = sorted(set(os.listdir(cartella)) - set(prima_file))

    # --- il PDF non riesce a nascere: il Word gia' scritto non resta ---------
    from core import pdfgen
    vero = pdfgen.build_pdf

    def guasto(*a, **k):
        raise RuntimeError('guasto di prova')
    pdfgen.build_pdf = guasto
    prima_file = sorted(os.listdir(cartella))
    try:
        c.post('/nuova', data=modulo(4, gettone='gettone-tre'))
    except RuntimeError:
        pass
    finally:
        pdfgen.build_pdf = vero
    fatti['pdf_guasto'] = sorted(set(os.listdir(cartella)) - set(prima_file))
    # e dopo il guasto la stessa fattura si puo' rifare, con lo stesso modulo
    n = len(righe())
    c.post('/nuova', data=modulo(4, gettone='gettone-tre'))
    fatti['dopo_il_guasto'] = len(righe()) - n

    print(MARCA + json.dumps(fatti))


def _test_numeri(r):
    from .selftest import _check
    from .selftest_revisione import _fatti
    f = _fatti('selftest_numeri', '_scenario_numeri')
    _check(r, 'Numeri', 'quattro fatture salvate nello stesso istante: #1, #2, #3, #4',
           f['numeri'], [1, 2, 3, 4])
    _check(r, 'Numeri', 'ognuna ha il suo file PDF, e i file ci sono',
           (f['file_diversi'], f['file_ci_sono']), (True, True))
    _check(r, 'Numeri', 'un doppio click fa una fattura sola, e la risposta è la stessa',
           (f['doppio_click']['fatture_nuove'], f['doppio_click']['file_diversi'],
            f['doppio_click']['tutte_a_posto'], f['doppio_click']['vanno_alla_stessa']),
           (1, True, True, True))
    _check(r, 'Numeri', 'rimandare lo stesso modulo non crea una seconda fattura',
           f['stesso_gettone_ancora'], 0)
    _check(r, 'Numeri', 'un modulo nuovo è un’altra fattura e si fa',
           f['gettone_nuovo'], 1)
    _check(r, 'Numeri', 'un mese di abbonamento già fatturato non lascia file orfani',
           f['file_orfani'], [])
    _check(r, 'Numeri', 'se il PDF non nasce il Word già scritto non resta in giro',
           f['pdf_guasto'], [])
    _check(r, 'Numeri', 'dopo il guasto la stessa fattura si rifà con lo stesso modulo',
           f['dopo_il_guasto'], 1)
