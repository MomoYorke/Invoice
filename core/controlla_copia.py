# -*- coding: utf-8 -*-
"""
Controlla una COPIA del database delle fatture e dice se i conti tornano.

Serve a chi collauda una modifica sui propri dati veri: invece di guardare le
pagine una per una, lancia questo e legge «a posto» oppure cosa non torna.
Non scrive niente: il database si apre in sola lettura.

Uso (dalla cartella dell'app):
    python3 controlla_copia.py "percorso/della/copia/fatture.db"
"""
import os
import sqlite3
import sys

try:                                  # per aprire il file in sola lettura
    from urllib.request import pathname2url
except ImportError:                   # pragma: no cover
    pathname2url = None


def _apri_in_lettura(percorso):
    uri = 'file:%s?mode=ro' % pathname2url(os.path.abspath(percorso))
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def controlla(percorso):
    """Ritorna (problemi, fatti): due liste di frasi in italiano.

    problemi = cose che non vanno; fatti = quante cose sono state guardate,
    cosi' «a posto» non e' un silenzio ma un conto."""
    problemi, fatti = [], []
    if not os.path.isfile(percorso):
        return ['Il file «%s» non esiste.' % percorso], fatti
    try:
        con = _apri_in_lettura(percorso)
        giro = con.execute('PRAGMA integrity_check').fetchone()[0]
    except sqlite3.Error as e:
        return ['Non riesco ad aprire il database: %s' % e], fatti
    if giro != 'ok':
        problemi.append('Il database è danneggiato: %s' % giro)
    else:
        fatti.append('Il database si apre ed è integro.')

    try:
        attive = con.execute(
            'SELECT id, number, total_cents, source, qr_ref FROM invoices '
            'WHERE deleted_at IS NULL').fetchall()
    except sqlite3.Error as e:
        con.close()
        problemi.append('Non riesco a leggere le fatture: %s' % e)
        return problemi, fatti
    fatti.append('Fatture attive guardate: %d.' % len(attive))

    # --- lo stesso numero su due fatture ---
    per_numero = {}
    for r in attive:
        if r['number'] is not None:
            per_numero.setdefault(r['number'], []).append(r['id'])
    doppi = sorted(n for n, ids in per_numero.items() if len(ids) > 1)
    if doppi:
        problemi.append('Numeri di fattura usati più di una volta: %s. '
                        'Finché ci sono, non si può mettere il vincolo «numero unico».'
                        % ', '.join('#%d' % n for n in doppi[:20]))
    else:
        fatti.append('Nessun numero di fattura è usato due volte '
                     '(il vincolo «numero unico» si può aggiungere).')

    # --- lo stesso riferimento QR su due fatture ---
    per_rif = {}
    for r in attive:
        if (r['qr_ref'] or '').strip():
            per_rif.setdefault(r['qr_ref'].strip(), []).append(r['number'])
    rif_doppi = sorted(v[0] for v in per_rif.values() if len(v) > 1 and v[0] is not None)
    if rif_doppi:
        problemi.append('Fatture con lo stesso riferimento di pagamento QR (un versamento '
                        'potrebbe finire sulla fattura sbagliata), per esempio la #%d.'
                        % rif_doppi[0])
    else:
        fatti.append('Ogni riferimento di pagamento QR è di una fattura sola.')

    # --- il totale e' la somma delle righe (per le fatture fatte dall'app) ---
    storte, senza_righe = [], []
    for r in attive:
        if r['source'] != 'app':
            continue
        somma, quante = con.execute(
            'SELECT COALESCE(SUM(total_cents), 0), COUNT(*) FROM items WHERE invoice_id=?',
            (r['id'],)).fetchone()
        if not quante:
            senza_righe.append(r['number'])
        elif r['total_cents'] is not None and somma != r['total_cents']:
            storte.append(r['number'])
    if storte:
        problemi.append('Il totale non è la somma delle righe nelle fatture: %s.'
                        % ', '.join('#%s' % n for n in storte[:20]))
    else:
        fatti.append('Nelle fatture fatte con l’app il totale è la somma delle righe.')
    if senza_righe:
        problemi.append('Fatture senza nessuna riga: %s.'
                        % ', '.join('#%s' % n for n in senza_righe[:20]))

    # --- importi che non dovrebbero esserci ---
    strani = [r['number'] for r in attive
              if r['total_cents'] is None or r['total_cents'] < 0]
    if strani:
        problemi.append('Fatture con il totale vuoto o negativo: %s.'
                        % ', '.join('#%s' % n for n in strani[:20]))
    con.close()
    return problemi, fatti


def main(argv):
    if len(argv) != 2:
        print('Uso: python3 controlla_copia.py "percorso/della/copia/fatture.db"')
        return 2
    problemi, fatti = controlla(argv[1])
    for f in fatti:
        print('  ok  ' + f)
    for p in problemi:
        print('  !!  ' + p)
    print()
    if problemi:
        print('Non torna tutto: %s (sopra, con !!).'
              % ('1 cosa da guardare' if len(problemi) == 1
                 else '%d cose da guardare' % len(problemi)))
        return 1
    print('A posto: i conti tornano. Il database non è stato modificato.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
