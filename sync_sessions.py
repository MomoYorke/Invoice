#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sincronizza le sessioni dal calendario nel registro crediti.

Il calendario si legge tramite il connettore Google Calendar di Claude, che non e'
accessibile a uno script Python. Quindi questo script lavora su un file di eventi:

  1) sync_sessions.py --finestra
     dice quale intervallo va letto dal calendario

  2) Claude legge il calendario e salva la risposta in eventi.json

  3) sync_sessions.py --eventi eventi.json [--prova]
     applica le regole, scarta i duplicati e aggiorna il registro

  sync_sessions.py --stato        mostra solo la vista crediti
"""
import os
import sys
import json
import argparse
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import sessions as S

CAL_EM_PT = 'cd4f38a7aee2123f09dde5cf8b69a9dc793403e4e7ae56d7931b8019e17e4eac@group.calendar.google.com'
CAL_ARCHIVIO = '707c70ca25fe3e1525c8a5a0480992fee1dcd67cc58b92222b6a31aeff71d98d@group.calendar.google.com'


def finestra(reg, oggi=None):
    """Intervallo da leggere: mai prima del 20.08.2026, mai oltre oggi (spec 5.1)."""
    oggi = oggi or datetime.date.today()
    ultima = S.ultima_data_registrata(reg)
    da = S.INIZIO_LETTURA
    if ultima:
        try:
            d = datetime.date.fromisoformat(ultima)
            da = max(da, d)   # ricomincio dall'ultima registrata: il dedup per ID fa il resto
        except ValueError:
            pass
    return da, oggi


def estrai_eventi(dati):
    """Accetta la risposta grezza dell'API ({'events': [...]}) o una lista."""
    if isinstance(dati, dict):
        dati = dati.get('events', dati.get('items', []))
    out = []
    for e in dati or []:
        start = e.get('start') or {}
        quando = start.get('dateTime') or start.get('date') or ''
        data = quando[:10]
        out.append({
            'id': e.get('id'),
            'titolo': e.get('summary', ''),
            'data': data,
            'stato_google': e.get('status', 'confirmed'),
        })
    return out


def sincronizza(reg, eventi, oggi=None, prova=False):
    """Applica le regole della sezione 5 e aggiorna il registro. Ritorna un rapporto."""
    oggi = oggi or datetime.date.today()
    da, a = finestra(reg, oggi)
    visti = S.id_evento_gia_presente(reg)

    rap = {'finestra': (da.isoformat(), a.isoformat()), 'letti': len(eventi),
           'aggiunte': [], 'duplicati': 0, 'fuori_finestra': 0, 'future': 0,
           'scartati': [], 'cancellati_google': 0, 'nuovi_pacchetti': [],
           'da_fatturare': []}

    # Prima passata: capisco quali clienti si allenano in ciascun giorno.
    # Serve per la regola della coppia (chi si allena in due paga un supplemento).
    clienti_per_giorno = {}
    for ev in eventi:
        k, _c, motivo = S.classifica(ev.get('titolo', ''))
        if k and ev.get('data'):
            clienti_per_giorno.setdefault(ev['data'], set()).add(k)

    for ev in sorted(eventi, key=lambda x: (x['data'], x['titolo'])):
        if not ev['data']:
            rap['scartati'].append((ev['titolo'], 'senza data'))
            continue
        try:
            d = datetime.date.fromisoformat(ev['data'])
        except ValueError:
            rap['scartati'].append((ev['titolo'], f"data illeggibile: {ev['data']}"))
            continue
        # spec 5.1: finestra di lettura
        if d < S.INIZIO_LETTURA:
            rap['fuori_finestra'] += 1
            continue
        if d > oggi:
            rap['future'] += 1          # appuntamenti previsti: non consumano crediti
            continue
        # eventi eliminati su Google: non sono sessioni svolte
        if ev.get('stato_google') == 'cancelled':
            rap['cancellati_google'] += 1
            continue
        # spec 5.5: deduplicazione sull'ID evento
        if ev['id'] and ev['id'] in visti:
            rap['duplicati'] += 1
            continue
        # spec 5.2: e' una sessione? di chi?
        chiave, cancellata, motivo = S.classifica(ev['titolo'])
        if chiave is None:
            rap['scartati'].append((ev['titolo'], motivo))
            continue
        if chiave in S.ex_clienti() and S.pacchetto_aperto_di(reg, chiave) is None:
            rap['scartati'].append((ev['titolo'], 'ex cliente senza pacchetto aperto'))
            continue
        # a chi va addebitato il credito (regola della coppia)
        addebito, nota = S.attribuisci(chiave, clienti_per_giorno.get(ev['data'], set()))
        if nota:
            rap.setdefault('addebiti_speciali', []).append((ev['data'], ev['titolo'], nota))
        if not prova:
            p, nuovo = S.aggiungi_sessione(reg, addebito, ev['data'], ev['titolo'],
                                           ev['id'], nota=nota, ora=ev.get('ora'))
            if nuovo:
                rap['nuovi_pacchetti'].append(p['id'])
        else:
            p, nuovo = S.pacchetto_aperto_di(reg, addebito), False
        if ev['id']:
            visti.add(ev['id'])
        rap['aggiunte'].append({
            'data': ev['data'], 'titolo': ev['titolo'],
            'cliente': S.nome_cliente(addebito), 'cancellata': cancellata,
            'nota': nota,
            'pacchetto': p['id'] if p else '(nuovo)',
        })

    for r in S.vista_crediti(reg):
        if r['terminati']:
            rap['da_fatturare'].append(r)
    return rap


def stampa_vista(reg):
    print('\n  CREDITI PER CLIENTE')
    print('  ' + '-' * 74)
    print(f"  {'Cliente':<12}{'Pacchetto':<10}{'Usati':>7}{'Rimasti':>9}  {'Dal':<12}Stato")
    print('  ' + '-' * 74)
    for r in S.vista_crediti(reg):
        segno = '!!' if r['terminati'] else ('! ' if r['in_esaurimento'] else '  ')
        print(f"  {r['cliente']:<12}{r['pacchetto']:<10}"
              f"{str(r['usati']) + '/' + str(r['crediti']):>7}{r['rimasti']:>9}  "
              f"{str(r['inizio'] or '—'):<12}{segno}{r['stato']}")
    print('  ' + '-' * 74)


def main():
    ap = argparse.ArgumentParser(description='Sincronizza sessioni e crediti')
    ap.add_argument('--eventi', help='file JSON con gli eventi del calendario')
    ap.add_argument('--stato', action='store_true', help='mostra solo i crediti')
    ap.add_argument('--finestra', action='store_true', help='mostra intervallo da leggere')
    ap.add_argument('--prova', action='store_true', help='simula senza salvare')
    ap.add_argument('--oggi', help='forza la data odierna (per i test)')
    a = ap.parse_args()

    oggi = datetime.date.fromisoformat(a.oggi) if a.oggi else datetime.date.today()
    reg = S.carica()

    if a.finestra or (not a.eventi and not a.stato):
        da, fino = finestra(reg, oggi)
        print(f"\n  Calendario da leggere : quello delle sessioni")
        print(f"  ID                    : {CAL_EM_PT}")
        print(f"  Intervallo            : {da} -> {fino}")
        if da > fino:
            print(f"\n  Nulla da leggere: la finestra parte dal {S.INIZIO_LETTURA} "
                  f"e oggi e' il {oggi}.")
        print(f"\n  (il calendario storico non va MAI letto)")
        if not a.eventi:
            stampa_vista(reg)
            return

    if a.stato:
        stampa_vista(reg)
        return

    with open(a.eventi, encoding='utf-8') as f:
        eventi = estrai_eventi(json.load(f))
    rap = sincronizza(reg, eventi, oggi, prova=a.prova)

    print(f"\n  Finestra: {rap['finestra'][0]} -> {rap['finestra'][1]}")
    print(f"  Eventi letti: {rap['letti']}")
    print(f"  Nuove sessioni: {len(rap['aggiunte'])}")
    for s in rap['aggiunte']:
        c = ' (CANCELLATA - consuma comunque)' if s['cancellata'] else ''
        print(f"    + {s['data']}  {s['cliente']:<10} {s['pacchetto']:<8} {s['titolo']!r}{c}")
    print(f"  Gia' registrate (duplicati scartati): {rap['duplicati']}")
    print(f"  Prima della finestra: {rap['fuori_finestra']}   Future: {rap['future']}"
          f"   Eliminate su Google: {rap['cancellati_google']}")
    if rap['scartati']:
        print(f"  Non conteggiati ({len(rap['scartati'])}):")
        for t, m in rap['scartati'][:15]:
            print(f"    - {t!r}: {m}")
    if rap.get('addebiti_speciali'):
        print("  Attribuzioni particolari:")
        for data, tit, nota in rap['addebiti_speciali']:
            print(f"    ! {data} {tit!r}: {nota}")
    if rap['nuovi_pacchetti']:
        print(f"  Nuovi pacchetti aperti: {', '.join(rap['nuovi_pacchetti'])}")

    if a.prova:
        print("\n  PROVA: nulla e' stato salvato.")
    else:
        S.salva(reg)
        print(f"\n  Registro aggiornato: {S.REGISTRY}")

    stampa_vista(reg)
    if rap['da_fatturare']:
        print("\n  CREDITI TERMINATI (serve la prossima fattura):")
        for r in rap['da_fatturare']:
            print(f"    - {r['cliente']}: pacchetto {r['pacchetto']}")


if __name__ == '__main__':
    main()
