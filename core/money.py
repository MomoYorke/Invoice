# -*- coding: utf-8 -*-
"""
Gestione importi in CHF, SEMPRE in centesimi interi (int).
Niente float nei calcoli: zero errori di arrotondamento.
"""
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def parse_amount(s):
    """Converte un importo scritto in qualsiasi formato svizzero/italiano in centesimi (int).

    Accetta: '110.-', '110.–', '150,00 CHF', "1'800.00", '1.800,00CHF',
             '1800', '1800.5', 'CHF 110', '110 CHF', '0.-'
    Ritorna None se non interpretabile.
    """
    if s is None:
        return None
    if isinstance(s, (int, float, Decimal)):
        return _to_cents(Decimal(str(s)))
    t = str(s).strip().upper()
    if not t:
        return None
    t = t.replace('CHF', '').replace('FR.', '').replace('SFR', '')
    # trattini finali svizzeri: "110.-" / "110.–" / "110.—"
    t = re.sub(r'\.\s*[-–—]\s*$', '', t.strip())
    t = t.replace('–', '').replace('—', '')
    t = t.replace("'", '').replace('’', '').replace(' ', '').replace(' ', '')
    t = t.strip('-').strip()
    if not re.search(r'\d', t):
        return None
    if ',' in t and '.' in t:
        # entrambi presenti: l'ultimo è il separatore decimale
        if t.rfind(',') > t.rfind('.'):
            t = t.replace('.', '').replace(',', '.')   # 1.800,00
        else:
            t = t.replace(',', '')                     # 1,800.00
    elif ',' in t:
        # solo virgola: decimale se seguita da 1-2 cifre finali, altrimenti migliaia
        if re.search(r',\d{1,2}$', t):
            t = t.replace(',', '.')
        else:
            t = t.replace(',', '')
    elif t.count('.') > 1:
        # piu' punti: tutti tranne l'ultimo sono migliaia
        parts = t.split('.')
        t = ''.join(parts[:-1]) + '.' + parts[-1]
    # se un solo punto seguito da 3 cifre esatte -> separatore migliaia (es. 1.800)
    if re.fullmatch(r'\d{1,3}\.\d{3}', t):
        t = t.replace('.', '')
    t = re.sub(r'[^0-9.]', '', t)
    if not t or t == '.':
        return None
    try:
        return _to_cents(Decimal(t))
    except (InvalidOperation, ValueError):
        return None


def _to_cents(d):
    return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def fmt_chf(cents, suffix=True):
    """1'800.00 CHF (formato svizzero, apostrofo per migliaia)."""
    if cents is None:
        return '—'
    sign = '-' if cents < 0 else ''
    cents = abs(int(cents))
    fr, ct = divmod(cents, 100)
    s = f"{fr:,}".replace(',', "'")
    out = f"{sign}{s}.{ct:02d}"
    return out + ' CHF' if suffix else out


def fmt_dash(cents):
    """Formato fattura: 1'800.- se intero, altrimenti 1'800.50"""
    if cents is None:
        return ''
    fr, ct = divmod(abs(int(cents)), 100)
    sign = '-' if cents < 0 else ''
    s = f"{fr:,}".replace(',', "'")
    return f"{sign}{s}.-" if ct == 0 else f"{sign}{s}.{ct:02d}"


def parse_qty(s):
    """Quantita': int se possibile, altrimenti Decimal a 2 decimali; default 1."""
    if s is None:
        return 1
    t = str(s).strip().replace(',', '.')
    if not t:
        return 1
    try:
        d = Decimal(t)
    except InvalidOperation:
        return 1
    if d == d.to_integral_value():
        return int(d)
    return d


def line_total(qty, unit_cents):
    """Totale riga = qty * unit, arrotondato al centesimo (HALF_UP)."""
    if unit_cents is None:
        return None
    q = qty if isinstance(qty, (int, Decimal)) else parse_qty(qty)
    d = Decimal(q) * Decimal(int(unit_cents))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
