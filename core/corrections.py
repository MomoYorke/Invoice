# -*- coding: utf-8 -*-
"""
Correzioni manuali e archiviazione delle anomalie storiche.

Problema che risolve: le fatture importate vengono cancellate e ricreate a ogni
"Reimporta", quindi il loro id cambia. Le correzioni sono quindi indicizzate su
una chiave STABILE (il percorso del file di origine), e vengono ri-applicate
automaticamente dopo ogni import.
"""
from . import db


def invoice_key(inv):
    """Identità stabile di una fattura: sopravvive al reimport."""
    if inv['source_file']:
        return inv['source_file']
    if inv['number'] is not None:
        return f"num:{inv['number']}"
    return f"id:{inv['id']}"


# ---------------------------------------------------------------- correzioni
def save_correction(con, inv, total_cents=None, date_iso=None, note='', number=None):
    """Salva (o aggiorna) la correzione e la applica subito alla fattura."""
    key = invoice_key(inv)
    row = con.execute('SELECT * FROM corrections WHERE key=?', (key,)).fetchone()
    # conserva i valori gia' corretti se questa volta non vengono ripassati
    if row:
        total_cents = total_cents if total_cents is not None else row['total_cents']
        date_iso = date_iso or row['date']
        note = note or row['note']
        number = number if number is not None else row['number']
    con.execute(
        'INSERT INTO corrections(key, total_cents, date, number, note, created_at) '
        'VALUES(?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET '
        'total_cents=excluded.total_cents, date=excluded.date, '
        'number=excluded.number, note=excluded.note, created_at=excluded.created_at',
        (key, total_cents, date_iso, number, note, db.now_iso()))
    apply_all(con)
    con.commit()
    return key


def remove_correction(con, key):
    """Annulla una correzione: il dato torna com'era nel file di origine."""
    con.execute('DELETE FROM corrections WHERE key=?', (key,))
    con.commit()


def apply_all(con):
    """Ri-applica tutte le correzioni salvate alle fatture presenti nel DB.
    Va chiamata dopo ogni import. Ritorna il numero di fatture aggiornate."""
    n = 0
    for c in con.execute('SELECT * FROM corrections').fetchall():
        key = c['key']
        if key.startswith('num:'):
            where, arg = 'number=?', key[4:]
        elif key.startswith('id:'):
            where, arg = 'id=?', key[3:]
        else:
            where, arg = 'source_file=?', key
        sets, args = [], []
        if c['total_cents'] is not None:
            sets.append('total_cents=?')
            args.append(c['total_cents'])
        if c['date']:
            sets.append('date=?')
            args.append(c['date'])
        if ('number' in c.keys()) and c['number'] is not None:
            sets.append('number=?')
            args.append(c['number'])
        if not sets:
            continue
        args.append(arg)
        cur = con.execute(f'UPDATE invoices SET {", ".join(sets)} WHERE {where}', args)
        n += cur.rowcount
    return n


def corrections_map(con):
    """dict key -> riga correzione, per mostrare cosa è stato corretto a mano."""
    return {r['key']: r for r in con.execute('SELECT * FROM corrections')}


# ---------------------------------------------------------------- archiviate
def acknowledge(con, key, kind, msg, note=''):
    con.execute(
        'INSERT INTO acknowledged(key, kind, msg, note, created_at) VALUES(?,?,?,?,?) '
        'ON CONFLICT(key) DO UPDATE SET note=excluded.note, created_at=excluded.created_at',
        (key, kind, msg, note, db.now_iso()))
    con.commit()


def unacknowledge(con, key):
    con.execute('DELETE FROM acknowledged WHERE key=?', (key,))
    con.commit()


def acknowledged_keys(con):
    return {r['key'] for r in con.execute('SELECT key FROM acknowledged')}


def acknowledged_list(con):
    return con.execute('SELECT * FROM acknowledged ORDER BY created_at DESC').fetchall()
