# -*- coding: utf-8 -*-
"""
Il listino: i servizi che vendi, e come si riconoscono nelle righe di fattura.

Il servizio e' l'unica fonte di nome, prezzo e sedute. La fattura, le sedute,
l'email e gli abbonamenti leggono da qui: prima le stesse cose stavano scritte
in sei posti che non si parlavano.

Restano qui anche gli aiuti sulle date degli abbonamenti: una descrizione come
«Abbonamento mensile 01.07.26 - 31.07.26» il mese dopo va rifatta identica con
le date spostate avanti, qualunque sia il testo attorno alle date.

Le vecchie regole «Nome = parole» (`regole`, `riconosci`) e `piu_usati` servono
solo alla migrazione (core/migra_servizi.py): l'app non le usa piu'.
"""
import re
import datetime

from dateutil.relativedelta import relativedelta

from . import language as L
from .money import fmt_chf, parse_amount

RX_DATA = re.compile(r'(\d{1,2})([.\-/])(\d{1,2})[.\-/](\d{2,4})')
QUANTI_PROPOSTI = 6
VIRGOLETTE = re.compile('["\'`«»“”„‘’]')


def elenco(con, settings):
    """I servizi da proporre. Prima quelli scritti a mano; se non ce ne sono,
    quelli piu' usati nelle fatture."""
    scritti = [r.strip() for r in (settings.get('servizi') or '').splitlines() if r.strip()]
    if scritti:
        return scritti[:12]
    return piu_usati(con)


def piu_usati(con, quanti=QUANTI_PROPOSTI):
    """Le descrizioni piu' ricorrenti, ripulite dal periodo.

    Le date vanno tolte prima di contare, altrimenti ogni mese e' una
    descrizione diversa e non si ripete mai niente."""
    conteggio = {}
    for r in con.execute(
            'SELECT i.description d FROM items i JOIN invoices f ON f.id = i.invoice_id '
            'WHERE f.deleted_at IS NULL AND i.description <> "" '
            'ORDER BY COALESCE(f.number, 0) DESC LIMIT 400'):
        testo = senza_date(r['d'])
        if len(testo) < 4:
            continue
        voce = conteggio.setdefault(testo, {'n': 0, 'testo': testo})
        voce['n'] += 1
    ordinati = sorted(conteggio.values(), key=lambda v: -v['n'])
    return [v['testo'] for v in ordinati[:quanti] if v['n'] > 1]


def senza_date(descrizione):
    """La descrizione senza il periodo: «Abbo 01.07.26 - 31.07.26» -> «Abbo»."""
    testo = RX_DATA.sub('', descrizione or '')
    testo = re.sub(r'\s+', ' ', testo)
    return testo.strip(' –—-,;:')


def stesso_servizio(a, b):
    """True se due descrizioni sono lo stesso servizio, periodo a parte."""
    x, y = senza_date(a).lower(), senza_date(b).lower()
    if not x or not y:
        return False
    return x == y or x.startswith(y) or y.startswith(x)


def avanza_periodo(descrizione, mesi=1):
    """Sposta avanti di un mese le due date della descrizione, lasciando
    intatto tutto il resto: il testo attorno alle date non lo tocchiamo,
    perche' e' quello che ha scritto chi usa l'app.

    Ritorna None se le date non sono due o non sono date vere."""
    trovate = list(RX_DATA.finditer(descrizione or ''))
    if len(trovate) < 2:
        return None
    date = []
    for m in trovate[:2]:
        giorno, mese, anno = int(m.group(1)), int(m.group(3)), int(m.group(4))
        if anno < 100:
            anno += 2000
        try:
            date.append(datetime.date(anno, mese, giorno))
        except ValueError:
            return None
    fuori, ultimo = '', 0
    for m, d in zip(trovate[:2], date):
        nuova = d + relativedelta(months=mesi)
        sep = m.group(2)
        anno = nuova.strftime('%y') if len(m.group(4)) == 2 else nuova.strftime('%Y')
        fuori += descrizione[ultimo:m.start()] + f'{nuova.day:02d}{sep}{nuova.month:02d}{sep}{anno}'
        ultimo = m.end()
    return fuori + descrizione[ultimo:]


# --- Riconoscere il servizio di una riga di fattura -------------------------
#
# Prima queste regole stavano scritte nel programma, ed erano i tre servizi di
# chi l'app l'ha scritta per se'. Adesso stanno nelle Impostazioni: due elenchi,
# uno per gli abbonamenti e uno per i pacchetti, una riga per servizio.
#
#     Nome del servizio = parola, parola, parola
#
# Le parole sono quelle che compaiono nelle righe della fattura. Senza «=», il
# nome fa anche da parola. L'ordine conta: vince la prima regola che riconosce,
# e gli abbonamenti si provano prima perche' le loro parole sono piu' precise.

MODELLI_SERVIZIO = (('servizi_abbonamento', 'coaching'),
                    ('servizi_pacchetto', 'pt'))


def _regola(riga):
    """«Nome = a, b» -> ('Nome', ['a', 'b']). None se la riga non dice niente."""
    nome, _uguale, parole = (riga or '').partition('=')
    nome = nome.strip()
    if not nome:
        return None
    chiavi = [p.strip().lower() for p in parole.split(',') if p.strip()]
    return (nome, chiavi or [nome.lower()])


def regole(settings):
    """[(nome, modello, parole)] nell'ordine in cui vanno provate."""
    fuori = []
    for chiave, modello in MODELLI_SERVIZIO:
        for riga in ((settings or {}).get(chiave) or '').splitlines():
            r = _regola(riga)
            if r:
                fuori.append((r[0], modello, r[1]))
    return fuori


def riconosci(descrizione, settings):
    """(nome, modello) della prima regola che riconosce la riga.

    (None, None) se non la riconosce nessuna: e' un risultato buono quanto gli
    altri. Chi usa l'app vende quello che vende, e inventargli un servizio che
    non ha e' peggio che non nominarlo."""
    testo = (descrizione or '').lower()
    if not testo:
        return (None, None)
    for nome, modello, parole in regole(settings):
        if any(p in testo for p in parole):
            return (nome, modello)
    return (None, None)


# --- La scheda del servizio ---------------------------------------------------

def normalizza_testo(testo):
    """Il testo di una riga ridotto a quello che conta per riconoscerla:
    senza date, senza virgolette, minuscolo, spazi compattati."""
    t = VIRGOLETTE.sub('', senza_date(testo or ''))
    return re.sub(r'\s+', ' ', t).strip(' –—-,;:').lower()


def _intero(valore):
    try:
        return int(str(valore).strip())
    except (TypeError, ValueError):
        return None


def dal_modulo(f):
    """I campi della scheda come arrivano dal modulo, gia' letti.

    Le domande che non si vedono non valgono: se «Comprende sedute?» e' No, un
    numero rimasto nella casella nascosta non deve diventare 12 sedute."""
    ogni_mese = f.get('ogni_mese') == '1'
    con_sedute = f.get('con_sedute') == '1'
    scadono = con_sedute and not ogni_mese and f.get('scadono') == '1'
    passano = con_sedute and ogni_mese and f.get('passano') == '1'
    prezzo_testo = (f.get('prezzo') or '').strip()
    return {
        'nome': re.sub(r'\s+', ' ', f.get('nome') or '').strip(),
        'prezzo_testo': prezzo_testo,
        'prezzo_cents': parse_amount(prezzo_testo) if prezzo_testo else None,
        'ogni_mese': 1 if ogni_mese else 0,
        'con_sedute': con_sedute,
        'sedute': _intero(f.get('sedute')) if con_sedute else 0,
        'scadono': scadono,
        'scadenza_mesi': _intero(f.get('scadenza_mesi')) if scadono else 0,
        'passano': 1 if passano else 0,
        'massimo': _intero(f.get('massimo')) if passano else 0,
    }


def _nome_occupato(con, nome, servizio_id=None):
    for s in con.execute('SELECT id, nome FROM servizi WHERE attivo = 1'):
        if s['id'] != servizio_id and s['nome'].strip().lower() == nome.strip().lower():
            return True
    return False


def controlla(con, dati, servizio_id=None):
    """Cosa non va nella scheda: [(frase, valori)], vuota se si puo' salvare."""
    errori = []
    if not dati['nome']:
        errori.append(('Scrivi come si chiama il servizio.', {}))
    elif _nome_occupato(con, dati['nome'], servizio_id):
        errori.append(('C’è già un servizio che si chiama «{nome}».', {'nome': dati['nome']}))
    if not dati['prezzo_testo']:
        errori.append(('Scrivi quanto costa il servizio.', {}))
    elif dati['prezzo_cents'] is None or dati['prezzo_cents'] < 0:
        errori.append(('Il prezzo «{prezzo}» non si capisce: scrivilo per esempio 110.-',
                       {'prezzo': dati['prezzo_testo']}))
    sedute_buone = True
    if dati['con_sedute'] and not (dati['sedute'] and 1 <= dati['sedute'] <= 99):
        errori.append(('Le sedute vanno da 1 a 99.', {}))
        sedute_buone = False
    if dati['scadono'] and not (dati['scadenza_mesi'] and 1 <= dati['scadenza_mesi'] <= 60):
        errori.append(('I mesi di scadenza vanno da 1 a 60.', {}))
    if dati['passano'] and sedute_buone and (dati['massimo'] is None
                                             or dati['massimo'] < dati['sedute']):
        errori.append(('Il massimo non può essere minore delle sedute del mese ({sedute}).',
                       {'sedute': dati['sedute']}))
    return errori


def salva(con, dati, servizio_id=None):
    """Scrive la scheda. Ritorna l'id del servizio."""
    valori = (dati['nome'], dati['prezzo_cents'], dati['ogni_mese'], dati['sedute'] or 0,
              dati['scadenza_mesi'] or 0, dati['passano'], dati['massimo'] or 0)
    if servizio_id:
        con.execute('UPDATE servizi SET nome=?, prezzo_cents=?, ogni_mese=?, sedute=?, '
                    'scadenza_mesi=?, passano=?, massimo=? WHERE id=?',
                    valori + (servizio_id,))
    else:
        pos = con.execute('SELECT COALESCE(MAX(pos), -1) + 1 FROM servizi').fetchone()[0]
        servizio_id = con.execute(
            'INSERT INTO servizi(nome, prezzo_cents, ogni_mese, sedute, scadenza_mesi, '
            'passano, massimo, attivo, pos, creato_il) VALUES(?,?,?,?,?,?,?,1,?,?)',
            valori + (pos, datetime.datetime.now().isoformat(timespec='seconds'))).lastrowid
    con.commit()
    return servizio_id


def tutti(con, solo_attivi=False):
    """I servizi: prima quelli che vendi, nell'ordine in cui li hai messi."""
    dove = ' WHERE attivo = 1' if solo_attivi else ''
    return con.execute('SELECT * FROM servizi%s ORDER BY attivo DESC, pos, id' % dove).fetchall()


def uno(con, servizio_id):
    return con.execute('SELECT * FROM servizi WHERE id=?', (servizio_id,)).fetchone()


def archivia(con, servizio_id, attivo=0):
    """«Non lo vendo più» (attivo=0) o «Lo vendo di nuovo» (attivo=1).

    Non si cancella mai: le fatture vecchie devono poter dire cosa vendevano.
    Riprenderlo non si puo' se nel frattempo un altro servizio ha preso il suo
    nome: due pulsanti uguali in fattura non si distinguono."""
    s = uno(con, servizio_id)
    if s is None:
        return False
    if attivo and _nome_occupato(con, s['nome'], servizio_id):
        return False
    con.execute('UPDATE servizi SET attivo=? WHERE id=?', (1 if attivo else 0, servizio_id))
    con.commit()
    return True


def fatturato(con, servizio_id):
    """Vero se c'e' almeno una fattura (fuori dal Cestino) che lo vende."""
    return con.execute(
        'SELECT 1 FROM items i JOIN invoices f ON f.id = i.invoice_id '
        'WHERE i.servizio_id = ? AND f.deleted_at IS NULL LIMIT 1',
        (servizio_id,)).fetchone() is not None


def massimo_proposto(sedute):
    """Il tetto proposto: le sedute del mese piu' la meta', per eccesso (4 -> 6)."""
    sedute = int(sedute or 0)
    return sedute + (sedute + 1) // 2 if sedute > 0 else 0


def modello(servizio):
    """Il testo di email da usare: abbonamento per «ogni mese», pacchetto per il resto."""
    return 'coaching' if servizio and servizio['ogni_mese'] else 'pt'


def _sedute_in_parole(n, lingua):
    return L.t('1 seduta', lingua) if n == 1 else L.t('{n} sedute', lingua).format(n=n)


def _mesi_in_parole(n, lingua):
    return L.t('1 mese', lingua) if n == 1 else L.t('{n} mesi', lingua).format(n=n)


def riga_breve(s, lingua=None):
    """La riga sotto il nome, nell'elenco: «1'800.00 CHF · 12 sedute»."""
    if s['prezzo_cents'] is None:
        pezzi = [L.t('manca il prezzo', lingua)]
    elif s['ogni_mese']:
        pezzi = [L.t('{prezzo} al mese', lingua).format(prezzo=fmt_chf(s['prezzo_cents']))]
    else:
        pezzi = [fmt_chf(s['prezzo_cents'])]
    n = int(s['sedute'] or 0)
    if n:
        sedute = _sedute_in_parole(n, lingua)
        pezzi.append(L.t('{sedute} al mese', lingua).format(sedute=sedute)
                     if s['ogni_mese'] else sedute)
    return ' · '.join(pezzi)


def riassunto(s, lingua=None):
    """La frase in fondo alla scheda, che dice in parole quello che hai scritto."""
    if s['prezzo_cents'] is None:
        frasi = [L.t('Manca il prezzo.', lingua)]
    elif s['ogni_mese']:
        frasi = [L.t('{prezzo} al mese.', lingua).format(prezzo=fmt_chf(s['prezzo_cents']))]
    else:
        frasi = [L.t('{prezzo}, una volta.', lingua).format(prezzo=fmt_chf(s['prezzo_cents']))]
    n = int(s['sedute'] or 0)
    if n:
        sedute = _sedute_in_parole(n, lingua)
        if not s['ogni_mese'] and s['scadenza_mesi']:
            frasi.append(L.t('{sedute}, da usare entro {mesi}.', lingua).format(
                sedute=sedute, mesi=_mesi_in_parole(int(s['scadenza_mesi']), lingua)))
        elif not s['ogni_mese']:
            frasi.append(L.t('{sedute}, senza scadenza.', lingua).format(sedute=sedute))
        elif s['passano']:
            frasi.append(L.t('Ogni mese {sedute}; quelle non usate passano al mese dopo, '
                             'ma in un mese non se ne possono avere più di {massimo}.',
                             lingua).format(sedute=sedute, massimo=s['massimo']))
        else:
            frasi.append(L.t('Ogni mese {sedute}; quelle non usate si perdono.',
                             lingua).format(sedute=sedute))
    return ' '.join(frasi)


# --- Quale servizio vende una riga ---------------------------------------------

def di_testo(con, descrizione, servizi=None):
    """Il servizio di una riga scritta a mano: id, 0 = «nessun servizio», None = libera.

    Prima il testo gia' deciso una volta (anche «nessun servizio»): e' una
    decisione di chi usa l'app e vince su tutto. Poi il nome di un servizio
    contenuto nel testo, a parola intera: se ce ne sono piu' d'uno vince il
    nome piu' lungo, cosi' «12 Sessions Pack – Personal Training» non diventa
    «Personal Training». Sconti e omaggi restano liberi: non vendono niente, e
    Performance li tratta gia' a parte."""
    from .stats import SCONTI, OMAGGI
    testo = normalizza_testo(descrizione)
    if not testo or SCONTI.search(testo) or OMAGGI.search(testo):
        return None
    deciso = con.execute('SELECT servizio_id FROM servizi_testi WHERE testo=?',
                         (testo,)).fetchone()
    if deciso is not None:
        return deciso['servizio_id']
    if servizi is None:
        servizi = con.execute('SELECT id, nome, attivo FROM servizi').fetchall()
    migliore = None
    for s in servizi:
        nome = normalizza_testo(s['nome'])
        if nome and re.search(r'(?<!\w)%s(?!\w)' % re.escape(nome), testo):
            peso = (len(nome), s['attivo'], -s['id'])
            if migliore is None or peso > migliore[0]:
                migliore = (peso, s['id'])
    return migliore[1] if migliore else None


def ricorda(con, descrizione, servizio_id):
    """Segna che quel testo e' quel servizio (0 = nessuno). Il commit lo fa chi chiama."""
    testo = normalizza_testo(descrizione)
    if testo and servizio_id is not None:
        con.execute('INSERT OR REPLACE INTO servizi_testi(testo, servizio_id) VALUES(?,?)',
                    (testo, int(servizio_id)))


def collega_righe(con):
    """Collega da sole le righe non ancora decise. Ritorna quante ne ha decise.

    Gira alla migrazione e dopo ogni Reimporta, che ricrea le righe importate.
    Il commit lo fa chi chiama."""
    servizi = con.execute('SELECT id, nome, attivo FROM servizi').fetchall()
    decise = 0
    for riga in con.execute('SELECT id, description FROM items '
                            'WHERE servizio_id IS NULL').fetchall():
        sid = di_testo(con, riga['description'], servizi)
        if sid is not None:
            con.execute('UPDATE items SET servizio_id=? WHERE id=?', (sid, riga['id']))
            decise += 1
    return decise


def ultima_riga(con, client_id, servizio_id):
    """L'ultima riga di quel servizio fatturata a quel cliente, fuori dal Cestino."""
    return con.execute(
        'SELECT i.qty, i.description, i.unit_cents, i.total_cents, f.number '
        'FROM items i JOIN invoices f ON f.id = i.invoice_id '
        'WHERE f.deleted_at IS NULL AND f.client_id = ? AND i.servizio_id = ? '
        'ORDER BY f.date DESC, COALESCE(f.number, 0) DESC, i.pos DESC LIMIT 1',
        (client_id, servizio_id)).fetchone()
