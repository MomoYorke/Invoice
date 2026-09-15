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
    """Fa la migrazione, se non e' ancora fatta. True se l'ha fatta adesso."""
    if fatta(con):
        return False
    try:
        if fai_copia and not _copia_gia_fatta(con):
            copia_di_sicurezza(con, registro_path)
        registro = _leggi_registro(registro_path)
        crea_servizi(con, D.get_settings(con), registro)
        srv.collega_righe(con)
        con.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)', (MARCATORE, '1'))
        con.execute('DELETE FROM settings WHERE key=?', (ERRORE,))
        con.commit()
    except Exception as guaio:
        con.rollback()
        logging.getLogger('fatture.errori').exception('Aggiornamento dei servizi non riuscito')
        try:
            con.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)',
                        (ERRORE, '%s: %s' % (type(guaio).__name__, guaio)))
            con.commit()
        except sqlite3.Error:
            pass            # database bloccato: resta il registro degli errori
        return False
    return True


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
    ultime 40 dentro backups/, e questa deve restare."""
    riga = next((x for x in con.execute('PRAGMA database_list') if x[1] == 'main'), None)
    percorso = riga[2] if riga else ''
    if not percorso or not con.execute('SELECT 1 FROM invoices LIMIT 1').fetchone():
        return []           # database in memoria, o appena nato: niente da perdere
    cartella = os.path.join(os.path.dirname(percorso), 'backups', CARTELLA_COPIE)
    os.makedirs(cartella, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    copia = os.path.join(cartella, f'fatture-{stamp}.db')
    dest = sqlite3.connect(copia)
    try:
        con.backup(dest)
    finally:
        dest.close()
    scritti = [copia]
    registro = registro_path or sess.REGISTRY
    if os.path.exists(registro):
        copia_reg = os.path.join(cartella, f'sessions-{stamp}.json')
        shutil.copy2(registro, copia_reg)
        scritti.append(copia_reg)
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
