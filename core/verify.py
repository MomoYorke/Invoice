# -*- coding: utf-8 -*-
"""
Verifica di correttezza delle fatture.

Due usi:
1. verify_generated(): chiamata SUBITO dopo aver generato docx+pdf di una nuova
   fattura. Rilegge i file veri e controlla che l'importo coincida al centesimo
   con quello calcolato. Se qualcosa non torna, la fattura NON viene salvata.
2. reconcile_all(): passa in rassegna tutte le fatture create dall'app e verifica
   che somma righe = totale salvato = importo scritto nel PDF.
"""
import os
import re

from . import importer
from .money import fmt_chf, parse_amount

try:
    from pypdf import PdfReader
    _HAS_PDF = True
except Exception:
    _HAS_PDF = False


def _pdf_total_cents(pdf_path):
    """Estrae l'importo 'TOTAL DUE' dal PDF generato. None se non leggibile."""
    if not _HAS_PDF or not os.path.exists(pdf_path):
        return None
    try:
        reader = PdfReader(pdf_path)
        text = '\n'.join(p.extract_text() or '' for p in reader.pages)
    except Exception:
        return None
    # cerca la riga TOTAL DUE e l'importo che la segue (anche su riga successiva)
    m = re.search(r"TOTAL\s*DUE\s*([0-9][0-9'’.\s,-]*)", text, re.I)
    if m:
        val = parse_amount(m.group(1))
        if val is not None:
            return val
    # fallback: prendi l'ultimo importo con marcatore CHF/.- nel testo
    cands = re.findall(r"([0-9][0-9'’.,]*\s*(?:\.\-|CHF))", text, re.I)
    for c in reversed(cands):
        v = parse_amount(c)
        if v is not None:
            return v
    return None


def verify_generated(docx_path, pdf_path, expected_total_cents, expected_items):
    """Ritorna lista di problemi (vuota = tutto corretto)."""
    problems = []

    # 1. coerenza interna: somma delle righe == totale atteso
    line_sum = sum(it['total_cents'] for it in expected_items
                   if it.get('total_cents') is not None)
    if line_sum != expected_total_cents:
        problems.append(
            f"La somma delle righe ({fmt_chf(line_sum)}) non coincide con il "
            f"totale della fattura ({fmt_chf(expected_total_cents)}).")

    # 2. rilettura del DOCX generato
    try:
        _, _, _, _, ritems, rtot = importer.extract_docx(docx_path)
        if rtot != expected_total_cents:
            problems.append(
                f"Il totale scritto nel documento Word ({fmt_chf(rtot)}) non "
                f"coincide con quello calcolato ({fmt_chf(expected_total_cents)}).")
        # confronto riga per riga
        exp = [it['total_cents'] for it in expected_items if it.get('total_cents') is not None]
        got = [t for (_, _, _, t) in ritems if t is not None]
        if sorted(exp) != sorted(got):
            problems.append(
                "Gli importi delle righe nel documento Word non corrispondono "
                "a quelli calcolati.")
    except Exception as e:
        problems.append(f"Impossibile rileggere il documento Word per la verifica ({e}).")

    # 3. rilettura del PDF vero (se possibile)
    pdf_tot = _pdf_total_cents(pdf_path)
    if pdf_tot is None and _HAS_PDF:
        problems.append("Non sono riuscito a rileggere l'importo dal PDF per verificarlo.")
    elif pdf_tot is not None and pdf_tot != expected_total_cents:
        problems.append(
            f"L'importo stampato sul PDF ({fmt_chf(pdf_tot)}) non coincide con "
            f"quello calcolato ({fmt_chf(expected_total_cents)}).")

    return problems


def reconcile_all(con):
    """Verifica ogni fattura 'app': somma righe == totale salvato == PDF.
    Ritorna lista di dict con le anomalie trovate (vuota = tutto in ordine)."""
    anomalies = []
    rows = con.execute("SELECT * FROM invoices WHERE source='app' AND deleted_at IS NULL ORDER BY number").fetchall()
    for inv in rows:
        items = con.execute('SELECT total_cents FROM items WHERE invoice_id=?',
                            (inv['id'],)).fetchall()
        line_sum = sum(r['total_cents'] or 0 for r in items)
        stored = inv['total_cents']
        problems = []
        if stored is not None and line_sum != stored:
            problems.append(f"somma righe {fmt_chf(line_sum)} ≠ totale salvato {fmt_chf(stored)}")
        if inv['pdf_path'] and os.path.exists(inv['pdf_path']):
            pdf_tot = _pdf_total_cents(inv['pdf_path'])
            if pdf_tot is not None and stored is not None and pdf_tot != stored:
                problems.append(f"PDF {fmt_chf(pdf_tot)} ≠ totale salvato {fmt_chf(stored)}")
        if problems:
            anomalies.append({'number': inv['number'], 'client': inv['client_name'],
                              'problems': problems})
    return {'checked': len(rows), 'anomalies': anomalies, 'pdf_reads': _HAS_PDF}
