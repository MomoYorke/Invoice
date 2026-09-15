# -*- coding: utf-8 -*-
"""
«Righe senza servizio»: le righe vecchie che l'app non ha saputo collegare.

E' una pagina da vedere una volta. Un elemento per ogni testo diverso (senza
date ne' virgolette), con quante righe lo usano e un'ipotesi gia' scelta.
«Fatto» scrive il servizio su tutte le righe di quel testo e se lo ricorda,
cosi' il Reimporta non lo richiede; quello che resta su «Scegli…» torna la
volta dopo. Non blocca niente: finche' non si decide, Performance le mette in
«Altro» come ha sempre fatto.

Sconti e omaggi non compaiono: Performance li tratta gia' a parte.
"""
import re

from . import services as srv
from .money import fmt_dash
from .stats import SCONTI, OMAGGI

PAROLA = re.compile(r'\w+')


def _intero(valore):
    try:
        return int(float(str(valore).replace(',', '.')))
    except (TypeError, ValueError):
        return None


def da_decidere(con):
    """I testi ancora da decidere, dal piu' usato."""
    gruppi = {}
    for r in con.execute(
            'SELECT i.description, i.qty, i.total_cents, f.number '
            'FROM items i JOIN invoices f ON f.id = i.invoice_id '
            'WHERE i.servizio_id IS NULL AND f.deleted_at IS NULL '
            'ORDER BY f.date DESC, COALESCE(f.number, 0) DESC, i.pos'):
        chiave = srv.normalizza_testo(r['description'])
        if not chiave or SCONTI.search(chiave) or OMAGGI.search(chiave):
            continue
        g = gruppi.get(chiave)
        if g is None:              # la prima che si incontra e' la piu' recente
            g = gruppi[chiave] = {
                'chiave': chiave, 'righe': 0,
                'testo': srv.senza_date(r['description']) or r['description'],
                'prezzo_cents': r['total_cents'], 'qty': r['qty'], 'numero': r['number']}
        g['righe'] += 1
    return sorted(gruppi.values(), key=lambda g: (-g['righe'], g['chiave']))


def quante(con):
    return len(da_decidere(con))


def ipotesi(elemento, servizi):
    """Il servizio piu' probabile per quel testo, o None se nessuno convince.

    Vince quello con piu' parole in comune. A parita', quello le cui sedute
    coincidono col numero scritto nel testo o con la quantita' della riga:
    «Personal Training Pack» 12 × 150 porta al servizio da 12 sedute."""
    parole = set(PAROLA.findall(elemento['chiave']))
    punteggi = []
    for s in servizi:
        comuni = len(parole & set(PAROLA.findall(srv.normalizza_testo(s['nome']))))
        if comuni:
            punteggi.append((comuni, s))
    if not punteggi:
        return None
    migliore = max(p for p, _s in punteggi)
    primi = [s for p, s in punteggi if p == migliore]
    if len(primi) == 1:
        return primi[0]['id']
    scritto = re.search(r'\d+', elemento['chiave'])
    numeri = {n for n in (int(scritto.group()) if scritto else None,
                          _intero(elemento.get('qty'))) if n}
    giusti = [s for s in primi if s['sedute'] and s['sedute'] in numeri]
    return giusti[0]['id'] if len(giusti) == 1 else None


def decidi(con, chiave, servizio_id):
    """Scrive il servizio (0 = nessuno) su tutte le righe non decise con quel
    testo, e se lo ricorda. Ritorna quante righe. Il commit lo fa chi chiama."""
    ids = [r['id'] for r in con.execute(
        'SELECT id, description FROM items WHERE servizio_id IS NULL')
        if srv.normalizza_testo(r['description']) == chiave]
    con.executemany('UPDATE items SET servizio_id=? WHERE id=?',
                    [(int(servizio_id), i) for i in ids])
    srv.ricorda(con, chiave, servizio_id)
    return len(ids)


def per_nuovo_servizio(elemento, registro=None):
    """La scheda «Nuovo servizio con questo nome…» gia' scritta.

    Il nome dal testo, il prezzo dall'ultima riga, le sedute dal pacchetto
    collegato a quella fattura, se c'e'. Il resto lo decide chi la salva."""
    sedute = 0
    for p in (registro or {}).get('pacchetti') or []:
        if elemento.get('numero') is not None and \
                str(p.get('fattura_numero')) == str(elemento['numero']):
            sedute = int(p.get('crediti') or 0)
            break
    prezzo = elemento.get('prezzo_cents')
    return {'nome': elemento['testo'], 'prezzo_cents': prezzo,
            'prezzo_testo': fmt_dash(prezzo) if prezzo is not None else '',
            'ogni_mese': 0, 'con_sedute': sedute > 0, 'sedute': sedute or None,
            'scadono': False, 'scadenza_mesi': 0, 'passano': 0, 'massimo': 0,
            'da_riga': elemento['chiave']}
