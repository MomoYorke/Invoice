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


def _test_vendibile(r):
    from .selftest import _check
    from .selftest_revisione import _fatti
    f = _fatti('selftest_vendibile', '_scenario_ripristino')
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
