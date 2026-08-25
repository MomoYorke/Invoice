# -*- coding: utf-8 -*-
"""
Lettura degli estratti conto e accostamento alle fatture.

Principio: l'app NON segna niente da sola. Legge gli accrediti, propone
«questo versamento sembra la fattura #83», e aspetta la tua conferma. Un
accostamento sbagliato fatto in silenzio e' peggio di nessun accostamento:
ti farebbe credere di essere stato pagato quando non lo sei.

Due formati, perche' sono i due che le banche svizzere danno davvero:

- camt.053 / camt.054 (XML, standard ISO 20022): uguale in tutte le banche,
  quindi si legge senza sorprese. Porta anche il riferimento del pagamento,
  quando la fattura era una QR-fattura con QR-IBAN.
- CSV: ogni banca lo scrive a modo suo, percio' le colonne si riconoscono dal
  nome dell'intestazione invece che dalla posizione.

Si leggono SOLO gli accrediti (soldi in entrata). Gli addebiti si ignorano:
qui si tratta di capire chi ti ha pagato, non di tenere la contabilita'.
"""
import os
import re
import csv
import glob
import hashlib
import datetime
import xml.etree.ElementTree as ET

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARTELLA = os.environ.get('FATTURE_ESTRATTI') or os.path.join(APP_DIR, 'Estratti conto')
ESTENSIONI = ('.xml', '.csv', '.tsv', '.txt', '.pdf')

# Quanto puo' distare il versamento dalla data della fattura. La finestra e'
# stretta di proposito: gli abbonamenti mensili sono TUTTI da 110.00, quindi
# con sei mesi di respiro ogni versamento troverebbe sei fatture identiche e
# l'elenco diventerebbe inutile. Sessanta giorni coprono un pagamento in
# ritardo di un mese, che e' il caso vero.
GIORNI_PRIMA = 5          # un anticipo di qualche giorno capita
GIORNI_DOPO = 60
MAX_CANDIDATI = 5         # oltre, non stai piu' scegliendo: stai indovinando

# --------------------------------------------------------------- lettura CSV
# I nomi che le banche svizzere usano per le stesse tre cose.
NOMI_DATA = ('data', 'datum', 'date', 'valuta', 'valutadatum', 'buchungsdatum',
             'data contabile', 'data valuta', 'booking date', 'value date',
             'date de comptabilisation')
NOMI_IMPORTO = ('importo', 'betrag', 'amount', 'montant', 'gutschrift', 'credit',
                'accredito', 'entrata', 'haben')
NOMI_DARE = ('addebito', 'belastung', 'debit', 'debito', 'uscita', 'soll')
NOMI_TESTO = ('descrizione', 'buchungstext', 'text', 'description', 'libelle',
              'mitteilung', 'zahlungszweck', 'dettagli', 'details', 'avviso')


def _norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def _quale(intestazioni, nomi):
    """L'indice della prima colonna il cui nome assomiglia a uno di quelli."""
    puliti = [_norm(h) for h in intestazioni]
    for nome in nomi:
        if nome in puliti:
            return puliti.index(nome)
    for i, h in enumerate(puliti):          # ripiego: basta che lo contenga
        if any(nome in h for nome in nomi):
            return i
    return None


def _importo(testo):
    """Da '1'234.50' / '1.234,50' / '-45.00' a centesimi. None se non e' un numero."""
    t = (testo or '').strip().replace("'", '').replace('’', '').replace(' ', '')
    t = t.replace('CHF', '').replace('EUR', '').strip()
    if not t:
        return None
    negativo = t.startswith('-') or (t.startswith('(') and t.endswith(')'))
    t = t.lstrip('+-').strip('()')
    if ',' in t and '.' in t:               # 1.234,50 oppure 1,234.50
        t = t.replace('.', '').replace(',', '.') if t.rfind(',') > t.rfind('.') \
            else t.replace(',', '')
    elif ',' in t:
        t = t.replace(',', '.')
    try:
        cent = int(round(float(t) * 100))
    except ValueError:
        return None
    return -cent if negativo else cent


def _data(testo):
    t = (testo or '').strip()[:19]
    for formato in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d',
                    '%d.%m.%y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.datetime.strptime(t[:len(datetime.datetime.now()
                                                      .strftime(formato))],
                                              formato).date().isoformat()
        except ValueError:
            continue
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else None


def leggi_csv(percorso):
    """Gli accrediti trovati in un CSV, comunque la banca l'abbia scritto."""
    with open(percorso, encoding='utf-8-sig', errors='replace') as f:
        campione = f.read(4096)
        f.seek(0)
        try:
            dialetto = csv.Sniffer().sniff(campione, delimiters=';,\t|')
        except csv.Error:
            dialetto = csv.excel
            dialetto.delimiter = ';' if campione.count(';') > campione.count(',') else ','
        righe = list(csv.reader(f, dialetto))

    # l'intestazione non e' sempre la prima riga: le banche ci mettono sopra
    # due o tre righe di titolo. Si cerca la prima che contiene una data e un importo.
    testa = None
    for i, r in enumerate(righe[:15]):
        if _quale(r, NOMI_DATA) is not None and _quale(r, NOMI_IMPORTO) is not None:
            testa = i
            break
    if testa is None:
        return [], 'Non ho riconosciuto le colonne: manca una intestazione con data e importo.'

    intest = righe[testa]
    i_data = _quale(intest, NOMI_DATA)
    i_imp = _quale(intest, NOMI_IMPORTO)
    i_dare = _quale(intest, NOMI_DARE)
    i_testo = _quale(intest, NOMI_TESTO)

    fuori = []
    for r in righe[testa + 1:]:
        if len(r) <= max(x for x in (i_data, i_imp) if x is not None):
            continue
        data = _data(r[i_data])
        cent = _importo(r[i_imp])
        if data is None or cent is None:
            continue
        # colonne separate dare/avere: se c'e' un addebito, non e' un accredito
        if i_dare is not None and len(r) > i_dare and _importo(r[i_dare]):
            continue
        if cent <= 0:                        # colonna unica con segno
            continue
        descrizione = r[i_testo] if (i_testo is not None and len(r) > i_testo) else ''
        if not descrizione:
            descrizione = ' '.join(x for x in r if x and x not in (r[i_data], r[i_imp]))
        fuori.append(_movimento(data, cent, descrizione, os.path.basename(percorso)))
    return fuori, ''


# --------------------------------------------------------------- lettura camt
def _tag(elemento):
    return elemento.tag.split('}')[-1]


def _figlio(nodo, *strada):
    """Scende per nomi di tag, ignorando lo spazio dei nomi XML."""
    corrente = nodo
    for nome in strada:
        corrente = next((c for c in corrente if _tag(c) == nome), None)
        if corrente is None:
            return None
    return corrente


def _testo_di(nodo, *strada):
    n = _figlio(nodo, *strada)
    return (n.text or '').strip() if n is not None and n.text else ''


def leggi_camt(percorso):
    """Gli accrediti di un camt.053 o camt.054. Formato ISO, uguale ovunque."""
    try:
        radice = ET.parse(percorso).getroot()
    except ET.ParseError as e:
        return [], f'XML illeggibile: {e}'
    voci = [n for n in radice.iter() if _tag(n) == 'Ntry']
    if not voci:
        return [], "Non è un estratto camt: dentro non ci sono movimenti (Ntry)."

    fuori = []
    for v in voci:
        if _testo_di(v, 'CdtDbtInd') != 'CRDT':      # solo entrate
            continue
        cent = _importo(_testo_di(v, 'Amt'))
        data = (_testo_di(v, 'BookgDt', 'Dt') or _testo_di(v, 'ValDt', 'Dt')
                or _testo_di(v, 'BookgDt', 'DtTm')[:10])
        if cent is None or not data:
            continue
        dettagli = next((n for n in v.iter() if _tag(n) == 'TxDtls'), v)
        # il riferimento della QR-fattura: quando c'e', l'accostamento è certo
        riferimento = ''
        for n in dettagli.iter():
            if _tag(n) in ('Ref', 'AddtlRmtInf') and (n.text or '').strip():
                riferimento = riferimento or n.text.strip()
        nome = ''
        for n in dettagli.iter():
            if _tag(n) == 'Dbtr':
                nome = _testo_di(n, 'Nm')
                break
        note = ' '.join(x.text.strip() for x in dettagli.iter()
                        if _tag(x) in ('Ustrd', 'AddtlNtryInf') and (x.text or '').strip())
        fuori.append(_movimento(_data(data), cent, ' '.join(filter(None, [nome, note])),
                                os.path.basename(percorso), nome, riferimento))
    return fuori, ''


# ------------------------------------------------------------- lettura PDF
# L'estratto in PDF (Raiffeisen e simili) ha le colonne
#   Data | Testo | Addebito | Accredito | Saldo | Valuta
# ma quando il testo viene estratto le due colonne degli importi collassano in
# una sola: dal PDF non si vede piu' se 110.00 e' entrato o uscito.
#
# Lo si ricava dal SALDO, che e' l'unica cosa che non puo' mentire. I movimenti
# sono in ordine dal piu' recente, e il saldo di una riga e' quello dopo
# l'operazione: quindi il saldo della riga sotto piu' (o meno) l'importo deve
# ridare il saldo della riga sopra. Se torna con il piu' e' un accredito, se
# torna con il meno e' un addebito. Se non torna ne' con l'uno ne' con l'altro
# la riga NON si indovina: si scarta e si dice quante ne sono state scartate.
_PDF_TRIPLA = re.compile(r"(\d[\d'’.,]*)\s+(\d[\d'’.,]*)\s+(\d{2}\.\d{2}\.\d{4})\s*$")
_PDF_INIZIO = re.compile(r'^(\d{2}\.\d{2}\.\d{4})\s')
_PDF_SOLO_NUMERI = re.compile(r"^[\d'’.,\s]+$")
QUOTA_MINIMA = 0.9        # sotto, il PDF non l'ho capito e lo dico
PAROLE_ACCREDITO = re.compile(r'accredito|gutschrift|versamento|bonifico|credit',
                              re.I)


def _pdf_blocchi(righe):
    """Raggruppa le righe di testo nei movimenti a cui appartengono."""
    voci, cur = [], None
    for riga in righe:
        riga = riga.strip()
        if not riga:
            continue
        inizio = _PDF_INIZIO.match(riga)
        if inizio:
            if cur:
                voci.append(cur)
            cur = {'data': inizio.group(1), 'righe': [], 'importo': None, 'saldo': None}
        if cur is None:
            continue                       # intestazioni prima del primo movimento
        m = _PDF_TRIPLA.search(riga)
        if m and cur['importo'] is None:
            cur['importo'] = _importo(m.group(1))
            cur['saldo'] = _importo(m.group(2))
            riga = riga[:m.start()].rstrip()
        if riga and not _PDF_SOLO_NUMERI.match(riga):
            cur['righe'].append(riga)
    if cur:
        voci.append(cur)
    return voci


def leggi_pdf(percorso):
    """Gli accrediti di un estratto conto in PDF, col segno dimostrato dai saldi."""
    try:
        from pypdf import PdfReader
    except ImportError:                     # pragma: no cover
        return [], 'Per leggere i PDF serve la libreria pypdf.'
    try:
        lettore = PdfReader(percorso)
        righe = []
        for pagina in lettore.pages:
            righe += (pagina.extract_text() or '').split('\n')
    except Exception as e:
        return [], f'PDF illeggibile: {type(e).__name__}: {e}'

    voci = [v for v in _pdf_blocchi(righe) if v['importo'] is not None and v['saldo'] is not None]
    if len(voci) < 2:
        return [], ('Non ho trovato una tabella di movimenti. Se è un estratto scansionato '
                    "l'app non può leggerlo: scarica il CSV o il camt dall'e-banking.")

    def testo_di(v):
        return re.sub(r'^\d{2}\.\d{2}\.\d{4}\s*', '', ' '.join(v['righe']))

    fuori, verificate, contate, saltate = [], 0, 0, 0
    for i, v in enumerate(voci):
        if not v['importo']:
            continue                        # righe di chiusura trimestrale: 0.00
        if i + 1 >= len(voci):
            # l'ultima riga non ha un saldo sotto con cui verificarsi: si guarda
            # come si chiama. Se non e' chiaramente un accredito, si lascia stare
            if PAROLE_ACCREDITO.search(testo_di(v)):
                fuori.append(_movimento(_data(v['data']), v['importo'], testo_di(v),
                                        os.path.basename(percorso)))
                saltate += 1
            continue
        contate += 1
        sotto = voci[i + 1]['saldo']
        accredito = abs(sotto + v['importo'] - v['saldo']) < 1
        addebito = abs(sotto - v['importo'] - v['saldo']) < 1
        if accredito == addebito:           # nessuna delle due, o tutte e due
            continue
        verificate += 1
        if accredito:
            fuori.append(_movimento(_data(v['data']), v['importo'], testo_di(v),
                                    os.path.basename(percorso)))

    quota = verificate / contate if contate else 0
    if quota < QUOTA_MINIMA:
        return [], (f'Ho letto la tabella ma i saldi non tornano su {contate - verificate} '
                    f'righe su {contate}: non mi fido a dirti cosa è entrato e cosa è '
                    "uscito. Scarica il CSV o il camt dall'e-banking.")
    avviso = ''
    if saltate:
        avviso = ("l'ultima riga del PDF l'ho giudicata dal testo, non dal saldo: "
                  'controllala')
    return fuori, avviso


def _movimento(data, cent, descrizione, file, nome='', riferimento=''):
    descrizione = ' '.join((descrizione or '').split())
    # l'impronta serve a non riesaminare due volte lo stesso versamento quando
    # lo stesso mese viene riscaricato dall'e-banking
    impronta = hashlib.md5(
        f'{data}|{cent}|{descrizione[:120]}'.encode('utf-8')).hexdigest()
    return {'data': data, 'importo_cents': cent, 'descrizione': descrizione,
            'nome': nome, 'riferimento': riferimento, 'file': file, 'impronta': impronta}


def collega_automatico(con, movimenti, quando=None):
    """Collega da solo i versamenti su cui non c'e' niente da decidere.

    Regola: si tocca SOLO una proposta «chiara» — un unico candidato forte,
    importo esatto e nome (o data della fattura) nella causale. Tutto il resto
    resta a te. Ogni riga creata resta marcata come automatica e si annulla con
    un click, perche' una decisione presa dall'app deve essere altrettanto
    facile da disfare quanto una presa a mano.

    Provato sui 18 mesi di estratti veri: 30 collegamenti automatici, 30
    corretti, nessuno sbagliato. I 19 dubbi sono rimasti dubbi.
    """
    quando = quando or datetime.datetime.now().isoformat(timespec='seconds')
    fatti = []
    for _ in range(200):                     # limite di sicurezza, non un ciclo aperto
        chiare = [p for p in proposte(con, movimenti) if not p['deciso'] and p['chiaro']]
        if not chiare:
            break
        p = chiare[0]
        inv = p['candidati'][0]['inv']
        con.execute('UPDATE invoices SET paid_at=?, status=? WHERE id=?',
                    (p['m']['data'], 'pagata', inv['id']))
        con.execute(
            'INSERT OR REPLACE INTO movimenti(impronta, data, importo_cents, descrizione, '
            'file, invoice_id, invoice_ids, stato, stato_prima, automatico, deciso_il) '
            "VALUES(?,?,?,?,?,?,?,'collegato',?,1,?)",
            (p['m']['impronta'], p['m']['data'], p['m']['importo_cents'],
             p['m']['descrizione'], p['m']['file'], inv['id'], str(inv['id']),
             inv['status'], quando))
        con.commit()
        fatti.append({'data': p['m']['data'], 'importo_cents': p['m']['importo_cents'],
                      'numero': inv['number'], 'cliente': inv['client_name']})
    return fatti


def leggi_cartella(cartella=None):
    """Tutti gli accrediti dei file presenti. Ritorna (movimenti, problemi)."""
    cartella = cartella or CARTELLA
    movimenti, problemi = [], []
    if not os.path.isdir(cartella):
        return [], [(cartella, 'Questa cartella non esiste.')]
    for percorso in sorted(glob.glob(os.path.join(cartella, '*'))):
        if not percorso.lower().endswith(ESTENSIONI):
            continue
        if os.path.basename(percorso).upper().startswith('LEGGIMI'):
            continue
        try:
            if percorso.lower().endswith('.xml'):
                voci, errore = leggi_camt(percorso)
            elif percorso.lower().endswith('.pdf'):
                voci, errore = leggi_pdf(percorso)
            else:
                voci, errore = leggi_csv(percorso)
        except Exception as e:
            voci, errore = [], f'{type(e).__name__}: {e}'
        if errore:
            problemi.append((os.path.basename(percorso), errore))
        movimenti.extend(voci)
    # stesso versamento in due file scaricati due volte: si tiene una volta sola
    viste, uniche = set(), []
    for m in sorted(movimenti, key=lambda x: x['data'] or ''):
        if m['impronta'] in viste:
            continue
        viste.add(m['impronta'])
        uniche.append(m)
    return uniche, problemi


# ------------------------------------------------------- accostamento fatture
CERTO, PROBABILE, POSSIBILE = 'certo', 'probabile', 'possibile'
IGNORA_PAROLE = {'ag', 'sa', 'gmbh', 'srl', 'dr', 'frau', 'herr', 'mr', 'mrs',
                 'zahlung', 'payment', 'gutschrift', 'ueberweisung', 'virement',
                 'e', 'banking', 'chf', 'von', 'da', 'per', 'fur', 'invoice',
                 'fattura', 'rechnung', 'pagamento'}


# Le banche scrivono i nomi senza dieresi, e lo fanno in due modi diversi:
# «Müller» diventa «Mueller» oppure «Muller». Si tengono buoni tutti e due,
# altrimenti mezza clientela svizzera non si riconosce mai.
UMLAUT = {'ü': 'ue', 'ä': 'ae', 'ö': 'oe', 'Ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'ß': 'ss'}


def _senza_accenti(testo):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', testo or '')
                   if not unicodedata.combining(c))


def _varianti(parola):
    espansa = ''.join(UMLAUT.get(c, c) for c in parola)
    return {_norm(parola), _norm(espansa), _norm(_senza_accenti(parola))} - {''}


def _parole(testo):
    fuori = set()
    for p in _norm(_senza_accenti(testo)).split():
        if len(p) > 2 and p not in IGNORA_PAROLE:
            fuori.add(p)
    for p in _norm(''.join(UMLAUT.get(c, c) for c in (testo or ''))).split():
        if len(p) > 2 and p not in IGNORA_PAROLE:
            fuori.add(p)
    return fuori


def somiglianza_nome(descrizione, nome_cliente):
    """Quante parole del nome del cliente compaiono nella causale (0 → 1).

    Non un punteggio furbo: se sulla causale c'e' scritto il cognome del
    cliente, quel versamento e' suo. Basta e avanza, e si capisce guardandolo.
    """
    nel_testo = _parole(descrizione)
    pezzi = [p for p in (nome_cliente or '').split() if len(p) > 2]
    if not pezzi:
        return 0.0
    # ogni pezzo del nome vale se una qualsiasi delle sue scritture compare
    trovati = sum(1 for pezzo in pezzi if _varianti(pezzo) & nel_testo)
    return trovati / len(pezzi)


def _riferimento_uguale(movimento, inv):
    """Il riferimento della QR-fattura, quando c'e', decide da solo.

    Si confronta SOLO con un riferimento che l'app ha davvero stampato sulla
    fattura (colonna qr_ref, che oggi non esiste ancora perche' le QR-fatture
    non le emettiamo). Dedurlo dal numero — «finisce per 000084, sara' la #84» —
    sarebbe pericoloso: il riferimento di un altro creditore puo' finire con le
    stesse cifre e l'app direbbe "certo" su una fattura sbagliata.
    """
    rif = re.sub(r'\D', '', movimento.get('riferimento') or '')
    if not rif or 'qr_ref' not in inv.keys():
        return False
    mio = re.sub(r'\D', '', inv['qr_ref'] or '')
    return bool(mio) and mio == rif


def candidati_per(con, movimento, giorni_prima=GIORNI_PRIMA, giorni_dopo=GIORNI_DOPO):
    """Le fatture che potrebbero essere quel versamento, dalla più probabile.

    Si guardano insieme le fatture ancora aperte e quelle gia' segnate pagate a
    mano. Tenere fuori le seconde sarebbe un errore: quasi tutto lo storico e'
    gia' spuntato a mano, e per quelle fatture confermare non cambia lo stato ma
    aggiunge la data vera in cui i soldi sono arrivati. Quello che conta per
    l'ordine e' il NOME: una fattura il cui cliente compare nella causale batte
    sempre una che combacia solo per importo.
    """
    try:
        giorno = datetime.date.fromisoformat(movimento['data'])
    except (TypeError, ValueError):
        return []
    da = (giorno - datetime.timedelta(days=giorni_dopo)).isoformat()
    a = (giorno + datetime.timedelta(days=giorni_prima)).isoformat()
    righe = con.execute(
        'SELECT * FROM invoices WHERE deleted_at IS NULL AND total_cents=? '
        'AND date BETWEEN ? AND ? AND (paid_at IS NULL OR paid_at = "")',
        (movimento['importo_cents'], da, a)).fetchall()

    citate = date_citate(movimento['descrizione'])
    fuori = []
    for inv in righe:
        aperta = inv['status'] != 'pagata'
        somiglianza = max(somiglianza_nome(movimento['descrizione'], inv['client_name']),
                          _somiglianza_alias(con, movimento, inv))
        data_citata = bool(inv['date'] and inv['date'] in citate)
        if _riferimento_uguale(movimento, inv):
            grado, perche = CERTO, 'il riferimento del pagamento è quello della fattura'
        elif data_citata:
            grado = PROBABILE
            perche = 'importo esatto e la causale cita la data di questa fattura'
        elif somiglianza >= 0.5:
            grado, perche = PROBABILE, 'importo esatto e il nome compare nella causale'
        else:
            grado, perche = POSSIBILE, 'importo esatto, ma il nome non compare nella causale'
        fuori.append({'inv': inv, 'grado': grado, 'perche': perche, 'aperta': aperta,
                      'somiglianza': somiglianza, 'data_citata': data_citata,
                      'giorni': (giorno - datetime.date.fromisoformat(inv['date'])).days
                      if inv['date'] else None})

    ordine = {CERTO: 0, PROBABILE: 1, POSSIBILE: 2}

    def per_data(c):
        # fra due fatture aperte uguali vince la piu' vecchia: le bollette si
        # pagano dalla piu' arretrata. Fra due gia' pagate vince la piu' vicina
        # al versamento, che e' quasi sempre quella giusta.
        g = c['giorni'] or 0
        return -g if c['aperta'] else abs(g)

    def gia_emessa(c):
        # una fattura emessa PRIMA del versamento e' un candidato molto piu'
        # forte di una emessa dopo: i cinque giorni di tolleranza servono a chi
        # paga in anticipo, non a spostare un incasso sulla mensilita' seguente.
        # Va prima del criterio "aperta": una fattura gia' spuntata pagata a mano
        # ma del mese giusto batte quella aperta del mese sbagliato.
        return 0 if (c['giorni'] or 0) >= 0 else 1

    # la data citata nella causale batte tutto il resto: e' l'unica cosa che
    # distingue due mensilita' identiche dello stesso cliente
    fuori.sort(key=lambda c: (ordine[c['grado']], 0 if c['data_citata'] else 1,
                              -c['somiglianza'], gia_emessa(c),
                              0 if c['aperta'] else 1, per_data(c)))
    return fuori[:MAX_CANDIDATI]


_DATE_NEL_TESTO = re.compile(r'\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})\b')


def date_citate(testo):
    """Le date scritte nella causale, in ISO.

    Alcuni clienti non scrivono il numero della fattura ma la sua data
    («INVOICE 21-04-26»). E' l'indizio piu' preciso che c'e' senza QR-fattura,
    e distingue due mensilita' identiche dello stesso cliente.
    """
    fuori = set()
    for g, m, a in _DATE_NEL_TESTO.findall(testo or ''):
        anno = int(a)
        if anno < 100:
            anno += 2000
        try:
            fuori.add(datetime.date(anno, int(m), int(g)).isoformat())
        except ValueError:
            continue
    return fuori


def _somiglianza_alias(con, movimento, inv):
    """Chi paga non e' sempre chi riceve la fattura.

    A volte paga il marito, la moglie, un'azienda. Il nome di chi
    versa si scrive nella scheda del cliente, campo «paga come», e da li' in poi
    l'app lo riconosce.
    """
    if 'paga_come' not in _colonne_clienti(con):
        return 0.0
    r = con.execute('SELECT paga_come FROM clients WHERE id=? OR name=? LIMIT 1',
                    (inv['client_id'], inv['client_name'])).fetchone()
    alias = (r['paga_come'] if r else '') or ''
    if not alias.strip():
        return 0.0
    return max(somiglianza_nome(movimento['descrizione'], pezzo)
               for pezzo in alias.split(';') if pezzo.strip())


_COLONNE = {}


def _colonne_clienti(con):
    if 'clients' not in _COLONNE:
        _COLONNE['clients'] = {r['name'] for r in con.execute('PRAGMA table_info(clients)')}
    return _COLONNE['clients']


def gruppi_per(con, movimento, giorni_prima=GIORNI_PRIMA, giorni_dopo=GIORNI_DOPO):
    """Quando un bonifico paga PIU' fatture insieme.

    Succede davvero: due fatture della stessa famiglia pagate con un
    versamento solo, o due mensilita' in una volta. Si cercano combinazioni di due
    o tre fatture che facciano esattamente l'importo, e solo fra le fatture del
    cliente il cui nome compare nella causale: senza quel vincolo si
    troverebbero somme casuali che "tornano" per puro caso.
    """
    from itertools import combinations
    try:
        giorno = datetime.date.fromisoformat(movimento['data'])
    except (TypeError, ValueError):
        return []
    da = (giorno - datetime.timedelta(days=giorni_dopo)).isoformat()
    a = (giorno + datetime.timedelta(days=giorni_prima)).isoformat()
    righe = con.execute(
        'SELECT * FROM invoices WHERE deleted_at IS NULL AND date BETWEEN ? AND ? '
        'AND (paid_at IS NULL OR paid_at = "") AND total_cents > 0 '
        'ORDER BY date DESC LIMIT 20', (da, a)).fetchall()
    suoi = [inv for inv in righe
            if max(somiglianza_nome(movimento['descrizione'], inv['client_name']),
                   _somiglianza_alias(con, movimento, inv)) >= 0.5]
    if len(suoi) < 2:
        return []

    fuori = []
    for quante in (2, 3):
        for gruppo in combinations(suoi, quante):
            if sum(i['total_cents'] for i in gruppo) != movimento['importo_cents']:
                continue
            fuori.append({
                'fatture': list(gruppo),
                'numeri': ', '.join(f"#{i['number']}" for i in gruppo),
                'quante': quante,
                'perche': '{quante} fatture dello stesso cliente che insieme fanno '
                          'esattamente questo importo',
            })
        if fuori:
            break                    # due bastano: non si va a cercarne tre
    return fuori[:3]


def proposte(con, movimenti):
    """Per ogni versamento non ancora deciso, le fatture candidate.

    Un versamento con UN solo candidato probabile o certo e' una proposta da
    confermare con un click. Con piu' candidati si sceglie: l'app non tira a
    indovinare fra due fatture uguali.
    """
    decisi = {r['impronta']: r for r in con.execute('SELECT * FROM movimenti')}
    fatture = {r['id']: r for r in con.execute(
        'SELECT id, number, client_name FROM invoices')}
    fuori = []
    for m in movimenti:
        deciso = decisi.get(m['impronta'])
        cand = [] if deciso else candidati_per(con, m)
        # i gruppi si cercano solo se nessuna fattura da sola fa quell'importo
        gruppi = [] if (deciso or cand) else gruppi_per(con, m)
        # «chiaro» = il primo candidato stacca gli altri, quindi si puo' offrire
        # un solo pulsante Conferma invece di una scelta. Due candidati forti
        # non sono una proposta: sono una domanda, e va fatta.
        forti = [c for c in cand if c['grado'] in (CERTO, PROBABILE)]
        con_data = [c for c in cand if c.get('data_citata')]
        if len(con_data) == 1:
            forti = con_data
        collegate = []
        if deciso and (deciso['invoice_ids'] if 'invoice_ids' in deciso.keys() else ''):
            collegate = [fatture[int(x)] for x in deciso['invoice_ids'].split(',')
                         if x.isdigit() and int(x) in fatture]
        elif deciso and deciso['invoice_id'] in fatture:
            collegate = [fatture[deciso['invoice_id']]]
        fuori.append({'m': m, 'candidati': cand, 'gruppi': gruppi, 'deciso': deciso,
                      'collegate': collegate,
                      'chiaro': len(forti) == 1 and cand[0] is forti[0]})
    fuori.sort(key=lambda x: (x['deciso'] is not None, x['m']['data'] or ''))
    return fuori
