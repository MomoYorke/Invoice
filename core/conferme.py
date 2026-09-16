# -*- coding: utf-8 -*-
"""
Confronta il registro delle sedute con quello che il calendario dice ADESSO.

Perche' esiste: la lettura del calendario e' sempre stata solo in aggiunta.
Se una seduta viene disdetta e l'evento sparisce da Google, il credito resta
consumato. Qui si guarda anche il verso opposto — cosa c'era e non c'e' piu' —
ma senza mai cancellare niente: si chiede.

Perche' solo 14 giorni: quando una serie ripetuta finisce, Google porta via
anche le sue occorrenze passate. Oltre la finestra il calendario non e' una
fonte attendibile sul passato, e credergli vorrebbe dire cancellare sedute
vere (vedi core/schedule.py).

Questo modulo non scrive: decide chi lo chiama.
"""
import datetime

from . import sessions as S

FINESTRA_GIORNI = 14
SOGLIA_GRUPPO = 3          # da qui in su le domande si fanno in blocco


def finestra(oggi, giorni=FINESTRA_GIORNI):
    """L'intervallo in cui il calendario si puo' credere anche sul passato."""
    return (oggi - datetime.timedelta(days=giorni), oggi)


def _uid(event_id):
    return (event_id or '').split('::')[0]


def _aperto(gruppo, oggi):
    """Un gruppo ancora in ballo: pacchetto non chiuso e non fatturato, oppure
    mese di abbonamento che comprende oggi (un mese porta sempre il numero
    della fattura che lo ha aperto: li' non vuol dire «conto chiuso»)."""
    if gruppo.get('dal'):
        return gruppo['dal'] <= oggi <= gruppo.get('al', gruppo['dal'])
    return not gruppo.get('fine') and not gruppo.get('fattura_numero')


def _gruppi(reg):
    return list(reg.get('pacchetti') or []) + list(reg.get('mensili') or [])


def candidate(reg, oggi, giorni=FINESTRA_GIORNI):
    """(gruppo, seduta) per le sedute che il confronto puo' guardare."""
    da, a = finestra(oggi, giorni)
    gia_in_lista = {v.get('event_id') for v in reg.get('da_confermare') or []}
    fuori = []
    for gruppo in _gruppi(reg):
        if not _aperto(gruppo, oggi.isoformat()):
            continue
        for s in gruppo.get('sessioni') or []:
            if not s.get('event_id') or s.get('non_fatta') or s.get('confermata'):
                continue
            if s['event_id'] in gia_in_lista:
                continue
            if not (da.isoformat() <= (s.get('data') or '') <= a.isoformat()):
                continue
            fuori.append((gruppo, s))
    return fuori


def confronta(reg, voci, oggi, giorni=FINESTRA_GIORNI):
    """Chi e' stata spostata e chi e' sparita, senza toccare il registro."""
    presenti = {v['id']: v for v in voci or []}
    per_uid = {}
    for v in voci or []:
        per_uid.setdefault(_uid(v['id']), []).append(v)
    registrate = {s.get('event_id') for gruppo in _gruppi(reg)
                  for s in gruppo.get('sessioni') or []}

    spostate, sparite = [], []
    for gruppo, s in candidate(reg, oggi, giorni):
        if s['event_id'] in presenti:
            continue
        uid = _uid(s['event_id'])
        altrove = [v for v in per_uid.get(uid, []) if v['id'] not in registrate]
        if altrove:
            # la piu' vicina al giorno di prima: se ne ha spostate due, la sua
            # e' quella che si e' mossa di meno
            vicina = min(altrove, key=lambda v: abs(
                (datetime.date.fromisoformat(v['data'])
                 - datetime.date.fromisoformat(s['data'])).days))
            spostate.append({'gruppo': gruppo, 'seduta': s, 'event_id': s['event_id'],
                             'data_nuova': vicina['data'], 'id_nuovo': vicina['id']})
            registrate.add(vicina['id'])
            continue
        sparite.append({'gruppo': gruppo, 'seduta': s, 'event_id': s['event_id']})
    return {'spostate': spostate, 'sparite': sparite}
