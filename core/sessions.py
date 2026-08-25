# -*- coding: utf-8 -*-
"""
Registro sessioni e crediti (SPEC-crediti.md).

Modello: il cliente compra un pacchetto di crediti, ogni sessione ne consuma uno,
a zero si rifattura.

Principi non negoziabili:
- Lo storico gia' nel registro NON si riscrive mai (spec 5.6): la sincronizzazione
  aggiunge in coda.
- Deduplicazione sull'ID evento Google Calendar (spec 5.5), mai su data+titolo.
- Una sessione cancellata CONSUMA il credito (spec 5.3).
"""
import os
import re
import json
import shutil
import datetime

from .money import fmt_chf

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.environ.get('FATTURE_SESSIONS') or os.path.join(APP_DIR, 'sessions.json')
SEED = os.path.join(APP_DIR, 'sessions_seed.json')

# Prima data leggibile dal calendario: tutto cio' che precede e' congelato (spec 5.1)
INIZIO_LETTURA = datetime.date(2026, 8, 20)

# spec 5.2 — titoli che contengono un nome cliente ma NON sono sessioni
PAROLE_ESCLUSE = ('birthday', 'compleanno', 'leaves', 'call', 'zoom')

SOGLIA_ESAURIMENTO = 2   # spec 6.2: <=2 rimasti => "In esaurimento"

# Etichette di stato (una sola definizione: le usano vista, CLI e pagine web)
STATO_TERMINATI = 'Crediti terminati'
STATO_ESAURIMENTO = 'In esaurimento'
STATO_CORSO = 'In corso'


# ------------------------------------------------------- chi lavora a crediti
# Chi sono i clienti a pacchetto, quanti crediti vale un pacchetto, a quale
# prezzo lo si riconosce su una fattura: prima stava scritto qui dentro, un
# nome per riga. Adesso sta nel database e si cambia dalla pagina Crediti;
# qui resta solo il modo di leggerlo.
#
# Il caso "marito e moglie" e' quello che ha fatto nascere il campo `compagno`:
# chi fa le sedute in coppia paga un pacchetto pieno piu' un supplemento, ma il
# supplemento vale solo nei giorni in cui ci sono tutti e due. Se quel giorno
# viene da solo, la sua e' una sessione piena e scala dal pacchetto grande.
_CONFIG = None


def configura(righe=None):
    """Carica in memoria l'elenco dei clienti a crediti.

    Senza argomenti lo legge dal database. Passandogli una lista di dizionari
    si usa nelle prove, senza database."""
    global _CONFIG
    if righe is None:
        from . import db
        con = db.connect()
        try:
            righe = [dict(r) for r in db.crediti_clienti(con)]
        finally:
            con.close()
    _CONFIG = [_normalizza(r) for r in righe]
    return _CONFIG


def ricarica():
    """Da chiamare dopo aver cambiato i clienti, perche' l'app se ne accorga."""
    global _CONFIG
    _CONFIG = None


def _normalizza(r):
    prezzi = r.get('prezzi')
    if isinstance(prezzi, str):
        prezzi = [int(x) for x in re.findall(r'\d+', prezzi)]
    return {
        'chiave': (r.get('chiave') or '').strip().lower(),
        'nome': (r.get('nome') or '').strip(),
        'crediti': int(r.get('crediti') or 0),
        'prefisso': (r.get('prefisso') or '').strip().upper(),
        'prezzi': [int(x) for x in (prezzi or [])],
        'fattura_a': (r.get('fattura_a') or '').strip(),
        'compagno': (r.get('compagno') or '').strip().lower(),
        'attivo': bool(int(r.get('attivo', 1) or 0)),
    }


def _tutti():
    global _CONFIG
    if _CONFIG is None:
        try:
            configura()
        except Exception:
            # senza database (script da riga di comando, prove) si lavora con
            # l'elenco vuoto: meglio nessun cliente che un errore in faccia
            _CONFIG = []
    return _CONFIG


def clienti():
    """I clienti a crediti attivi: chiave -> dati."""
    return {c['chiave']: c for c in _tutti() if c['attivo']}


def ex_clienti():
    """Chi non e' piu' cliente. I suoi titoli si riconoscono ancora, perche'
    puo' comparire in un pacchetto condiviso ancora aperto."""
    return {c['chiave']: c['nome'] for c in _tutti() if not c['attivo']}


def cliente(chiave):
    return next((c for c in _tutti() if c['chiave'] == chiave), None)


def chiave_da_nome(testo):
    """La parola cercata nei titoli del calendario: minuscola, senza spazi."""
    return re.sub(r'[^a-z0-9]', '', (testo or '').strip().lower())


def prezzi_da_testo(testo):
    """«1'800.00 CHF, 150.-» -> «180000,150000».

    Chi usa l'app scrive i prezzi come li ha in testa, non in centesimi, e li
    separa con la virgola o col punto e virgola."""
    from .money import parse_amount
    fuori = []
    for pezzo in re.split(r'[;,\n]', testo or ''):
        if not pezzo.strip():
            continue
        c = parse_amount(pezzo)
        if c is not None:
            fuori.append(str(c))
    return ','.join(fuori)


def prezzo_atteso(chiave):
    """Quanto costa di solito il pacchetto, scritto per essere letto."""
    c = cliente(chiave)
    return fmt_chf(c['prezzi'][0]) if c and c['prezzi'] else None


# ------------------------------------------------------------------ utilita'
def normalizza(titolo):
    """spec 5.2: trim + lowercase, spazi interni compattati."""
    return re.sub(r'\s+', ' ', (titolo or '').strip().lower())


def e_cancellata(titolo):
    """spec 5.3: riconosce la cancellazione dal titolo."""
    return 'cancel' in normalizza(titolo)


def classifica(titolo):
    """Da un titolo di calendario ricava (chiave_cliente, cancellata, motivo_scarto).

    Ritorna chiave_cliente=None se l'evento non e' una sessione conteggiabile;
    in quel caso motivo_scarto spiega perche'."""
    t = normalizza(titolo)
    if not t:
        return None, False, 'titolo vuoto'
    # "no ..." = sessione annullata in partenza, non conteggiata (spec 5.2)
    if t.startswith('no '):
        return None, False, 'titolo che inizia con "no "'
    for parola in PAROLE_ESCLUSE:
        if parola in t:
            return None, False, f'contiene "{parola}"'
    # Se nel titolo compaiono piu' nomi (es. "Anna - cancelled by Bruno"),
    # il cliente e' quello nominato per PRIMO: e' il soggetto della sessione,
    # e il credito va scalato a lui.
    trovati = []
    for chiave in (c['chiave'] for c in _tutti()):
        # match sul nome come parola (copre "Anna pt Bike", "ANNA", "Anna ")
        m = re.search(rf'\b{re.escape(chiave)}\b', t)
        if m:
            trovati.append((m.start(), chiave))
    if trovati:
        trovati.sort()
        return trovati[0][1], e_cancellata(titolo), None
    return None, False, 'nessun cliente riconosciuto'


def attribuisci(chiave, clienti_del_giorno):
    """Decide a quale cliente va addebitato il credito.

    Chi fa le sedute in coppia paga un pacchetto ridotto: e' il supplemento di
    quello dell'altro, e vale solo nei giorni in cui ci sono tutti e due. Se
    quel giorno viene da solo la sessione e' piena, e scala dal pacchetto
    dell'altro. Ritorna (chiave_addebito, nota)."""
    compagno = (cliente(chiave) or {}).get('compagno')
    if compagno and compagno not in set(clienti_del_giorno):
        return compagno, (f'{nome_cliente(chiave)} da solo: sessione piena, '
                          f'consuma un credito di {nome_cliente(compagno)}')
    return chiave, None


def e_saldato(p):
    """True se il pacchetto risulta gia' incassato/fatturato.
    Copre anche i casi scritti a mano tipo 'no - pagato contanti': incassato
    lo stesso, non e' un'anomalia."""
    f = (p.get('fatturato') or 'no').strip().lower()
    if p.get('fattura_numero'):
        return True
    return f.startswith('si') or 'pagato' in f


def nome_cliente(chiave):
    c = cliente(chiave)
    return c['nome'] if c and c['nome'] else (chiave or '').title()


# ------------------------------------------------------------------ registro
def carica(path=None):
    """Carica il registro. Se non esiste lo crea: dal seed se c'e' (spec 3),
    altrimenti vuoto — un'app appena installata non ha nessuno storico da
    ricopiare, e questo non e' un errore."""
    path = path or REGISTRY
    if not os.path.exists(path):
        if os.path.exists(SEED):
            shutil.copy2(SEED, path)
        else:
            salva({'generato': datetime.date.today().isoformat(),
                   'pacchetti': [], 'esclusi': [], 'prepagate': {}}, path)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def salva(reg, path=None):
    """Salvataggio atomico + copia di sicurezza del registro precedente."""
    path = path or REGISTRY
    if os.path.exists(path):
        bdir = os.path.join(os.path.dirname(path), 'data', 'backups')
        os.makedirs(bdir, exist_ok=True)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        shutil.copy2(path, os.path.join(bdir, f'sessions-{stamp}.json'))
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def pacchetti_aperti(reg):
    return [p for p in reg['pacchetti'] if not p.get('fine')]


def pacchetto_aperto_di(reg, chiave):
    """Pacchetto aperto che copre quel cliente (gestisce i pacchetti condivisi)."""
    nome = nome_cliente(chiave).lower()
    for p in pacchetti_aperti(reg):
        if nome in p['cliente'].lower():
            return p
    return None


def id_evento_gia_presente(reg):
    """Tutti gli ID evento Google gia' registrati (spec 5.5)."""
    visti = set()
    for p in reg['pacchetti']:
        for s in p.get('sessioni', []):
            if s.get('event_id'):
                visti.add(s['event_id'])
    for e in reg.get('esclusi', []):
        if e.get('event_id'):
            visti.add(e['event_id'])
    return visti


def ultima_data_registrata(reg):
    date = [s['data'] for p in reg['pacchetti'] for s in p.get('sessioni', []) if s.get('data')]
    return max(date) if date else None


def prossimo_id_pacchetto(reg, chiave):
    c = cliente(chiave)
    # senza prefisso scritto se ne ricava uno dal nome: Anna Rossi -> ANN-01
    pref = (c and c['prefisso']) or (chiave or 'PAC')[:3].upper()
    n = 0
    for p in reg['pacchetti']:
        m = re.match(rf'^{pref}-(\d+)$', p['id'])
        if m:
            n = max(n, int(m.group(1)))
    return f'{pref}-{n + 1:02d}'


def apri_pacchetto(reg, chiave, data_inizio):
    """Apre il pacchetto successivo per quel cliente (spec 6.1 punto 7)."""
    cfg = cliente(chiave)
    if cfg is None:
        raise KeyError(f'{chiave} non è fra i clienti a crediti')
    p = {
        'id': prossimo_id_pacchetto(reg, chiave),
        'cliente': cfg['nome'],
        'crediti': cfg['crediti'],
        'inizio': data_inizio,
        'fine': None,
        'fatturato': 'no',
        'usati': 0,
        'rimasti': cfg['crediti'],
        'sessioni': [],
        'nota': 'Aperto automaticamente dalla sincronizzazione calendario',
    }
    reg['pacchetti'].append(p)
    return p


def ricalcola(p):
    """Aggiorna usati/rimasti di un pacchetto dalle sue sessioni."""
    p['usati'] = len(p.get('sessioni', []))
    p['rimasti'] = p['crediti'] - p['usati']
    return p


def aggiungi_sessione(reg, chiave, data, titolo, event_id=None, nota=None, ora=None):
    """Aggiunge una sessione al pacchetto aperto, aprendo il successivo se pieno.
    Ritorna (pacchetto, aperto_nuovo: bool)."""
    p = pacchetto_aperto_di(reg, chiave)
    aperto_nuovo = False
    if p is None:
        p = apri_pacchetto(reg, chiave, data)
        usa_prepagata(reg, chiave, p)
        aperto_nuovo = True
    elif len(p.get('sessioni', [])) >= p['crediti']:
        # pacchetto pieno: si chiude e si apre il successivo (spec 6.1 punto 7)
        p['fine'] = max(s['data'] for s in p['sessioni'])
        ricalcola(p)
        p = apri_pacchetto(reg, chiave, data)
        usa_prepagata(reg, chiave, p)
        aperto_nuovo = True
    p.setdefault('sessioni', []).append({
        'n': len(p.get('sessioni', [])) + 1,
        'data': data,
        'titolo': titolo,
        'cancellata': e_cancellata(titolo),
        # l'ora serve solo all'Agenda: i crediti si contano a giornate
        **({'ora': ora} if ora else {}),
        **({'event_id': event_id} if event_id else {}),
        **({'nota': nota} if nota else {}),
    })
    ricalcola(p)
    return p, aperto_nuovo


# ------------------------------------------------------------------ vista
def vista_crediti(reg):
    """spec 6.2 — per ogni cliente attivo: totali, usati, rimasti, inizio, stato.

    "Crediti terminati" vuol dire che il pacchetto e' finito e servono crediti
    nuovi, quindi va emessa la PROSSIMA fattura. NON significa che il pacchetto
    sia rimasto da pagare: i pacchetti si pagano in anticipo (la fattura li apre),
    percio' lo stato non si spegne collegando la fattura che lo aveva pagato.
    """
    righe = []
    for chiave, cfg in clienti().items():
        p = pacchetto_aperto_di(reg, chiave)
        if p:
            ricalcola(p)
            rimasti = p['rimasti']
            if rimasti <= 0:
                stato = STATO_TERMINATI
            elif rimasti <= SOGLIA_ESAURIMENTO:
                stato = STATO_ESAURIMENTO
            else:
                stato = STATO_CORSO
            rif = p
        else:
            chiusi = [q for q in reg['pacchetti']
                      if cfg['nome'].lower() in q['cliente'].lower() and q.get('fine')]
            rif = max(chiusi, key=lambda q: q['fine']) if chiusi else None
            stato = STATO_TERMINATI
            rimasti = 0
        righe.append({
            'cliente': cfg['nome'], 'chiave': chiave,
            'pacchetto': rif['id'] if rif else '—',
            'intestato_a': rif['cliente'] if rif else cfg['nome'],
            'fattura_a': cfg['fattura_a'] or cfg['nome'],
            'importo_atteso': prezzo_atteso(chiave),
            'crediti': rif['crediti'] if rif else cfg['crediti'],
            'usati': len(rif.get('sessioni', [])) if rif else 0,
            'rimasti': rimasti,
            'inizio': rif['inizio'] if rif else None,
            'stato': stato,
            'terminati': stato == STATO_TERMINATI,
            'in_esaurimento': stato == STATO_ESAURIMENTO,
            'aperto': bool(p),
            'saldato': e_saldato(rif) if rif else False,
            'fatturato': rif.get('fatturato') if rif else None,
            'fattura_numero': rif.get('fattura_numero') if rif else None,
            'nota': rif.get('nota', '') if rif else '',
            'ultima_sessione': max((s['data'] for s in rif.get('sessioni', [])), default=None) if rif else None,
        })
    ordine = {STATO_TERMINATI: 0, STATO_ESAURIMENTO: 1, STATO_CORSO: 2}
    righe.sort(key=lambda r: (ordine.get(r['stato'], 9), r['cliente']))
    return righe


# ------------------------------------------------------------------ fatture
def collega_fattura(reg, pacchetto_id, numero_fattura, chiudi=True):
    """spec 6.3 — marca le sessioni coperte col numero fattura e apre il successivo."""
    p = next((q for q in reg['pacchetti'] if q['id'] == pacchetto_id), None)
    if p is None:
        raise KeyError(f'Pacchetto {pacchetto_id} inesistente')
    p['fatturato'] = f'si - #{numero_fattura}'
    p['fattura_numero'] = numero_fattura
    for s in p.get('sessioni', []):
        s['fattura'] = numero_fattura
    nuovo = None
    # Si chiude SOLO se i crediti sono finiti davvero: collegare la fattura a un
    # pacchetto ancora in corso non deve mai bruciare i crediti residui.
    esaurito = len(p.get('sessioni', [])) >= p['crediti']
    if chiudi and esaurito and not p.get('fine'):
        p['fine'] = max((s['data'] for s in p.get('sessioni', [])), default=None) or p['inizio']
        ricalcola(p)
        chiave = next((k for k, c in clienti().items()
                       if c['nome'].lower() in p['cliente'].lower()), None)
        # il pacchetto successivo si apre alla prima sessione utile, non subito:
        # qui lo segnaliamo soltanto
        nuovo = chiave
    return p, nuovo


# ------------------------------------------------------------------ aggancio automatico
def _candidati_per_fattura(client_name):
    """Clienti-crediti la cui fattura e' intestata a questo nome."""
    low = (client_name or '').lower()
    out = []
    for chiave, cfg in clienti().items():
        intestatario = cfg['fattura_a'] or cfg['nome']
        if intestatario.lower() in low or cfg['nome'].lower() in low:
            out.append(chiave)
    return out


# Parole che indicano "questa fattura compra un pacchetto di sessioni"
PAROLE_PACCHETTO = ('sessions pack', 'session pack', 'sessions -', 'credits',
                    'crediti', 'add-on', 'addon', 'pacchetto')


def riconosci_pacchetto(client_name, total_cents):
    """Chiave cliente se l'importo corrisponde a un prezzo di pacchetto noto."""
    if total_cents is None:
        return None
    for chiave in _candidati_per_fattura(client_name):
        if total_cents in (cliente(chiave) or {}).get('prezzi', []):
            return chiave
    return None


def analizza_fattura(client_name, total_cents, descrizioni=()):
    """Capisce che tipo di fattura e' e cosa deve succedere ai crediti.

    Ritorna un dict:
      chiave         cliente-crediti coinvolto (o None)
      e_pacchetto    True se la fattura compra un pacchetto di sessioni
      prezzo_ok      True se l'importo corrisponde al prezzo abituale
      prezzo_atteso  lista dei prezzi noti per quel cliente (centesimi)
      ha_crediti     True se l'intestatario ha pacchetti a crediti
    """
    testo = ' '.join(descrizioni).lower()
    candidati = _candidati_per_fattura(client_name)
    res = {'chiave': None, 'e_pacchetto': False, 'prezzo_ok': False,
           'prezzo_atteso': [], 'ha_crediti': bool(candidati)}

    # 1) l'importo corrisponde a un prezzo noto: caso pulito
    chiave = riconosci_pacchetto(client_name, total_cents)
    if chiave:
        res.update(chiave=chiave, e_pacchetto=True, prezzo_ok=True,
                   prezzo_atteso=cliente(chiave)['prezzi'])
        return res

    # 2) la descrizione dice che e' un pacchetto, ma l'importo e' inatteso
    if candidati and any(w in testo for w in PAROLE_PACCHETTO):
        supplemento = [k for k in candidati if (cliente(k) or {}).get('compagno')]
        if 'add-on' in testo or 'addon' in testo:
            scelto = supplemento[0] if supplemento else candidati[0]
        else:
            # il cliente "proprio", cioe' quello che non e' un supplemento
            scelto = next((k for k in candidati if k not in supplemento), candidati[0])
        res.update(chiave=scelto, e_pacchetto=True, prezzo_ok=False,
                   prezzo_atteso=(cliente(scelto) or {}).get('prezzi', []))
    return res


def aggancia_fattura(reg, client_name, numero, total_cents, data=None):
    """Collega automaticamente una fattura appena emessa al pacchetto giusto.

    Tre casi:
      - nessun pacchetto aperto (o esaurito) -> ne apre uno nuovo, gia' pagato
      - pacchetto aperto e senza fattura     -> registra la fattura su quello
      - pacchetto aperto e gia' collegato    -> la mette in attesa: verra' usata
                                                dal pacchetto successivo
    Ritorna (esito, messaggio) con esito in {None,'nuovo','collegato','in_attesa'}.
    """
    chiave = riconosci_pacchetto(client_name, total_cents)
    if not chiave:
        return None, None
    nome = nome_cliente(chiave)
    p = pacchetto_aperto_di(reg, chiave)

    if p is not None and p['crediti'] - len(p.get('sessioni', [])) > 0:
        # si attacca al pacchetto in corso SOLO se quello non risulta gia' pagato:
        # altrimenti questa fattura sta comprando il pacchetto successivo
        if not e_saldato(p):
            p['fatturato'] = f'si - #{numero}'
            p['fattura_numero'] = numero
            return 'collegato', (f'Collegata al pacchetto {p["id"]} di {nome}, '
                                 f'che ha ancora {p["crediti"] - len(p.get("sessioni", []))} crediti.')
        reg.setdefault('prepagate', {})[chiave] = numero
        return 'in_attesa', (f'{nome} ha ancora crediti sul pacchetto {p["id"]}: '
                             f'questa fattura resta in attesa e aprira' + chr(39) + ' il pacchetto '
                             f'successivo alla prima sessione utile.')

    # pacchetto esaurito o inesistente: la fattura ne apre uno nuovo, gia' pagato
    if p is not None:
        p['fine'] = max((x['data'] for x in p.get('sessioni', [])), default=None) or p['inizio']
        ricalcola(p)
    nuovo = apri_pacchetto(reg, chiave, data or datetime.date.today().isoformat())
    nuovo['fatturato'] = f'si - #{numero}'
    nuovo['fattura_numero'] = numero
    nuovo['nota'] = f'Aperto dalla fattura #{numero}'
    return 'nuovo', (f'Aperto il pacchetto {nuovo["id"]} per {nome}: '
                     f'{nuovo["crediti"]} crediti disponibili.')


def usa_prepagata(reg, chiave, pacchetto):
    """Se c'era una fattura in attesa per quel cliente, la applica al pacchetto nuovo."""
    numero = (reg.get('prepagate') or {}).pop(chiave, None)
    if numero:
        pacchetto['fatturato'] = f'si - #{numero}'
        pacchetto['fattura_numero'] = numero
        pacchetto['nota'] = f'Pagato dalla fattura #{numero} (emessa in anticipo)'
    return numero
