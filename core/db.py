# -*- coding: utf-8 -*-
"""Database SQLite dell'app fatture."""
import os
import sqlite3
import datetime

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Il database vero. Si può puntare a una COPIA con la variabile FATTURE_DB:
# serve per provare modifiche senza mai toccare i dati reali.
DB_PATH = os.environ.get('FATTURE_DB') or os.path.join(APP_DIR, 'data', 'fatture.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients(
  id INTEGER PRIMARY KEY,
  key TEXT UNIQUE,
  name TEXT NOT NULL,
  address1 TEXT DEFAULT '',
  address2 TEXT DEFAULT '',
  file_label TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  archived INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invoices(
  id INTEGER PRIMARY KEY,
  number INTEGER,
  client_id INTEGER REFERENCES clients(id),
  client_name TEXT NOT NULL,
  client_address TEXT DEFAULT '',
  date TEXT,
  year INTEGER,
  total_cents INTEGER,
  status TEXT DEFAULT 'emessa',
  source TEXT DEFAULT 'app',
  source_file TEXT DEFAULT '',
  docx_path TEXT DEFAULT '',
  pdf_path TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS items(
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  pos INTEGER DEFAULT 0,
  qty TEXT DEFAULT '1',
  description TEXT DEFAULT '',
  unit_cents INTEGER,
  total_cents INTEGER
);
CREATE TABLE IF NOT EXISTS legacy_year_totals(
  id INTEGER PRIMARY KEY,
  year INTEGER,
  client TEXT,
  invoiced_cents INTEGER,
  paid_cents INTEGER,
  note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
-- Correzioni manuali fatte dall'utente. Sono indicizzate su una chiave STABILE
-- (il file di origine), cosi' sopravvivono al Reimporta che ricrea le fatture.
-- Versamenti dell'estratto conto gia' decisi: collegati a una fattura oppure
-- messi da parte. Quelli non ancora decisi NON stanno qui: si rileggono dai
-- file ogni volta, cosi' la cartella resta la fonte e il database non
-- accumula copie di dati che non gli appartengono.
CREATE TABLE IF NOT EXISTS movimenti(
  impronta TEXT PRIMARY KEY,
  data TEXT,
  importo_cents INTEGER,
  descrizione TEXT DEFAULT '',
  file TEXT DEFAULT '',
  invoice_id INTEGER,             -- NULL = messo da parte, non e' una fattura
  invoice_ids TEXT DEFAULT '',    -- un bonifico puo' pagare piu' fatture insieme
  stato TEXT DEFAULT 'collegato', -- collegato | ignorato
  stato_prima TEXT DEFAULT '',    -- com'era la fattura: annullare deve annullare davvero
  automatico INTEGER DEFAULT 0,   -- 1 = collegato dall'app, non da te
  deciso_il TEXT
);
-- Registro delle email partite dall'app: una riga per tentativo, riusciti e
-- falliti. Serve a ritrovare cosa e' stato mandato senza dover aprire Mail,
-- e a capire com'e' andata quando qualcosa non parte.
CREATE TABLE IF NOT EXISTS email_log(
  id INTEGER PRIMARY KEY,
  sent_at TEXT NOT NULL,
  destinatario TEXT DEFAULT '',
  oggetto TEXT DEFAULT '',
  fatture TEXT DEFAULT '',        -- numeri, separati da virgola
  invoice_id INTEGER,             -- quella da cui e' partito l'invio
  allegati TEXT DEFAULT '',
  prova INTEGER DEFAULT 0,        -- 1 = "Prova su di me"
  esito TEXT DEFAULT 'ok',        -- ok | errore
  motivo TEXT DEFAULT '',
  cartella TEXT DEFAULT '',       -- dove ne e' finita la copia, se ci e' riuscito
  mittente TEXT DEFAULT '',
  ccn TEXT DEFAULT '',            -- la copia nascosta a se stessi, se c'era
  corpo TEXT DEFAULT ''           -- il testo esatto che ha letto il cliente
);
CREATE INDEX IF NOT EXISTS idx_email_log_data ON email_log(sent_at DESC);
CREATE TABLE IF NOT EXISTS corrections(
  key TEXT PRIMARY KEY,
  total_cents INTEGER,
  date TEXT,
  number INTEGER,
  note TEXT DEFAULT '',
  created_at TEXT
);
-- Anomalie storiche archiviate ("lo so, va bene cosi'").
CREATE TABLE IF NOT EXISTS acknowledged(
  key TEXT PRIMARY KEY,
  kind TEXT,
  msg TEXT,
  note TEXT DEFAULT '',
  created_at TEXT
);
-- Chi lavora a pacchetti di sessioni prepagate. Una riga per persona: da qui
-- l'app sa quali nomi cercare nei titoli del calendario, quanti crediti vale
-- un pacchetto e a quale prezzo lo riconosce sulle fatture. Prima erano scritti
-- nel codice; adesso si aggiungono dalla pagina Crediti.
CREATE TABLE IF NOT EXISTS crediti_clienti(
  chiave TEXT PRIMARY KEY,        -- la parola cercata nei titoli ("anna")
  nome TEXT NOT NULL,             -- come appare nell'app ("Anna")
  crediti INTEGER NOT NULL DEFAULT 10,   -- quante sessioni vale un pacchetto
  prefisso TEXT NOT NULL DEFAULT '',     -- ANN -> ANN-01, ANN-02...
  prezzi TEXT DEFAULT '',         -- centesimi separati da virgola: 180000,150000
  fattura_a TEXT DEFAULT '',      -- se la fattura va intestata a un'altra persona
  compagno TEXT DEFAULT '',       -- chiave di chi deve esserci perche' sia un supplemento
  attivo INTEGER DEFAULT 1,       -- 0 = ex cliente: si riconosce ancora, non si fattura piu'
  pos INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_inv_year ON invoices(year);
CREATE INDEX IF NOT EXISTS idx_inv_number ON invoices(number);
"""

DEFAULT_SETTINGS = {
    # Chi emette la fattura: vuoto di proposito. Sono i dati di chi usa l'app,
    # e li scrive lui in Impostazioni la prima volta. Meglio una fattura con
    # dei buchi evidenti che una con sopra il nome e l'IBAN di un altro.
    # Nota: questi valori valgono solo per un database nuovo. Chi ha gia'
    # l'app installata si tiene quello che ha scritto.
    'business_name': '',
    'business_uid': '',
    'business_addr1': '',
    'business_addr2': '',
    'business_phone': '',
    'business_web': '',
    'business_iban': '',
    'terms': 'Payable within 30 days net to:',
    'accountant_name': '',
    'accountant_city': '',
    # una cartella di fatture vecchie da leggere all'avvio, se ne hai una.
    # Vuoto = si parte da zero. Viene solo letta, mai modificata.
    'source_folder': '',
    # i servizi proposti sopra le righe della fattura, uno per riga. Vuoto =
    # l'app propone le descrizioni che hai gia' usato di piu'.
    'servizi': '',
    # Quali servizi l'app riconosce nelle righe della fattura, e a quale
    # modello di email appartengono. Una riga per servizio:
    #     Nome del servizio = parola, parola
    # Servono alla dashboard, per raggruppare il fatturato, e all'email, per
    # nominare il servizio e scegliere il testo. Vuoti = l'app non prova a
    # indovinare: meglio non nominare il servizio che nominarne uno sbagliato.
    # la lingua dell'APP (menu, pagine, messaggi). Quella dei DOCUMENTI sta
    # sul singolo cliente: la fattura la legge lui, non chi la scrive.
    'lingua': 'it',
    'servizi_abbonamento': '',
    'servizi_pacchetto': '',
    # copia completa fuori dal disco dell'app (iCloud): database,
    # registro sessioni e PDF delle fatture in un unico zip datato
    # Posta: si spedisce dal proprio server, non da Gmail. Se il tuo dominio
    # dichiara SPF -all, una mail mandata da Gmail a nome del tuo indirizzo
    # finisce nello spam. Attenzione al nome dell'host: spesso il certificato
    # copre 'tuodominio.ch' ma non 'mail.tuodominio.ch'.
    'smtp_host': '',
    'smtp_port': '587',
    'smtp_user': '',
    'smtp_pass': '',
    # copia in «Inviata»: SMTP consegna soltanto, la copia si deposita via IMAP
    'imap_host': '',
    'imap_port': '993',
    'imap_cartella': '',          # vuoto = la cerca da sola sul server
    'email_from': '',
    'email_test_to': '',
    # copia nascosta a se stessi: la fattura spedita arriva anche nella
    # propria posta in arrivo, dove Mail la vede
    'email_copia_a_me': '1',
    # due password sbagliate di fila e il server blocca l'IP per un pezzo:
    # l'app si ferma prima, da sola
    # indirizzo segreto in formato iCal del calendario delle sessioni: si
    # incolla una volta e l'app legge le sessioni da sola
    'calendario_ics': '',
    # secondo calendario, di sola lettura: quello dove stanno le sedute
    # vecchie. Serve solo all'Agenda, per sapere a che ora sono state fatte:
    # i crediti non lo guardano mai.
    'calendario_storico_ics': '',
    # come si chiamano, secondo loro stessi: l'app li legge dal file iCal a
    # ogni sincronizzazione, cosi' le pagine possono nominarli senza che il
    # nome di nessuno finisca scritto nel programma
    'calendario_nome': '',
    'calendario_storico_nome': '',
    'calendario_ultimo': '',
    # banca: l'app collega da sola i versamenti su cui non c'e' nulla da decidere
    'banca_auto': '1',
    'banca_ultimo_estratto': '',   # data del movimento piu' recente letto
    'banca_letto_il': '',
    'smtp_fallimenti': '0',
    'smtp_pausa_fino': '',
    # Due oggetti, uno per modello, come per la frase centrale: l'abbonamento
    # nell'oggetto porta il mese coperto ({mese}, dedotto dal periodo scritto
    # sulla fattura), il pacchetto di sedute si paga in una volta e il mese
    # non c'entra. Restano generici apposta: ognuno ci scrive i suoi.
    'email_oggetto_coaching': 'Invoice \u2013 [{mese}]',
    'email_oggetto_pt': 'Invoice',
    # Il testo della mail. Sotto {saluto} va la firma: scrivila in Impostazioni,
    # com'e' scritta in fondo alle mail che mandi davvero.
    'email_body': (
        "Dear {nome},\n\n"
        "{apertura}\n"
        "{riga_abbonamento}"
        "{corpo}\n\n"
        "{saluto}"),
    # Come chiudi la mail. Due versioni, perche' con qualcuno ci si da' del tu
    # e con qualcun altro no: nella scheda del cliente si sceglie quale usare.
    'email_saluto_informale': 'Best,\n',
    'email_saluto_formale': 'Best regards,\n\n',
    # La riga centrale, quella che cambia da persona a persona. Ce ne sono due
    # perche' i due modelli hanno due discorsi diversi: l'abbonamento continua
    # di mese in mese, il pacchetto di sedute si compra una volta e si
    # consuma. L'app sceglie da sola quale usare guardando le
    # righe della fattura; nell'anteprima si cambia con un click e si riscrive.
    'email_corpo_coaching': 'Thank you again for your trust.',
    'email_corpo_pt': 'Thank you again for your trust.',
    'backup_dir': os.path.expanduser(
        '~/Library/Mobile Documents/com~apple~CloudDocs/Fatture App - Backup'),
}


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


def init():
    con = connect()
    con.executescript(SCHEMA)
    _migrate(con)
    for k, v in DEFAULT_SETTINGS.items():
        con.execute('INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)', (k, v))
    con.commit()
    return con


def _migrate(con):
    """Aggiunge colonne nuove ai database gia' esistenti."""
    cols = {r['name'] for r in con.execute('PRAGMA table_info(invoices)')}
    if 'deleted_at' not in cols:
        # eliminazione reversibile: la fattura non sparisce, finisce nel Cestino
        con.execute('ALTER TABLE invoices ADD COLUMN deleted_at TEXT')
    if 'deleted_reason' not in cols:
        con.execute('ALTER TABLE invoices ADD COLUMN deleted_reason TEXT DEFAULT ""')
    if 'sent_at' not in cols:
        # quando la fattura e' stata spedita al cliente per email
        con.execute('ALTER TABLE invoices ADD COLUMN sent_at TEXT')
    if 'paid_at' not in cols:
        # quando i soldi sono arrivati davvero in banca. Diverso da status:
        # 'pagata' e' una spunta messa a mano, questa e' una data che viene
        # dall'estratto conto
        con.execute('ALTER TABLE invoices ADD COLUMN paid_at TEXT')
    cli = {r['name'] for r in con.execute('PRAGMA table_info(clients)')}
    if 'email' not in cli:
        con.execute('ALTER TABLE clients ADD COLUMN email TEXT DEFAULT ""')
    if 'tono' not in cli:
        # con chi ci si da' del tu si chiude col saluto confidenziale; con
        # il saluto formale invece del confidenziale
        con.execute("ALTER TABLE clients ADD COLUMN tono TEXT DEFAULT 'informale'")
    if 'intestatario' not in cli:
        # A volte la fattura va intestata a una persona diversa da chi
        # fa le sedute: un genitore, un coniuge, un'azienda.
        # Vuoto = la fattura va intestata al cliente stesso.
        con.execute('ALTER TABLE clients ADD COLUMN intestatario TEXT DEFAULT ""')
    if 'paga_come' not in cli:
        # chi versa i soldi non e' sempre l'intestatario della fattura: sul
        # conto puo' arrivare il nome del marito, della moglie, di un'azienda.
        # Piu' nomi separati da punto e virgola.
        con.execute('ALTER TABLE clients ADD COLUMN paga_come TEXT DEFAULT ""')
    if 'lingua' not in cli:
        # I documenti finora uscivano in inglese per tutti: i clienti che ci
        # sono gia' restano in inglese, cosi' nessuno si ritrova a mandare una
        # fattura in un'altra lingua senza averlo chiesto. I clienti nuovi
        # ereditano la lingua dell'app.
        con.execute("ALTER TABLE clients ADD COLUMN lingua TEXT DEFAULT 'en'")
    if 'abbonamento' not in cli:
        # clienti con ordine permanente: nell'email va la frase sullo standing order
        con.execute('ALTER TABLE clients ADD COLUMN abbonamento INTEGER DEFAULT 0')
    _migra_modelli_email(con)
    _migra_oggetti_email(con)
    _migra_registro_email(con)
    _migra_servizi_riconosciuti(con)
    mov = {r['name'] for r in con.execute('PRAGMA table_info(movimenti)')}
    if 'stato_prima' not in mov:
        con.execute('ALTER TABLE movimenti ADD COLUMN stato_prima TEXT DEFAULT ""')
    if 'invoice_ids' not in mov:
        con.execute('ALTER TABLE movimenti ADD COLUMN invoice_ids TEXT DEFAULT ""')
    if 'automatico' not in mov:
        con.execute('ALTER TABLE movimenti ADD COLUMN automatico INTEGER DEFAULT 0')
    corr = {r['name'] for r in con.execute('PRAGMA table_info(corrections)')}
    if 'number' not in corr:
        # il numero di fattura si legge dal nome del file: per cambiarlo serve
        # una correzione, altrimenti il prossimo Reimporta lo rimette com'era
        con.execute('ALTER TABLE corrections ADD COLUMN number INTEGER')
    log = {r['name'] for r in con.execute('PRAGMA table_info(email_log)')}
    for colonna in ('mittente', 'ccn', 'corpo'):
        if colonna not in log:
            # il testo della mail: si tiene per poterla rileggere dall'app
            con.execute(f'ALTER TABLE email_log ADD COLUMN {colonna} TEXT DEFAULT ""')
    con.commit()


def _migra_servizi_riconosciuti(con):
    """Le regole che riconoscono i servizi escono dal programma ed entrano
    nelle Impostazioni.

    Erano tre servizi scritti nel codice: quelli di chi l'app l'ha scritta per
    se'. Chi ha gia' fatturato se li ritrova scritti come erano, cosi' non
    cambia niente e ora puo' correggerli; chi installa da zero parte con gli
    elenchi vuoti e ci mette i propri, invece di ereditare il mestiere di un
    altro.

    Gira prima che le impostazioni di partenza vengano inserite, quindi scrive
    lei la riga: dopo, l'INSERT OR IGNORE la lascia dov'e'."""
    gia = con.execute(
        "SELECT 1 FROM settings WHERE key IN ('servizi_abbonamento', 'servizi_pacchetto')"
        " AND value <> '' LIMIT 1").fetchone()
    if gia:
        return
    if not con.execute('SELECT 1 FROM invoices LIMIT 1').fetchone():
        return   # installazione nuova: gli elenchi restano vuoti
    for chiave, valore in (
            ('servizi_abbonamento',
             'Running Coaching = running coaching\nOnline Coaching = coaching online'),
            ('servizi_pacchetto',
             'Personal Training = session, personal training, allenament, '
             'add-on, credit, crediti')):
        con.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)',
                    (chiave, valore))


# Il motivo scritto nel registro quando la riga viene dedotta da una fattura
# vecchia. Sta nel database in italiano; a tradurlo e' la pagina che lo mostra.
MOTIVO_RICOSTRUITO = ('riga ricostruita dalla data segnata sulla fattura: '
                      'destinatario e oggetto non erano stati registrati')


def _migra_modelli_email(con):
    """Dalla frase centrale unica ai due modelli, abbonamento e pacchetto.

    Il testo che era gia' stato scritto a mano non va perso: diventa il punto
    di partenza di tutti e due. La chiave vecchia sparisce solo dopo che il suo
    contenuto e' stato messo al sicuro nelle nuove.
    """
    r = con.execute("SELECT value FROM settings WHERE key='email_corpo'").fetchone()
    if r is None:
        return
    for k in ('email_corpo_coaching', 'email_corpo_pt'):
        con.execute('INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)', (k, r['value']))
    con.execute("DELETE FROM settings WHERE key='email_corpo'")


def _migra_oggetti_email(con):
    """Da un oggetto solo ai due oggetti per servizio.

    Il vecchio 'email_subject' era uguale per tutti e non diceva niente del
    mese. I due nuovi lo dicono, quindi il vecchio non serve piu': si toglie
    solo dopo che i due nuovi esistono davvero, cosi' un'interruzione a meta'
    non lascia l'app senza oggetto.
    """
    if con.execute("SELECT 1 FROM settings WHERE key='email_subject'").fetchone() is None:
        return
    for k in ('email_oggetto_coaching', 'email_oggetto_pt'):
        con.execute('INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)',
                    (k, DEFAULT_SETTINGS[k]))
    con.execute("DELETE FROM settings WHERE key='email_subject'")


def _migra_registro_email(con):
    """Il registro nasce vuoto, ma delle fatture gia' spedite sappiamo quando.

    Si ricostruisce una riga per ognuna, marcata come ricostruita: meglio una
    riga onesta e incompleta che un elenco che comincia da oggi e sembra dire
    che prima non era stato mandato niente. Gira una volta sola.
    """
    if con.execute('SELECT COUNT(*) c FROM email_log').fetchone()['c']:
        return
    fatto = con.execute("SELECT value FROM settings WHERE key='email_log_ricostruito'").fetchone()
    if fatto:
        return
    righe = con.execute('SELECT id, number, sent_at FROM invoices '
                        'WHERE sent_at IS NOT NULL AND sent_at <> "" '
                        'ORDER BY sent_at').fetchall()
    for r in righe:
        con.execute(
            'INSERT INTO email_log(sent_at, destinatario, oggetto, fatture, invoice_id, '
            'prova, esito, motivo) VALUES(?,?,?,?,?,0,?,?)',
            (r['sent_at'], '', '', str(r['number'] or ''), r['id'], 'ok',
             MOTIVO_RICOSTRUITO))
    con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('email_log_ricostruito', ?)",
                (str(len(righe)),))


def get_settings(con):
    return {r['key']: r['value'] for r in con.execute('SELECT key, value FROM settings')}


def set_setting(con, key, value):
    con.execute('INSERT INTO settings(key,value) VALUES(?,?) '
                'ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
    con.commit()


def crediti_clienti(con, solo_attivi=False):
    """I clienti che lavorano a pacchetti di crediti, in ordine di elenco."""
    sql = 'SELECT * FROM crediti_clienti'
    if solo_attivi:
        sql += ' WHERE attivo = 1'
    return con.execute(sql + ' ORDER BY attivo DESC, pos, nome').fetchall()


def crediti_cliente_salva(con, chiave, dati):
    """Aggiunge o aggiorna un cliente a crediti. `chiave` e' la parola cercata
    nei titoli del calendario e non cambia mai: e' quella che tiene insieme il
    cliente e i pacchetti gia' registrati a suo nome."""
    campi = ('nome', 'crediti', 'prefisso', 'prezzi', 'fattura_a', 'compagno',
             'attivo', 'pos')
    valori = [dati.get(c) for c in campi]
    con.execute(
        'INSERT INTO crediti_clienti(chiave, %s) VALUES(?, %s) '
        'ON CONFLICT(chiave) DO UPDATE SET %s'
        % (', '.join(campi), ', '.join('?' * len(campi)),
           ', '.join(f'{c}=excluded.{c}' for c in campi)),
        [chiave] + valori)
    con.commit()


def crediti_cliente_elimina(con, chiave):
    con.execute('DELETE FROM crediti_clienti WHERE chiave = ?', (chiave,))
    con.commit()


def next_number(con):
    """Prossimo numero libero.

    Si basa sulle fatture ATTIVE: se l'ultima e' finita nel Cestino, il suo numero
    torna disponibile (serve per rifare una fattura sbagliata senza lasciare buchi).
    Il riuso non e' mai silenzioso: la conferma di creazione lo dice esplicitamente.
    """
    r = con.execute('SELECT MAX(number) AS m FROM invoices WHERE deleted_at IS NULL').fetchone()
    n = (r['m'] or 0) + 1
    # non scavalcare mai una fattura attiva
    while con.execute('SELECT 1 FROM invoices WHERE number=? AND deleted_at IS NULL',
                      (n,)).fetchone():
        n += 1
    return n


def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
