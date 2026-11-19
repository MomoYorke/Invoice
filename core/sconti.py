# -*- coding: utf-8 -*-
"""
Lo sconto di un cliente: fisso (50 franchi) o in percentuale (10%).

Si scrive una volta nella scheda del cliente. Quando nella nuova fattura premi
il pulsante di un pacchetto per quel cliente, l'app aggiunge da sola una riga
a parte con il meno davanti. La riga non e' collegata a nessun servizio: toglie
soldi, non apre e non toglie sedute. Se una volta non va, la cancelli prima di
premere Crea.

Vale solo per i pacchetti (servizi «una volta» con sedute): su un abbonamento
uno sconto automatico ogni mese sarebbe una sorpresa.

Il valore si tiene in interi: il fisso in centesimi, la percentuale in
centesimi di punto (10% = 1000, 7,5% = 750). Niente float.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from .money import parse_amount, fmt_dash
from . import language as lng

TIPI = ('', 'percento', 'fisso')


def leggi(tipo, testo):
    """Quello che arriva dalla scheda: (tipo, valore, perche'). Con un perche'
    non vuoto il valore non va salvato."""
    tipo = tipo if tipo in TIPI else ''
    if not tipo:
        return '', 0, ''
    if tipo == 'fisso':
        cents = parse_amount(testo)
        if cents is None or cents == 0:
            return tipo, 0, "Scrivi l'importo dello sconto in franchi, per esempio 50."
        return tipo, abs(cents), ''
    t = str(testo or '').replace('%', '').replace(',', '.').strip().lstrip('-').strip()
    try:
        pct = Decimal(t)
    except (InvalidOperation, ValueError):
        pct = None
    if pct is None or not pct.is_finite() or pct <= 0 or pct > 100:
        return tipo, 0, 'Scrivi la percentuale dello sconto fra 1 e 100, per esempio 10.'
    return tipo, int((pct * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)), ''


def _campo(cliente, nome, predefinito=None):
    try:
        v = cliente[nome]
    except (KeyError, IndexError, TypeError):
        return predefinito
    return predefinito if v is None else v


def vale_per(servizio):
    """Solo i pacchetti: servizi che si pagano una volta e comprendono sedute."""
    return (servizio is not None and int(_campo(servizio, 'sedute', 0) or 0) > 0
            and not int(_campo(servizio, 'ogni_mese', 0) or 0))


def importo(cliente, servizio, prezzo_cents):
    """La riga di sconto in centesimi (negativa), o None se non c'e' sconto.
    Mai piu' grande del pacchetto: la fattura non va sotto zero."""
    tipo = _campo(cliente, 'sconto_tipo', '') or ''
    valore = int(_campo(cliente, 'sconto_valore', 0) or 0)
    if tipo not in ('fisso', 'percento') or valore <= 0 or not vale_per(servizio):
        return None
    prezzo = int(prezzo_cents or 0)
    if prezzo <= 0:
        return None
    if tipo == 'fisso':
        cents = valore
    else:
        # prezzo × percentuale, arrotondato al centesimo, mezzo per eccesso
        cents = (prezzo * valore + 5000) // 10000
    return -min(cents, prezzo)


def percentuale_testo(valore):
    """1000 -> «10%», 750 -> «7.5%»."""
    s = str(Decimal(int(valore)) / 100)
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s + '%'


def da_mostrare(valore, tipo, con_unita=False):
    """Il valore salvato come si riscrive nella scheda: «10» / «50.-»;
    con l'unita' per l'elenco: «10%» / «50.- CHF»."""
    if tipo == 'percento':
        testo = percentuale_testo(valore or 0)
        return testo if con_unita else testo[:-1]
    if tipo == 'fisso':
        testo = fmt_dash(int(valore or 0))
        return testo + ' CHF' if con_unita else testo
    return ''


def descrizione(cliente, lingua):
    """Il testo della riga: il nome scritto nella scheda (o «Sconto» nella
    lingua del cliente); per la percentuale, la percentuale in fondo."""
    nome = (_campo(cliente, 'sconto_nome', '') or '').strip() or lng.t_doc('Sconto', lingua)
    if _campo(cliente, 'sconto_tipo', '') == 'percento' and '%' not in nome:
        nome = '%s %s' % (nome, percentuale_testo(_campo(cliente, 'sconto_valore', 0)))
    return nome


def riga(cliente, servizio, prezzo_cents):
    """Quello che il pulsante della nuova fattura aggiunge sotto il pacchetto,
    o None. «percento» serve alla pagina per rifare il conto se cambi il prezzo."""
    cents = importo(cliente, servizio, prezzo_cents)
    if cents is None:
        return None
    pct = (int(_campo(cliente, 'sconto_valore', 0))
           if _campo(cliente, 'sconto_tipo', '') == 'percento' else None)
    return {'description': descrizione(cliente, _campo(cliente, 'lingua', 'en')),
            'qty': '1', 'unit': fmt_dash(cents), 'percento': pct}
