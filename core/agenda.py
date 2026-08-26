# -*- coding: utf-8 -*-
"""
Agenda: le sedute davvero svolte, con giorno e ora.

Da dove vengono i dati, e perche' da li':

- QUALI sessioni: dal registro crediti (sessions.json). E' l'unico elenco
  completo e gia' validato contro le fatture — il calendario di Google non lo e'
  piu', perche' le serie ripetute finite vengono cancellate e sparisce anche il
  passato. Ogni riga dell'agenda e' quindi una sessione che ha consumato un
  credito: niente appuntamenti previsti, niente eventi che non erano sessioni.

- A CHE ORA: dal calendario. Il registro nasce senza orari (i crediti si
  contano a giornate) e lo storico gia' scritto non si tocca mai, percio' gli
  orari stanno a parte, in data/orari.json: un semplice indice
  «giorno + titolo → ora» che si puo' buttare e ricostruire quando si vuole,
  senza rischi per i crediti.
"""
import os
import json
import datetime

from . import calendario

from . import db as _db

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDICE = (_db.env('INVOICE_TIMES', 'FATTURE_ORARI')
          or os.path.join(APP_DIR, 'data', 'orari.json'))


def _chiave(data, titolo):
    return f"{data}|{(titolo or '').strip().lower()}"


def carica_indice():
    try:
        with open(INDICE, encoding='utf-8') as f:
            d = json.load(f)
        return d.get('orari', {}) if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def salva_indice(orari):
    os.makedirs(os.path.dirname(INDICE), exist_ok=True)
    tmp = INDICE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'aggiornato': datetime.datetime.now().isoformat(timespec='seconds'),
                   'orari': orari}, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, INDICE)      # mai un file mezzo scritto


def aggiorna_da_calendario(urls, da, a):
    """Scarica i calendari e aggiunge all'indice gli orari che ancora mancano.

    Non sovrascrive quelli gia' noti: se un evento viene spostato oggi, l'ora a
    cui la seduta si e' svolta davvero resta quella registrata allora.
    Ritorna (quanti_nuovi, elenco_errori, {url: nome_del_calendario}). I nomi
    arrivano dal file iCal stesso: si scarica gia', tanto vale chiedergli anche
    come si chiama invece di scriverlo nel programma.
    """
    orari = carica_indice()
    nuovi, errori, nomi = 0, [], {}
    for url in [u for u in urls if (u or '').strip()]:
        try:
            testo = calendario.scarica(url.strip())
            nomi[url] = calendario.nome(testo)
            voci = calendario.leggi(testo, da, a, e_testo=True)
        except Exception as e:
            errori.append(str(e))
            continue
        for v in voci:
            if not v.get('ora'):
                continue
            k = _chiave(v['data'], v['titolo'])
            if k not in orari:
                orari[k] = v['ora']
                nuovi += 1
    if nuovi:
        salva_indice(orari)
    return nuovi, errori, nomi


def elenco(reg, orari=None, cliente=None, anno=None):
    """Tutte le sessioni del registro, dalla piu' recente, pronte da mostrare."""
    orari = carica_indice() if orari is None else orari
    righe = []
    for p in reg.get('pacchetti', []):
        for s in p.get('sessioni', []):
            data = s.get('data') or ''
            righe.append({
                'data': data,
                'ora': s.get('ora') or orari.get(_chiave(data, s.get('titolo'))),
                'titolo': (s.get('titolo') or '').strip(),
                'cliente': p.get('cliente', ''),
                'pacchetto': p.get('id', ''),
                'n': s.get('n'),
                'crediti': p.get('crediti'),
                'cancellata': bool(s.get('cancellata')),
                'nota': s.get('nota') or '',
                'fattura': p.get('fattura_numero'),
            })
    if cliente:
        c = cliente.lower()
        righe = [r for r in righe
                 if c in r['cliente'].lower() or c in r['titolo'].lower()]
    if anno:
        righe = [r for r in righe if r['data'][:4] == str(anno)]
    # piu' recenti in cima; dentro la giornata, la seduta piu' tardi per
    # primo, e quelli di cui non si conosce l'ora in fondo
    righe.sort(key=lambda r: (r['data'], r['ora'] or ''), reverse=True)
    return righe


def anni(reg):
    return sorted({s['data'][:4] for p in reg.get('pacchetti', [])
                   for s in p.get('sessioni', []) if s.get('data')}, reverse=True)


def riepilogo(righe):
    """I due numeri che servono in cima alla pagina."""
    return {
        'totale': len(righe),
        'con_ora': sum(1 for r in righe if r['ora']),
        'cancellate': sum(1 for r in righe if r['cancellata']),
    }
