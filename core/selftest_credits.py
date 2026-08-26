# -*- coding: utf-8 -*-
"""
Verifica della logica crediti contro lo storico congelato (SPEC-crediti.md sez. 7).
Se un pacchetto chiuso non torna, e' sbagliata la logica, non i dati.

I valori attesi non stanno qui dentro: stanno in data/crediti-attesi.json,
insieme allo storico a cui si riferiscono. Sono i tuoi clienti e i tuoi
conteggi, e non hanno senso per nessun altro — per questo restano coi dati e
non col programma. Chi installa l'app non ha ne' l'uno ne' l'altro, e questi
controlli semplicemente non si eseguono.

Il file ha questa forma:
    {"chiusi":  {"XXX-01": ["inizio", "fine", crediti]},
     "aperti":  {"Nome": [usati, crediti, rimasti, "stato"]},
     "titoli":  [["titolo di calendario", "chiave" o null, cancellata]],
     "cancellata": {"pacchetto": "XXX-01", "quante": 1, "sessioni": 11},
     "esclusi": 32}
"""
import json
import os

from . import sessions as S

ATTESI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'data', 'crediti-attesi.json')


def _attesi():
    with open(ATTESI, encoding='utf-8') as f:
        return json.load(f)


def applicabile():
    """Questi controlli confrontano la logica con uno storico congelato.

    Un'app appena installata quello storico non ce l'ha, e non e' un errore:
    non c'e' niente da verificare finche' non ci sono ne' i clienti a crediti,
    ne' il registro di riferimento, ne' i conteggi attesi."""
    return os.path.exists(S.SEED) and os.path.exists(ATTESI) and bool(S.clienti())


def run_all(reg=None):
    # I test di riferimento girano sul SEED: e' il dato validato contro le fatture
    # e non cambia mai. Il registro vivo evolve (nuove sessioni, collegamenti
    # fattura) e non e' quindi la base giusta per una verifica di regressione.
    if not applicabile():
        return True, []
    atteso = _attesi()
    if reg is None:
        with open(S.SEED, encoding='utf-8') as f:
            reg = json.load(f)
    r = []

    def chk(cat, desc, got, exp):
        ok = got == exp
        r.append((cat, desc, ok, '' if ok else f'ottenuto {got!r}, atteso {exp!r}'))

    # --- classificazione titoli ---
    for titolo, cliente_atteso, canc_atteso in atteso['titoli']:
        chiave, canc, _motivo = S.classifica(titolo)
        chk('Riconoscimento titoli', f'{titolo!r} -> {cliente_atteso}', chiave, cliente_atteso)
        if cliente_atteso:
            chk('Cancellazioni', f'{titolo!r} cancellata={canc_atteso}', canc, canc_atteso)

    # --- ogni titolo dello storico deve essere riconosciuto come sessione valida ---
    per_pacchetto = {}
    for p in reg['pacchetti']:
        non_riconosciuti = []
        for s in p.get('sessioni', []):
            chiave, _c, motivo = S.classifica(s['titolo'])
            if chiave is None:
                non_riconosciuti.append((s['titolo'], motivo))
        per_pacchetto[p['id']] = non_riconosciuti
        chk('Storico riconosciuto', f"{p['id']}: tutti i titoli sono sessioni valide",
            non_riconosciuti, [])

    # --- pacchetti chiusi: il conteggio deve tornare esatto (spec 7) ---
    idx = {p['id']: p for p in reg['pacchetti']}
    for pid, (inizio, fine, crediti) in atteso['chiusi'].items():
        p = idx.get(pid)
        if not p:
            chk('Pacchetti chiusi', f'{pid} presente nel registro', False, True)
            continue
        chk('Pacchetti chiusi', f'{pid} inizio {inizio}', p['inizio'], inizio)
        chk('Pacchetti chiusi', f'{pid} fine {fine}', p.get('fine'), fine)
        chk('Pacchetti chiusi', f'{pid} crediti {crediti}', p['crediti'], crediti)
        chk('Pacchetti chiusi', f'{pid} sessioni conteggiate = {crediti}',
            len(p.get('sessioni', [])), crediti)
        chk('Pacchetti chiusi', f'{pid} residuo 0', p['crediti'] - len(p.get('sessioni', [])), 0)

    # --- stato dei pacchetti aperti al 19.08.2026 (spec 7) ---
    vista = {v['cliente']: v for v in S.vista_crediti(reg)}
    for cliente, (usati, crediti, rimasti, stato) in atteso['aperti'].items():
        v = vista.get(cliente)
        if not v:
            chk('Stato attuale', f'{cliente} presente nella vista', False, True)
            continue
        chk('Stato attuale', f'{cliente}: {usati}/{crediti} usati', (v['usati'], v['crediti']), (usati, crediti))
        chk('Stato attuale', f'{cliente}: {rimasti} rimasti', v['rimasti'], rimasti)
        chk('Stato attuale', f'{cliente}: stato "{stato}"', v['stato'], stato)

    # --- la sessione cancellata consuma il credito (spec 5.3) ---
    c = atteso.get('cancellata') or {}
    p = idx.get(c.get('pacchetto'))
    if p:
        canc = [x for x in p['sessioni'] if x.get('cancellata')]
        chk('Cancellazioni', f"{c['pacchetto']} contiene la sessione cancellata",
            len(canc), c['quante'])
        chk('Cancellazioni',
            f"{c['pacchetto']}: la cancellata rientra nelle {c['sessioni']} usate",
            len(p['sessioni']), c['sessioni'])

    # --- storico congelato: gli esclusi non si reinterpretano (spec 8) ---
    chk('Storico congelato', f"{atteso['esclusi']} eventi esclusi restano tali",
        len(reg.get('esclusi', [])), atteso['esclusi'])

    return all(x[2] for x in r), r
