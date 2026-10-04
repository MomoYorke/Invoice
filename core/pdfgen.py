# -*- coding: utf-8 -*-
"""
Genera il PDF della fattura NATIVAMENTE (reportlab), replicando il layout
del template ufficiale: intestazione con logo, numero/data, destinatario,
tabella articoli, TOTAL DUE, ringraziamento e Terms con IBAN.
Nessuna dipendenza da LibreOffice/Word.
"""
import os
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from xml.sax.saxutils import escape
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle

from .money import fmt_dash
from . import docgen
from . import language as L
from . import branding
from . import qrbill
from . import caratteri

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGE_W, PAGE_H = A4
ML = MR = 1.905 * cm          # margini come il template Word
MT, MB = 1.905 * cm, 1.778 * cm
USABLE = PAGE_W - ML - MR

GRID = colors.HexColor('#808080')
DESC_STYLE = ParagraphStyle('desc', fontName=caratteri.REG, fontSize=9, leading=11)


def _descrizione(testo):
    """La descrizione di una riga, come testo.

    Un Paragraph la legge come marcatura: «Taglia <M>» perdeva la parola
    fra i segni, e «Coaching <premium» faceva cadere la fattura con
    un errore. Qui i segni < > & restano quello che sono."""
    t = escape(caratteri.stampabile(testo or ''))
    return Paragraph(t.replace('\n', '<br/>'), DESC_STYLE)


def _distribuisci(h_righe, h_intest, h_totale, alto_prima, alto_altre, margine, fondo_ultima):
    """Su quali pagine va ogni riga. Ritorna una lista di liste di posizioni.

    Il totale sta sull'ultima pagina e sotto di lui devono restare `fondo_ultima`
    punti per il ringraziamento e le condizioni. Le pagine intermedie si
    riempiono fino al `margine`. Con tutto che entra, e' una pagina sola."""
    pagine, i, n, prima = [], 0, len(h_righe), True
    while True:
        alto = alto_prima if prima else alto_altre
        if alto - (h_intest + sum(h_righe[i:]) + h_totale) >= fondo_ultima:
            pagine.append(list(range(i, n)))
            return pagine
        j, usato = i, h_intest
        while j < n and alto - (usato + h_righe[j]) >= margine:
            usato += h_righe[j]
            j += 1
        if j == i:
            j = i + 1                  # una riga da sola e' piu' alta della pagina: va lo stesso
        pagine.append(list(range(i, j)))
        i, prima = j, False
        if i >= n:
            # le righe sono finite, il totale no: va sull'ultima pagina, ma non da
            # solo — gli si porta dietro l'ultima riga, cosi' non e' un foglio vuoto
            if len(pagine[-1]) > 1:
                pagine.append([pagine[-1].pop()])
            else:
                pagine.append([])
            return pagine


def pagina_qr(c, number, date_str, client_name, addr_lines, total_cents,
              settings, lingua=None, qr_ref=None):
    """La QR-fattura, su un foglio suo, dopo la fattura. Ritorna (fatta, motivo).

    Su un foglio suo, e non in fondo alla fattura, perche' la fascia del
    bollettino si prende i 105 mm bassi del foglio tutti per se' e li' oggi ci
    sono la tabella e le condizioni. Lo standard prevede il caso: il bollettino
    puo' viaggiare su un foglio separato purche' sia l'ultimo. Cosi' la fattura
    che i clienti conoscono da un anno non si sposta di un millimetro.
    """
    if (settings.get('qr_fattura') or '0') != '1':
        return False, ''
    mio, motivo = qrbill.da_impostazioni(settings)
    if not mio:
        return False, motivo

    riferimento = qr_ref or qrbill.riferimento_della_fattura(number, settings)
    # l'indirizzo del cliente si stampa solo se si legge per intero: meglio il
    # campo vuoto, che chi paga riempie in un attimo, di un indirizzo inventato
    suo = qrbill.indirizzo_strutturato(*(list(addr_lines) + ['', ''])[:2])
    messaggio = L.t_doc('Fattura {n} del {d}', lingua).format(n=number, d=date_str)
    debitore = client_name if suo else ''

    # Prima si compone il codice, POI si disegna. Al contrario, un codice che non
    # si poteva fare lasciava in coda alla fattura una mezza pagina con scritto
    # «da staccare», e niente da staccare. Il guaio si scrive nel registro: una
    # fattura che esce senza bollettino senza che nessuno lo sappia e' il modo
    # migliore per accorgersene dal cliente che non paga.
    try:
        qrbill.dati_qr(mio['iban'], mio['nome'], mio['indirizzo'], total_cents,
                       riferimento, messaggio, debitore_nome=debitore, debitore_ind=suo)
    except ValueError as guaio:
        logging.getLogger('fatture.errori').error(
            'QR-fattura #%s non stampata: %s', number, guaio)
        return False, str(guaio)

    c.setFont(caratteri.BOLD, 11)
    c.drawString(ML, PAGE_H - MT - 12, settings.get('business_name', ''))
    c.setFont(caratteri.REG, 10)
    c.drawString(ML, PAGE_H - MT - 30,
                 L.t_doc('Fattura {n} del {d}', lingua).format(n=number, d=date_str))
    c.drawString(ML, PAGE_H - MT - 46,
                 L.t_doc('Da staccare e usare per il pagamento.', lingua))
    qrbill.disegna_su(c, PAGE_W, mio['iban'], mio['nome'], mio['indirizzo'],
                      total_cents, riferimento, messaggio=messaggio,
                      lingua=(lingua or 'it'),
                      debitore_nome=debitore, debitore_ind=suo)
    c.showPage()
    return True, ''


def build_pdf(out_path, number, date_str, client_name, addr_lines, items,
              total_cents, settings, lingua=None, qr_ref=None):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    c = caratteri.Canvas(out_path, pagesize=A4)
    c.setTitle(f"Fattura #{number} - {settings.get('business_name', '')}")

    top = PAGE_H - MT
    # --- intestazione sinistra ---
    c.setFont(caratteri.BOLD, 12)
    c.drawString(ML, top - 12, settings.get('business_name', ''))
    c.setFont(caratteri.REG, 9)
    c.drawString(ML, top - 26, settings.get('business_uid', ''))
    y = top - 78
    for line in (settings.get('business_addr1', ''), settings.get('business_addr2', ''),
                 settings.get('business_phone', ''), settings.get('business_web', '')):
        if line:
            c.drawString(ML, y, line)
            y -= 13
    # --- logo in alto a destra ---
    # come nel .docx: se il logo non c'e' lo spazio resta vuoto, non ci
    # mettiamo il segnaposto
    logo = branding.percorso()
    if branding.personalizzato() and os.path.exists(logo):
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo)
            iw, ih = img.getSize()
            w = 2.4 * cm
            h = w * ih / iw
            c.drawImage(img, PAGE_W - MR - w, top - h, w, h,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    # --- numero e data a destra ---
    c.setFont(caratteri.REG, 10)
    c.drawRightString(PAGE_W - MR, top - 135, f'#{number}')
    c.drawRightString(PAGE_W - MR, top - 149, date_str)
    # --- destinatario ---
    y = top - 205
    c.setFont(caratteri.REG, 10)
    c.drawString(ML, y, client_name)
    for line in addr_lines:
        if line and line.strip():
            y -= 14
            c.drawString(ML, y, line.strip())

    # --- tabella articoli ---
    # Le righe vanno dove c'e' posto: sulla prima pagina sotto il destinatario,
    # e se non bastano su altre pagine, con l'intestazione ripetuta. Il totale,
    # il ringraziamento e le condizioni stanno sull'ultima. Prima le righe erano
    # sempre otto in un punto fisso: dalla sesta in poi, o con descrizioni
    # lunghe, il testo finiva sopra il ringraziamento.
    col_w = [90, 245, 82, 70]
    scale = USABLE / sum(col_w)
    col_w = [w * scale for w in col_w]

    header = [L.t_doc(x, lingua) for x in
              ('QUANTITÀ', 'DESCRIZIONE', 'PREZZO UNITARIO', 'TOTALE')]
    righe = []
    for it in items:
        unit = fmt_dash(it['unit_cents']) if it['unit_cents'] is not None else ''
        tot = (fmt_dash(it['total_cents']) + '\nCHF') if it['total_cents'] is not None else ''
        righe.append([str(it['qty']), _descrizione(it['description']), unit, tot])
    vuota = ['', '', '', '']
    riga_totale = [['', '', L.t_doc('TOTALE DA PAGARE', lingua), fmt_dash(total_cents) + '\nCHF']]

    stile_righe = [
        ('FONT', (0, 0), (-1, 0), caratteri.BOLD, 9),
        ('FONT', (0, 1), (-1, -1), caratteri.REG, 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (3, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.6, GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (1, 1), (1, -1), 8),
    ]
    stile_totale = [
        ('FONT', (2, 0), (-1, 0), caratteri.BOLD, 9),
        ('ALIGN', (2, 0), (3, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (3, 0), (3, 0), 0.9, GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]

    def tabella(dati, stile):
        t = Table(dati, colWidths=col_w)
        t.setStyle(TableStyle(stile))
        t.wrapOn(c, USABLE, PAGE_H)
        return t

    altezze = tabella([header] + righe, stile_righe)._rowHeights
    h_intest, h_righe = altezze[0], list(altezze[1:])
    h_totale = tabella(riga_totale, stile_totale)._rowHeights[0]
    h_vuota = tabella([header, vuota], stile_righe)._rowHeights[1]

    table_top = top - 330
    sopra_seconda = PAGE_H - MT - 30               # le pagine dopo la prima
    sotto_ultima = MB + 150                        # sotto il totale: ringraziamento e condizioni
    pagine = _distribuisci(h_righe, h_intest, h_totale, table_top, sopra_seconda,
                           MB + 20, sotto_ultima)
    if len(pagine) == 1:
        # il foglio che i clienti conoscono: otto righe, anche se vuote, quando c'e' posto
        spazio = table_top - (h_intest + sum(h_righe) + h_totale) - sotto_ultima
        vuote = max(0, min(8 - len(righe), int(spazio // h_vuota)))
        righe += [vuota] * vuote

    y_fondo = table_top
    for n_pagina, indici in enumerate(pagine):
        ultima = n_pagina == len(pagine) - 1
        if n_pagina:
            c.showPage()
            c.setFont(caratteri.REG, 9)
            c.drawString(ML, PAGE_H - MT - 12,
                         L.t_doc('Fattura {n} del {d}', lingua).format(n=number, d=date_str)
                         + ' — ' + client_name)
        alto = table_top if n_pagina == 0 else sopra_seconda
        pezzo = [header] + [righe[i] for i in indici]
        if len(pagine) == 1:
            pezzo = [header] + righe
        if indici or len(pagine) == 1:
            t = tabella(pezzo, stile_righe)
            th = sum(t._rowHeights)
            t.drawOn(c, ML, alto - th)
            y_fondo = alto - th
        else:
            y_fondo = alto                 # pagina col solo totale
        if ultima:
            tt = tabella(riga_totale, stile_totale)
            tt.drawOn(c, ML, y_fondo - h_totale)
            y_fondo -= h_totale

    # --- ringraziamento ---
    c.setFont(caratteri.REG, 10)
    thanks_y = max(MB + 130, y_fondo - 60)
    c.drawCentredString(PAGE_W / 2, thanks_y,
                        L.t_doc('Grazie per aver scelto {nome}!', lingua).format(
                            nome=settings.get('business_name', '')))

    # --- terms ---
    y = MB + 62
    c.setFont(caratteri.REG, 9)
    etichetta = L.t_doc('Condizioni', lingua) + ':'
    c.drawString(ML, y, etichetta)
    c.line(ML, y - 1.5, ML + c.stringWidth(etichetta, caratteri.REG, 9), y - 1.5)
    for line in (docgen.condizioni(settings, lingua), settings.get('business_name', ''),
                 'IBAN: ' + settings.get('business_iban', '')):
        y -= 13
        c.drawString(ML, y, line)

    c.showPage()
    # il bollettino, se acceso e se i dati ci sono. Un guaio qui non deve far
    # fallire la fattura: la fattura vale da sola, il bollettino e' in piu'.
    try:
        pagina_qr(c, number, date_str, client_name, addr_lines, total_cents,
                  settings, lingua, qr_ref)
    except Exception as guaio:                               # pragma: no cover
        # zitto no: una fattura che esce senza bollettino senza che nessuno lo
        # sappia e' il modo migliore per accorgersene dal cliente che non paga
        logging.getLogger('fatture.errori').error(
            'QR-fattura #%s non stampata: %s', number, guaio)
    c.save()
    return out_path
