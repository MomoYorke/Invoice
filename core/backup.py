# -*- coding: utf-8 -*-
"""
Backup automatici del database.

Regola: PRIMA di ogni operazione che può distruggere dati (eliminazione,
reimport) e a ogni avvio dell'app viene salvata una copia datata del database.
Così qualunque errore — dell'app, mio o tuo — è sempre recuperabile.
"""
import os
import shutil
import sqlite3
import datetime

from . import language as L
from . import db

BACKUP_DIR = os.path.join(os.path.dirname(db.DB_PATH), 'backups')
KEEP = 40  # quante copie tenere


# Il perche' di una copia sta dentro il NOME del file, quindi resta una
# siglina in italiano per sempre. A renderlo leggibile — e nella lingua
# giusta — e' chi lo mostra, non chi lo scrive.
MOTIVI = {'avvio': 'all’avvio dell’app',
          'manuale': 'chiesta a mano',
          'prima-reimport': 'prima di reimportare lo storico',
          'prima-del-ripristino': 'prima di ripristinare una fattura',
          'prima-aggiornamento': 'prima di aggiornare il programma'}
PRIMA_DI_ELIMINARE = 'prima-eliminazione-'


def motivo_in_parole(sigla, lingua=None):
    """La siglina scritta nel nome del file, detta in parole."""
    if sigla in MOTIVI:
        return L.t(MOTIVI[sigla], lingua)
    if sigla.startswith(PRIMA_DI_ELIMINARE):
        return L.t('prima di eliminare la #{n}', lingua).format(
            n=sigla[len(PRIMA_DI_ELIMINARE):])
    return sigla


def make_backup(reason='manuale'):
    """Copia sicura del DB (usa l'API di backup di SQLite: coerente anche se l'app sta scrivendo)."""
    if not os.path.exists(db.DB_PATH):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in reason)[:40]
    out = os.path.join(BACKUP_DIR, f'fatture-{stamp}-{safe}.db')
    if os.path.exists(out):
        return out
    try:
        src = sqlite3.connect(db.DB_PATH)
        dst = sqlite3.connect(out)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
    except Exception:
        shutil.copy2(db.DB_PATH, out)   # fallback
    prune()
    return out


def prune(keep=KEEP):
    files = list_backups()
    for f in files[keep:]:
        try:
            os.remove(f['path'])
        except OSError:
            pass


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    out = []
    for name in os.listdir(BACKUP_DIR):
        if not name.endswith('.db'):
            continue
        p = os.path.join(BACKUP_DIR, name)
        st = os.stat(p)
        reason = name.replace('.db', '').split('-', 3)
        out.append({'path': p, 'name': name,
                    'when': datetime.datetime.fromtimestamp(st.st_mtime),
                    'size': st.st_size,
                    'reason': reason[3] if len(reason) > 3 else ''})
    return sorted(out, key=lambda x: x['when'], reverse=True)


def restore(path):
    """Ripristina un backup, salvando prima lo stato attuale (così è reversibile)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    make_backup('prima-del-ripristino')
    shutil.copy2(path, db.DB_PATH)
    return db.DB_PATH


# ---------------------------------------------------------------------------
# Backup FUORI dal Mac.
#
# make_backup() qui sopra copia il solo database, e lo copia sullo stesso disco:
# se il disco muore, muoiono insieme originale e copie. archivia_fuori() salva
# invece TUTTO cio' che non deve andare perso — database, registro delle
# sessioni, PDF e docx delle fatture — dentro un unico zip datato, su iCloud.
# ---------------------------------------------------------------------------
import zipfile
import tempfile
import hashlib

from . import desktop

# Dove vanno a finire, se nessuno ha detto altrove: lo decide desktop.py,
# che sa cosa offre il sistema su cui stiamo girando (iCloud sul Mac,
# OneDrive su Windows, Documenti quando non c'e' ne' l'uno ne' l'altro).
# Si puo' deviare con INVOICE_BACKUP, come per il database: cosi' un'app di
# prova non va a depositare le sue copie fra quelle vere, dove col ricambio
# spingerebbero fuori le buone.
DEST_DEFAULT = (db.env('INVOICE_BACKUP', 'FATTURE_BACKUP')
                or desktop.cartella_backup())
TIENI_GIORNALIERI = 30          # quante copie recenti conservare
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sorgenti():
    """Cosa finisce nello zip: (percorso sul disco, nome dentro l'archivio).

    Le variabili d'ambiente sono le stesse usate dal resto dell'app, cosi' una
    prova su una copia archivia la copia e non i dati veri.
    """
    registro = (db.env('INVOICE_SESSIONS', 'FATTURE_SESSIONS')
                or os.path.join(APP_DIR, 'sessions.json'))
    fatture = db.DIR_FATTURE
    return [
        (db.DB_PATH, 'fatture.db'),
        (registro, 'sessions.json'),
        (fatture, 'Fatture'),
    ]


def _md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for pezzo in iter(lambda: f.read(65536), b''):
            h.update(pezzo)
    return h.hexdigest()


def _conta_fatture():
    try:
        con = sqlite3.connect(db.DB_PATH)
        n = con.execute('SELECT COUNT(*) FROM invoices WHERE deleted_at IS NULL').fetchone()[0]
        con.close()
        return n
    except Exception:
        return -1


def _verifica_zip(path):
    """Riapre l'archivio e controlla che il database dentro sia sano.

    Un backup che non si riapre non e' un backup, e non voglio scoprirlo il
    giorno che serve. Ritorna (True, '') oppure (False, motivo).
    """
    try:
        with zipfile.ZipFile(path) as z:
            rotto = z.testzip()
            if rotto:
                return False, f'file danneggiato nell\'archivio: {rotto}'
            if 'fatture.db' not in z.namelist():
                return False, 'manca il database nell\'archivio'
            with tempfile.TemporaryDirectory() as tmp:
                z.extract('fatture.db', tmp)
                con = sqlite3.connect(os.path.join(tmp, 'fatture.db'))
                esito = con.execute('PRAGMA integrity_check').fetchone()[0]
                n = con.execute('SELECT COUNT(*) FROM invoices WHERE deleted_at IS NULL').fetchone()[0]
                con.close()
                if esito != 'ok':
                    return False, f'integrity_check: {esito}'
                if n != _conta_fatture():
                    return False, f'nell\'archivio ci sono {n} fatture invece di {_conta_fatture()}'
        return True, ''
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


def archivia_fuori(dest_dir=None, motivo='avvio'):
    """Crea lo zip completo fuori dal disco dell'app e lo verifica.

    Ritorna un dizionario con esito, percorso e motivo dell'eventuale errore.
    Non solleva mai: un backup che fallisce non deve impedire di lavorare.
    """
    dest_dir = dest_dir or DEST_DEFAULT
    esito = {'ok': False, 'path': None, 'errore': '', 'quando': datetime.datetime.now(),
             'motivo': motivo, 'bytes': 0}
    try:
        os.makedirs(dest_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        out = os.path.join(dest_dir, f'fatture-app-{stamp}.zip')
        manifest = [f'Backup Fatture App',
                    f'creato: {datetime.datetime.now():%d.%m.%Y %H:%M:%S}',
                    f'motivo: {motivo}',
                    f'fatture attive: {_conta_fatture()}', '']
        # scrivo prima in un file temporaneo: cosi' in destinazione non compare
        # mai un archivio a meta'
        parziale = out + '.parziale'
        with zipfile.ZipFile(parziale, 'w', zipfile.ZIP_DEFLATED) as z:
            for percorso, nome in _sorgenti():
                if os.path.isfile(percorso):
                    z.write(percorso, nome)
                    manifest.append(f'{nome:<28} {os.path.getsize(percorso):>9} byte  md5 {_md5(percorso)}')
                elif os.path.isdir(percorso):
                    quanti = 0
                    for radice, _dirs, files in os.walk(percorso):
                        for f in files:
                            if f == '.DS_Store':
                                continue
                            p = os.path.join(radice, f)
                            z.write(p, os.path.join(nome, os.path.relpath(p, percorso)))
                            quanti += 1
                    manifest.append(f'{nome + "/":<28} {quanti:>9} file')
                else:
                    manifest.append(f'{nome:<28} ASSENTE')
            z.writestr('manifest.txt', '\n'.join(manifest) + '\n')
        os.replace(parziale, out)

        ok, perche = _verifica_zip(out)
        if not ok:
            os.remove(out)          # un archivio che non si riapre non lo tengo
            esito['errore'] = perche
            return esito
        esito.update(ok=True, path=out, bytes=os.path.getsize(out))
        prune_esterni(dest_dir)
        return esito
    except Exception as e:
        esito['errore'] = f'{type(e).__name__}: {e}'
        return esito


def elenco_esterni(dest_dir=None):
    """Gli zip presenti in destinazione, dal piu' recente."""
    dest_dir = dest_dir or DEST_DEFAULT
    if not os.path.isdir(dest_dir):
        return []
    out = []
    for nome in os.listdir(dest_dir):
        if not (nome.startswith('fatture-app-') and nome.endswith('.zip')):
            continue
        p = os.path.join(dest_dir, nome)
        st = os.stat(p)
        out.append({'path': p, 'name': nome, 'size': st.st_size,
                    'when': datetime.datetime.fromtimestamp(st.st_mtime)})
    return sorted(out, key=lambda x: x['when'], reverse=True)


def prune_esterni(dest_dir=None, tieni=TIENI_GIORNALIERI):
    """Tiene le ultime copie piu' la prima di ogni mese, che non si tocca mai."""
    copie = elenco_esterni(dest_dir)
    primi_del_mese = set()
    for c in sorted(copie, key=lambda x: x['when']):
        chiave = c['when'].strftime('%Y-%m')
        if chiave not in primi_del_mese:
            primi_del_mese.add(chiave)
            c['storica'] = True
    for c in copie[tieni:]:
        if c.get('storica'):
            continue
        try:
            os.remove(c['path'])
        except OSError:
            pass


def ultimo_esterno(dest_dir=None):
    copie = elenco_esterni(dest_dir)
    return copie[0] if copie else None


def serve_backup_oggi(dest_dir=None):
    """Vero se oggi non e' ancora stata fatta nessuna copia esterna."""
    ultimo = ultimo_esterno(dest_dir)
    return ultimo is None or ultimo['when'].date() < datetime.date.today()


# --- lo storico: i documenti nella cartella indicata in Impostazioni -------
# Le fatture piu' vecchie dell'app esistono solo li'. Quella cartella si legge
# e non si tocca mai, ma senza una copia basta un disco rotto per perderle.
# Cambia di rado, quindi la si archivia a parte e solo quando e' cambiata
# davvero: altrimenti ogni copia giornaliera si porterebbe dietro 7,7 MB.

FIRMA = '.storico-firma'
TIENI_STORICI = 3


def _firma_cartella(percorso):
    """Impronta del contenuto: nome, dimensione e data di ogni file."""
    righe = []
    for radice, _dirs, files in os.walk(percorso):
        for f in sorted(files):
            if f == '.DS_Store':
                continue
            p = os.path.join(radice, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            righe.append(f'{os.path.relpath(p, percorso)}|{st.st_size}|{int(st.st_mtime)}')
    h = hashlib.md5()
    h.update('\n'.join(sorted(righe)).encode('utf-8'))
    return h.hexdigest(), len(righe)


def archivia_storico(sorgente, dest_dir=None, forza=False):
    """Copia lo storico solo se e' cambiato dall'ultima volta."""
    dest_dir = dest_dir or DEST_DEFAULT
    esito = {'ok': False, 'path': None, 'errore': '', 'saltato': False, 'file': 0}
    if not os.path.isdir(sorgente):
        esito['errore'] = f'cartella storico non trovata: {sorgente}'
        return esito
    try:
        firma, quanti = _firma_cartella(sorgente)
        esito['file'] = quanti
        os.makedirs(dest_dir, exist_ok=True)
        segna = os.path.join(dest_dir, FIRMA)
        if not forza and os.path.exists(segna):
            with open(segna, encoding='utf-8') as f:
                if f.read().strip() == firma:
                    esito.update(ok=True, saltato=True)
                    return esito          # niente e' cambiato: nessuna copia nuova
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        out = os.path.join(dest_dir, f'storico-{stamp}.zip')
        parziale = out + '.parziale'
        with zipfile.ZipFile(parziale, 'w', zipfile.ZIP_DEFLATED) as z:
            for radice, _dirs, files in os.walk(sorgente):
                for f in files:
                    if f == '.DS_Store':
                        continue
                    p = os.path.join(radice, f)
                    z.write(p, os.path.relpath(p, sorgente))
            z.writestr('manifest.txt',
                       f'Storico (cartella di sola lettura)\n'
                       f'creato: {datetime.datetime.now():%d.%m.%Y %H:%M:%S}\n'
                       f'documenti: {quanti}\nfirma: {firma}\n')
        os.replace(parziale, out)
        with zipfile.ZipFile(out) as z:
            rotto = z.testzip()
        if rotto:
            os.remove(out)
            esito['errore'] = f'archivio danneggiato: {rotto}'
            return esito
        with open(segna, 'w', encoding='utf-8') as f:
            f.write(firma)
        for vecchio in sorted(
                (n for n in os.listdir(dest_dir)
                 if n.startswith('storico-') and n.endswith('.zip')),
                reverse=True)[TIENI_STORICI:]:
            try:
                os.remove(os.path.join(dest_dir, vecchio))
            except OSError:
                pass
        esito.update(ok=True, path=out)
        return esito
    except Exception as e:
        esito['errore'] = f'{type(e).__name__}: {e}'
        return esito
