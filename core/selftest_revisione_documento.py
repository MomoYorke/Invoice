# -*- coding: utf-8 -*-
"""
Collaudi del documento che arriva al cliente: Word e PDF.

Si guardano i file veri, riletti: il testo e dove sta scritto. Una fattura puo'
passare «verificata ✓» (l'importo e' giusto) e intanto avere una riga sopra
l'altra o un nome pieno di quadratini.
"""
import json
import os
import tempfile

MARCA = '@@FATTI@@'


def _impostazioni():
    from .db import DEFAULT_SETTINGS
    return dict(DEFAULT_SETTINGS, business_name='Studio Bianchi Fisioterapia',
                business_uid='CHE-000.000.000', business_addr1='Bahnhofstrasse 1',
                business_addr2='8001 Zürich', business_iban='CH9300762011623852957',
                qr_fattura='0')


def _riga(qty, desc, totale, unit=None):
    return {'qty': qty, 'description': desc, 'unit_cents': unit, 'total_cents': totale,
            'servizio_id': None, 'ricorda': False}


def _pezzi(percorso):
    """Per ogni pagina: [(x0, y, x1, testo)] di ogni pezzo di testo scritto."""
    from pypdf import PdfReader
    pagine = []
    for pagina in PdfReader(percorso).pages:
        pezzi = []

        def visita(testo, cm, tm, font, dim):
            if not testo.strip():
                return
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            pezzi.append((x, y, x + len(testo) * (dim or 9) * 0.5, testo.strip(), dim or 9))
        pagina.extract_text(visitor_text=visita)
        pagine.append(pezzi)
    return pagine


def _sovrapposti(pagine):
    """I pezzi di testo che si pestano: stessa altezza, stesso tratto di riga."""
    guai = []
    for n, pezzi in enumerate(pagine, 1):
        for i, a in enumerate(pezzi):
            for b in pezzi[i + 1:]:
                if abs(a[1] - b[1]) < 0.7 * min(a[4], b[4]) and a[0] < b[2] and b[0] < a[2]:
                    guai.append((n, a[3][:20], b[3][:20]))
    return guai


def _testo(percorso):
    from pypdf import PdfReader
    return '\n'.join(p.extract_text() or '' for p in PdfReader(percorso).pages)


def _prove_documento(r):
    from . import docgen, importer, pdfgen, verify, caratteri
    from .selftest import _check, _senza_scoppiare
    impostazioni = _impostazioni()
    cartella = tempfile.mkdtemp(prefix='prova-documento-')

    def pdf(nome, righe, cliente='Giulia Ferrari', indirizzo=('Musterstrasse 1', '8000 Zürich')):
        percorso = os.path.join(cartella, nome + '.pdf')
        totale = sum(x['total_cents'] or 0 for x in righe)
        pdfgen.build_pdf(percorso, 1, '01-10-26', cliente, list(indirizzo), righe, totale,
                         impostazioni, 'it')
        return percorso

    # --- B5: i segni < e > di una descrizione sono testo, non marcatura ---------
    for desc in ('Taglia <M>', 'Coaching <premium', 'Prezzo <br> speciale', 'Pizza & birra'):
        esito = _senza_scoppiare(lambda: _testo(pdf('segni', [_riga(1, desc, 1000)])))
        _check(r, 'Documento', 'una descrizione con «%s» esce com’è scritta' % desc,
               desc in esito, True)

    # --- B3: le lettere che il Helvetica standard non ha ------------------------
    esito = _senza_scoppiare(lambda: _testo(pdf(
        'lettere', [_riga(1, 'Ćiro Đurić ł ő', 1000)], cliente='Željko Ćosić')))
    atteso = ('Željko Ćosić', 'Ćiro Đurić ł ő') if caratteri.UNICODE else ('Zeljko Cosic', 'Ciro Duric l o')
    _check(r, 'Documento', 'nome e descrizione con lettere dell’Est restano leggibili',
           (atteso[0] in esito, atteso[1] in esito), (True, True))

    # --- B4: righe e descrizioni lunghe non si sovrappongono, il totale resta ----
    lunga = ('Allenamento personale individuale con valutazione iniziale, programma scritto '
             'e controllo della tecnica ogni settimana, compreso materiale')
    for quante, desc in ((1, 'Pack 10 sedute'), (5, lunga), (6, lunga), (8, lunga), (14, lunga)):
        righe = [_riga(1, '%d) %s' % (i + 1, desc), 12345 + i) for i in range(quante)]
        esito = _senza_scoppiare(lambda: _pezzi(pdf('righe%d' % quante, righe)))
        if isinstance(esito, str):
            _check(r, 'Documento', '%d righe: il PDF si fa' % quante, esito, 'un PDF')
            continue
        testo = _testo(os.path.join(cartella, 'righe%d.pdf' % quante))
        totale = sum(x['total_cents'] for x in righe)
        _check(r, 'Documento', '%d righe: niente testo sopra altro testo' % quante,
               _sovrapposti(esito), [])
        from pypdf import PdfReader
        ultima = (PdfReader(os.path.join(cartella, 'righe%d.pdf' % quante)).pages[-1]
                  .extract_text() or '')
        _check(r, 'Documento', '%d righe: l’ultima pagina non porta il solo totale' % quante,
               ('%d) ' % quante) in ultima, True)
        _check(r, 'Documento', '%d righe: ci sono tutte, e il totale una volta sola' % quante,
               (all(('%d) ' % (i + 1)) in testo for i in range(quante)),
                testo.count('TOTALE DA PAGARE')), (True, 1))

    # --- Word: oltre le otto righe del modello ---------------------------------
    righe = [_riga(1, 'Riga %d' % (i + 1), 10000 + i) for i in range(12)]
    totale = sum(x['total_cents'] for x in righe)
    d = os.path.join(cartella, 'dodici.docx')
    esito = _senza_scoppiare(lambda: docgen.build_docx(
        d, 1, '01-10-26', 'Giulia Ferrari', ['Musterstrasse 1', '8000 Zürich'], righe, totale,
        impostazioni, 'it'))
    riletto = _senza_scoppiare(lambda: importer.extract_docx(d))
    _check(r, 'Documento', 'dodici righe: il Word le ha tutte e il totale torna',
           (len(riletto[4]) if isinstance(riletto, tuple) else riletto,
            riletto[5] if isinstance(riletto, tuple) else None), (12, totale))
    p = pdf('dodici', righe)
    _check(r, 'Documento', 'dodici righe: la verifica automatica non trova problemi',
           _senza_scoppiare(lambda: verify.verify_generated(d, p, totale, righe)), [])


def _scenario():
    """Nel processo di prova: il Cestino e il numero delle fatture."""
    import app as APP
    from core import db as D

    fatti = {}
    con = D.init()
    con.execute("INSERT INTO clients(id, key, name, address1, address2, file_label) "
                "VALUES(1, 'giulia', 'Giulia Ferrari', 'Musterstrasse 1', '8000 Zürich', "
                "'Giulia Ferrari')")
    con.commit()
    con.close()
    c = APP.app.test_client()
    riga = {'client_id': '1', 'data': '2026-10-04', 'desc_0': 'Seduta', 'tot_0': '100',
            'numero': '70'}
    c.post('/nuova', data=riga)
    k = D.connect()
    vecchia = k.execute('SELECT id FROM invoices WHERE number=70').fetchone()['id']
    k.execute("UPDATE invoices SET deleted_at='2026-10-04T10:00:00' WHERE id=?", (vecchia,))
    k.commit()
    k.close()
    # il numero torna libero e si riusa: la fattura rifatta e' un'altra riga con lo stesso numero
    import shutil
    for nome in os.listdir(APP.INVOICE_DIR):               # i file della prima non servono piu'
        shutil.rmtree(os.path.join(APP.INVOICE_DIR, nome), ignore_errors=True)
    c.post('/nuova', data=riga)
    pagina = c.post('/cestino/%d/ripristina' % vecchia, follow_redirects=True).get_data(as_text=True)
    k = D.connect()
    fatti['attive_numero_70'] = k.execute(
        'SELECT COUNT(*) FROM invoices WHERE number=70 AND deleted_at IS NULL').fetchone()[0]
    fatti['avviso'] = 'già usato' in pagina or 'gi&agrave; usato' in pagina
    k.close()
    print(MARCA + json.dumps(fatti))


def _test_revisione_documento(r):
    from .selftest import _check
    from .selftest_revisione import _fatti
    _prove_documento(r)
    f = _fatti('selftest_revisione_documento', '_scenario')
    _check(r, 'Documento', 'dal Cestino non torna una seconda fattura con lo stesso numero',
           (f['attive_numero_70'], f['avviso']), (1, True))
