# -*- coding: utf-8 -*-
"""
I mesi di sedute degli abbonamenti.

Un abbonamento con sedute non e' un pacchetto: non finisce quando finiscono le
sedute, finisce quando finisce il mese. Ogni fattura di un servizio «ogni mese»
apre un mese di sedute nella lista `mensili` del registro:

    {id, chiavi, cliente, servizio_id, fattura_numero, dal, al, sedute,
     passano, massimo, prezzo_seduta_cents, sessioni,
     riportate, disponibili, usate, in_piu}     <- gli ultimi quattro si ricalcolano

Le regole:
- disponibili: se le sedute passano, min(sedute + riportate, massimo); se no,
  le sedute del mese;
- riportate: quello che e' avanzato nel mese prima, stesso cliente e stesso
  servizio, solo se quel mese ha una fattura e finisce il giorno prima;
- un mese senza fattura esiste lo stesso, subito dopo uno fatturato: zero
  sedute nuove, ci si usano le rimaste, e al mese dopo non riporta niente;
- le sedute oltre le disponibili restano scritte, con in_piu: True.

Questo modulo non importa sessions: e' sessions che usa lui.
"""
import re
import datetime

from dateutil.relativedelta import relativedelta

MOTIVO_NESSUN_ABBONAMENTO = 'nessun abbonamento in corso'


def _giorno(iso):
    return datetime.date.fromisoformat(iso)


def _giorno_prima(d):
    return (d - datetime.timedelta(days=1)).isoformat()


def periodo_di(data, periodo='', giorno=None):
    """(dal, al) del mese di sedute di una fattura, come date ISO.

    Da un abbonamento: dal giorno di rinnovo di quel mese al giorno prima del
    rinnovo dopo. Da una fattura qualsiasi: dalla sua data al giorno prima
    dello stesso giorno del mese dopo."""
    from . import recurring
    if periodo and recurring.valido(periodo):
        dal = recurring.giorno_di_emissione(periodo, giorno or 1)
        dopo = recurring.giorno_di_emissione(recurring.mese_succ(periodo), giorno or 1)
        return dal.isoformat(), _giorno_prima(dopo)
    dal = _giorno(data)
    return dal.isoformat(), _giorno_prima(dal + relativedelta(months=1))


def di(reg, chiave):
    """I mesi di sedute di un cliente."""
    return [m for m in reg.get('mensili') or [] if chiave in (m.get('chiavi') or [])]


def prossimo_id(reg, chiave):
    pref = (chiave or 'abo')[:3].upper() + '-M'
    n = 0
    for m in reg.get('mensili') or []:
        trovato = re.match(r'^%s(\d+)$' % re.escape(pref), m.get('id') or '')
        if trovato:
            n = max(n, int(trovato.group(1)))
    return f'{pref}{n + 1:02d}'


def precedente(reg, m):
    """Il mese dello stesso cliente e servizio che finisce il giorno prima."""
    prima = _giorno_prima(_giorno(m['dal']))
    return next((x for x in reg.get('mensili') or []
                 if x is not m and x.get('servizio_id') == m.get('servizio_id')
                 and set(x.get('chiavi') or []) & set(m.get('chiavi') or [])
                 and x['al'] == prima), None)


def riportate(reg, m):
    """Le sedute che arrivano dal mese prima. Mai meno di zero.

    Calcola disponibili(reg, p) una volta sola: chiamare anche usate(reg, p),
    che internamente richiama di nuovo disponibili(reg, p), raddoppierebbe il
    lavoro ad ogni mese di catena (con 18 mesi consecutivi che si riportano,
    oltre un milione di chiamate)."""
    if not m.get('passano'):
        return 0
    p = precedente(reg, m)
    if p is None or not p.get('fattura_numero'):
        return 0            # un mese senza fattura non riporta niente
    d = disponibili(reg, p)
    return max(0, d - min(len(p.get('sessioni') or []), d))


def disponibili(reg, m):
    nuove = int(m.get('sedute') or 0) if m.get('fattura_numero') else 0
    if not m.get('passano'):
        return nuove
    return min(nuove + riportate(reg, m), max(int(m.get('massimo') or 0), nuove))


def usate(reg, m):
    """Le sedute scalate davvero: quelle in piu' non contano."""
    return min(len(m.get('sessioni') or []), disponibili(reg, m))


def ha_posto(reg, m):
    return len(m.get('sessioni') or []) < disponibili(reg, m)


def ricalcola(reg, m):
    """Numeri e sedute in piu' di un mese, nell'ordine delle date."""
    disp = disponibili(reg, m)
    sessioni = sorted(m.get('sessioni') or [], key=lambda s: s.get('data') or '')
    for i, s in enumerate(sessioni):
        s['n'] = i + 1
        if i < disp:
            s.pop('in_piu', None)
        else:
            s['in_piu'] = True
    m['sessioni'] = sessioni
    m['riportate'] = riportate(reg, m)
    m['disponibili'] = disp
    m['usate'] = min(len(sessioni), disp)
    m['in_piu'] = max(0, len(sessioni) - disp)
    return m


def ricalcola_tutti(reg):
    for m in sorted(reg.get('mensili') or [], key=lambda x: x['dal']):
        ricalcola(reg, m)


def _nuovo(reg, chiave, cliente, dal, al, **campi):
    m = {'id': prossimo_id(reg, chiave), 'chiavi': [chiave], 'cliente': cliente,
         'servizio_id': None, 'fattura_numero': None, 'dal': dal, 'al': al, 'sedute': 0,
         'passano': 0, 'massimo': 0, 'prezzo_seduta_cents': None, 'sessioni': []}
    m.update(campi)
    reg.setdefault('mensili', []).append(m)
    return m


def _recupera_esclusi(reg, m, chiave):
    """Le sedute finite fra gli esclusi perche' il mese non c'era ancora (la
    seduta del giorno di rinnovo, prima della fattura) tornano dentro."""
    if not reg.get('esclusi'):
        return
    restano = []
    for e in reg['esclusi']:
        if (e.get('motivo') == MOTIVO_NESSUN_ABBONAMENTO and e.get('chiave') == chiave
                and m['dal'] <= (e.get('data') or '') <= m['al']):
            m['sessioni'].append({k: e[k] for k in ('data', 'titolo', 'cancellata', 'ora',
                                                    'event_id', 'nota') if k in e})
        else:
            restano.append(e)
    reg['esclusi'] = restano


def da_fattura(reg, chiave, cliente, numero, data, servizio, periodo='', giorno=None):
    """Il mese di sedute di una fattura «ogni mese». Ritorna il mese.

    Se quel mese c'era gia' (un mese senza fattura, fatturato dopo) la fattura
    lo completa invece di farne un secondo."""
    dal, al = periodo_di(data, periodo, giorno)
    n = int(servizio['sedute'] or 0)
    prezzo = servizio['prezzo_cents']
    campi = {'servizio_id': servizio['id'], 'fattura_numero': numero, 'al': al, 'sedute': n,
             'passano': int(servizio['passano'] or 0), 'massimo': int(servizio['massimo'] or 0),
             'prezzo_seduta_cents': prezzo // n if prezzo and n else None}
    m = next((x for x in di(reg, chiave)
              if x.get('servizio_id') == servizio['id'] and x['dal'] == dal), None)
    if m is None:
        # 'al' e' gia' un parametro posizionale di _nuovo: non ripassarlo
        # anche dentro **campi, che serve com'e' al ramo m.update(campi) sotto.
        m = _nuovo(reg, chiave, cliente, dal, al,
                   **{k: v for k, v in campi.items() if k != 'al'})
    else:
        m.update(campi)
    _recupera_esclusi(reg, m, chiave)
    ricalcola_tutti(reg)
    return m


def coprente(reg, chiave, data, crea=True):
    """Il mese di sedute del cliente che copre quella data, o None.

    Con due abbonamenti nello stesso giorno: prima quello che ha ancora sedute,
    e fra questi quello che finisce prima. Un mese senza fattura esiste solo
    subito dopo un mese fatturato: con crea=True lo si aggiunge."""
    suoi = di(reg, chiave)
    qui = [m for m in suoi if m['dal'] <= data <= m['al']]
    if not qui and crea:
        for m in sorted(suoi, key=lambda x: x['al']):
            if not m.get('fattura_numero'):
                continue
            inizio = _giorno(m['al']) + datetime.timedelta(days=1)
            dal, al = inizio.isoformat(), _giorno_prima(inizio + relativedelta(months=1))
            gia = any(x.get('servizio_id') == m.get('servizio_id') and x['dal'] == dal
                      for x in suoi)
            if not gia and dal <= data <= al:
                qui.append(_nuovo(reg, chiave, m.get('cliente', ''), dal, al,
                                  chiavi=list(m['chiavi']), servizio_id=m.get('servizio_id'),
                                  passano=m.get('passano', 0), massimo=m.get('massimo', 0),
                                  prezzo_seduta_cents=m.get('prezzo_seduta_cents')))
                ricalcola_tutti(reg)
                break
    if not qui:
        return None
    qui.sort(key=lambda x: (not ha_posto(reg, x), x['al']))
    return qui[0]


def aggiungi(reg, m, seduta):
    """Scrive la seduta nel mese e ricalcola: il mese dopo dipende da questo."""
    m.setdefault('sessioni', []).append(dict(seduta))
    ricalcola_tutti(reg)
    return m


def in_piu_recenti(reg, oggi=None):
    """I mesi con sedute in piu': quello in corso e quelli chiusi da non piu' di
    un mese. Dopo, l'avviso non serve piu' a nessuno."""
    oggi = oggi or datetime.date.today()
    fuori = []
    for m in reg.get('mensili') or []:
        if not m.get('in_piu'):
            continue
        dal, al = _giorno(m['dal']), _giorno(m['al'])
        if dal <= oggi <= al or 0 < (oggi - al).days <= 31:
            fuori.append({'cliente': m.get('cliente') or '', 'id': m['id'],
                          'dal': m['dal'], 'al': m['al'], 'in_piu': m['in_piu']})
    return sorted(fuori, key=lambda x: (x['cliente'], x['dal']))
