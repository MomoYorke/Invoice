# -*- coding: utf-8 -*-
"""
Legge un calendario Google dal suo indirizzo segreto in formato iCal.

Perche' l'iCal e non l'API di Google: l'indirizzo segreto si incolla una volta
in Impostazioni e basta. Nessun progetto Google Cloud, nessun OAuth, nessuna
password da custodire.

Il prezzo da pagare e' che l'iCal descrive una serie ricorrente come UNA sola
voce piu' le sue eccezioni, mentre l'API dava un evento gia' pronto per ogni
ripetizione. Qui le ripetizioni si espandono a mano con dateutil (che l'app ha
gia') e l'identificativo per non contare due volte la stessa sessione diventa
UID + data.

leggi() restituisce esattamente la forma che sync_sessions.py si aspetta:
    {'id', 'titolo', 'data', 'stato_google'}
cosi' tutte le regole gia' collaudate — finestra, deduplicazione, sessioni
future, regola della coppia — restano dove sono.
"""
import re
import datetime
import urllib.request

from dateutil.rrule import rrulestr

try:                                  # ora locale: serve per i DTSTART in UTC
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo('Europe/Zurich')
except Exception:                     # pragma: no cover - macOS ce l'ha sempre
    FUSO = None

TIMEOUT = 20
MAX_BYTE = 8 * 1024 * 1024      # un calendario di sessioni non pesa piu' di cosi'


def scarica(url, timeout=TIMEOUT):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read(MAX_BYTE).decode('utf-8', errors='replace')


def nome(testo):
    """Come si chiama il calendario, secondo il calendario stesso.

    Google mette il nome in cima al file iCal (X-WR-CALNAME). Chiederlo a lui
    e' meglio che scriverlo nel programma: cosi' ognuno vede il nome del
    proprio calendario senza doverlo configurare, e nel codice non resta il
    nome del calendario di nessuno.
    """
    for riga in _srotola(testo):
        if riga.upper().startswith('X-WR-CALNAME'):
            return _testo(_valore(riga)[1])
    return ''


def _srotola(testo):
    """Nell'iCal una riga lunga continua sulla successiva se inizia con spazio."""
    righe = []
    for riga in testo.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if riga[:1] in (' ', '\t') and righe:
            righe[-1] += riga[1:]
        else:
            righe.append(riga)
    return righe


def _valore(riga):
    """'DTSTART;TZID=Europe/Zurich:20260820T093000' -> (parametri, valore)"""
    etichetta, _, resto = riga.partition(':')
    return etichetta, resto


def _testo(v):
    return (v.replace('\\n', ' ').replace('\\,', ',')
             .replace('\;', ';').replace('\\\\', '\\').strip())


def _data(v):
    """Prende solo la data: l'ora non serve, i crediti si contano a giornate."""
    m = re.search(r'(\d{4})(\d{2})(\d{2})', v or '')
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _ora(v):
    """L'ora di inizio, in ora locale svizzera, come 'HH:MM'.

    Google scrive DTSTART in due modi: con il fuso esplicito
    (DTSTART;TZID=Europe/Zurich:20260414T073000) e allora l'ora e' gia' quella
    dell'orologio, oppure in UTC (...T053000Z) e allora va riportata indietro.
    Un evento di sola giornata non ha ora: ritorna None.
    """
    m = re.search(r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(Z?)', v or '')
    if not m:
        return None
    aa, mm, gg, h, mi, _s, zulu = m.groups()
    try:
        t = datetime.datetime(int(aa), int(mm), int(gg), int(h), int(mi))
    except ValueError:
        return None
    if zulu == 'Z' and FUSO is not None:
        t = t.replace(tzinfo=datetime.timezone.utc).astimezone(FUSO)
    return t.strftime('%H:%M')


def _eventi_grezzi(testo):
    """Spezza il file nei suoi VEVENT, ognuno come dizionario di campi."""
    eventi, corrente = [], None
    for riga in _srotola(testo):
        if riga.startswith('BEGIN:VEVENT'):
            corrente = {'exdate': []}
        elif riga.startswith('END:VEVENT'):
            if corrente is not None:
                eventi.append(corrente)
            corrente = None
        elif corrente is not None:
            nome, valore = _valore(riga)
            capo = nome.split(';')[0].upper()
            if capo == 'EXDATE':
                corrente['exdate'].extend(d for d in (_data(x) for x in valore.split(',')) if d)
            elif capo in ('UID', 'SUMMARY', 'DTSTART', 'RRULE', 'STATUS',
                          'RECURRENCE-ID'):
                corrente[capo.lower().replace('-', '_')] = valore
    return eventi


def _ripetizioni(ev, da, a):
    """Le date in cui questo evento cade dentro la finestra."""
    inizio = _data(ev.get('dtstart'))
    if not inizio:
        return []
    if not ev.get('rrule'):
        return [inizio] if da <= inizio <= a else []
    # dateutil lavora su datetime: uso mezzogiorno per stare lontano dai
    # cambi d'ora, tanto la parte che conta e' il giorno
    partenza = datetime.datetime.combine(inizio, datetime.time(12))
    try:
        regola = rrulestr(ev['rrule'], dtstart=partenza)
    except (ValueError, TypeError):
        return [inizio] if da <= inizio <= a else []
    date = []
    for d in regola.between(datetime.datetime.combine(da, datetime.time(0)),
                            datetime.datetime.combine(a, datetime.time(23, 59)),
                            inc=True):
        date.append(d.date())
    return date


def leggi(url_o_testo, da, a, e_testo=False):
    """Gli eventi del calendario fra due date, ripetizioni comprese.

    Ogni voce: {'id': 'UID::AAAA-MM-GG', 'titolo', 'data', 'ora', 'stato_google'}.
    """
    testo = url_o_testo if e_testo else scarica(url_o_testo)
    grezzi = _eventi_grezzi(testo)

    # le eccezioni (una singola ripetizione spostata o cancellata) hanno
    # RECURRENCE-ID e vincono sulla serie
    eccezioni = {}
    serie = []
    for ev in grezzi:
        if ev.get('recurrence_id'):
            d = _data(ev['recurrence_id'])
            if d:
                eccezioni[(ev.get('uid', ''), d)] = ev
        else:
            serie.append(ev)

    fuori = {}
    for (uid, d), ev in eccezioni.items():
        nuova = _data(ev.get('dtstart')) or d
        if nuova != d:
            fuori[(uid, d)] = True      # spostata altrove: nel giorno originale non c'e'

    voci = {}

    def aggiungi(uid, giorno, titolo, stato, ora=None):
        if not (da <= giorno <= a):
            return
        voci[(uid, giorno)] = {
            'id': f'{uid}::{giorno.isoformat()}',
            'titolo': titolo,
            'data': giorno.isoformat(),
            'ora': ora,
            'stato_google': stato,
        }

    for ev in serie:
        uid = ev.get('uid', '')
        titolo = _testo(ev.get('summary', ''))
        stato = (ev.get('status') or 'CONFIRMED').strip().lower()
        saltate = set(ev['exdate'])
        # in una serie l'ora e' quella del primo evento e vale per tutte le
        # ripetizioni; le singole spostate hanno la propria e passano di sotto
        ora = _ora(ev.get('dtstart'))
        for giorno in _ripetizioni(ev, da, a):
            if giorno in saltate or fuori.get((uid, giorno)):
                continue
            chiave = (uid, giorno)
            if chiave in eccezioni:
                continue                # la tratta il ciclo dopo
            aggiungi(uid, giorno, titolo, 'cancelled' if stato == 'cancelled' else 'confirmed',
                     ora)

    for (uid, originale), ev in eccezioni.items():
        giorno = _data(ev.get('dtstart')) or originale
        stato = (ev.get('status') or 'CONFIRMED').strip().lower()
        aggiungi(uid, giorno, _testo(ev.get('summary', '')),
                 'cancelled' if stato == 'cancelled' else 'confirmed',
                 _ora(ev.get('dtstart')))

    return sorted(voci.values(), key=lambda v: (v['data'], v['titolo']))
