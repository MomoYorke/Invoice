# -*- coding: utf-8 -*-
"""
I servizi che proponi in fattura, e le descrizioni che si ripetono ogni mese.

Due cose distinte:

- L'ELENCO dei servizi: i pulsanti sopra le righe della fattura. Si scrive in
  Impostazioni. Chi non l'ha ancora scritto se lo vede proporre dalle proprie
  fatture passate: le descrizioni che ha usato di piu'.

- Il PERIODO degli abbonamenti: una descrizione come «Abbonamento mensile
  01.07.26 - 31.07.26» il mese dopo va rifatta identica con le date spostate
  avanti. L'app la ritrova e le sposta da sola, qualunque sia il testo attorno
  alle date: non deve sapere come chiami il tuo abbonamento.
"""
import re
import datetime

from dateutil.relativedelta import relativedelta

RX_DATA = re.compile(r'(\d{1,2})([.\-/])(\d{1,2})[.\-/](\d{2,4})')
QUANTI_PROPOSTI = 6


def elenco(con, settings):
    """I servizi da proporre. Prima quelli scritti a mano; se non ce ne sono,
    quelli piu' usati nelle fatture."""
    scritti = [r.strip() for r in (settings.get('servizi') or '').splitlines() if r.strip()]
    if scritti:
        return scritti[:12]
    return piu_usati(con)


def piu_usati(con, quanti=QUANTI_PROPOSTI):
    """Le descrizioni piu' ricorrenti, ripulite dal periodo.

    Le date vanno tolte prima di contare, altrimenti ogni mese e' una
    descrizione diversa e non si ripete mai niente."""
    conteggio = {}
    for r in con.execute(
            'SELECT i.description d FROM items i JOIN invoices f ON f.id = i.invoice_id '
            'WHERE f.deleted_at IS NULL AND i.description <> "" '
            'ORDER BY COALESCE(f.number, 0) DESC LIMIT 400'):
        testo = senza_date(r['d'])
        if len(testo) < 4:
            continue
        voce = conteggio.setdefault(testo, {'n': 0, 'testo': testo})
        voce['n'] += 1
    ordinati = sorted(conteggio.values(), key=lambda v: -v['n'])
    return [v['testo'] for v in ordinati[:quanti] if v['n'] > 1]


def senza_date(descrizione):
    """La descrizione senza il periodo: «Abbo 01.07.26 - 31.07.26» -> «Abbo»."""
    testo = RX_DATA.sub('', descrizione or '')
    testo = re.sub(r'\s+', ' ', testo)
    return testo.strip(' –—-,;:')


def stesso_servizio(a, b):
    """True se due descrizioni sono lo stesso servizio, periodo a parte."""
    x, y = senza_date(a).lower(), senza_date(b).lower()
    if not x or not y:
        return False
    return x == y or x.startswith(y) or y.startswith(x)


def avanza_periodo(descrizione, mesi=1):
    """Sposta avanti di un mese le due date della descrizione, lasciando
    intatto tutto il resto: il testo attorno alle date non lo tocchiamo,
    perche' e' quello che ha scritto chi usa l'app.

    Ritorna None se le date non sono due o non sono date vere."""
    trovate = list(RX_DATA.finditer(descrizione or ''))
    if len(trovate) < 2:
        return None
    date = []
    for m in trovate[:2]:
        giorno, mese, anno = int(m.group(1)), int(m.group(3)), int(m.group(4))
        if anno < 100:
            anno += 2000
        try:
            date.append(datetime.date(anno, mese, giorno))
        except ValueError:
            return None
    fuori, ultimo = '', 0
    for m, d in zip(trovate[:2], date):
        nuova = d + relativedelta(months=mesi)
        sep = m.group(2)
        anno = nuova.strftime('%y') if len(m.group(4)) == 2 else nuova.strftime('%Y')
        fuori += descrizione[ultimo:m.start()] + f'{nuova.day:02d}{sep}{nuova.month:02d}{sep}{anno}'
        ultimo = m.end()
    return fuori + descrizione[ultimo:]


# --- Riconoscere il servizio di una riga di fattura -------------------------
#
# Prima queste regole stavano scritte nel programma, ed erano i tre servizi di
# chi l'app l'ha scritta per se'. Adesso stanno nelle Impostazioni: due elenchi,
# uno per gli abbonamenti e uno per i pacchetti, una riga per servizio.
#
#     Nome del servizio = parola, parola, parola
#
# Le parole sono quelle che compaiono nelle righe della fattura. Senza «=», il
# nome fa anche da parola. L'ordine conta: vince la prima regola che riconosce,
# e gli abbonamenti si provano prima perche' le loro parole sono piu' precise.

MODELLI_SERVIZIO = (('servizi_abbonamento', 'coaching'),
                    ('servizi_pacchetto', 'pt'))


def _regola(riga):
    """«Nome = a, b» -> ('Nome', ['a', 'b']). None se la riga non dice niente."""
    nome, _uguale, parole = (riga or '').partition('=')
    nome = nome.strip()
    if not nome:
        return None
    chiavi = [p.strip().lower() for p in parole.split(',') if p.strip()]
    return (nome, chiavi or [nome.lower()])


def regole(settings):
    """[(nome, modello, parole)] nell'ordine in cui vanno provate."""
    fuori = []
    for chiave, modello in MODELLI_SERVIZIO:
        for riga in ((settings or {}).get(chiave) or '').splitlines():
            r = _regola(riga)
            if r:
                fuori.append((r[0], modello, r[1]))
    return fuori


def riconosci(descrizione, settings):
    """(nome, modello) della prima regola che riconosce la riga.

    (None, None) se non la riconosce nessuna: e' un risultato buono quanto gli
    altri. Chi usa l'app vende quello che vende, e inventargli un servizio che
    non ha e' peggio che non nominarlo."""
    testo = (descrizione or '').lower()
    if not testo:
        return (None, None)
    for nome, modello, parole in regole(settings):
        if any(p in testo for p in parole):
            return (nome, modello)
    return (None, None)
