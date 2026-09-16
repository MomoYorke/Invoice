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

from dateutil.relativedelta import relativedelta

from . import mensili

from . import db as _db

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = (_db.env('INVOICE_SESSIONS', 'FATTURE_SESSIONS')
            or os.path.join(APP_DIR, 'sessions.json'))
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


# ------------------------------------------------------- chi fa le sedute
# I clienti con le sedute sono clienti come gli altri: la scheda cliente dice
# come si chiamano nel calendario e con chi si allenano. Qui resta solo il
# modo di leggerli. La misura dei pacchetti e i prezzi arrivano dal servizio
# venduto in fattura.
#
# Il caso "marito e moglie" e' quello che ha fatto nascere il campo `compagno`:
# chi fa le sedute in coppia paga un pacchetto pieno piu' un supplemento, ma il
# supplemento vale solo nei giorni in cui ci sono tutti e due. Se quel giorno
# viene da solo, la sua e' una sessione piena e scala dal pacchetto grande.
_CONFIG = None


def configura(righe=None):
    """Carica in memoria i clienti con le sedute.

    Senza argomenti li legge dal database. Passandogli una lista di dizionari
    (le colonne di db.clienti_sedute) si usa nelle prove, senza database."""
    global _CONFIG
    if righe is None:
        from . import db
        con = db.connect()
        try:
            righe = [dict(r) for r in db.clienti_sedute(con)]
        finally:
            con.close()
    _CONFIG = [_normalizza(r) for r in righe]
    return _CONFIG


def ricarica():
    """Da chiamare dopo aver cambiato i clienti, perche' l'app se ne accorga."""
    global _CONFIG
    _CONFIG = None


def nomi_calendario(testo, nome_cliente=''):
    """I nomi con cui il cliente compare nei titoli del calendario.

    «Giuly, Giulia F.» -> ['Giuly', 'Giulia F.']; vuoto -> il primo nome."""
    nomi = [n.strip() for n in (testo or '').split(',') if n.strip()]
    return nomi or (nome_cliente or '').strip().split()[:1]


def _normalizza(r):
    chiave = (r.get('chiave_sedute') or '').strip().lower()
    nomi = nomi_calendario(r.get('nome_calendario'), r.get('name'))
    return {
        'chiave': chiave,
        'client_id': r.get('id'),
        'nome': nomi[0] if nomi else chiave.title(),
        'nomi': nomi,
        'parole': [normalizza(n) for n in nomi],
        'prefisso': chiave[:3].upper(),
        'fattura_a': (r.get('intestatario') or '').strip(),
        'compagno': (r.get('compagno') or '').strip().lower(),
        'attivo': not int(r.get('archived') or 0),
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
    for c in _tutti():
        for parola in c['parole']:
            # il nome come parola intera: «Giulia pt Bike» sì, «Giuliana» no.
            # A pari posizione vince il nome più lungo («Marco B.» su «Marco»)
            m = re.search(r'(?<!\w)' + re.escape(parola) + r'(?!\w)', t) if parola else None
            if m:
                trovati.append((m.start(), -len(parola), c['chiave']))
    if trovati:
        trovati.sort()
        return trovati[0][2], e_cancellata(titolo), None
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


def _chiavi_di(p, config=None):
    """Le chiavi dei clienti di un pacchetto (uno diviso ne ha due).

    I pacchetti scritti prima delle chiavi si riconoscono dal nome, come si
    faceva prima: un nome del calendario, come parola intera, in «cliente»."""
    if p.get('chiavi'):
        return list(p['chiavi'])
    testo = normalizza(p.get('cliente'))
    return [c['chiave'] for c in (_tutti() if config is None else config)
            if any(re.search(r'(?<!\w)' + re.escape(parola) + r'(?!\w)', testo)
                   for parola in c['parole'] if parola)]


def pacchetto_aperto_di(reg, chiave):
    """Pacchetto aperto che copre quel cliente (gestisce i pacchetti condivisi)."""
    for p in pacchetti_aperti(reg):
        if chiave in _chiavi_di(p):
            return p
    return None


def id_evento_gia_presente(reg):
    """Tutti gli ID evento gia' registrati (spec 5.5): pacchetti, mesi, esclusi."""
    visti = set()
    for gruppo in list(reg['pacchetti']) + list(reg.get('mensili') or []):
        for s in gruppo.get('sessioni', []):
            if s.get('event_id'):
                visti.add(s['event_id'])
    for e in reg.get('esclusi', []):
        if e.get('event_id'):
            visti.add(e['event_id'])
    return visti


def ultima_data_registrata(reg):
    date = [s['data'] for gruppo in list(reg['pacchetti']) + list(reg.get('mensili') or [])
            for s in gruppo.get('sessioni', []) if s.get('data')]
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


class SenzaPacchetto(KeyError):
    """`apri_pacchetto` la solleva quando non c'e' nessun pacchetto da aprire:
    il cliente non e' (piu') fra quelli con le sedute, oppure non c'e' nessuna
    misura da cui partire (spec 6.1 punto 7) — i due soli casi in cui una
    seduta letta dal calendario va scartata invece di fermare la lettura.

    E' una sottoclasse di KeyError apposta: chi la cattura ancora come
    KeyError (le prove, per esempio) continua a funzionare senza cambiare
    niente. `sync_sessions.sincronizza` la cattura per nome, cosi' un guaio
    diverso dentro `aggiungi_sessione` — un pacchetto senza 'crediti', una
    sessione senza 'data', un pacchetto senza 'id' — resta un KeyError
    semplice: non si scambia per «nessun pacchetto» e ferma la lettura invece
    di sparire in silenzio, come succedeva prima di questo scarto."""


def apri_pacchetto(reg, chiave, data_inizio, crediti=None):
    """Apre il pacchetto successivo per quel cliente (spec 6.1 punto 7).

    La misura e' quella detta (dal servizio in fattura) o, senza, quella
    dell'ultimo pacchetto del cliente. Senza nessuna delle due non si apre
    niente: inventare quante sedute ha comprato qualcuno e' peggio che dirlo."""
    cfg = cliente(chiave)
    if cfg is None:
        raise SenzaPacchetto(f'{chiave} non è fra i clienti con le sedute')
    if crediti is None:
        suoi = [p for p in reg['pacchetti'] if chiave in _chiavi_di(p)]
        crediti = suoi[-1]['crediti'] if suoi else None
    if not crediti:
        raise SenzaPacchetto(f'{chiave}: nessun pacchetto da cui prendere la misura')
    p = {
        'id': prossimo_id_pacchetto(reg, chiave),
        'cliente': cfg['nome'],
        'chiavi': [chiave],
        'crediti': crediti,
        'inizio': data_inizio,
        'fine': None,
        'fatturato': 'no',
        'usati': 0,
        'rimasti': crediti,
        'sessioni': [],
        'nota': 'Aperto automaticamente dalla sincronizzazione calendario',
    }
    reg['pacchetti'].append(p)
    return p


def contate(gruppo):
    """Le sedute che consumano un credito: tutte tranne quelle segnate non fatte.

    La regola sta qui e in nessun altro posto: se un conteggio la ripetesse per
    conto suo, un giorno una pagina direbbe 9 e un'altra 10.
    """
    return [s for s in (gruppo or {}).get('sessioni') or [] if not s.get('non_fatta')]


def ricalcola(p):
    """Aggiorna usati/rimasti di un pacchetto dalle sue sessioni."""
    p['usati'] = len(contate(p))
    p['rimasti'] = p['crediti'] - p['usati']
    return p


def chiudi_scaduto(p):
    """Chiude un pacchetto scaduto: le sedute rimaste si perdono."""
    p['fine'] = p['scade']
    p['scaduto'] = True
    ricalcola(p)
    return p


def _apri_successivo(reg, chiave, data):
    """Il pacchetto dopo: con le sedute della fattura in attesa, se ce n'e' una.

    Se la fattura in attesa porta una scadenza gia' passata per `data`, il
    pacchetto nasce gia' scaduto: si chiude subito (le sue sedute, zero, non
    si perdono perche' non ce ne sono) e si riprova con la prossima fattura
    in attesa, finche' non se ne trova una ancora valida o non ce ne sono
    piu' — un pacchetto senza fattura in attesa non ha scadenza, e il giro
    finisce li'."""
    attesa = _prima_prepagata(reg, chiave)
    p = apri_pacchetto(reg, chiave, data,
                       crediti=attesa.get('sedute') if isinstance(attesa, dict) else None)
    usa_prepagata(reg, chiave, p)
    if p.get('scade') and data > p['scade']:
        p['inizio'] = p['scade']
        chiudi_scaduto(p)
        return _apri_successivo(reg, chiave, data)
    return p


def _scade_prima(p, data, mese):
    """Vero se il pacchetto aperto va usato prima del mese: scade prima che il
    mese finisca, e ha ancora sedute."""
    return (p is not None and bool(p.get('scade')) and data <= p['scade'] < mese['al']
            and len(contate(p)) < p['crediti'])


def _nel_pacchetto(reg, chiave, seduta):
    """La seduta nel pacchetto aperto, aprendo il successivo se e' pieno o
    scaduto. Ritorna (pacchetto, aperto_nuovo)."""
    data = seduta['data']
    p = pacchetto_aperto_di(reg, chiave)
    aperto_nuovo = False
    if p is not None and p.get('scade') and data > p['scade']:
        chiudi_scaduto(p)
        p = None
    if p is None:
        p = _apri_successivo(reg, chiave, data)
        aperto_nuovo = True
    elif len(contate(p)) >= p['crediti']:
        # pacchetto pieno: si chiude e si apre il successivo (spec 6.1 punto 7)
        p['fine'] = max(s['data'] for s in p['sessioni'])
        ricalcola(p)
        p = _apri_successivo(reg, chiave, data)
        aperto_nuovo = True
    p.setdefault('sessioni', []).append(dict({'n': len(p.get('sessioni', [])) + 1}, **seduta))
    ricalcola(p)
    return p, aperto_nuovo


def aggiungi_sessione(reg, chiave, data, titolo, event_id=None, nota=None, ora=None):
    """Scrive una seduta dove va scalata. L'ordine:

    1. il mese di abbonamento che copre la data, se ha ancora sedute (salvo un
       pacchetto aperto che scade prima della fine di quel mese);
    2. il pacchetto aperto, o il successivo, per chi ha pacchetti;
    3. per chi ha solo abbonamenti, «in piu'» nel mese che copre la data;
    4. se nessun mese la copre, fra gli esclusi: nessun abbonamento in corso.

    Ritorna (pacchetto o mese, aperto_nuovo), oppure (None, False) se esclusa."""
    seduta = {
        'data': data,
        'titolo': titolo,
        'cancellata': e_cancellata(titolo),
        # l'ora serve solo all'Agenda: i crediti si contano a giornate
        **({'ora': ora} if ora else {}),
        **({'event_id': event_id} if event_id else {}),
        **({'nota': nota} if nota else {}),
    }
    mese = mensili.coprente(reg, chiave, data)
    p = pacchetto_aperto_di(reg, chiave)
    if mese is not None and mensili.ha_posto(reg, mese) and not _scade_prima(p, data, mese):
        return mensili.aggiungi(reg, mese, seduta), False
    if any(chiave in _chiavi_di(q) for q in reg['pacchetti']):
        return _nel_pacchetto(reg, chiave, seduta)
    if mese is not None:
        return mensili.aggiungi(reg, mese, seduta), False
    reg.setdefault('esclusi', []).append(dict(seduta, cliente=nome_cliente(chiave), chiave=chiave,
                                              motivo=mensili.MOTIVO_NESSUN_ABBONAMENTO))
    return None, False


# ------------------------------------------------------------------ vista
def _mese_in_vista(reg, mesi, oggi):
    """Il mese di abbonamento da mostrare: quello in corso, o l'ultimo iniziato."""
    iniziati = sorted((m for m in mesi if m['dal'] <= oggi), key=lambda m: (m['dal'], m['al']))
    if not iniziati:
        return None
    in_corso = [m for m in iniziati if m['al'] >= oggi]
    m = in_corso[0] if in_corso else iniziati[-1]
    disponibili = mensili.disponibili(reg, m)
    return {'id': m['id'], 'dal': m['dal'], 'al': m['al'],
            'usate': mensili.usate(reg, m), 'disponibili': disponibili,
            'nuove': int(m.get('sedute') or 0) if m.get('fattura_numero') else 0,
            'riportate': mensili.riportate(reg, m),
            'in_piu': max(0, len(m.get('sessioni') or []) - disponibili),
            'in_corso': bool(in_corso), 'fatturato': bool(m.get('fattura_numero'))}


def vista_crediti(reg, oggi=None):
    """spec 6.2 — per ogni cliente con pacchetti o abbonamenti con sedute: il
    pacchetto (totali, usati, rimasti, inizio, stato) e il mese in corso.

    "Crediti terminati" vuol dire che il pacchetto e' finito e servono crediti
    nuovi, quindi va emessa la PROSSIMA fattura. NON significa che il pacchetto
    sia rimasto da pagare: i pacchetti si pagano in anticipo (la fattura li apre),
    percio' lo stato non si spegne collegando la fattura che lo aveva pagato.
    Chi ha solo un abbonamento non ha pacchetti da finire: niente stato.
    """
    oggi = (oggi or datetime.date.today()).isoformat()
    righe = []
    for chiave, cfg in clienti().items():
        suoi = [q for q in reg['pacchetti'] if chiave in _chiavi_di(q)]
        mensile = _mese_in_vista(reg, mensili.di(reg, chiave), oggi)
        if not suoi and mensile is None:
            continue
        p = pacchetto_aperto_di(reg, chiave)
        rif, stato, rimasti = None, '', 0
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
        elif suoi:
            chiusi = [q for q in suoi if q.get('fine')]
            rif = max(chiusi, key=lambda q: q['fine']) if chiusi else None
            stato = STATO_TERMINATI
        usati = len(contate(rif)) if rif else 0
        scaduto = bool(rif and rif.get('scaduto'))
        righe.append({
            'cliente': cfg['nome'], 'chiave': chiave,
            'pacchetto': rif['id'] if rif else None,
            'intestato_a': rif['cliente'] if rif else cfg['nome'],
            'fattura_a': cfg['fattura_a'] or cfg['nome'],
            'crediti': rif['crediti'] if rif else 0,
            'usati': usati,
            'rimasti': rimasti,
            'inizio': rif['inizio'] if rif else None,
            'fine': rif.get('fine') if rif else None,
            'scade': rif.get('scade') if rif and not scaduto else None,
            'scaduto': scaduto,
            'non_usate': max(0, rif['crediti'] - usati) if scaduto else 0,
            'stato': stato,
            'terminati': stato == STATO_TERMINATI,
            'in_esaurimento': stato == STATO_ESAURIMENTO,
            'aperto': bool(p),
            'saldato': e_saldato(rif) if rif else False,
            'fatturato': rif.get('fatturato') if rif else None,
            'fattura_numero': rif.get('fattura_numero') if rif else None,
            'nota': rif.get('nota', '') if rif else '',
            'ultima_sessione': max((s['data'] for s in contate(rif)), default=None) if rif else None,
            'mensile': mensile,
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
    esaurito = len(contate(p)) >= p['crediti']
    if chiudi and esaurito and not p.get('fine'):
        p['fine'] = max((s['data'] for s in p.get('sessioni', [])), default=None) or p['inizio']
        ricalcola(p)
        chiave = next((k for k in _chiavi_di(p) if k in clienti()), None)
        # il pacchetto successivo si apre alla prima sessione utile, non subito:
        # qui lo segnaliamo soltanto
        nuovo = chiave
    return p, nuovo


# ------------------------------------------------------------------ sedute dalla fattura
# Le sedute le porta la riga del servizio venduto: quante, a che prezzo, fino a
# quando. Prima una fattura diventava un pacchetto se il totale era uno dei
# prezzi scritti a mano per quel cliente, e bastava uno sconto per perderle.

def sedute_della_riga(servizio, qty, total_cents=None):
    """Quante sedute compra una riga: le sedute del servizio per la quantita',
    per difetto.

    Con un prezzo e un totale, la quantita' conta le sedute invece dei
    pacchetti solo se il prezzo a unita' (totale/quantita') e' piu' vicino,
    per rapporto, al prezzo di una seduta che a quello di un pacchetto —
    cosi' un pacchetto scontato resta un pacchetto. Senza prezzo o senza
    totale vale la vecchia regola: la quantita' uguale alle sedute del
    servizio le conta, il resto sono pacchetti."""
    n = int(servizio['sedute'] or 0)
    try:
        q = float(qty)
    except (TypeError, ValueError):
        q = 1.0
    if n <= 0 or q <= 0:
        return 0
    prezzo = servizio['prezzo_cents']
    if q > 1:
        if prezzo and total_cents is not None:
            # sessioni iff totale/qty piu' vicino, per rapporto, a prezzo/n che
            # a prezzo: il punto di parita' e' la media geometrica dei due,
            # cioe' prezzo/sqrt(n); senza radici e senza float, al quadrato:
            # totale² × n < prezzo² × qty²
            if total_cents ** 2 * n < prezzo ** 2 * qty ** 2:
                return int(q)
        elif q == n:
            return n
    return int(n * q)


def dati_del_servizio(servizio, data):
    """Quello che un pacchetto si porta dietro dal servizio, al momento della
    fattura: il prezzo a seduta di allora e il giorno in cui scade."""
    n = int(servizio['sedute'] or 0)
    prezzo = servizio['prezzo_cents']
    mesi = int(servizio['scadenza_mesi'] or 0)
    scade = None
    if mesi > 0:
        scade = (datetime.date.fromisoformat(data) + relativedelta(months=mesi)).isoformat()
    return {'servizio_id': servizio['id'],
            'prezzo_seduta_cents': prezzo // n if prezzo and n else None,
            'scade': scade}


def _paga(p, numero, sedute, dati, nota=None):
    """La fattura paga il pacchetto: numero, sedute della riga, dati del servizio.

    I crediti diventano le sedute della riga, punto: se il pacchetto ne aveva
    gia' fatte di piu', le rimanenti non restano qui a passare per pagate.
    Le sposta `aggancia_pacchetto`, prima di chiamare questa funzione."""
    p['fatturato'] = f'si - #{numero}'
    p['fattura_numero'] = numero
    if sedute:
        p['crediti'] = int(sedute)
    p.update(dati)
    if nota:
        p['nota'] = nota
    ricalcola(p)


def _accoda_prepagata(reg, chiave, numero, sedute, dati):
    """Mette una fattura in fondo a `prepagate`: chi c'era prima resta il
    primo a essere servito quando un pacchetto si libera (spec: la piu'
    vecchia prima, come gia' fa `_apri_successivo` con le sedute lette dal
    calendario)."""
    prepagate = reg.setdefault('prepagate', {})
    attese = prepagate.get(chiave)
    if not isinstance(attese, list):
        attese = [] if attese in (None, '') else [attese]
    attese.append(dict(numero=numero, sedute=int(sedute), **dati))
    prepagate[chiave] = attese


def aggancia_pacchetto(reg, chiave, numero, data, sedute, servizio):
    """Le sedute di una riga «una volta» entrano nel registro. Tre casi:

      - pacchetto aperto e non ancora fatturato (pieno o no) -> la fattura lo
        paga, con le sedute della riga («Paga quello finito»: un pacchetto
        finito ma da fatturare si comporta come uno quasi finito, non come
        uno gia' incassato)
      - pacchetto aperto e gia' fatturato, non ancora finito -> la fattura
        aspetta in `prepagate`
      - nessun pacchetto aperto, o finito e gia' fatturato -> ne nasce uno
        nuovo; se pero' c'e' gia' una fattura piu' vecchia in coda, tocca a
        lei aprirlo (la piu' vecchia prima) e questa fattura si accoda dietro

    Se il pacchetto che paga aveva gia' piu' sedute fatte di quante ne paga la
    riga, tiene le piu' vecchie (per data, poi per numero) e chiude su quelle;
    le sedute in piu' escono e vanno a `aggiungi_sessione`, che le tratta come
    sedute lette adesso dal calendario: scadenza, fattura in attesa, o un
    pacchetto nuovo da fatturare.

    Ritorna (esito, (frase, valori))."""
    nome = nome_cliente(chiave)
    dati = dati_del_servizio(servizio, data)
    p = pacchetto_aperto_di(reg, chiave)
    if p is not None and p.get('scade') and data > p['scade']:
        chiudi_scaduto(p)
        p = None
    if p is not None and not e_saldato(p):
        sessioni = p.get('sessioni', [])
        paga_n = int(sedute) if sedute else 0
        if paga_n and len(sessioni) > paga_n:
            ordinate = sorted(sessioni, key=lambda s: (s['data'], s['n']))
            tenute, eccesso = ordinate[:paga_n], ordinate[paga_n:]
            for i, s in enumerate(tenute, 1):
                s['n'] = i
            _paga(p, numero, sedute, dati)
            # si chiude PRIMA di piazzare l'eccesso, sennò aggiungi_sessione
            # lo ritroverebbe ancora aperto e ci rimetterebbe dentro le sedute
            p['sessioni'] = tenute
            p['fine'] = tenute[-1]['data']
            ricalcola(p)
            nuovo_id = None
            for s in eccesso:
                piazzata, _aperto = aggiungi_sessione(
                    reg, chiave, s['data'], s['titolo'],
                    s.get('event_id'), s.get('nota'), s.get('ora'))
                # piazzata puo' essere un mese: mensili.aggiungi riordina le
                # sessioni per data, quindi quella appena messa non e'
                # detto che sia l'ultima della lista. E' pero' l'ultima con
                # la sua stessa data e titolo, perche' un pacchetto la
                # accoda in fondo e l'ordinamento di un mese e' stabile.
                ultima = next(x for x in reversed(piazzata['sessioni'])
                              if x['data'] == s['data'] and x['titolo'] == s['titolo'])
                for k, v in s.items():
                    if k != 'n' and k not in ultima:
                        ultima[k] = v
                if nuovo_id is None:
                    nuovo_id = piazzata['id']
            return 'collegato', (
                'Collegata al pacchetto {pid} di {nome}: paga {sedute} sedute, e quelle '
                'già fatte in più ({extra}) passano al pacchetto {nuovo}.',
                {'pid': p['id'], 'nome': nome, 'sedute': paga_n,
                 'extra': len(eccesso), 'nuovo': nuovo_id})
        _paga(p, numero, sedute, dati)
        return 'collegato', (
            'Collegata al pacchetto {pid} di {nome}, che ha ancora {rimasti} sedute.',
            {'pid': p['id'], 'nome': nome, 'rimasti': p['rimasti']})
    if p is not None and p['crediti'] - len(contate(p)) > 0:
        _accoda_prepagata(reg, chiave, numero, sedute, dati)
        return 'in_attesa', (
            '{nome} ha ancora sedute sul pacchetto {pid}: questa fattura resta in attesa '
            'e aprirà il pacchetto successivo alla prima seduta utile.',
            {'nome': nome, 'pid': p['id']})
    if p is not None:
        p['fine'] = max((x['data'] for x in p.get('sessioni', [])), default=None) or p['inizio']
        ricalcola(p)
    if _prima_prepagata(reg, chiave) is not None:
        # una fattura piu' vecchia sta gia' aspettando il turno: tocca a lei
        # aprire il pacchetto dopo (spec: la piu' vecchia prima), non a questa
        # che arriva ora — si accoda anche lei, dietro chi aspettava gia'
        _accoda_prepagata(reg, chiave, numero, sedute, dati)
        nuovo = _apri_successivo(reg, chiave, data)
        if nuovo.get('fattura_numero') == numero:
            return 'nuovo', ('Aperto il pacchetto {pid} per {nome}: {crediti} sedute disponibili.',
                             {'pid': nuovo['id'], 'nome': nome, 'crediti': nuovo['crediti']})
        return 'in_attesa', (
            '{nome} ha altre fatture più vecchie in attesa: questa aprirà il pacchetto '
            'successivo al suo turno.',
            {'nome': nome})
    nuovo = apri_pacchetto(reg, chiave, data, crediti=int(sedute))
    _paga(nuovo, numero, sedute, dati, nota=f'Aperto dalla fattura #{numero}')
    return 'nuovo', ('Aperto il pacchetto {pid} per {nome}: {crediti} sedute disponibili.',
                     {'pid': nuovo['id'], 'nome': nome, 'crediti': nuovo['crediti']})


def _prima_prepagata(reg, chiave):
    """La prima fattura in attesa per quel cliente, senza toglierla: un
    dizionario, un numero (la forma vecchia) oppure None."""
    attese = (reg.get('prepagate') or {}).get(chiave)
    if isinstance(attese, list):
        return attese[0] if attese else None
    return attese or None


def usa_prepagata(reg, chiave, pacchetto):
    """Se c'era una fattura in attesa per quel cliente, la applica al pacchetto nuovo.

    `prepagate` era {chiave: numero}; ora e' {chiave: [attese]}, la piu' vecchia
    prima. La forma vecchia si legge ancora. Ritorna il numero, o None."""
    attesa = _prima_prepagata(reg, chiave)
    if attesa is None:
        return None
    prepagate = reg['prepagate']
    if isinstance(prepagate[chiave], list):
        prepagate[chiave].pop(0)
        if not prepagate[chiave]:
            del prepagate[chiave]
    else:
        del prepagate[chiave]
    if isinstance(attesa, dict):
        numero = attesa['numero']
        _paga(pacchetto, numero, attesa.get('sedute'),
              {k: attesa.get(k) for k in ('servizio_id', 'prezzo_seduta_cents', 'scade')})
    else:
        numero = attesa
        pacchetto['fatturato'] = f'si - #{numero}'
        pacchetto['fattura_numero'] = numero
    pacchetto['nota'] = f'Pagato dalla fattura #{numero} (emessa in anticipo)'
    return numero


def _giorno_breve(iso):
    return datetime.date.fromisoformat(iso).strftime('%d.%m.%Y')


def sedute_dalla_fattura(reg, chiave, numero, data, righe, periodo='', giorno=None):
    """Le sedute delle righe di una fattura appena salvata.

    righe: [(servizio, quantita', totale)] da services.righe_con_sedute.
    Ritorna le frasi da mostrare a chi fattura: [(frase, valori)]."""
    frasi = []
    for servizio, qty, totale in righe:
        if servizio['ogni_mese']:
            try:
                q = float(qty)
            except (TypeError, ValueError):
                q = 1.0
            if q <= 0:
                continue    # spec 7: quantita' 0 o negativa, nessuna seduta
            nome = nome_cliente(chiave)
            m = mensili.da_fattura(reg, chiave, nome, numero, data, servizio, periodo, giorno)
            frasi.append(('Sedute di {nome} dal {dal} al {al}: {sedute}.',
                          {'nome': nome, 'dal': _giorno_breve(m['dal']),
                           'al': _giorno_breve(m['al']), 'sedute': m['disponibili']}))
            continue
        sedute = sedute_della_riga(servizio, qty, totale)
        if sedute <= 0:
            continue
        _esito, frase = aggancia_pacchetto(reg, chiave, numero, data, sedute, servizio)
        frasi.append(frase)
    return frasi
