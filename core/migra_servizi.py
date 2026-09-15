# -*- coding: utf-8 -*-
"""
Il passaggio, una volta sola, dalle caselle delle Impostazioni al listino.

Prima i servizi stavano in tre caselle: i pulsanti della nuova fattura e due
elenchi di regole «Nome = parole». Adesso sono una tabella, e ogni riga di
fattura sa di quale servizio e'. Qui si costruisce il listino da quello che
c'era e si collegano le righe gia' fatturate.

Le regole del gioco:
- prima una copia di database e registro, in una cartella che la pulizia delle
  copie non tocca;
- i passi sul database stanno in una transazione sola: o tutto o niente;
- ripeterla non cambia niente: la ricorda l'impostazione `servizi_migrati`;
- non si cancella niente: le caselle vecchie restano dove sono;
- se qualcosa va storto l'app parte lo stesso: il guaio va in data/error.log e
  in Controlli, e al prossimo avvio si riprova.
"""
import os
import re
import json
import glob
import shutil
import sqlite3
import logging
import datetime

from . import db as D
from . import services as srv
from . import sessions as sess

MARCATORE = 'servizi_migrati'
ERRORE = 'servizi_migrazione_errore'
CARTELLA_COPIE = 'prima-dei-servizi'


def fatta(con):
    return con.execute('SELECT 1 FROM settings WHERE key=?', (MARCATORE,)).fetchone() is not None


def esegui(con, registro_path=None, fai_copia=True):
    """Fa la migrazione, se non e' ancora fatta. True se l'ha fatta adesso.

    Il registro viene dopo il database, e ci si riprova a ogni avvio finche'
    tutti i pacchetti hanno le loro chiavi."""
    adesso = False
    if not fatta(con):
        try:
            if fai_copia and not _copia_gia_fatta(con):
                copia_di_sicurezza(con, registro_path)
            registro = _leggi_registro(registro_path)
            crea_servizi(con, D.get_settings(con), registro)
            srv.collega_righe(con)
            clienti_da_crediti(con, registro)
            con.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)',
                        (MARCATORE, '1'))
            con.execute('DELETE FROM settings WHERE key=?', (ERRORE,))
            con.commit()
            adesso = True
        except Exception as guaio:
            con.rollback()
            logging.getLogger('fatture.errori').exception('Aggiornamento dei servizi non riuscito')
            try:
                con.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)',
                            (ERRORE, '%s: %s' % (type(guaio).__name__, guaio)))
                con.commit()
            except sqlite3.Error:
                pass        # database bloccato: resta il registro degli errori
            return False
    chiavi_nel_registro(con, registro_path)
    return adesso


def _leggi_registro(path=None):
    """Il registro delle sedute, solo da leggere: {} se non c'e'.

    Non si usa sessions.carica(), che un registro mancante lo crea."""
    try:
        with open(path or sess.REGISTRY, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _copia_gia_fatta(con):
    """True se in backups/prima-dei-servizi/ c'e' gia' una copia di un
    tentativo precedente: un guaio che si ripete a ogni avvio non deve
    scriverne una nuova ogni volta. Un tentativo fallito fa rollback e non
    cambia il database, quindi la prima copia resta buona per il prossimo."""
    riga = next((x for x in con.execute('PRAGMA database_list') if x[1] == 'main'), None)
    percorso = riga[2] if riga else ''
    if not percorso:
        return False
    cartella = os.path.join(os.path.dirname(percorso), 'backups', CARTELLA_COPIE)
    return bool(glob.glob(os.path.join(cartella, 'fatture-*.db')))


def copia_di_sicurezza(con, registro_path=None):
    """Copia database e registro prima di toccarli. Ritorna i file scritti.

    Stanno in backups/prima-dei-servizi/: la pulizia delle copie tiene solo le
    ultime 40 dentro backups/, e questa deve restare. Il database si scrive
    prima sotto un nome temporaneo fisso, che il pattern `fatture-*.db` di
    `_copia_gia_fatta` non riconosce; solo quando anche il registro e' stato
    copiato il file temporaneo diventa `fatture-<data>.db`, con `os.replace`.
    Cosi' un tentativo interrotto a meta' (disco pieno, processo ucciso,
    database bloccato) non lascia mai una copia col nome finale: il prossimo
    tentativo la rifa' da capo, invece di scambiare il rottame per una copia
    buona e non riprovare mai piu'."""
    riga = next((x for x in con.execute('PRAGMA database_list') if x[1] == 'main'), None)
    percorso = riga[2] if riga else ''
    if not percorso or not con.execute('SELECT 1 FROM invoices LIMIT 1').fetchone():
        return []           # database in memoria, o appena nato: niente da perdere
    cartella = os.path.join(os.path.dirname(percorso), 'backups', CARTELLA_COPIE)
    os.makedirs(cartella, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    in_corso = os.path.join(cartella, 'fatture-in-corso.db.tmp')
    if os.path.exists(in_corso):
        os.remove(in_corso)     # un tentativo precedente puo' averlo lasciato a meta'
    dest = sqlite3.connect(in_corso)
    try:
        con.backup(dest)
    finally:
        dest.close()
    scritti = []
    registro = registro_path or sess.REGISTRY
    if os.path.exists(registro):
        copia_reg = os.path.join(cartella, f'sessions-{stamp}.json')
        shutil.copy2(registro, copia_reg)
        scritti.append(copia_reg)
    copia = os.path.join(cartella, f'fatture-{stamp}.db')
    os.replace(in_corso, copia)     # solo adesso, con tutto fatto, compare col nome finale
    scritti.insert(0, copia)
    return scritti


def _contiene(testo, nome):
    """True se il nome sta nel testo come parole intere, date e virgolette a parte."""
    t, n = srv.normalizza_testo(testo), srv.normalizza_testo(nome)
    return bool(n) and re.search(r'(?<!\w)' + re.escape(n) + r'(?!\w)', t) is not None


def _regola_del_nome(nome, settings):
    """(nome della regola, modello) per quel servizio, oppure (None, None)."""
    for n, modello, _parole in srv.regole(settings):
        if n.lower() == nome.lower():
            return n, modello
    return srv.riconosci(nome, settings)


def _righe_del_servizio(righe, nome, settings):
    """Le righe di quel servizio, dalla piu' recente: quelle col nome; se
    nessuna lo contiene, quelle che le vecchie regole riconoscevano come lui."""
    sue = [x for x in righe if _contiene(x['description'], nome)]
    if sue:
        return sue
    regola = _regola_del_nome(nome, settings)[0]
    if not regola:
        return []
    return [x for x in righe if srv.riconosci(x['description'], settings)[0] == regola]


def nomi_di_partenza(con, settings, righe):
    """I nomi del listino, nell'ordine in cui compariranno.

    Prima i pulsanti. Poi i nomi delle regole che un pulsante non contiene gia'
    («Running Coaching» sta dentro «Monthly abo: running coaching») e che hanno
    riconosciuto almeno una riga: una regola mai servita non e' un servizio che
    vendi. Se non c'e' niente, le descrizioni usate piu' spesso."""
    pulsanti = [x.strip() for x in (settings.get('servizi') or '').splitlines() if x.strip()]
    nomi = list(pulsanti)
    for nome, _modello, _parole in srv.regole(settings):
        if any(nome.lower() in p.lower() for p in pulsanti):
            continue
        if _righe_del_servizio(righe, nome, settings):
            nomi.append(nome)
    if not nomi:
        nomi = srv.piu_usati(con)
    visti, fuori = set(), []
    for nome in nomi:
        chiave = srv.normalizza_testo(nome)
        if chiave and chiave not in visti:
            visti.add(chiave)
            fuori.append(nome)
    return fuori


def crea_servizi(con, settings, registro):
    """Il listino costruito da quello che c'era. Ritorna quanti servizi ha creato.

    Non fa niente se un listino c'e' gia'. Il commit lo fa chi chiama."""
    if con.execute('SELECT 1 FROM servizi LIMIT 1').fetchone():
        return 0
    righe = con.execute(
        'SELECT i.description, i.total_cents, f.number '
        'FROM items i JOIN invoices f ON f.id = i.invoice_id '
        "WHERE f.deleted_at IS NULL AND i.description <> '' "
        'ORDER BY f.date DESC, COALESCE(f.number, 0) DESC, i.pos DESC').fetchall()
    crediti_della_fattura = {}
    for p in (registro or {}).get('pacchetti') or []:
        if p.get('fattura_numero') not in (None, ''):
            crediti_della_fattura.setdefault(str(p['fattura_numero']), int(p.get('crediti') or 0))
    adesso = datetime.datetime.now().isoformat(timespec='seconds')
    creati = 0
    for pos, nome in enumerate(nomi_di_partenza(con, settings, righe)):
        sue = _righe_del_servizio(righe, nome, settings)
        ultima = sue[0] if sue else None
        ogni_mese = (_regola_del_nome(nome, settings)[1] == 'coaching'
                     or any(len(srv.RX_DATA.findall(x['description'])) >= 2 for x in sue))
        sedute = 0
        if ultima is not None and not ogni_mese and ultima['number'] is not None:
            sedute = crediti_della_fattura.get(str(ultima['number']), 0)
        con.execute(
            'INSERT INTO servizi(nome, prezzo_cents, ogni_mese, sedute, scadenza_mesi, '
            'passano, massimo, attivo, pos, creato_il) VALUES(?,?,?,?,0,0,0,1,?,?)',
            (nome, ultima['total_cents'] if ultima else None, int(ogni_mese), sedute,
             pos, adesso))
        creati += 1
    return creati


# --- Clienti a crediti -> clienti con le sedute ---------------------------------

def _primo_nome(nome):
    pezzi = (nome or '').strip().split()
    return pezzi[0].lower() if pezzi else ''


def _numeri_dei_pacchetti(registro, nome):
    """I numeri delle fatture dei pacchetti che portano quel nome."""
    parola = sess.normalizza(nome)
    numeri = set()
    for p in (registro or {}).get('pacchetti') or []:
        if (parola and p.get('fattura_numero') not in (None, '')
                and re.search(r'(?<!\w)' + re.escape(parola) + r'(?!\w)',
                              sess.normalizza(p.get('cliente')))):
            numeri.add(str(p['fattura_numero']))
    return numeri


def _clienti_delle_fatture(con, numeri):
    ids = []
    for numero in sorted(numeri):
        riga = con.execute(
            'SELECT client_id FROM invoices WHERE CAST(number AS TEXT) = ? '
            'AND client_id IS NOT NULL AND deleted_at IS NULL ORDER BY id DESC LIMIT 1',
            (numero,)).fetchone()
        if riga and riga['client_id'] not in ids:
            ids.append(riga['client_id'])
    return ids


def _cliente_per_nome(con, nome, numeri, liberi=True):
    """Il cliente con quel primo nome.

    Se sono piu' d'uno, quello a cui sono intestate le fatture dei suoi
    pacchetti; se non si capisce, il primo attivo. Mai un doppione.
    liberi=True guarda solo i clienti che una chiave non ce l'hanno ancora."""
    primo = _primo_nome(nome)
    sql = 'SELECT * FROM clients'
    if liberi:
        sql += " WHERE COALESCE(chiave_sedute, '') = ''"
    candidati = [c for c in con.execute(sql + ' ORDER BY archived, id')
                 if primo and _primo_nome(c['name']) == primo]
    if len(candidati) <= 1:
        return candidati[0] if candidati else None
    delle_fatture = _clienti_delle_fatture(con, numeri)
    giusti = [c for c in candidati if c['id'] in delle_fatture]
    return giusti[0] if giusti else candidati[0]


def _cliente_da_copiare(con, cc, registro):
    """Da chi prendere indirizzo, email, lingua e tono per un supplemento: il
    cliente di «fattura a», o quello delle fatture dei suoi pacchetti."""
    fattura_a = (cc['fattura_a'] or '').strip()
    if fattura_a:
        c = con.execute('SELECT * FROM clients WHERE lower(name) = lower(?) '
                        'ORDER BY archived, id LIMIT 1', (fattura_a,)).fetchone()
        c = c or _cliente_per_nome(con, fattura_a, set(), liberi=False)
        if c is not None:
            return c
    ids = _clienti_delle_fatture(con, _numeri_dei_pacchetti(registro, cc['nome']))
    return con.execute('SELECT * FROM clients WHERE id=?', (ids[0],)).fetchone() if ids else None


def _chiave_cliente_libera(con, nome):
    """La chiave di clients (unica), fatta come la fa la nuova fattura."""
    base = re.sub(r'[^a-z0-9]+', '-', (nome or '').lower()).strip('-') or 'cliente'
    chiave, n = base, 1
    while con.execute('SELECT 1 FROM clients WHERE key=?', (chiave,)).fetchone():
        n += 1
        chiave = f'{base}-{n}'
    return chiave


def clienti_da_crediti(con, registro):
    """I «clienti a crediti» diventano clienti con la chiave delle sedute.

    Ritorna (trovati, nuovi, archiviati). La tabella vecchia resta com'e'.
    Il commit lo fa chi chiama."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                       "AND name='crediti_clienti'").fetchone():
        return (0, 0, 0)
    righe = con.execute('SELECT * FROM crediti_clienti ORDER BY pos, chiave').fetchall()
    trovati = nuovi = archiviati = 0
    for cc in righe:
        chiave = (cc['chiave'] or '').strip().lower()
        nome = (cc['nome'] or '').strip()
        if not chiave or con.execute('SELECT 1 FROM clients WHERE chiave_sedute=?',
                                     (chiave,)).fetchone():
            continue                                    # gia' fatto
        c = _cliente_per_nome(con, nome, _numeri_dei_pacchetti(registro, nome))
        if c is not None:
            nome_cal = '' if _primo_nome(c['name']) == nome.lower() else nome
            con.execute('UPDATE clients SET chiave_sedute=?, nome_calendario=? WHERE id=?',
                        (chiave, nome_cal, c['id']))
            trovati += 1
        elif int(cc['attivo'] or 0):
            m = _cliente_da_copiare(con, cc, registro)
            con.execute(
                'INSERT INTO clients(key, name, file_label, address1, address2, email, lingua, '
                'tono, intestatario, paga_come, chiave_sedute) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (_chiave_cliente_libera(con, nome), nome, nome,
                 m['address1'] if m else '', m['address2'] if m else '',
                 m['email'] if m else '', (m['lingua'] if m else '') or 'en',
                 (m['tono'] if m else '') or 'informale',
                 m['name'] if m else '', ((m['paga_come'] or m['name']) if m else ''), chiave))
            nuovi += 1
        else:
            con.execute('INSERT INTO clients(key, name, file_label, archived, chiave_sedute) '
                        'VALUES(?,?,?,1,?)', (_chiave_cliente_libera(con, nome), nome, nome, chiave))
            archiviati += 1
    for cc in righe:
        compagno = (cc['compagno'] or '').strip().lower()
        if compagno:
            con.execute('UPDATE clients SET compagno_id = '
                        '(SELECT id FROM clients WHERE chiave_sedute = ?) '
                        'WHERE chiave_sedute = ? AND compagno_id IS NULL',
                        (compagno, (cc['chiave'] or '').strip().lower()))
    return trovati, nuovi, archiviati


def chiavi_nel_registro(con, registro_path=None):
    """Scrive `chiavi` sui pacchetti che non l'hanno. Ritorna quanti ne ha toccati.

    Tocca solo quel campo: le sedute restano intatte, e sessions.salva() copia il
    registro prima di riscriverlo. Un database senza clienti con le sedute non
    tocca nessun registro. Se non riesce, i pacchetti si trovano ancora per
    nome, e si riprova al prossimo avvio."""
    path = registro_path or sess.REGISTRY
    righe = D.clienti_sedute(con)
    if not righe or not os.path.exists(path):
        return 0
    try:
        reg = _leggi_registro(path)
        config = [sess._normalizza(dict(x)) for x in righe]
        toccati = 0
        for p in reg.get('pacchetti') or []:
            if not p.get('chiavi'):
                chiavi = sess._chiavi_di(p, config)
                if chiavi:
                    p['chiavi'] = chiavi
                    toccati += 1
        if toccati:
            sess.salva(reg, path)
        return toccati
    except Exception:
        logging.getLogger('fatture.errori').exception('Chiavi dei pacchetti non scritte nel registro')
        return 0
