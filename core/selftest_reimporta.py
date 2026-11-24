# -*- coding: utf-8 -*-
"""
Collaudi del «Reimporta»: rileggere lo storico non deve disfare il lavoro fatto.

Prima il Reimporta cancellava tutte le fatture importate e le rifaceva da capo,
con identificativi nuovi. Una fattura gia' pagata tornava «non pagata», mentre
il versamento in banca restava «collegato» a un numero che non era piu' suo:
se nel frattempo nello storico era comparso un file nuovo, quel numero era
diventato la fattura di un altro cliente. Si perdevano anche la data d'invio e
il Cestino (una fattura buttata via tornava fra quelle vive).

Qui si prova con una cartella storico finta, fatture Word vere fatte dall'app e
un database in memoria con lo schema vero. Nessun dato vero.
"""
import datetime
import os
import shutil
import tempfile


def _impostazioni():
    from .db import DEFAULT_SETTINGS
    return dict(DEFAULT_SETTINGS, business_name='Studio Bianchi Fisioterapia',
                business_uid='CHE-000.000.000', business_addr1='Bahnhofstrasse 1',
                business_addr2='8001 Zürich', business_iban='CH9300762011623852957',
                qr_fattura='0')


def _fattura_word(cartella, nome_file, numero, cliente, totale_cents, desc='Seduta'):
    from . import docgen
    os.makedirs(cartella, exist_ok=True)
    riga = {'qty': '1', 'description': desc, 'unit_cents': totale_cents,
            'total_cents': totale_cents, 'servizio_id': None, 'ricorda': False}
    docgen.build_docx(os.path.join(cartella, nome_file), numero, '04-10-26', cliente,
                      ['Musterstrasse 1', '8000 Zürich'], [riga], totale_cents,
                      _impostazioni(), 'it')


def _scenario(r):
    from . import importer
    from .selftest import _check, _db_servizi
    from .db import now_iso

    radice = tempfile.mkdtemp(prefix='prova-reimporta-')
    try:
        quest_anno = str(datetime.date.today().year)
        cartella = os.path.join(radice, quest_anno)
        _fattura_word(cartella, 'Giulia Ferrari 101.docx', 101, 'Giulia Ferrari', 15000)
        _fattura_word(cartella, 'Marco Bianchi 102.docx', 102, 'Marco Bianchi', 22000)
        _fattura_word(cartella, 'Sofia Rossi 103.docx', 103, 'Sofia Rossi', 9000)

        con = _db_servizi()
        importer.import_all(con, radice)

        def fattura(numero):
            return con.execute('SELECT * FROM invoices WHERE number=?', (numero,)).fetchone()

        giulia, marco, sofia = fattura(101), fattura(102), fattura(103)
        _check(r, 'Reimporta', 'il primo import legge le tre fatture',
               [x['total_cents'] if x else None for x in (giulia, marco, sofia)],
               [15000, 22000, 9000])

        # Quello che fa chi usa l'app dopo l'import: Giulia paga in banca e il
        # versamento si collega alla sua fattura; quella di Marco parte per
        # email; quella di Sofia finisce nel Cestino.
        con.execute("UPDATE invoices SET status='pagata', paid_at='2026-10-20' WHERE id=?",
                    (giulia['id'],))
        con.execute(
            'INSERT INTO movimenti(impronta, data, importo_cents, descrizione, file, '
            "invoice_id, invoice_ids, stato, stato_prima, deciso_il) "
            "VALUES('v1', '2026-10-20', 15000, 'Giulia Ferrari', 'conto.csv', ?, ?, "
            "'collegato', 'emessa', ?)", (giulia['id'], str(giulia['id']), now_iso()))
        con.execute("UPDATE invoices SET sent_at='2026-10-05T09:00:00' WHERE id=?",
                    (marco['id'],))
        con.execute("UPDATE invoices SET deleted_at=?, deleted_reason='doppione' WHERE id=?",
                    (now_iso(), sofia['id']))
        con.commit()

        # Nello storico compare un file nuovo che viene prima degli altri in
        # ordine alfabetico, e nel Word di Marco cambia l'importo.
        _fattura_word(cartella, 'Anna Rossi 100.docx', 100, 'Anna Rossi', 5000)
        _fattura_word(cartella, 'Marco Bianchi 102.docx', 102, 'Marco Bianchi', 24000)

        importer.import_all(con, radice)

        dopo = fattura(101)
        mov = con.execute("SELECT invoice_id, invoice_ids FROM movimenti WHERE impronta='v1'"
                          ).fetchone()
        collegata = con.execute('SELECT number, client_name FROM invoices WHERE id=?',
                                (mov['invoice_id'],)).fetchone()
        _check(r, 'Reimporta', 'una fattura pagata resta pagata, con la sua data di pagamento',
               [dopo['status'], dopo['paid_at']] if dopo else None,
               ['pagata', '2026-10-20'])
        _check(r, 'Reimporta', 'il versamento resta collegato alla fattura di chi ha pagato',
               [collegata['number'], collegata['client_name']] if collegata else None,
               [101, 'Giulia Ferrari'])
        _check(r, 'Reimporta', 'anche il versamento che paga piu\' fatture punta ancora a lei',
               mov['invoice_ids'], str(dopo['id']) if dopo else None)

        dopo = fattura(102)
        _check(r, 'Reimporta', 'la data d\'invio della fattura resta',
               dopo['sent_at'] if dopo else None, '2026-10-05T09:00:00')
        _check(r, 'Reimporta', 'un importo cambiato nel file dello storico viene ripreso',
               dopo['total_cents'] if dopo else None, 24000)
        _check(r, 'Reimporta', 'e la riga della fattura con lui',
               [x['total_cents'] for x in con.execute(
                   'SELECT total_cents FROM items WHERE invoice_id=?',
                   (dopo['id'] if dopo else 0,))], [24000])

        dopo = fattura(103)
        _check(r, 'Reimporta', 'una fattura nel Cestino resta nel Cestino',
               [bool(dopo['deleted_at']), dopo['deleted_reason']] if dopo else None,
               [True, 'doppione'])

        nuova = fattura(100)
        _check(r, 'Reimporta', 'il file nuovo dello storico entra come fattura nuova',
               [nuova['client_name'], nuova['total_cents'], nuova['status']] if nuova else None,
               ['Anna Rossi', 5000, 'emessa'])
        _check(r, 'Reimporta', 'nessuna fattura doppia dopo due import',
               con.execute("SELECT COUNT(*) FROM invoices WHERE source='import'").fetchone()[0],
               4)

        # Un file tolto dalla cartella: la fattura non sparisce per sempre,
        # va nel Cestino (si ripristina con un click) e lo dice.
        os.remove(os.path.join(cartella, 'Anna Rossi 100.docx'))
        importer.import_all(con, radice)
        tolta = fattura(100)
        _check(r, 'Reimporta', 'un file tolto dallo storico manda la fattura nel Cestino',
               [bool(tolta['deleted_at']), tolta['deleted_reason']] if tolta else None,
               [True, importer.FILE_SPARITO])
        _check(r, 'Reimporta', 'le altre fatture restano dove sono',
               [bool(fattura(n)['deleted_at']) for n in (101, 102)], [False, False])

        # ...e se il file torna, la fattura torna fra quelle vive.
        _fattura_word(cartella, 'Anna Rossi 100.docx', 100, 'Anna Rossi', 5000)
        importer.import_all(con, radice)
        tornata = fattura(100)
        _check(r, 'Reimporta', 'se il file torna nello storico, la fattura esce dal Cestino',
               [tornata['deleted_at'], tornata['deleted_reason']] if tornata else None,
               [None, ''])
        _check(r, 'Reimporta', 'ma quella buttata via da te resta nel Cestino',
               bool(fattura(103)['deleted_at']), True)

        # Le correzioni a mano restano sopra il file; annullata la correzione,
        # il Reimporta riporta l'importo del file.
        from . import corrections
        corrections.save_correction(con, fattura(101), total_cents=16000)
        importer.import_all(con, radice)
        _check(r, 'Reimporta', 'una correzione a mano resta dopo il Reimporta',
               [fattura(101)['total_cents'], fattura(101)['status']], [16000, 'pagata'])
        corrections.remove_correction(con, corrections.invoice_key(fattura(101)))
        importer.import_all(con, radice)
        _check(r, 'Reimporta', 'annullata la correzione, torna l\'importo del file',
               [fattura(101)['total_cents'], fattura(101)['status']], [15000, 'pagata'])
        con.close()
    finally:
        shutil.rmtree(radice, ignore_errors=True)


def _test_reimporta(r):
    from .selftest import _check, _senza_scoppiare
    esito = _senza_scoppiare(_scenario, r)
    if isinstance(esito, str):
        _check(r, 'Reimporta', 'la prova del Reimporta arriva in fondo', esito, None)
