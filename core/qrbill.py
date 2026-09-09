# -*- coding: utf-8 -*-
"""La QR-fattura svizzera: il riferimento, i dati del codice, il foglio.

Lo standard e' pubblico (Swiss Payment Standards, «Swiss Implementation
Guidelines QR-bill»): non serve chiedere il permesso a nessuno, ne' alla banca
ne' a un ente. Chiunque puo' stampare una QR-fattura sul proprio conto.

Due cose vanno sapute prima di leggere il resto.

IL RIFERIMENTO. Ce ne sono tre tipi, e non si sceglie: lo decide l'IBAN.
  - QRR: 27 cifre, ma vuole un QR-IBAN, cioe' un IBAN il cui numero d'istituto
    sta fra 30000 e 31999. Un IBAN normale non lo accetta.
  - SCOR: il «Creditor Reference» ISO 11649, quello che comincia per RF. Va su
    QUALUNQUE IBAN.
  - NON: nessun riferimento. Il pagamento arriva, ma non si sa di quale fattura
    e' — che e' esattamente il problema che la QR-fattura serve a togliere.
Quest'app stampa sempre SCOR: va su qualunque IBAN, senza chiedere niente alla
banca. Resta fuori un caso, ed e' bene saperlo: chi ha un QR-IBAN per lo
standard DEVE usare QRR, e QRR qui non si compone. Il QR-IBAN l'app lo sa
riconoscere (e_qr_iban, qui sotto) ma non lo chiede a nessuno: finche' e' cosi',
un utente con QR-IBAN stamperebbe bollettini che la sua banca rifiuta.

L'INDIRIZZO. Fino al 21.11.2025 si poteva scrivere l'indirizzo «combinato» (due
righe libere, tipo K). Da allora e' ammesso solo quello STRUTTURATO (tipo S),
con via, numero, CAP e localita' in campi separati. Qui si scrive solo S — e
dove i campi non ci sono con certezza, il debitore si lascia fuori del tutto,
che lo standard permette, invece di indovinarlo.
"""
import re

# I tre tipi di riferimento, con i nomi che vanno scritti nel codice
QRR, SCOR, NON = 'QRR', 'SCOR', 'NON'

# Un QR-IBAN si riconosce dal numero d'istituto (le posizioni 5-9 dell'IBAN)
IID_QR_DA, IID_QR_A = 30000, 31999

MONETE = ('CHF', 'EUR')


def normalizza_iban(iban):
    """L'IBAN senza spazi e in maiuscolo. Non lo valida: lo pulisce."""
    return re.sub(r'\s+', '', (iban or '')).upper()


def e_qr_iban(iban):
    """Vero se l'IBAN e' un QR-IBAN, cioe' se accetta i riferimenti QRR."""
    i = normalizza_iban(iban)
    if len(i) < 9 or not i[4:9].isdigit():
        return False
    return IID_QR_DA <= int(i[4:9]) <= IID_QR_A


def _mod97(testo):
    """Il resto modulo 97 alla maniera di IBAN e ISO 11649.

    Le lettere valgono 10-35 (A=10 ... Z=35). Il numero che ne esce e' troppo
    lungo per stare in un intero di tante lingue, ma non di Python: si potrebbe
    scrivere in un colpo solo. Si va a pezzi lo stesso, perche' cosi' la
    funzione dice da sola come e' fatta e non dipende dagli interi lunghi.
    """
    resto = 0
    for ch in testo:
        if ch.isdigit():
            resto = (resto * 10 + int(ch)) % 97
        else:
            resto = (resto * 100 + ord(ch) - 55) % 97
    return resto


def riferimento_scor(parte):
    """Il Creditor Reference ISO 11649 per «parte»: RF + due cifre + parte.

    Le due cifre sono un controllo: se chi paga digita male il riferimento, la
    banca se ne accorge prima che il pagamento parta. Si calcolano spostando
    «RF00» in fondo, leggendo tutto come numero e prendendo 98 meno il resto.

    >>> riferimento_scor('539007547034')
    'RF18539007547034'
    """
    parte = re.sub(r'[^0-9A-Za-z]', '', str(parte)).upper()
    if not parte:
        raise ValueError('un riferimento vuoto non è un riferimento')
    if len(parte) > 21:
        raise ValueError('il Creditor Reference tiene al massimo 21 caratteri')
    controllo = 98 - _mod97(parte + 'RF00')
    return 'RF%02d%s' % (controllo, parte)


def scor_valido(riferimento):
    """Vero se il riferimento e' un SCOR ben formato e con il controllo giusto."""
    r = re.sub(r'\s+', '', (riferimento or '')).upper()
    if not re.match(r'^RF[0-9]{2}[0-9A-Z]{1,21}$', r):
        return False
    return _mod97(r[4:] + r[:4]) == 1


def riferimento_per(numero_fattura, iban=None):
    """Il riferimento da stampare sulla fattura numero «numero_fattura».

    Il numero della fattura e' gia' unico dentro l'app, e ritrovarlo a occhio in
    mezzo al riferimento serve piu' di quanto sembri: quando qualcosa non torna,
    chi guarda l'estratto conto legge «RF83 87» e sa subito che e' la 87.
    """
    return riferimento_scor(numero_fattura)


# ------------------------------------------------------------- indirizzi
# Il CAP svizzero: quattro cifre, eventualmente precedute da «CH-».
_CAP = re.compile(r'^(?:CH[- ]?)?(\d{4})[,\s]+(.+)$')
_CAP_DOPO = re.compile(r'^(.+?)[,\s]+(?:CH[- ]?)?(\d{4})$')
# Una via finisce col numero civico: «Musterstrasse 45», «Musterweg 8a»
_VIA = re.compile(r'^(.*?)[,\s]+(\d+\s*[a-zA-Z]?)$')


def indirizzo_strutturato(riga1, riga2, paese='CH'):
    """Da due righe scritte a mano ai campi che lo standard vuole separati.

    Ritorna {'via', 'civico', 'cap', 'localita', 'paese'} oppure None se le due
    righe non dicono con certezza tutte queste cose. None NON e' un errore: e'
    la risposta giusta quando l'indirizzo e' «Ireland», o «Address», o
    «Kilchberg, Zurich» senza CAP. Un indirizzo indovinato finisce stampato su
    un documento di pagamento, e li' non ci si puo' permettere di indovinare.

    Il CAP sta prima della localita' quasi sempre, ma non sempre: c'e' chi lo
    scrive dopo, «Musterstadt, 8000». Si prova nei due versi, e la cifra a
    quattro posti dice da che parte sta.
    """
    riga1 = ' '.join((riga1 or '').split())
    riga2 = ' '.join((riga2 or '').split())
    if not riga1 or not riga2:
        return None

    m = _CAP.match(riga2) or None
    if m:
        cap, localita = m.group(1), m.group(2)
    else:
        m = _CAP_DOPO.match(riga2)
        if not m:
            return None
        localita, cap = m.group(1), m.group(2)
    localita = localita.strip(' ,-')
    if not localita or localita.isdigit():
        return None

    v = _VIA.match(riga1)
    if not v:
        return None
    via, civico = v.group(1).strip(' ,-'), v.group(2).replace(' ', '')
    if not via:
        return None
    return {'via': via, 'civico': civico, 'cap': cap,
            'localita': localita, 'paese': (paese or 'CH').upper()[:2]}


def _righe_indirizzo(nome, ind):
    """Le sette righe che lo standard riserva a un soggetto (tipo S)."""
    if not nome or not ind:
        return ['', '', '', '', '', '', '']
    return ['S', nome[:70], ind['via'][:70], ind['civico'][:16],
            ind['cap'][:16], ind['localita'][:35], ind['paese']]


# ----------------------------------------------------- il codice QR vero
MAX_CARATTERI = 997


def dati_qr(iban, creditore_nome, creditore_ind, importo_cents, riferimento,
            messaggio='', moneta='CHF', debitore_nome='', debitore_ind=None):
    """Il contenuto del codice QR: righe fisse, in ordine fisso, separate da LF.

    L'ordine non e' una scelta di chi scrive: e' la struttura dello standard, e
    una riga in piu' o in meno sposta tutto quello che viene dopo. Per questo
    le righe vuote ci sono lo stesso — sono posti, non spazio sprecato.
    """
    iban = normalizza_iban(iban)
    if not creditore_ind:
        raise ValueError("senza il tuo indirizzo completo la QR-fattura non si può fare")
    if moneta not in MONETE:
        raise ValueError('la QR-fattura vale solo in CHF o EUR')
    tipo = SCOR if riferimento else NON
    if riferimento and not scor_valido(riferimento):
        raise ValueError('il riferimento non è un Creditor Reference valido')

    righe = ['SPC', '0200', '1', iban]
    righe += _righe_indirizzo(creditore_nome, creditore_ind)
    righe += ['', '', '', '', '', '', '']          # creditore finale: non si usa
    righe += ['' if importo_cents is None else '%d.%02d' % divmod(importo_cents, 100),
              moneta]
    righe += _righe_indirizzo(debitore_nome, debitore_ind)
    righe += [tipo, riferimento or '', (messaggio or '')[:140], 'EPD']

    testo = '\n'.join(righe)
    if len(testo) > MAX_CARATTERI:
        raise ValueError('il contenuto del codice QR supera i %d caratteri'
                         % MAX_CARATTERI)
    return testo


# ------------------------------------------------------------- il foglio
# Le etichette non si traducono a orecchio: lo standard le detta parola per
# parola in tedesco, francese, italiano e inglese, ed e' cosi' che la gente le
# riconosce da un capo all'altro del paese. Per questo stanno qui e non nei
# dizionari dell'app, dove sarebbero frasi come tutte le altre.
ETICHETTE = {
    'it': {'ricevuta': 'Ricevuta', 'sezione': 'Sezione pagamento',
           'conto': 'Conto / Pagabile a', 'riferimento': 'Riferimento',
           'informazioni': 'Informazioni supplementari',
           'pagabile': 'Pagabile da', 'pagabile_vuoto': 'Pagabile da (nome/indirizzo)',
           'valuta': 'Valuta', 'importo': 'Importo',
           'accettazione': 'Punto di accettazione'},
    'de': {'ricevuta': 'Empfangsschein', 'sezione': 'Zahlteil',
           'conto': 'Konto / Zahlbar an', 'riferimento': 'Referenz',
           'informazioni': 'Zusätzliche Informationen',
           'pagabile': 'Zahlbar durch', 'pagabile_vuoto': 'Zahlbar durch (Name/Adresse)',
           'valuta': 'Währung', 'importo': 'Betrag',
           'accettazione': 'Annahmestelle'},
    'en': {'ricevuta': 'Receipt', 'sezione': 'Payment part',
           'conto': 'Account / Payable to', 'riferimento': 'Reference',
           'informazioni': 'Additional information',
           'pagabile': 'Payable by', 'pagabile_vuoto': 'Payable by (name/address)',
           'valuta': 'Currency', 'importo': 'Amount',
           'accettazione': 'Acceptance point'},
    'fr': {'ricevuta': 'Récépissé', 'sezione': 'Section paiement',
           'conto': 'Compte / Payable à', 'riferimento': 'Référence',
           'informazioni': 'Informations supplémentaires',
           'pagabile': 'Payable par', 'pagabile_vuoto': 'Payable par (nom/adresse)',
           'valuta': 'Monnaie', 'importo': 'Montant',
           'accettazione': 'Point de dépôt'},
}

# Le misure dello standard, in millimetri. Non sono preferenze: la fascia in
# fondo al foglio e' 210x105, la ricevuta ne occupa 62 e la sezione pagamento i
# restanti 148, e il codice QR e' 46x46 con 5 mm di bianco intorno. Chi stampa
# su carta perforata trova le pieghe esattamente li'.
FASCIA_H = 105.0
RICEVUTA_W = 62.0
PAGAMENTO_W = 148.0
MARGINE = 5.0
QR_LATO = 46.0
CROCE_LATO = 7.0
# La sezione pagamento e' fatta di due colonne: a sinistra 51 mm per il codice
# (46 di codice piu' i 5 di bianco che gli devono restare intorno), a destra 87
# per le informazioni. Con i due margini da 5 fanno esattamente i 148 mm.
QR_COLONNA_W = 51.0
INFO_W = 87.0


def _spezza(testo, font, dim, larghezza_mm, c):
    """Il testo a capo dove ci sta, misurando davvero la larghezza."""
    from reportlab.lib.units import mm
    limite = larghezza_mm * mm
    righe, corrente = [], ''
    for parola in (testo or '').split():
        prova = (corrente + ' ' + parola).strip()
        if corrente and c.stringWidth(prova, font, dim) > limite:
            righe.append(corrente)
            corrente = parola
        else:
            corrente = prova
    if corrente:
        righe.append(corrente)
    return righe


PT = 25.4 / 72.0                  # un punto tipografico, in millimetri


def _blocco(c, x, y, titolo, righe, dim_titolo, dim_testo, larghezza):
    """Un'etichetta in grassetto e sotto il suo contenuto.

    Tutto in millimetri, come le misure dello standard: si converte in punti
    solo nel momento di scrivere. Ritorna la quota a cui il blocco finisce, cosi'
    chi chiama impila i blocchi senza contare le righe.
    """
    from reportlab.lib.units import mm
    c.setFont('Helvetica-Bold', dim_titolo)
    c.drawString(x * mm, y * mm, titolo)
    # l'etichetta sta ATTACCATA a cio' che spiega, non a mezza via fra il suo
    # contenuto e il blocco di sopra: lo stacco sotto e' solo un respiro
    y -= dim_titolo * 0.3 * PT
    c.setFont('Helvetica', dim_testo)
    passo = dim_testo * 1.2 * PT
    for riga in righe:
        for pezzo in _spezza(riga, 'Helvetica', dim_testo, larghezza, c):
            y -= passo
            c.drawString(x * mm, y * mm, pezzo)
    return y


def _croce_svizzera(c, cx_mm, cy_mm):
    """Il quadrato nero con la croce bianca, in mezzo al codice.

    Le proporzioni sono quelle della bandiera: su un lato di 32, i bracci sono
    larghi 6 e lunghi 20. Intorno al nero ci va un filo di bianco, altrimenti si
    confonde con i moduli del QR e il lettore fatica.
    """
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    lato = CROCE_LATO
    c.setFillColor(colors.white)
    c.rect((cx_mm - lato / 2 - 0.6) * mm, (cy_mm - lato / 2 - 0.6) * mm,
           (lato + 1.2) * mm, (lato + 1.2) * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.rect((cx_mm - lato / 2) * mm, (cy_mm - lato / 2) * mm,
           lato * mm, lato * mm, stroke=0, fill=1)
    braccio_l = lato * 6.0 / 32.0
    braccio_lungo = lato * 20.0 / 32.0
    c.setFillColor(colors.white)
    c.rect((cx_mm - braccio_lungo / 2) * mm, (cy_mm - braccio_l / 2) * mm,
           braccio_lungo * mm, braccio_l * mm, stroke=0, fill=1)
    c.rect((cx_mm - braccio_l / 2) * mm, (cy_mm - braccio_lungo / 2) * mm,
           braccio_l * mm, braccio_lungo * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)


def disegna_qr(c, testo, x_mm, y_mm):
    """Il codice QR con la croce, largo esattamente 46 mm.

    Il livello di correzione e' M perche' lo dice lo standard, e il contenuto va
    in UTF-8: reportlab codifica in byte mode con UTF-8, che e' quello giusto.
    """
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing

    widget = qr.QrCodeWidget(testo, barLevel='M', barBorder=0)
    x1, y1, x2, y2 = widget.getBounds()
    d = Drawing(QR_LATO * mm, QR_LATO * mm,
                transform=[QR_LATO * mm / (x2 - x1), 0, 0,
                           QR_LATO * mm / (y2 - y1), 0, 0])
    d.add(widget)
    d.drawOn(c, x_mm * mm, y_mm * mm)
    _croce_svizzera(c, x_mm + QR_LATO / 2, y_mm + QR_LATO / 2)


def _importo_scritto(cents):
    """L'importo come lo vuole lo standard: migliaia separate da uno spazio."""
    intero, resto = divmod(int(cents), 100)
    pezzi = []
    while intero >= 1000:
        intero, tre = divmod(intero, 1000)
        pezzi.append('%03d' % tre)
    pezzi.append(str(intero))
    return ' '.join(reversed(pezzi)) + '.%02d' % resto


def _angoli(c, x, y, larghezza, altezza):
    """I quattro angoli a squadra del campo da riempire a mano.

    Non e' un rettangolo intero: lo standard vuole gli angoli, e chi ha in mano
    una QR-fattura riconosce quel segno come «qui ci scrivi tu»."""
    from reportlab.lib.units import mm
    braccio = 3.0
    c.setLineWidth(0.75)
    for dx, dy in ((0, 0), (larghezza, 0), (0, altezza), (larghezza, altezza)):
        px, py = x + dx, y + dy
        verso_x = -1 if dx else 1
        verso_y = -1 if dy else 1
        c.line(px * mm, py * mm, (px + braccio * verso_x) * mm, py * mm)
        c.line(px * mm, py * mm, px * mm, (py + braccio * verso_y) * mm)


def _linee_di_taglio(c, largh_pagina):
    """Le pieghe: sopra la fascia e fra ricevuta e sezione pagamento."""
    from reportlab.lib.units import mm
    c.setLineWidth(0.5)
    c.setDash(2, 2)
    c.line(0, FASCIA_H * mm, largh_pagina, FASCIA_H * mm)
    c.line(RICEVUTA_W * mm, 0, RICEVUTA_W * mm, FASCIA_H * mm)
    c.setDash()
    _forbici(c, 8, FASCIA_H)
    _forbici(c, RICEVUTA_W, 30, verticale=True)


def _forbici(c, x, y, verticale=False):
    """Il segno delle forbici sulla piega, disegnato a mano.

    Il glifo ci sarebbe in ZapfDingbats, ma non tutti i lettori di PDF lo
    pescano dalla stessa casella e al posto delle forbici esce un quadrato nero.
    Su un documento che va in mano ai clienti un quadrato nero e' peggio di
    niente, quindi si disegna: due lame e due anelli, e sono forbici ovunque.
    """
    from reportlab.lib.units import mm
    c.saveState()
    c.translate(x * mm, y * mm)
    if verticale:
        c.rotate(-90)
    c.setLineWidth(0.5)
    c.setDash()
    lama, apertura = 3.4, 0.85
    c.line(-lama * mm, apertura * mm, 0.4 * mm, -apertura * mm)
    c.line(-lama * mm, -apertura * mm, 0.4 * mm, apertura * mm)
    for verso in (1, -1):
        c.circle(-(lama + 0.7) * mm, verso * (apertura + 0.55) * mm, 0.62 * mm)
    c.restoreState()


def disegna_su(c, largh_pagina, iban, creditore_nome, creditore_ind,
               importo_cents, riferimento, messaggio='', lingua='it',
               debitore_nome='', debitore_ind=None, moneta='CHF'):
    """Ricevuta e sezione pagamento, nella fascia alta 105 mm in fondo al foglio.

    Disegna e basta: il contenuto del codice lo prepara «dati_qr», che e' la
    parte dove un errore si paga caro e infatti e' quella provata di piu'.
    """
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    E = ETICHETTE.get((lingua or 'it')[:2], ETICHETTE['it'])
    testo_qr = dati_qr(iban, creditore_nome, creditore_ind, importo_cents,
                       riferimento, messaggio, moneta, debitore_nome, debitore_ind)
    conto = [_a_gruppi(normalizza_iban(iban)), creditore_nome,
             '%s %s' % (creditore_ind['via'], creditore_ind['civico']),
             '%s %s' % (creditore_ind['cap'], creditore_ind['localita'])]
    pagante = ([debitore_nome,
                '%s %s' % (debitore_ind['via'], debitore_ind['civico']),
                '%s %s' % (debitore_ind['cap'], debitore_ind['localita'])]
               if debitore_nome and debitore_ind else [])

    c.saveState()
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    _linee_di_taglio(c, largh_pagina)

    # lo stacco fra un blocco e il successivo: piu' largo di quello fra
    # l'etichetta e il suo contenuto, se no non si vede dove finisce una cosa e
    # ne comincia un'altra
    # una riga di testo piu' un respiro: meno di cosi' e l'etichetta sembra
    # l'ultima riga del blocco di sopra invece del titolo di quello di sotto
    STACCO_R, STACCO_P = 4.6, 5.7

    # ------------------------------------------------------- la ricevuta
    c.setFont('Helvetica-Bold', 11)
    c.drawString(MARGINE * mm, 96 * mm, E['ricevuta'])
    y = _blocco(c, MARGINE, 88, E['conto'], conto, 6, 8, 52)
    if riferimento:
        y = _blocco(c, MARGINE, y - STACCO_R, E['riferimento'],
                    [_a_gruppi(riferimento)], 6, 8, 52)
    if pagante:
        _blocco(c, MARGINE, y - STACCO_R, E['pagabile'], pagante, 6, 8, 52)
    else:
        c.setFont('Helvetica-Bold', 6)
        c.drawString(MARGINE * mm, (y - STACCO_R) * mm, E['pagabile_vuoto'])
        # il fondo del campo e' fisso: sotto ci sono valuta e importo, e un
        # riquadro che ci finisce sopra si stampa addosso alle cifre
        alto = y - STACCO_R - 2
        _angoli(c, MARGINE, 41, 52, alto - 41)

    c.setFont('Helvetica-Bold', 6)
    c.drawString(MARGINE * mm, 37 * mm, E['valuta'])
    c.drawString((MARGINE + 12) * mm, 37 * mm, E['importo'])
    c.setFont('Helvetica', 8)
    c.drawString(MARGINE * mm, 33 * mm, moneta)
    c.drawString((MARGINE + 12) * mm, 33 * mm, _importo_scritto(importo_cents))
    c.setFont('Helvetica-Bold', 6)
    c.drawRightString((RICEVUTA_W - MARGINE) * mm, 21 * mm, E['accettazione'])

    # ------------------------------------------- la sezione di pagamento
    sx = RICEVUTA_W + MARGINE                     # margine sinistro della sezione
    c.setFont('Helvetica-Bold', 11)
    c.drawString(sx * mm, 96 * mm, E['sezione'])
    disegna_qr(c, testo_qr, sx, 42)

    c.setFont('Helvetica-Bold', 8)
    c.drawString(sx * mm, 37 * mm, E['valuta'])
    c.drawString((sx + 20) * mm, 37 * mm, E['importo'])
    c.setFont('Helvetica', 10)
    c.drawString(sx * mm, 32 * mm, moneta)
    c.drawString((sx + 20) * mm, 32 * mm, _importo_scritto(importo_cents))

    # la colonna delle informazioni comincia DOPO i 5 mm di bianco che devono
    # restare a destra del codice: attaccarcela sopra e' l'errore che rende il
    # codice piu' difficile da leggere proprio ai lettori piu' scarsi
    dx = RICEVUTA_W + MARGINE + QR_COLONNA_W
    y = _blocco(c, dx, 88, E['conto'], conto, 8, 10, INFO_W)
    if riferimento:
        y = _blocco(c, dx, y - STACCO_P, E['riferimento'],
                    [_a_gruppi(riferimento)], 8, 10, INFO_W)
    if messaggio:
        y = _blocco(c, dx, y - STACCO_P, E['informazioni'], [messaggio],
                    8, 10, INFO_W)
    if pagante:
        _blocco(c, dx, y - STACCO_P, E['pagabile'], pagante, 8, 10, INFO_W)
    else:
        c.setFont('Helvetica-Bold', 8)
        c.drawString(dx * mm, (y - STACCO_P) * mm, E['pagabile_vuoto'])
        _angoli(c, dx, y - STACCO_P - 28, 65, 25)
    c.restoreState()


def _a_gruppi(riferimento):
    """Il riferimento a gruppi di quattro: si legge e si ricopia senza perdersi."""
    r = re.sub(r'\s+', '', riferimento or '')
    return ' '.join(r[i:i + 4] for i in range(0, len(r), 4))


# ------------------------------------------------- dalle impostazioni al foglio
# Perche' una QR-fattura esista servono tre cose, e se ne manca una NON si
# stampa un foglio a meta': si dice quale manca e come si sistema. Un bollettino
# con l'IBAN sbagliato o l'indirizzo storto e' peggio di nessun bollettino,
# perche' sembra buono.
SENZA_IBAN = ('Per la QR-fattura serve il tuo IBAN svizzero nelle impostazioni '
              '(21 caratteri, comincia per CH o LI).')
SENZA_NOME = 'Per la QR-fattura serve il nome della tua attività nelle impostazioni.'
SENZA_INDIRIZZO = (
    'Per la QR-fattura il tuo indirizzo deve essere leggibile a pezzi: via e '
    'numero sulla prima riga, CAP e località sulla seconda. Ora c\'è «{r1}» e '
    '«{r2}»: scrivi per esempio «Musterstrasse 45» e «8000 Musterstadt».')


def da_impostazioni(settings):
    """Il creditore ricavato dalle impostazioni. Ritorna (dati, motivo).

    Se «dati» e' None, «motivo» dice in italiano che cosa manca — una frase da
    far vedere a chi usa l'app, non un codice d'errore.
    """
    nome = (settings.get('business_name') or '').strip()
    iban = normalizza_iban(settings.get('business_iban'))
    r1 = (settings.get('business_addr1') or '').strip()
    r2 = (settings.get('business_addr2') or '').strip()
    if not re.match(r'^(CH|LI)[0-9]{19}$', iban):
        return None, SENZA_IBAN
    if not nome:
        return None, SENZA_NOME
    ind = indirizzo_strutturato(r1, r2)
    if not ind:
        return None, SENZA_INDIRIZZO.format(r1=r1 or '—', r2=r2 or '—')
    return {'iban': iban, 'nome': nome, 'indirizzo': ind}, ''
