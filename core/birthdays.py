# -*- coding: utf-8 -*-
"""I compleanni dei clienti: come si scrivono, e chi li compie fra poco.

Un compleanno si scrive come lo scrive la gente, «15.03», e l'anno solo se lo
si sa: quasi nessuno lo chiede a un cliente, e un campo che lo pretende resta
vuoto. Nel database va in una forma sola, che si confronta senza sorprese:
«03-15» senza l'anno, «1986-03-15» con.
"""
import datetime
import re

# Da quanti giorni prima un compleanno compare sulla Dashboard
GIORNI_PRIMA = 7
ANNO_MINIMO = 1900

# Le frasi per chi scrive un compleanno che non si capisce. Sono costanti
# COMPLEANNO_*: la prova della lingua le raccoglie da sola.
COMPLEANNO_NON_CAPITO = ('Il compleanno non si capisce: scrivilo come giorno e mese, '
                         'per esempio 15.03, e aggiungi l’anno solo se lo sai.')
COMPLEANNO_GIORNO_INESISTENTE = 'Quel giorno nel calendario non c’è: controlla giorno e mese.'
COMPLEANNO_ANNO_STRANO = 'L’anno di nascita non torna: controllalo, oppure lascialo fuori.'

_GG_MM = re.compile(r'^(\d{1,2})[./\-](\d{1,2})(?:[./\-](\d{4}))?$')
_ISO = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')
_NEL_DATABASE = re.compile(r'^(?:(\d{4})-)?(\d{2})-(\d{2})$')


def leggi_compleanno(testo, oggi=None):
    """Da come l'ha scritto qualcuno a come sta nel database. Ritorna (valore, motivo).

    Vuoto va bene: e' la risposta giusta per chi non lo sa. Un giorno che non
    esiste — il 31 febbraio, il 29 di un anno che non e' bisestile — non si
    aggiusta in silenzio: si dice, perche' un giorno sbagliato sulla Dashboard
    e' un augurio fatto il giorno sbagliato.
    """
    t = (testo or '').strip()
    if not t:
        return '', ''
    oggi = oggi or datetime.date.today()
    m = _ISO.match(t)
    if m:
        anno, mese, giorno = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = _GG_MM.match(t.replace(' ', ''))
        if not m:
            return None, COMPLEANNO_NON_CAPITO
        giorno, mese = int(m.group(1)), int(m.group(2))
        anno = int(m.group(3)) if m.group(3) else None
    if anno is not None and not ANNO_MINIMO <= anno <= oggi.year:
        return None, COMPLEANNO_ANNO_STRANO
    try:
        # senza l'anno si prova su un anno bisestile, dove il 29 febbraio c'e'
        datetime.date(anno or 2000, mese, giorno)
    except ValueError:
        return None, COMPLEANNO_GIORNO_INESISTENTE
    if anno is None:
        return '%02d-%02d' % (mese, giorno), ''
    return '%04d-%02d-%02d' % (anno, mese, giorno), ''


def _parti(valore):
    """(anno o None, mese, giorno) da come sta nel database; None se non si legge."""
    m = _NEL_DATABASE.match((valore or '').strip())
    if not m:
        return None
    return (int(m.group(1)) if m.group(1) else None), int(m.group(2)), int(m.group(3))


def da_mostrare(valore):
    """Come si rilegge sulla scheda del cliente: «15.03», oppure «15.03.1986»."""
    p = _parti(valore)
    if not p:
        return ''
    anno, mese, giorno = p
    return '%02d.%02d' % (giorno, mese) + ('.%04d' % anno if anno else '')


def _nell_anno(anno, mese, giorno):
    """Il compleanno in quell'anno. Il 29 febbraio, dove non c'e', cade il 28."""
    try:
        return datetime.date(anno, mese, giorno)
    except ValueError:
        return datetime.date(anno, 2, 28)


def in_arrivo(clienti, oggi=None, giorni=GIORNI_PRIMA):
    """Chi compie gli anni da oggi a «giorni» giorni, dal piu' vicino.

    Il prossimo compleanno si cerca quest'anno e, se e' gia' passato, l'anno
    dopo: e' cosi' che il 28 dicembre il 2 gennaio e' fra cinque giorni, e che
    chi e' nato il 2 gennaio compie gli anni dell'anno nuovo, non di quello
    che finisce. Gli archiviati restano fuori: chi non e' piu' tuo cliente non
    aspetta gli auguri dal tuo gestionale.
    """
    oggi = oggi or datetime.date.today()
    fuori = []
    for c in clienti:
        if c['archived']:
            continue
        p = _parti(c['compleanno'])
        if not p:
            continue
        nato, mese, giorno = p
        quando = _nell_anno(oggi.year, mese, giorno)
        if quando < oggi:
            quando = _nell_anno(oggi.year + 1, mese, giorno)
        tra = (quando - oggi).days
        if tra > giorni:
            continue
        fuori.append({'id': c['id'], 'nome': c['name'], 'quando': quando, 'tra': tra,
                      'anni': quando.year - nato if nato else None})
    fuori.sort(key=lambda x: (x['tra'], x['nome'].lower()))
    return fuori
