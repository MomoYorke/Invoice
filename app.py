# -*- coding: utf-8 -*-
"""
Fatture — app locale per la fatturazione di un personal trainer.
Flask + SQLite. Avvio: doppio click su "Avvia Fatture.command".
Il nome dell'attività, l'indirizzo, l'IBAN e il logo si mettono nelle
Impostazioni: nel programma non c'è niente di personale.
La cartella dello storico, se ne indichi una, viene letta ma MAI modificata.
"""
import os
import re
import glob
import shutil
import datetime
import logging
import traceback
import subprocess

from flask import (Flask, render_template, request, redirect, url_for,
                   send_file, jsonify, flash, abort, g)
from dateutil.relativedelta import relativedelta

from core import db, stats, importer, exports, verify, selftest, corrections, backup, mailer
from core import calendario
from core import agenda as ag
from core import cruscotto
from core import banca
from core import sessions as sess
from core.money import parse_amount, fmt_chf, fmt_dash, parse_qty, line_total
from core import docgen, pdfgen
from core import marchio
from core import servizi as srv
from core import benvenuto as ben
from core import icone
from core import menu
from core import lingua as lng

APP_DIR = os.path.dirname(os.path.abspath(__file__))
# La cartella delle fatture si puo' deviare con INVOICE_DIR: serve per provare
# modifiche senza scrivere documenti nella cartella vera.
INVOICE_DIR = db.DIR_FATTURE
TRASH_DIR = db.DIR_CESTINO

app = Flask(__name__)
app.secret_key = 'em-fatture-locale'
app.jinja_env.filters['chf'] = fmt_chf
app.jinja_env.filters['dash'] = fmt_dash
app.jinja_env.globals['icona'] = icone.icona
app.jinja_env.globals['pallino'] = icone.pallino

# --- log persistente dei SOLI errori: data/error.log ---
ERROR_LOG = os.path.join(APP_DIR, 'data', 'error.log')
os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
err_logger = logging.getLogger('fatture.errori')
err_logger.setLevel(logging.ERROR)
err_logger.propagate = False
_h = logging.FileHandler(ERROR_LOG, encoding='utf-8')
_h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
err_logger.addHandler(_h)


@app.route('/logo.png')
def logo():
    """Il logo dell'attività. Non sta fra i file del programma ma nei dati
    dell'utente, così chi riceve l'app non si porta dietro il marchio altrui."""
    r = send_file(marchio.percorso(), mimetype='image/png')
    # il browser puo' tenerselo un'ora; quando cambia, cambia anche il ?v=
    r.headers['Cache-Control'] = 'private, max-age=3600'
    return r


@app.route('/health')
def health():
    """Usato dal launcher per capire se l'app è viva e sana."""
    try:
        con = get_con()
        con.execute('SELECT 1 FROM invoices LIMIT 1')
        con.close()
        return 'ok', 200
    except Exception as e:
        return f'db-error: {e}', 500


@app.errorhandler(Exception)
def handle_any_error(e):
    """Niente più muro grigio: pagina chiara + traccia salvata in data/error.log."""
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException) and e.code != 500:
        return e  # 404 ecc. gestiti normalmente
    tb = traceback.format_exc()
    err_logger.error('Errore su %s\n%s', request.path if request else '?', tb)
    try:
        return render_template('errore.html', error=str(e), path=request.path,
                               log_path=ERROR_LOG), 500
    except Exception:
        return (f'<h2>Si è verificato un errore</h2><p>{e}</p>'
                f'<pre>{tb}</pre>'), 500

MESI_S = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
          'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

def get_con():
    return db.init()


def fmt_date_it(iso):
    if not iso:
        return '—'
    try:
        return datetime.date.fromisoformat(iso).strftime('%d.%m.%Y')
    except ValueError:
        return iso


GIORNI = ('lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom')


def fmt_giorno_settimana(iso):
    try:
        return GIORNI[datetime.date.fromisoformat(iso).weekday()]
    except (ValueError, TypeError):
        return ''


app.jinja_env.filters['dateit'] = fmt_date_it
app.jinja_env.filters['giorno_settimana'] = fmt_giorno_settimana


@app.context_processor
def inject_globals():
    con = get_con()
    years = [r['year'] for r in con.execute(
        'SELECT DISTINCT year FROM invoices WHERE year IS NOT NULL AND deleted_at IS NULL ORDER BY year DESC')]
    impostazioni = db.get_settings(con)
    nome = impostazioni.get('business_name', '')
    # il menu mostra «Primi passi» solo finché resta qualcosa da fare: e' l'unico
    # modo per tornarci dopo aver chiuso il promemoria della Dashboard
    try:
        restano = len(ben.da_fare(ben.passi(con, impostazioni)))
    except Exception:                                   # pragma: no cover
        restano = 0
    con.close()
    riga1, riga2 = marchio.due_righe(nome)
    # «_» traduce nella lingua dell'app. Le pagine scrivono _('Fatture') e
    # ottengono l'italiano, l'inglese o il tedesco senza sapere quale sia.
    codice = lng.normalizza(impostazioni.get('lingua'))
    return {'all_years': years, 'current_year': datetime.date.today().year,
            'attivita': nome or 'La tua attività',
            'marchio_riga1': riga1, 'marchio_riga2': riga2,
            'logo_versione': marchio.versione(),
            '_': lambda frase: lng.t(frase, codice),
            'lingua': codice, 'lingue': lng.LINGUE,
            'menu_gruppi': menu.GRUPPI, 'primi_passi_restano': restano,
            'calendario_nome': impostazioni.get('calendario_nome') or 'il calendario delle sessioni',
            'calendario_storico_nome': (impostazioni.get('calendario_storico_nome')
                                        or 'il calendario storico')}


@app.route('/lingua/<codice>')
def cambia_lingua(codice):
    """Cambia la lingua dell'app e torna dov'eri.

    Solo la lingua dell'APP: quella dei documenti sta sul cliente, perche' la
    fattura la legge lui. Un codice che non conosciamo torna all'italiano
    invece di rompere la pagina.
    """
    con = get_con()
    db.set_setting(con, 'lingua', lng.normalizza(codice))
    con.commit()
    con.close()
    # si torna alla pagina di prima, ma solo se e' una pagina di questa app:
    # un indirizzo esterno nel referrer non deve poterci mandare altrove
    dove = request.referrer or ''
    if not dove.startswith(request.host_url):
        dove = url_for('dashboard')
    return redirect(dove)


# ---------------------------------------------------------------- dashboard
@app.route('/')
def dashboard():
    con = get_con()
    # app appena installata: la Dashboard di un archivio vuoto non dice niente
    # a nessuno. Meglio mostrare da dove si comincia, una volta sola.
    passi = ben.passi(con, db.get_settings(con))
    if ben.manca_l_essenziale(passi):
        con.close()
        return redirect(url_for('benvenuto'))
    year = request.args.get('anno', type=int) or datetime.date.today().year
    k = stats.kpis(con, year)
    months = stats.monthly(con, year)
    settings = db.get_settings(con)
    try:
        registro = sess.carica()
    except Exception as e:                      # il registro non deve poter
        err_logger.error('Registro non letto: %s', e)       # spegnere la Dashboard
        registro = None
    cose = cruscotto.da_fare(con, settings, registro)
    try:
        novita = cruscotto.attivita(con, registro if registro is not None else {},
                                    lingua=settings.get('lingua'))
    except Exception as e:
        err_logger.error('Attività non costruita: %s', e)
        novita = []
    oggi = datetime.date.today()
    # il confronto col mese prima ha senso solo sull'anno in corso: se guardi
    # il 2024 il «questo mese» non esiste, e fingere che esista sarebbe peggio
    mese = stats.mese_su_mese(con, year, oggi.month) if year == oggi.year else None
    restano = ben.da_fare(passi)
    con.close()
    return render_template('dashboard.html', k=k, year=year, months=months,
                           cose=cose, novita=novita, restano=restano,
                           elenco_restano=', '.join(
                               lng.in_frase(lng.t(p['titolo'], _lingua_app()), _lingua_app())
                               for p in restano),
                           mese=mese, mesi_nome=lng.mesi_app(_lingua_app()),
                           saluto=settings.get('owner_first_name', '').strip(),
                           oggi_giorno=lng.giorni_app(_lingua_app())[oggi.weekday()],
                           oggi_numero=oggi.day,
                           oggi_mese=lng.mesi_app(_lingua_app())[oggi.month - 1])


@app.route('/performance')
def performance():
    """Come sta andando: i numeri che si guardano, non quelli su cui si agisce.

    Stavano tutti sulla Dashboard, e la Dashboard non riusciva piu' a dire
    quale fosse la cosa da fare. Qui hanno lo spazio per essere grafici veri.
    """
    con = get_con()
    year = request.args.get('anno', type=int) or datetime.date.today().year
    k = stats.kpis(con, year)
    months = stats.monthly(con, year)
    months_prev = stats.monthly(con, year - 1)
    yearly = stats.revenue_by_year(con)
    clients = stats.by_client(con, year)[:8]
    services = stats.by_service(con, year)
    stato = cruscotto.stato_fatture(con, year)
    max_month = max(months + months_prev + [1])
    max_year_v = max([v['invoiced'] for v in yearly.values()] + [1])
    max_client = max([c[1] for c in clients] + [1])
    max_service = max([s[1] for s in services] + [1])
    con.close()
    return render_template('performance.html', k=k, year=year, months=months,
                           months_prev=months_prev, mesi=MESI_S, yearly=yearly,
                           clients=clients, services=services, stato=stato,
                           max_month=max_month, max_year_v=max_year_v,
                           max_client=max_client, max_service=max_service,
                           legacy_years=stats.LEGACY_YEARS)


@app.route('/benvenuto')
def benvenuto():
    """I primi passi. Ci si arriva da soli la prima volta, e ci si torna dal
    promemoria sulla Dashboard finché resta qualcosa da fare."""
    con = get_con()
    settings = db.get_settings(con)
    passi = ben.passi(con, settings)
    con.close()
    fatti, totali = ben.avanzamento(passi)
    return render_template('benvenuto.html', passi=passi, fatti=fatti, totali=totali,
                           essenziale_manca=ben.manca_l_essenziale(passi),
                           primo_avvio=fatti == 0)


# ---------------------------------------------------------------- nuova fattura
@app.route('/nuova', methods=['GET', 'POST'])
def nuova():
    con = get_con()
    if request.method == 'POST':
        return _crea_fattura(con)
    clients = con.execute('SELECT * FROM clients WHERE archived=0 ORDER BY name').fetchall()
    nxt = db.next_number(con)
    today = datetime.date.today()
    cestinata = con.execute('SELECT client_name FROM invoices WHERE number=? '
                            'AND deleted_at IS NOT NULL', (nxt,)).fetchone()
    elenco_servizi = srv.elenco(con, db.get_settings(con))
    con.close()
    return render_template('nuova.html', clients=clients, next_number=nxt,
                           today=today.isoformat(), servizi=elenco_servizi,
                           cestinata=cestinata['client_name'] if cestinata else None)


def _crea_fattura(con):
    f = request.form
    # --- cliente ---
    client_id = f.get('client_id', type=int)
    if f.get('nuovo_cliente') == '1':
        name = f.get('nc_nome', '').strip()
        a1 = f.get('nc_indirizzo1', '').strip()
        a2 = f.get('nc_indirizzo2', '').strip()
        if not name:
            avvisa('Nome del nuovo cliente mancante.', 'error')
            return redirect(url_for('nuova'))
        key = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        cur = con.execute(
            'INSERT INTO clients(key, name, address1, address2, file_label) VALUES(?,?,?,?,?) '
            'ON CONFLICT(key) DO UPDATE SET name=excluded.name RETURNING id',
            (key, name, a1, a2, name))
        client_id = cur.fetchone()['id']
    client = con.execute('SELECT * FROM clients WHERE id=?', (client_id,)).fetchone()
    if not client:
        avvisa('Seleziona un cliente.', 'error')
        return redirect(url_for('nuova'))
    addr_lines = [l for l in ([client['address1']] + (client['address2'] or '').split('\n')) if l]
    # Chi fa le sedute e chi riceve la fattura possono essere due persone
    # diverse (viene una persona, la fattura è intestata a un'altra).
    # Il nome sul documento e nel registro è l'intestatario; il nome del file
    # resta quello del cliente, così i documenti restano in fila con i vecchi.
    intestatario = (client['intestatario'] or '').strip() or client['name']

    # --- righe ---
    items = []
    total = 0
    for i in range(8):
        desc = f.get(f'desc_{i}', '').strip()
        qty_raw = f.get(f'qty_{i}', '').strip()
        unit_raw = f.get(f'unit_{i}', '').strip()
        tot_raw = f.get(f'tot_{i}', '').strip()
        if not desc and not tot_raw:
            continue
        qty = parse_qty(qty_raw or '1')
        unit_c = parse_amount(unit_raw)
        tot_c = parse_amount(tot_raw)
        if tot_c is None and unit_c is not None:
            tot_c = line_total(qty, unit_c)
        if tot_c is None:
            avvisa('Riga {n}: importo non riconosciuto («{cosa}»).', 'error',
                   n=i + 1, cosa=tot_raw or unit_raw)
            return redirect(url_for('nuova'))
        # Coerenza qty x unit = totale. Con quantita' 1 NON si blocca: e' il formato
        # che usi spesso sulle fatture-pacchetto (1 | "12 Sessions Pack" | 150.- | 1'800.-),
        # dove il prezzo unitario e' la tariffa a sessione e il totale e' il pacchetto.
        # Con quantita' maggiore di 1 una discrepanza e' invece un errore vero.
        if unit_c is not None and qty != 1:
            calc = line_total(qty, unit_c)
            if calc != tot_c:
                suggerimento = ''
                m = re.search(r'(\d+)\s*(?:x|×)?\s*(?:sessions?|credits?|crediti|sessioni)',
                              desc, re.I)
                if m and int(m.group(1)) != qty:
                    suggerimento = lng.t(' La descrizione parla di {quante} sessioni: '
                                         'forse la quantità è {quante}?',
                                         _lingua_app()).format(quante=m.group(1))
                avvisa('Riga {n}: {qty} × {unit} = {calc}, ma il totale riga indicato è '
                       '{tot}.{suggerimento} Correggi una delle cifre, oppure lascia '
                       'vuoto il totale e lo calcolo io.', 'error',
                       n=i + 1, qty=qty, unit=fmt_chf(unit_c), calc=fmt_chf(calc),
                       tot=fmt_chf(tot_c), suggerimento=suggerimento)
                return redirect(url_for('nuova'))
        items.append({'qty': qty, 'description': desc, 'unit_cents': unit_c, 'total_cents': tot_c})
        total += tot_c
    if not items:
        avvisa('Inserisci almeno una riga con descrizione e importo.', 'error')
        return redirect(url_for('nuova'))

    # --- numero e data ---
    number = f.get('numero', type=int) or db.next_number(con)
    dup = con.execute('SELECT id FROM invoices WHERE number=? AND deleted_at IS NULL',
                      (number,)).fetchone()
    if dup:
        avvisa('Il numero #{n} esiste già. Il prossimo libero è #{libero}.', 'error',
               n=number, libero=db.next_number(con))
        return redirect(url_for('nuova'))
    # se quel numero appartiene solo a una fattura nel Cestino, si puo' riusare:
    # serve per rifare una fattura sbagliata senza lasciare buchi
    nel_cestino = con.execute('SELECT number FROM invoices WHERE number=? AND deleted_at IS NOT NULL',
                              (number,)).fetchone()
    date_iso = f.get('data') or datetime.date.today().isoformat()
    d = datetime.date.fromisoformat(date_iso)
    date_str = d.strftime('%d-%m-%y')
    year = d.year

    # --- genera file ---
    settings = db.get_settings(con)
    label = (client['file_label'] or client['name']).strip()
    fname = f'{label} #{number}'
    out_dir = os.path.join(INVOICE_DIR, str(year))
    docx_path = os.path.join(out_dir, fname + '.docx')
    pdf_path = os.path.join(out_dir, fname + '.pdf')
    if os.path.exists(docx_path) or os.path.exists(pdf_path):
        avvisa('Esiste già un file «{file}» — per sicurezza non sovrascrivo.', 'error',
               file=fname)
        return redirect(url_for('nuova'))
    # la lingua della fattura e' quella del CLIENTE: e' lui che la legge
    lingua_cliente = lng.normalizza_doc(
        client['lingua'] if 'lingua' in client.keys() else None)
    docgen.build_docx(docx_path, number, date_str, intestatario, addr_lines, items, total,
                      settings, lingua_cliente)
    pdfgen.build_pdf(pdf_path, number, date_str, intestatario, addr_lines, items,
                     total, settings, lingua_cliente)

    # --- VERIFICA AUTOMATICA: rileggo i file veri e controllo gli importi al centesimo.
    #     Se qualcosa non torna, NON salvo la fattura e rimuovo i file generati. ---
    problems = verify.verify_generated(docx_path, pdf_path, total, items)
    if problems:
        for p in (docx_path, pdf_path):
            if os.path.exists(p):
                os.remove(p)
        con.close()
        avvisa('⚠️ Fattura NON creata: la verifica automatica ha trovato un problema. '
               '{guai} Nessun file è stato salvato: controlla i dati e riprova.', 'error',
               guai=' '.join(problems))
        return redirect(url_for('nuova'))

    cur = con.execute(
        'INSERT INTO invoices(number, client_id, client_name, client_address, date, year, '
        "total_cents, status, source, docx_path, pdf_path, created_at) "
        "VALUES(?,?,?,?,?,?,?, 'emessa', 'app', ?, ?, ?)",
        (number, client['id'], intestatario, '\n'.join(addr_lines), date_iso, year,
         total, docx_path, pdf_path, db.now_iso()))
    inv_id = cur.lastrowid
    for pos, it in enumerate(items):
        con.execute('INSERT INTO items(invoice_id,pos,qty,description,unit_cents,total_cents) '
                    'VALUES(?,?,?,?,?,?)',
                    (inv_id, pos, str(it['qty']), it['description'],
                     it['unit_cents'], it['total_cents']))
    con.commit()
    con.close()
    lg = _lingua_app()
    msg = lng.t('Fattura #{n} creata e verificata ✓ — {tot} (importo confermato '
                'identico su Word e PDF).', lg).format(n=number, tot=fmt_chf(total))
    if nel_cestino:
        msg += lng.t(' Il numero #{n} è stato riusato da una fattura nel Cestino.',
                     lg).format(n=number)
    # --- crediti: si aggiornano da soli, e se qualcosa non torna lo dicono ---
    avviso = None
    try:
        reg = sess.carica()
        info = sess.analizza_fattura(client['name'], total,
                                     [it['description'] for it in items])
        if info['e_pacchetto'] and info['prezzo_ok']:
            esito, dettaglio = sess.aggancia_fattura(reg, client['name'], number,
                                                     total, date_iso)
            if esito:
                sess.salva(reg)
                frase, valori = dettaglio
                msg += ' 🎟️ ' + lng.t(frase, lg).format(**valori)
        elif info['e_pacchetto'] and not info['prezzo_ok']:
            # sembra un pacchetto ma l'importo non e' quello solito: NON tocco i crediti
            attesi = ' o '.join(fmt_chf(x) for x in info['prezzo_atteso']) or '—'
            avviso = lng.t(
                '⚠️ Crediti NON aggiornati. Questa sembra una fattura-pacchetto per '
                '{chi}, ma il totale è {tot} mentre il pacchetto costa {attesi}. '
                'Controlla la quantità e il prezzo: per un pacchetto da {crediti} '
                'crediti la quantità di solito non è 1. Se invece il prezzo è cambiato '
                'davvero, aggiornalo nella scheda del cliente a crediti.', lg).format(
                    chi=sess.nome_cliente(info['chiave']), tot=fmt_chf(total),
                    attesi=attesi, crediti=sess.cliente(info['chiave'])['crediti'])
        elif info['ha_crediti']:
            msg += lng.t(' 🎟️ Crediti invariati: questa fattura non compra un '
                         'pacchetto di sessioni.', lg)
    except Exception as e:
        err_logger.error('Aggancio crediti fallito per #%s: %s', number, e)
        avviso = lng.t('Non sono riuscito ad aggiornare i crediti per questa '
                       'fattura: controlla la pagina Crediti.', lg)
    # --- copia fuori dal Mac: una fattura appena fatta non deve stare in un
    # posto solo nemmeno per un minuto ---
    esito = backup.archivia_fuori(_cartella_backup(), motivo=f'fattura-{number}')
    if not esito['ok']:
        err_logger.error('Backup esterno fallito dopo #%s: %s', number, esito['errore'])
        avvisa('La fattura è salvata, ma la copia di sicurezza fuori dal Mac non è '
               'riuscita: {guaio} — controlla in Impostazioni.', 'error',
               guaio=esito['errore'])
    flash(msg, 'ok')
    if avviso:
        flash(avviso, 'error')
    return redirect(url_for('fattura', inv_id=inv_id))


# ---------------------------------------------------------------- elenco/dettaglio
@app.route('/fatture')
def fatture():
    con = get_con()
    # entrando si guarda l'anno in corso: e' quello che serve nove volte su
    # dieci. «Tutti gli anni» arriva come anno= vuoto, ed e' una scelta esplicita
    # che va rispettata; se nell'anno in corso non c'e' ancora niente si ripiega
    # sull'ultimo anno che ha fatture, per non aprire su una pagina vuota.
    if 'anno' in request.args:
        year = request.args.get('anno', type=int)
    else:
        anni = [r['year'] for r in con.execute(
            'SELECT DISTINCT year FROM invoices WHERE year IS NOT NULL '
            'AND deleted_at IS NULL ORDER BY year DESC')]
        oggi = datetime.date.today().year
        year = oggi if oggi in anni else (anni[0] if anni else None)
    q = request.args.get('q', '').strip()
    stato = request.args.get('stato', '')
    sql = 'SELECT * FROM invoices WHERE deleted_at IS NULL'
    args = []
    if year:
        sql += ' AND year=?'
        args.append(year)
    if q:
        sql += ' AND (client_name LIKE ? OR CAST(number AS TEXT) LIKE ?)'
        args += [f'%{q}%', f'%{q}%']
    if stato:
        sql += ' AND status=?'
        args.append(stato)
    invio = request.args.get('invio', '')
    if invio == 'inviate':
        sql += ' AND sent_at IS NOT NULL'
    elif invio == 'da-mandare':
        sql += " AND sent_at IS NULL AND source='app'"
    sql += ' ORDER BY COALESCE(number, 0) DESC, date DESC'
    rows = con.execute(sql, args).fetchall()
    tot = sum(r['total_cents'] or 0 for r in rows)
    con.close()
    return render_template('fatture.html', rows=rows, year=year, q=q, stato=stato,
                           invio=invio, tot=tot)


@app.route('/fattura/<int:inv_id>')
def fattura(inv_id):
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE id=?', (inv_id,)).fetchone()
    if not inv:
        abort(404)
    items = con.execute('SELECT * FROM items WHERE invoice_id=? ORDER BY pos', (inv_id,)).fetchall()
    settings = db.get_settings(con)
    src_root = settings['source_folder']
    con.close()
    has_src = bool(inv['source_file']) and os.path.exists(os.path.join(src_root, inv['source_file']))
    return render_template('fattura.html', inv=inv, items=items, has_src=has_src)


@app.route('/fattura/<int:inv_id>/stato', methods=['POST'])
def toggle_stato(inv_id):
    con = get_con()
    inv = con.execute('SELECT status FROM invoices WHERE id=?', (inv_id,)).fetchone()
    if inv:
        new = 'pagata' if inv['status'] != 'pagata' else 'emessa'
        con.execute('UPDATE invoices SET status=? WHERE id=?', (new, inv_id))
        con.commit()
    con.close()
    return redirect(request.referrer or url_for('fatture'))


@app.route('/fattura/<int:inv_id>/file/<kind>')
def fattura_file(inv_id, kind):
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE id=?', (inv_id,)).fetchone()
    settings = db.get_settings(con)
    con.close()
    if not inv:
        abort(404)
    path = None
    if kind == 'pdf' and inv['pdf_path'] and os.path.exists(inv['pdf_path']):
        path = inv['pdf_path']
    elif kind == 'docx' and inv['docx_path'] and os.path.exists(inv['docx_path']):
        path = inv['docx_path']
    elif kind == 'src' and inv['source_file']:
        cand = os.path.join(settings['source_folder'], inv['source_file'])
        if os.path.exists(cand):
            path = cand
    if not path:
        abort(404)
    return send_file(path)


def _fatture_allegabili(con, inv):
    """Le altre fatture che potrebbero andare nella stessa mail.

    Il caso vero: a una persona si manda la sua fattura piu' quella del
    coniuge, fatte lo stesso giorno. Quindi NON si filtra per cliente ma per
    tempo: le fatture recenti fatte con l'app (le uniche che hanno un PDF) e
    non ancora spedite.
    """
    limite = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    righe = con.execute(
        "SELECT * FROM invoices WHERE deleted_at IS NULL AND id != ? "
        "AND sent_at IS NULL AND source = 'app' AND date >= ? "
        "ORDER BY COALESCE(number, 0) DESC LIMIT 8", (inv['id'], limite)).fetchall()
    return [r for r in righe if r['pdf_path'] and os.path.exists(r['pdf_path'])]


def _oggetti_email(con, inv, cli):
    """Gli oggetti delle mail gia' partite: tutti, e quelli di questa persona.

    Servono a due cose diverse. Da tutti si impara come abbrevia i mesi (se una
    volta ha scritto «Sept», l'app continua a scrivere «Sept»); da quelli di
    questa persona si riparte quando sulla fattura non c'e' scritto il periodo.
    Ordine dal piu' vecchio al piu' recente: l'ultima parola e' quella buona.
    """
    email = ((cli['email'] if cli and 'email' in cli.keys() else '') or '').strip()
    righe = con.execute(
        "SELECT e.oggetto, e.destinatario, i.client_name "
        "FROM email_log e LEFT JOIN invoices i ON i.id = e.invoice_id "
        "WHERE e.esito = 'ok' AND COALESCE(e.prova, 0) = 0 AND COALESCE(e.oggetto, '') != '' "
        "ORDER BY e.id").fetchall()
    tutti = [r['oggetto'] for r in righe]
    suoi = [r['oggetto'] for r in righe
            if (email and (r['destinatario'] or '').strip().lower() == email.lower())
            or (r['client_name'] and r['client_name'] == inv['client_name'])]
    return tutti, suoi


def _percorsi_extra(con, ids, settings):
    """Da id di fattura a PDF da allegare. Ritorna anche cosa non si e' trovato."""
    out, mancanti = [], []
    for i in ids:
        r = con.execute('SELECT * FROM invoices WHERE id=? AND deleted_at IS NULL', (i,)).fetchone()
        if not r:
            continue
        p = mailer.allegato_di(r, settings)
        if p:
            out.append(p)
        else:
            mancanti.append(f"#{r['number']}")
    return out, mancanti


PAUSA_MINUTI = 20


def _lingua_app():
    """La lingua scelta, letta una volta sola per ogni richiesta."""
    if not hasattr(g, 'lingua_app'):
        con = get_con()
        g.lingua_app = lng.normalizza(db.get_settings(con).get('lingua'))
        con.close()
    return g.lingua_app


def avvisa(frase, categoria='ok', **valori):
    """Un messaggio in cima alla pagina, nella lingua dell'app.

    La frase italiana e' la chiave del dizionario, e i pezzi che cambiano
    (numeri, nomi, importi) arrivano a parte invece che gia' incollati
    dentro: una frase composta a pezzi non si potrebbe tradurre, perche'
    ogni lingua mette le parole in un ordine suo.
    """
    testo = lng.t(frase, _lingua_app())
    flash(testo.format(**valori) if valori else testo, categoria)


def _pausa_smtp(settings):
    """Dopo due password sbagliate l'app smette di provare per un po'.

    Non e' pignoleria: il server blocca l'indirizzo IP dopo pochi tentativi
    falliti, e da quel momento non funziona nemmeno la password giusta.
    """
    fino = settings.get('smtp_pausa_fino') or ''
    if not fino:
        return ''
    try:
        quando = datetime.datetime.fromisoformat(fino)
    except ValueError:
        return ''
    if datetime.datetime.now() >= quando:
        return ''
    restano = int((quando - datetime.datetime.now()).total_seconds() // 60) + 1
    return lng.t('Mi fermo qui. Il server ha già rifiutato la password due volte e al '
                 'terzo tentativo blocca il tuo indirizzo IP per un pezzo. Riprova fra '
                 '{restano} minuti, oppure correggi prima la password in Impostazioni: '
                 'salvarla azzera questa pausa.',
                 lng.normalizza(settings.get('lingua'))).format(restano=restano)


def _conta_fallimento(con, codice, errore):
    """Tiene il conto delle password rifiutate e mette in pausa al secondo no."""
    if codice != 'auth':
        return errore
    n = int(db.get_settings(con).get('smtp_fallimenti') or 0) + 1
    db.set_setting(con, 'smtp_fallimenti', str(n))
    if n >= 2:
        fino = datetime.datetime.now() + datetime.timedelta(minutes=PAUSA_MINUTI)
        db.set_setting(con, 'smtp_pausa_fino', fino.isoformat(timespec='seconds'))
        return errore + lng.t(
            ' È il {n}° rifiuto: non provo più per {minuti} minuti, altrimenti il '
            'server blocca il tuo indirizzo IP. Correggi la password in Impostazioni '
            '— salvarla toglie la pausa.',
            _lingua_app()).format(n=n, minuti=PAUSA_MINUTI)
    return errore


def _numeri_fatture(con, ids):
    """I numeri delle fatture allegate, nell'ordine in cui sono stati scelti."""
    fuori = []
    for i in ids:
        r = con.execute('SELECT number FROM invoices WHERE id=?', (i,)).fetchone()
        if r and r['number']:
            fuori.append(str(r['number']))
    return ', '.join(fuori)


def _intestazioni(msg, settings, destinatario=None):
    """Mittente, copia nascosta e testo, come sono partiti davvero."""
    copia = (settings.get('email_copia_a_me') == '1') and not destinatario
    return {
        'mittente': settings.get('email_from') or settings.get('smtp_user', ''),
        'ccn': settings.get('smtp_user', '') if copia else '',
        'corpo': msg.get('body') or '',
    }


def _registra_email(con, **campi):
    """Una riga nel registro delle email. Non deve mai far fallire un invio:
    la mail e' gia' partita, perdere la riga di diario e' meno grave."""
    campi.setdefault('sent_at', datetime.datetime.now().isoformat(timespec='seconds'))
    colonne = ('sent_at', 'destinatario', 'oggetto', 'fatture', 'invoice_id',
               'allegati', 'prova', 'esito', 'motivo', 'cartella',
               'mittente', 'ccn', 'corpo')
    try:
        con.execute(
            f"INSERT INTO email_log({','.join(colonne)}) "
            f"VALUES({','.join('?' * len(colonne))})",
            [campi.get(c, '') if c not in ('invoice_id', 'prova') else campi.get(c)
             for c in colonne])
        con.commit()
    except Exception as e:                       # pragma: no cover
        err_logger.error('Registro email non scritto: %s', e)


@app.route('/fattura/<int:inv_id>/email', methods=['GET', 'POST'])
def fattura_email(inv_id):
    """Anteprima e invio. Niente parte finche' non si preme un pulsante."""
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE id=?', (inv_id,)).fetchone()
    if inv is None:
        con.close()
        abort(404)
    cli = None
    if inv['client_id']:
        cli = con.execute('SELECT * FROM clients WHERE id=?', (inv['client_id'],)).fetchone()
    if cli is None:
        cli = con.execute('SELECT * FROM clients WHERE name=?', (inv['client_name'],)).fetchone()
    desc = [r['description'] for r in
            con.execute('SELECT description FROM items WHERE invoice_id=? ORDER BY pos', (inv_id,))]
    settings = db.get_settings(con)
    altre = _fatture_allegabili(con, inv)

    f = request.form
    scelte = [int(x) for x in f.getlist('allega') if x.isdigit()]
    azione = f.get('azione', '')
    corpo = f.get('corpo') if 'corpo' in f else None
    # il modello scelto a mano vince sulla deduzione automatica; se non e' stato
    # scelto niente decide componi() guardando le righe della fattura
    modello = f.get('modello') or None
    extra, senza_pdf = _percorsi_extra(con, scelte, settings)
    tutti_oggetti, suoi_oggetti = _oggetti_email(con, inv, cli)
    mese = mailer.mese_oggetto(desc, suoi_oggetti, tutti_oggetti)
    msg = mailer.componi(inv, cli, settings, desc, corpo, extra, modello, mese)
    # l'oggetto dell'altro modello serve gia' pronto: cosi' cambiando servizio
    # cambia subito, senza dover riscrivere anche il testo
    oggetti = {}
    for chiave, _nome in mailer.MODELLI:
        altro = mailer.componi(inv, cli, settings, desc, corpo, extra, chiave, mese)
        oggetti[chiave] = {'subject': altro['subject'], 'usa_mese': altro['usa_mese']}
    if senza_pdf:
        msg['problemi'].append('Di ' + ', '.join(senza_pdf) + " non esiste il PDF "
                               '(sono fatture vecchie salvate solo in Word): non posso allegarle.')

    # il testo mostrato: quello ricalcolato, oppure quello che sta ritoccando
    if azione in ('prova', 'invia') and f.get('body'):
        msg['subject'] = f.get('subject', msg['subject'])
        msg['body'] = f['body']

    def pagina():
        return render_template('email.html', inv=inv, cli=cli, msg=msg, settings=settings,
                               altre=altre, scelte=scelte, modelli=mailer.MODELLI,
                               oggetti=oggetti, segnaposto_mese=mailer.SEGNAPOSTO_MESE,
                               corpo=corpo if corpo is not None
                               else mailer.testo_modello(settings, msg['modello'],
                                                         msg['lingua']))

    if azione in ('prova', 'invia'):
        pausa = _pausa_smtp(settings)
        if pausa:
            flash(pausa, 'error')
            con.close()
            return pagina()
        if msg['problemi']:
            avvisa("Non mando niente finché c'è un problema aperto: {guai}", 'error',
                   guai=' '.join(msg['problemi']))
            con.close()
            return pagina()
        destinatario = (settings.get('email_test_to') or settings.get('smtp_user')) \
            if azione == 'prova' else None
        numeri = _numeri_fatture(con, [inv_id] + scelte)
        allegati = ', '.join(os.path.basename(x) for x in msg.get('allegati') or [])
        ok, errore, codice = mailer.spedisci(msg, settings, destinatario)
        if not ok:
            err_logger.error('Invio email fallito per #%s: %s', inv['number'], errore)
            _registra_email(con, destinatario=destinatario or msg['to'],
                            oggetto=msg['subject'], fatture=numeri, invoice_id=inv_id,
                            allegati=allegati, prova=1 if azione == 'prova' else 0,
                            esito='errore', motivo=mailer._nascondi(errore, settings),
                            **_intestazioni(msg, settings, destinatario))
            avvisa('Non è partita: {guaio}', 'error',
                   guaio=_conta_fallimento(con, codice, errore))
            con.close()
            return pagina()
        db.set_setting(con, 'smtp_fallimenti', '0')
        db.set_setting(con, 'smtp_pausa_fino', '')
        # copia in «Inviata», cosi' la mail si ritrova da Mail e dal telefono come
        # tutte le altre. Vale anche per la prova: una prova che non prova il
        # deposito non proverebbe la cosa che interessa.
        copiata, perche, cartella = mailer.archivia_in_inviata(msg['_inviato'], settings)
        if copiata:
            if cartella and cartella != settings.get('imap_cartella'):
                db.set_setting(con, 'imap_cartella', cartella)
        else:
            err_logger.error('Copia in Inviata fallita per #%s: %s', inv['number'], perche)
            avvisa('La mail è partita, ma non sono riuscito a metterne una copia in '
                   'Inviata: {guaio}', 'error', guaio=perche)
        _registra_email(con, destinatario=destinatario or msg['to'],
                        oggetto=msg['subject'], fatture=numeri, invoice_id=inv_id,
                        allegati=allegati, prova=1 if azione == 'prova' else 0,
                        esito='ok', cartella=cartella if copiata else '',
                        motivo='' if copiata else 'copia in Inviata non riuscita: ' + perche,
                        **_intestazioni(msg, settings, destinatario))
        if azione == 'prova':
            dove = (lng.t(' e ne trovi la copia in «{cartella}»',
                          _lingua_app()).format(cartella=cartella) if copiata else '')
            avvisa("Prova inviata a {a}{dove}. Guarda com'è arrivata prima di mandarla "
                   'al cliente.', 'ok', a=destinatario, dove=dove)
            con.close()
            return pagina()
        adesso = datetime.datetime.now().isoformat(timespec='seconds')
        for i in [inv_id] + scelte:
            con.execute('UPDATE invoices SET sent_at=? WHERE id=?', (adesso, i))
        con.commit()
        con.close()
        quante = 1 + len(scelte)
        adesso_it = datetime.datetime.now()
        avvisa('Fattura inviata a {a} il {data} alle {ora}.' if quante == 1
               else '{quante} fatture inviate a {a} il {data} alle {ora}.', 'ok',
               quante=quante, a=msg['to'], data=adesso_it.strftime('%d.%m.%Y'),
               ora=adesso_it.strftime('%H:%M'))
        return redirect(url_for('fattura', inv_id=inv_id))

    con.close()
    return pagina()


@app.route('/fattura/<int:inv_id>/elimina', methods=['POST'])
def elimina(inv_id):
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE id=?', (inv_id,)).fetchone()
    if not inv:
        abort(404)
    if inv['source'] != 'app':
        avvisa('Le fatture importate dallo storico non si possono eliminare da qui.', 'error')
        con.close()
        return redirect(url_for('fattura', inv_id=inv_id))
    # backup del database PRIMA di toccare qualsiasi cosa
    backup.make_backup(f"prima-eliminazione-{inv['number']}")
    # eliminazione REVERSIBILE: la fattura non viene cancellata, va nel Cestino.
    # I file vengono spostati (mai eliminati) e tornano al loro posto se ripristini.
    os.makedirs(TRASH_DIR, exist_ok=True)
    for p in (inv['docx_path'], inv['pdf_path']):
        if p and os.path.exists(p):
            dest = os.path.join(TRASH_DIR, os.path.basename(p))
            if os.path.exists(dest):
                dest = os.path.join(TRASH_DIR, f"{inv['id']}-{os.path.basename(p)}")
            shutil.move(p, dest)
    con.execute('UPDATE invoices SET deleted_at=?, deleted_reason=? WHERE id=?',
                (db.now_iso(), (request.form.get('motivo') or '').strip(), inv_id))
    con.commit()
    con.close()
    avvisa('Fattura #{n} spostata nel Cestino. Nulla è andato perso: puoi '
           'ripristinarla dalla pagina Cestino.', 'ok', n=inv['number'])
    return redirect(url_for('fatture'))


@app.route('/cestino')
def cestino():
    con = get_con()
    rows = con.execute('SELECT * FROM invoices WHERE deleted_at IS NOT NULL '
                       'ORDER BY deleted_at DESC').fetchall()
    backups = backup.list_backups()
    con.close()
    lg = _lingua_app()
    for b in backups[:12]:
        b['motivo'] = backup.motivo_in_parole(b.get('reason') or '', lg)
    return render_template('cestino.html', rows=rows, backups=backups[:12],
                           n_backups=len(backups), trash_dir=TRASH_DIR)


@app.route('/cestino/<int:inv_id>/ripristina', methods=['POST'])
def cestino_ripristina(inv_id):
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE id=?', (inv_id,)).fetchone()
    if not inv or not inv['deleted_at']:
        con.close()
        abort(404)
    # rimetto i file al loro posto
    restored = 0
    for p in (inv['docx_path'], inv['pdf_path']):
        if not p:
            continue
        base = os.path.basename(p)
        for cand in (os.path.join(TRASH_DIR, base),
                     os.path.join(TRASH_DIR, f"{inv['id']}-{base}")):
            if os.path.exists(cand) and not os.path.exists(p):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                shutil.move(cand, p)
                restored += 1
                break
    con.execute('UPDATE invoices SET deleted_at=NULL, deleted_reason="" WHERE id=?', (inv_id,))
    con.commit()
    con.close()
    avvisa('Fattura #{n} ripristinata ({quanti} file rimessi al loro posto).', 'ok',
           n=inv['number'], quanti=restored)
    return redirect(url_for('fattura', inv_id=inv_id))


# ---------------------------------------------------------------- clienti
@app.route('/clienti')
def clienti():
    con = get_con()
    rows = con.execute('SELECT * FROM clients ORDER BY archived, name').fetchall()
    stats_c = {}
    for r in con.execute('SELECT client_id, COUNT(*) n, SUM(total_cents) t, MAX(date) last '
                         'FROM invoices WHERE client_id IS NOT NULL AND deleted_at IS NULL GROUP BY client_id'):
        stats_c[r['client_id']] = r
    st = db.get_settings(con)
    con.close()
    # come si chiudono le mail: si mostra il testo vero, non un esempio
    codice = lng.normalizza(st.get('lingua'))
    saluti = {lg: {t: (mailer.saluto_di(st, t, lg)
                       or lng.t('(non ancora scritto)', codice)).strip()
                   for t in ('informale', 'formale')}
              for lg in db.LINGUE_MODELLI}
    return render_template('clienti.html', rows=rows, stats_c=stats_c, saluti=saluti)


@app.route('/cliente/<int:cid>', methods=['POST'])
def cliente_salva(cid):
    f = request.form
    con = get_con()
    # 'tono' c'era nel modulo ma non qui: il menu «come ti firmi» si poteva
    # cambiare e non veniva mai salvato
    con.execute('UPDATE clients SET name=?, address1=?, address2=?, file_label=?, notes=?, '
                'email=?, tono=?, lingua=?, paga_come=?, intestatario=?, abbonamento=?, '
                'archived=? WHERE id=?',
                (f.get('name', '').strip(), f.get('address1', '').strip(),
                 f.get('address2', '').strip(), f.get('file_label', '').strip(),
                 f.get('notes', '').strip(), f.get('email', '').strip(),
                 'formale' if f.get('tono') == 'formale' else 'informale',
                 lng.normalizza_doc(f.get('lingua')),
                 f.get('paga_come', '').strip(),
                 f.get('intestatario', '').strip(),
                 1 if f.get('abbonamento') else 0,
                 1 if f.get('archived') else 0, cid))
    con.commit()
    con.close()
    avvisa('Cliente aggiornato.', 'ok')
    return redirect(url_for('clienti'))


@app.route('/cliente/nuovo', methods=['POST'])
def cliente_nuovo():
    f = request.form
    name = f.get('name', '').strip()
    if not name:
        avvisa('Nome mancante.', 'error')
        return redirect(url_for('clienti'))
    key = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    con = get_con()
    con.execute('INSERT OR IGNORE INTO clients(key,name,address1,address2,file_label,email) '
                'VALUES(?,?,?,?,?,?)',
                (key, name, f.get('address1', '').strip(), f.get('address2', '').strip(),
                 f.get('file_label', '').strip() or name, f.get('email', '').strip()))
    con.commit()
    con.close()
    avvisa('Cliente «{nome}» aggiunto.', 'ok', nome=name)
    return redirect(url_for('clienti'))


# ---------------------------------------------------------------- commercialista
@app.route('/commercialista')
def commercialista():
    con = get_con()
    yearly = stats.revenue_by_year(con)
    settings = db.get_settings(con)
    con.close()
    pkgs = sorted(glob.glob(os.path.join(exports.EXPORT_DIR, '*.zip')), reverse=True)
    return render_template('commercialista.html', yearly=yearly, settings=settings,
                           pkgs=[os.path.basename(p) for p in pkgs],
                           legacy_years=stats.LEGACY_YEARS)


@app.route('/commercialista/genera', methods=['POST'])
def commercialista_genera():
    year = request.form.get('anno', type=int)
    con = get_con()
    settings = db.get_settings(con)
    res = exports.build_package(con, year, settings, settings['source_folder'],
                                exports.lingua_pacchetto(settings, _lingua_app()))
    con.close()
    lg = _lingua_app()
    msg = lng.t('Pacchetto {anno} pronto: Excel + PDF riepilogo + {quante} fatture '
                'PDF. Zip: {zip}', lg).format(anno=year, quante=res['copied'],
                                              zip=os.path.basename(res['zip']))
    if res['missing']:
        msg += lng.t(' — PDF non trovati per: {elenco}', lg).format(
            elenco=', '.join(res['missing'][:6]))
    flash(msg, 'ok')
    subprocess.Popen(['open', res['folder']])
    return redirect(url_for('commercialista'))


@app.route('/esporti/<path:fname>')
def esporti_file(fname):
    p = os.path.join(exports.EXPORT_DIR, fname)
    if not os.path.exists(p):
        abort(404)
    return send_file(p, as_attachment=True)


# ---------------------------------------------------------------- crediti
MINUTI_FRA_SINCRONIZZAZIONI = 15


def _sincronizza_calendario(forzata=False):
    """Legge il calendario delle sessioni e aggiorna i crediti.

    Ritorna (esito, messaggio). Non solleva mai: se il calendario non risponde
    si continua a mostrare l'ultima situazione conosciuta, che e' molto meglio
    di una pagina di errore al posto dei propri dati.
    """
    import sync_sessions
    con = get_con()
    s = db.get_settings(con)
    con.close()
    url = (s.get('calendario_ics') or '').strip()
    if not url:
        return 'spento', ''
    ultimo = s.get('calendario_ultimo') or ''
    if not forzata and ultimo:
        try:
            quando = datetime.datetime.fromisoformat(ultimo)
            if (datetime.datetime.now() - quando).total_seconds() < MINUTI_FRA_SINCRONIZZAZIONI * 60:
                return 'recente', ''
        except ValueError:
            pass
    reg = sess.carica()
    da, a = sync_sessions.finestra(reg)
    if da > a:
        return 'niente', ''
    try:
        testo = calendario.scarica(url)
        eventi = calendario.leggi(testo, da, a, e_testo=True)
    except Exception as e:
        err_logger.error('Lettura calendario fallita: %s', e)
        return 'errore', f'{type(e).__name__}: {e}'
    try:
        rap = sync_sessions.sincronizza(reg, eventi)
        if rap['aggiunte']:
            sess.salva(reg)
    except Exception as e:
        err_logger.error('Sincronizzazione crediti fallita: %s', e)
        return 'errore', f'{type(e).__name__}: {e}'
    con = get_con()
    db.set_setting(con, 'calendario_ultimo',
                   datetime.datetime.now().isoformat(timespec='seconds'))
    # come si chiama, l'ha detto lui: cosi' le pagine lo nominano per nome
    # senza che il nome di nessuno stia scritto nel programma
    come_si_chiama = calendario.nome(testo)
    if come_si_chiama:
        db.set_setting(con, 'calendario_nome', come_si_chiama)
    con.close()
    nuove = [f"{x['data']} {x['cliente']}" for x in rap['aggiunte']]
    return 'fatto', ' · '.join(nuove)


@app.route('/crediti/sincronizza', methods=['POST'])
def crediti_sincronizza():
    esito, dettaglio = _sincronizza_calendario(forzata=True)
    if esito == 'spento':
        avvisa("Manca l'indirizzo iCal del calendario: si incolla in Impostazioni.", 'error')
    elif esito == 'errore':
        avvisa('Il calendario non risponde: {guaio} — i crediti qui sotto sono quelli '
               "dell'ultima lettura riuscita.", 'error', guaio=dettaglio)
    elif dettaglio:
        avvisa('Sessioni nuove registrate: {dettaglio}', 'ok', dettaglio=dettaglio)
    else:
        avvisa('Calendario letto: nessuna sessione nuova.', 'ok')
    return redirect(url_for('crediti'))


@app.route('/crediti')
def crediti():
    """Vista crediti per cliente (SPEC-crediti.md 6.2)."""
    esito_sync, dettaglio_sync = _sincronizza_calendario()
    reg = sess.carica()
    righe = sess.vista_crediti(reg)
    da, a = None, datetime.date.today()
    try:
        import sync_sessions
        da, a = sync_sessions.finestra(reg)
    except Exception:
        pass
    con = get_con()
    # fatture recenti per il collegamento pacchetto -> fattura (6.3)
    recenti = con.execute(
        'SELECT number, client_name, date, total_cents FROM invoices '
        'WHERE deleted_at IS NULL AND number IS NOT NULL '
        'ORDER BY number DESC LIMIT 25').fetchall()
    # il registro sa solo QUALE fattura copre il pacchetto, non se e' stata
    # incassata: lo stato di pagamento sta nel database e si legge ogni volta.
    stati = {r['number']: r['status'] for r in con.execute(
        'SELECT number, status FROM invoices '
        'WHERE deleted_at IS NULL AND number IS NOT NULL')}
    con.close()
    for r in righe:
        r['fattura_stato'] = stati.get(r.get('fattura_numero'))
    pacchetti = {p['id']: p for p in reg['pacchetti']}
    con2 = get_con()
    impostazioni_cal = db.get_settings(con2)
    con2.close()
    return render_template('crediti.html', righe=righe, pacchetti=pacchetti,
                           recenti=recenti, finestra=(da, a),
                           aggiornato=reg.get('generato'),
                           sync_esito=esito_sync, sync_dettaglio=dettaglio_sync,
                           sync_quando=impostazioni_cal.get('calendario_ultimo'),
                           sync_attivo=bool((impostazioni_cal.get('calendario_ics') or '').strip()))


@app.route('/crediti/clienti')
def crediti_clienti():
    """Chi lavora a pacchetti di sessioni prepagate."""
    con = get_con()
    righe = [dict(r) for r in db.crediti_clienti(con)]
    con.close()
    reg = sess.carica()
    for r in righe:
        r['prezzi_leggibili'] = ', '.join(
            fmt_chf(int(x), False) for x in r['prezzi'].split(',') if x.strip())
        # quanti pacchetti porta gia' il suo nome: dice se si puo' cancellare
        r['pacchetti'] = sum(1 for p in reg['pacchetti']
                             if r['nome'].lower() in p['cliente'].lower())
    return render_template('crediti_clienti.html', righe=righe,
                           nomi={r['chiave']: r['nome'] for r in righe})


@app.route('/crediti/clienti/salva', methods=['POST'])
def crediti_cliente_salva():
    f = request.form
    chiave = sess.chiave_da_nome(f.get('chiave') or f.get('nome'))
    nome = (f.get('nome') or '').strip()
    if not chiave or not nome:
        avvisa('Servono almeno il nome e la parola da cercare nel calendario.', 'error')
        return redirect(url_for('crediti_clienti'))
    try:
        crediti = max(0, int(f.get('crediti') or 0))
    except ValueError:
        avvisa('I crediti devono essere un numero.', 'error')
        return redirect(url_for('crediti_clienti'))
    con = get_con()
    esistenti = {r['chiave']: r for r in db.crediti_clienti(con)}
    nuovo = chiave not in esistenti
    compagno = sess.chiave_da_nome(f.get('compagno'))
    if compagno == chiave:
        compagno = ''                       # non puo' essere il supplemento di se stesso
    if compagno and compagno not in esistenti:
        con.close()
        avvisa('«{chi}» non è fra i clienti a crediti: aggiungilo prima.', 'error',
               chi=compagno)
        return redirect(url_for('crediti_clienti'))
    db.crediti_cliente_salva(con, chiave, {
        'nome': nome,
        'crediti': crediti,
        'prefisso': (f.get('prefisso') or nome[:3]).strip().upper(),
        'prezzi': sess.prezzi_da_testo(f.get('prezzi')),
        'fattura_a': (f.get('fattura_a') or '').strip(),
        'compagno': compagno,
        'attivo': 0 if f.get('archiviato') else 1,
        'pos': esistenti[chiave]['pos'] if not nuovo else len(esistenti),
    })
    con.close()
    sess.ricarica()          # l'app deve accorgersene subito
    avvisa('{nome} è ora fra i clienti a crediti.' if nuovo
           else 'Modifiche salvate per {nome}.', 'ok', nome=nome)
    return redirect(url_for('crediti_clienti'))


@app.route('/crediti/clienti/<chiave>/elimina', methods=['POST'])
def crediti_cliente_elimina(chiave):
    con = get_con()
    riga = next((r for r in db.crediti_clienti(con) if r['chiave'] == chiave), None)
    if riga is None:
        con.close()
        abort(404)
    # se ha gia' dei pacchetti nel registro, cancellarlo lascerebbe quei
    # pacchetti senza padrone: si archivia e basta
    reg = sess.carica()
    quanti = sum(1 for p in reg['pacchetti'] if riga['nome'].lower() in p['cliente'].lower())
    if quanti:
        db.crediti_cliente_salva(con, chiave, dict(riga, attivo=0))
        con.close()
        sess.ricarica()
        avvisa(('{nome} ha {quanti} pacchetto nel registro: cancellare la scheda '
                "perderebbe quella storia. L'ho archiviata — il nome resta riconosciuto "
                'nel calendario, ma non si aprono più pacchetti nuovi.') if quanti == 1
               else ('{nome} ha {quanti} pacchetti nel registro: cancellare la scheda '
                     "perderebbe quella storia. L'ho archiviata — il nome resta "
                     'riconosciuto nel calendario, ma non si aprono più pacchetti nuovi.'),
               'ok', nome=riga['nome'], quanti=quanti)
        return redirect(url_for('crediti_clienti'))
    db.crediti_cliente_elimina(con, chiave)
    con.close()
    sess.ricarica()
    avvisa('{nome} non è più fra i clienti a crediti.', 'ok', nome=riga['nome'])
    return redirect(url_for('crediti_clienti'))


# La finestra da cui si vanno a cercare gli orari mancanti. Un anno indietro
# copre tutto lo storico e non fa scaricare mezzo calendario a ogni click.
MESI_ORARI = 14


def _url_calendari():
    con = get_con()
    s = db.get_settings(con)
    con.close()
    return [s.get('calendario_ics', ''), s.get('calendario_storico_ics', '')]


def _leggi_banca(con, automatico=True):
    """Legge la cartella degli estratti e, se acceso, collega le certezze.

    Ritorna (movimenti, problemi, collegati_da_solo). Non solleva mai: se i file
    sono illeggibili si continua con quello che c'e'.
    """
    try:
        movimenti, problemi = banca.leggi_cartella()
    except Exception as e:                                   # pragma: no cover
        err_logger.error('Lettura estratti fallita: %s', e)
        return [], [f'{type(e).__name__}: {e}'], []
    if movimenti:
        db.set_setting(con, 'banca_ultimo_estratto', max(m['data'] for m in movimenti))
        db.set_setting(con, 'banca_letto_il',
                       datetime.datetime.now().isoformat(timespec='seconds'))
    fatti = []
    if automatico and db.get_settings(con).get('banca_auto') == '1':
        try:
            fatti = banca.collega_automatico(con, movimenti)
        except Exception as e:                               # pragma: no cover
            err_logger.error('Collegamento automatico fallito: %s', e)
    return movimenti, problemi, fatti


@app.route('/banca')
def banca_pagina():
    """Gli accrediti dell'estratto conto, accostati alle fatture."""
    con = get_con()
    movimenti, problemi, fatti = _leggi_banca(con)
    if fatti:
        quali = ' · '.join(f"#{x['numero']} {x['cliente'].split()[0]}" for x in fatti[:6])
        extra = (lng.t(' e altri {n}', _lingua_app()).format(n=len(fatti) - 6)
                 if len(fatti) > 6 else '')
        avvisa(("Ho collegato da solo {quanti} versamento, quello su cui non c'era "
                'niente da decidere: {quali}{extra}. Lo trovi qui sotto marcato '
                "«collegato dall'app»: se sbaglio, Annulla.") if len(fatti) == 1
               else ("Ho collegato da solo {quanti} versamenti, quelli su cui non c'era "
                     'niente da decidere: {quali}{extra}. Li trovi qui sotto marcati '
                     "«collegato dall'app»: se sbaglio, Annulla."),
               'ok', quanti=len(fatti), quali=quali, extra=extra)
    prop = banca.proposte(con, movimenti)
    con.close()
    da_decidere = [p for p in prop if not p['deciso']]
    return render_template('banca.html', prop=prop, problemi=problemi,
                           cartella=banca.CARTELLA,
                           da_decidere=da_decidere,
                           decisi=[p for p in prop if p['deciso']],
                           chiare=sum(1 for p in da_decidere if p['chiaro']))


@app.route('/banca/collega', methods=['POST'])
def banca_collega():
    """Conferma: questo versamento è quella fattura. Solo su tua richiesta."""
    impronta = request.form.get('impronta', '')
    inv_id = request.form.get('invoice_id', type=int)
    azione = request.form.get('azione', 'collega')
    con = get_con()
    m = next((x for x in banca.leggi_cartella()[0] if x['impronta'] == impronta), None)
    if m is None:
        avvisa('Quel versamento non è più nei file della cartella.', 'error')
        con.close()
        return redirect(url_for('banca_pagina'))

    adesso = datetime.datetime.now().isoformat(timespec='seconds')
    if azione == 'ignora':
        con.execute('INSERT OR REPLACE INTO movimenti(impronta, data, importo_cents, '
                    'descrizione, file, invoice_id, stato, stato_prima, deciso_il) '
                    'VALUES(?,?,?,?,?,NULL,?,"",?)',
                    (impronta, m['data'], m['importo_cents'], m['descrizione'],
                     m['file'], 'ignorato', adesso))
        con.commit()
        avvisa('Versamento messo da parte: non è una fattura.', 'ok')
    elif azione == 'annulla':
        r = con.execute('SELECT invoice_id, invoice_ids, stato_prima FROM movimenti '
                        'WHERE impronta=?', (impronta,)).fetchone()
        if r:
            ids = [int(x) for x in (r['invoice_ids'] or '').split(',') if x.isdigit()] \
                or ([r['invoice_id']] if r['invoice_id'] else [])
            prima = (r['stato_prima'] or '').split(',')
            # annullare deve annullare davvero: ogni fattura torna com'era prima
            # del collegamento, data e stato compresi
            for n_, i in enumerate(ids):
                con.execute('UPDATE invoices SET paid_at=NULL, status=? WHERE id=?',
                            (prima[n_] if n_ < len(prima) and prima[n_] else 'emessa', i))
        con.execute('DELETE FROM movimenti WHERE impronta=?', (impronta,))
        con.commit()
        avvisa('Collegamento annullato. Il versamento torna fra quelli da decidere.', 'ok')
    else:
        # un bonifico puo' pagare piu' fatture insieme
        ids = [int(x) for x in (request.form.get('invoice_ids') or '').split(',')
               if x.strip().isdigit()] or ([inv_id] if inv_id else [])
        fatture = [con.execute('SELECT * FROM invoices WHERE id=?', (i,)).fetchone()
                   for i in ids]
        fatture = [f for f in fatture if f is not None]

        # collegamento a mano: si indicano i NUMERI di fattura, anche più di uno.
        # Serve per i casi che l'app non può proporre da sola — un pagamento
        # arrivato mesi dopo, o di un importo che non combacia.
        numeri = re.findall(r'\d+', request.form.get('numeri') or '')
        if numeri and not fatture:
            for n_ in numeri:
                trovate = con.execute(
                    'SELECT * FROM invoices WHERE number=? AND deleted_at IS NULL',
                    (int(n_),)).fetchall()
                if len(trovate) > 1:
                    # numero usato due volte (succede: #58 sta su due fatture).
                    # Si scioglie col nome di chi ha versato, che è nella causale.
                    suoi = [t for t in trovate
                            if banca.somiglianza_nome(m['descrizione'], t['client_name']) >= 0.5]
                    if len(suoi) != 1:
                        elenco = ' · '.join(
                            f"{t['client_name']} del {t['date']} ({t['total_cents'] / 100:.2f})"
                            for t in trovate)
                        avvisa('Il numero {n} è su più di una fattura e dalla causale '
                               'non capisco quale: {elenco}. Rinumerane una e riprova.',
                               'error', n=n_, elenco=elenco)
                        con.close()
                        return redirect(url_for('banca_pagina'))
                    trovate = suoi
                if not trovate:
                    avvisa('La fattura numero {n} non esiste.', 'error', n=n_)
                    con.close()
                    return redirect(url_for('banca_pagina'))
                fatture.append(trovate[0])

        if not fatture:
            avvisa('Fattura non trovata.', 'error')
            con.close()
            return redirect(url_for('banca_pagina'))

        totale = sum(f['total_cents'] for f in fatture)
        if totale != m['importo_cents'] and not request.form.get('accetta_differenza'):
            differenza = (m['importo_cents'] - totale) / 100
            quali = ', '.join(f"#{f['number']}" for f in fatture)
            avvisa('Attenzione: {quali} fa {somma} ma il versamento è di {importo} '
                   '({differenza}). Non ho collegato niente. Se è giusto lo stesso, '
                   'rimetti i numeri e spunta la casella.', 'error',
                   quali=quali, somma=f'{totale / 100:.2f}',
                   importo=f"{m['importo_cents'] / 100:.2f}",
                   differenza=f'{differenza:+.2f}')
            con.close()
            return redirect(url_for('banca_pagina'))
        for f in fatture:
            con.execute('UPDATE invoices SET paid_at=?, status=? WHERE id=?',
                        (m['data'], 'pagata', f['id']))
        con.execute('INSERT OR REPLACE INTO movimenti(impronta, data, importo_cents, '
                    'descrizione, file, invoice_id, invoice_ids, stato, stato_prima, '
                    'deciso_il) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (impronta, m['data'], m['importo_cents'], m['descrizione'],
                     m['file'], fatture[0]['id'],
                     ','.join(str(f['id']) for f in fatture), 'collegato',
                     ','.join(f['status'] for f in fatture), adesso))
        con.commit()
        quali = ', '.join(f"#{f['number']}" for f in fatture)
        quando = datetime.date.fromisoformat(m['data']).strftime('%d.%m.%Y')
        avvisa('Fattura {quali} segnata pagata il {data}.' if len(fatture) == 1
               else 'Fatture {quali} segnate pagate il {data}.', 'ok',
               quali=quali, data=quando)
    con.close()
    return redirect(url_for('banca_pagina'))


@app.route('/email')
def email_inviate():
    """Il diario di tutto quello che l'app ha spedito."""
    con = get_con()
    solo = request.args.get('solo', '')
    sql = 'SELECT * FROM email_log'
    dove = []
    if solo == 'clienti':
        dove.append('prova=0')
    elif solo == 'prove':
        dove.append('prova=1')
    elif solo == 'errori':
        dove.append("esito='errore'")
    if dove:
        sql += ' WHERE ' + ' AND '.join(dove)
    sql += ' ORDER BY sent_at DESC, id DESC LIMIT 300'
    righe = con.execute(sql).fetchall()
    conteggi = {
        'tutte': con.execute('SELECT COUNT(*) c FROM email_log').fetchone()['c'],
        'clienti': con.execute('SELECT COUNT(*) c FROM email_log WHERE prova=0').fetchone()['c'],
        'prove': con.execute('SELECT COUNT(*) c FROM email_log WHERE prova=1').fetchone()['c'],
        'errori': con.execute("SELECT COUNT(*) c FROM email_log WHERE esito='errore'")
                     .fetchone()['c'],
    }
    con.close()
    return render_template('email_inviate.html', righe=righe, solo=solo, conteggi=conteggi)


@app.route('/email/<int:log_id>')
def email_letta(log_id):
    """La mail com'era: si rilegge senza aprire nient'altro."""
    con = get_con()
    e = con.execute('SELECT * FROM email_log WHERE id=?', (log_id,)).fetchone()
    if e is None:
        con.close()
        abort(404)
    inv = None
    if e['invoice_id']:
        inv = con.execute('SELECT * FROM invoices WHERE id=?', (e['invoice_id'],)).fetchone()
    con.close()
    return render_template('email_letta.html', e=e, inv=inv)


@app.route('/agenda')
def agenda():
    reg = sess.carica()
    cliente = request.args.get('cliente', '').strip()
    anno = request.args.get('anno', '').strip()
    righe = ag.elenco(reg, cliente=cliente or None, anno=anno or None)
    clienti = sorted({p['cliente'] for p in reg.get('pacchetti', []) if p.get('cliente')})
    return render_template('agenda.html', righe=righe, r=ag.riepilogo(righe),
                           clienti=clienti, anni=ag.anni(reg),
                           cliente=cliente, anno=anno,
                           senza_ora=sum(1 for x in righe if not x['ora']))


@app.route('/agenda/orari', methods=['POST'])
def agenda_orari():
    """Riempie gli orari mancanti leggendo i calendari configurati."""
    oggi = datetime.date.today()
    da = oggi - datetime.timedelta(days=31 * MESI_ORARI)
    principale, storico = _url_calendari()
    nuovi, errori, nomi = ag.aggiorna_da_calendario([principale, storico], da, oggi)
    con = get_con()
    for url, chiave in ((principale, 'calendario_nome'), (storico, 'calendario_storico_nome')):
        if nomi.get(url):
            db.set_setting(con, chiave, nomi[url])
    con.close()
    if errori:
        for e in errori:
            err_logger.error('Lettura orari fallita: %s', e)
        avvisa('Un calendario non ha risposto: {guaio}', 'error',
               guaio=' · '.join(errori))
    if nuovi:
        avvisa('Orari trovati: {quanti}.', 'ok', quanti=nuovi)
    elif not errori:
        avvisa('Nessun orario nuovo: il calendario non sa altro di quei giorni.', 'ok')
    return redirect(url_for('agenda', **request.args.to_dict()))


@app.route('/crediti/pacchetto/<pid>')
def crediti_pacchetto(pid):
    reg = sess.carica()
    p = next((q for q in reg['pacchetti'] if q['id'] == pid), None)
    if not p:
        abort(404)
    stato = None
    if p.get('fattura_numero'):
        con = get_con()
        row = con.execute('SELECT status FROM invoices WHERE number=? AND deleted_at IS NULL',
                          (p['fattura_numero'],)).fetchone()
        con.close()
        stato = row['status'] if row else None
    return render_template('pacchetto.html', p=p, fattura_stato=stato)


@app.route('/crediti/collega', methods=['POST'])
def crediti_collega():
    """Marca le sessioni del pacchetto col numero fattura e lo chiude (6.3)."""
    pid = request.form.get('pacchetto', '')
    numero = request.form.get('numero', type=int)
    if not numero:
        avvisa('Indica il numero della fattura.', 'error')
        return redirect(url_for('crediti'))
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE number=? AND deleted_at IS NULL',
                      (numero,)).fetchone()
    con.close()
    if not inv:
        avvisa('Non esiste una fattura #{n}.', 'error', n=numero)
        return redirect(url_for('crediti'))
    reg = sess.carica()
    try:
        p, _ = sess.collega_fattura(reg, pid, numero)
    except KeyError:
        avvisa('Pacchetto inesistente.', 'error')
        return redirect(url_for('crediti'))
    sess.salva(reg)
    avvisa('Pacchetto {pid} collegato alla fattura #{n} ({cliente}): {quante} sessioni '
           'marcate. Il prossimo pacchetto si apre da solo alla prima sessione nuova.',
           'ok', pid=pid, n=numero, cliente=inv['client_name'],
           quante=len(p.get('sessioni', [])))
    return redirect(url_for('crediti'))


# ---------------------------------------------------------------- controlli / impostazioni
@app.route('/controlli')
def controlli():
    con = get_con()
    issues = stats.health(con)
    archived = corrections.acknowledged_list(con)
    corr = corrections.corrections_map(con)
    # le reti di sicurezza: stavano in Dashboard, ma non sono cose da guardare
    # ogni mattina — sono cose da controllare quando si controlla
    salute = cruscotto.salute(con, db.get_settings(con), _cartella_backup(),
                              _lingua_app())
    con.close()
    return render_template('controlli.html', issues=issues, archived=archived,
                           corr=corr, n_corr=len(corr), salute=salute)


@app.route('/controlli/correggi', methods=['POST'])
def controlli_correggi():
    """Salva importo/data inseriti a mano. La correzione sopravvive al Reimporta."""
    inv_id = request.form.get('inv_id', type=int)
    con = get_con()
    inv = con.execute('SELECT * FROM invoices WHERE id=?', (inv_id,)).fetchone()
    if not inv:
        con.close()
        avvisa('Fattura non trovata.', 'error')
        return redirect(url_for('controlli'))

    importo_raw = (request.form.get('importo') or '').strip()
    data_raw = (request.form.get('data') or '').strip()
    total_cents = None
    if importo_raw:
        total_cents = parse_amount(importo_raw)
        if total_cents is None:
            con.close()
            avvisa('Importo «{cosa}» non riconosciuto. Scrivilo come 1’800.- oppure '
                   '1800.00 e riprova.', 'error', cosa=importo_raw)
            return redirect(url_for('controlli'))
    date_iso = None
    if data_raw:
        try:
            date_iso = datetime.date.fromisoformat(data_raw).isoformat()
        except ValueError:
            con.close()
            avvisa('Data non valida.', 'error')
            return redirect(url_for('controlli'))

    if total_cents is None and date_iso is None:
        con.close()
        avvisa('Non hai inserito nulla da correggere.', 'error')
        return redirect(url_for('controlli'))

    corrections.save_correction(con, inv, total_cents, date_iso,
                                note=(request.form.get('nota') or '').strip())
    con.close()
    parts = []
    if total_cents is not None:
        parts.append(f'importo {fmt_chf(total_cents)}')
    if date_iso:
        parts.append(f'data {fmt_date_it(date_iso)}')
    avvisa('Corretta la fattura #{n} ({cliente}): {cosa}. La correzione resta anche '
           'dopo un Reimporta.', 'ok', n=inv['number'] or '—',
           cliente=inv['client_name'], cosa=', '.join(parts))
    return redirect(url_for('controlli'))


@app.route('/controlli/annulla-correzione', methods=['POST'])
def controlli_annulla_correzione():
    key = request.form.get('key', '')
    con = get_con()
    corrections.remove_correction(con, key)
    # rileggo lo storico per riportare il dato com'era nel file di origine
    settings = db.get_settings(con)
    if os.path.isdir(settings['source_folder']):
        importer.import_all(con, settings['source_folder'])
    con.close()
    avvisa('Correzione annullata: il dato è tornato come nel file di origine.', 'ok')
    return redirect(url_for('controlli'))


@app.route('/controlli/archivia', methods=['POST'])
def controlli_archivia():
    """'Lo so, va bene così': l'anomalia storica smette di comparire."""
    con = get_con()
    corrections.acknowledge(con, request.form.get('key', ''),
                            request.form.get('kind', ''),
                            request.form.get('msg', ''),
                            (request.form.get('nota') or '').strip())
    con.close()
    avvisa('Anomalia archiviata. La trovi in fondo alla pagina se ti serve rivederla.', 'ok')
    return redirect(url_for('controlli'))


@app.route('/controlli/ripristina', methods=['POST'])
def controlli_ripristina():
    con = get_con()
    corrections.unacknowledge(con, request.form.get('key', ''))
    con.close()
    avvisa('Anomalia ripristinata: torna nell\'elenco dei controlli.', 'ok')
    return redirect(url_for('controlli'))


@app.route('/verifica')
def verifica():
    con = get_con()
    all_ok, results = selftest.run_all()
    # raggruppa i test per categoria
    by_cat = {}
    for cat, desc, ok, detail in results:
        by_cat.setdefault(cat, []).append((desc, ok, detail))
    n_total = len(results)
    n_ok = sum(1 for x in results if x[2])
    # l'autotest costa un quarto di secondo: si esegue qui e il risultato resta
    # scritto, cosi' la Dashboard lo mostra senza rifarlo a ogni apertura
    db.set_setting(con, 'autotest_esito', f'{n_ok}/{n_total}')
    db.set_setting(con, 'autotest_quando', datetime.datetime.now().isoformat(timespec='seconds'))
    rec = verify.reconcile_all(con)
    con.close()
    # test della logica crediti contro lo storico congelato (SPEC-crediti.md sez. 7)
    try:
        from core import selftest_crediti
        cred_ok, cred_res = selftest_crediti.run_all()
        for cat, desc, ok, detail in cred_res:
            by_cat.setdefault('Crediti — ' + cat, []).append((desc, ok, detail))
        n_total += len(cred_res)
        n_ok += sum(1 for x in cred_res if x[2])
        all_ok = all_ok and cred_ok
    except Exception as e:
        by_cat.setdefault('Crediti', []).append((f'test non eseguiti: {e}', False, str(e)))
        all_ok = False
    return render_template('verifica.html', all_ok=all_ok, by_cat=by_cat,
                           n_total=n_total, n_ok=n_ok, rec=rec)


@app.route('/reimporta', methods=['POST'])
def reimporta():
    con = get_con()
    backup.make_backup('prima-reimport')
    settings = db.get_settings(con)
    msgs = importer.import_all(con, settings['source_folder'])
    con.close()
    avvisa('Reimport completato: {dettaglio}', 'ok', dettaglio=' • '.join(msgs))
    return redirect(url_for('controlli'))


def _cartella_backup():
    """Dove va la copia esterna. Impostabile; se manca, iCloud.

    INVOICE_BACKUP passa davanti a tutto, anche all'impostazione salvata:
    un'app di prova parte spesso da una copia del database vero, e senza
    questo si metterebbe a scrivere le sue copie in mezzo a quelle buone."""
    if db.env('INVOICE_BACKUP', 'FATTURE_BACKUP'):
        return db.env('INVOICE_BACKUP', 'FATTURE_BACKUP')
    try:
        con = get_con()
        d = db.get_settings(con).get('backup_dir') or backup.DEST_DEFAULT
        con.close()
        return d
    except Exception:
        return backup.DEST_DEFAULT


@app.route('/impostazioni', methods=['GET', 'POST'])
def impostazioni():
    con = get_con()
    if request.method == 'POST':
        # una casella non spuntata non compare nel modulo: va spenta a mano
        if 'email_oggetto_coaching' in request.form:   # siamo nel riquadro della posta
            db.set_setting(con, 'email_copia_a_me',
                           '1' if request.form.get('email_copia_a_me') else '0')
        if 'banca_marcatore' in request.form:    # riquadro della banca
            db.set_setting(con, 'banca_auto',
                           '1' if request.form.get('banca_auto') else '0')
        for k in db.DEFAULT_SETTINGS:
            if k not in request.form:
                continue
            valore = request.form[k]
            if k == 'smtp_pass':
                # il campo arriva vuoto quando non lo si tocca: non cancellare
                # la password gia' salvata
                if not valore.strip():
                    continue
                # spazi e a capo incollati per sbaglio: il server li conta e
                # rifiuta la password
                valore = valore.strip()
                # password nuova: si riparte da zero, pausa compresa
                db.set_setting(con, 'smtp_fallimenti', '0')
                db.set_setting(con, 'smtp_pausa_fino', '')
            elif k in db.TESTI_INTOCCABILI:
                # il testo va tenuto com'e': negli a capo in fondo a un saluto
                # c'e' lo spazio prima della firma, e toglierli lo rovina
                valore = valore.replace('\r\n', '\n')
            else:
                valore = valore.strip()
            db.set_setting(con, k, valore)
        avvisa('Impostazioni salvate.', 'ok')
        con.close()
        return redirect(url_for('impostazioni'))
    settings = db.get_settings(con)
    con.close()
    dest = settings.get('backup_dir') or backup.DEST_DEFAULT
    return render_template('impostazioni.html', settings=settings,
                           cartella_estratti=os.path.basename(db.DIR_ESTRATTI),
                           copie=backup.elenco_esterni(dest)[:10],
                           ultimo=backup.ultimo_esterno(dest),
                           pausa=_pausa_smtp(settings),
                           logo_suo=marchio.personalizzato())


@app.route('/impostazioni/logo', methods=['POST'])
def impostazioni_logo():
    file = request.files.get('logo')
    errore = marchio.salva(file.read() if file else b'')
    if errore:
        avvisa(errore[0], 'error', **errore[1])
    else:
        avvisa('Logo aggiornato. Lo trovi sulle prossime fatture, in PDF e in Word.', 'ok')
    return redirect(url_for('impostazioni'))


@app.route('/impostazioni/logo/rimuovi', methods=['POST'])
def impostazioni_logo_rimuovi():
    if marchio.rimuovi():
        avvisa('Logo rimosso: al suo posto torna il segnaposto.', 'ok')
    else:
        avvisa('Non c\'era nessun logo da rimuovere.', 'error')
    return redirect(url_for('impostazioni'))


@app.route('/impostazioni/backup-ora', methods=['POST'])
def backup_ora():
    dest = _cartella_backup()
    esito = backup.archivia_fuori(dest, motivo='a-richiesta')
    if esito['ok']:
        avvisa('Copia creata e verificata: {file} ({kb} KB). Il database dentro '
               "l'archivio è integro.", 'ok',
               file=os.path.basename(esito['path']), kb=esito['bytes'] // 1024)
    else:
        avvisa('Copia NON riuscita: {guaio}', 'error', guaio=esito['errore'])
    con = get_con()
    sorgente = db.get_settings(con)['source_folder']
    con.close()
    st = backup.archivia_storico(sorgente, dest)
    if st['ok'] and st['saltato']:
        avvisa("Storico ({quanti} documenti): invariato dall'ultima copia, non ne "
               'serviva una nuova.', 'ok', quanti=st['file'])
    elif st['ok']:
        avvisa('Storico copiato: {file} — {quanti} documenti.', 'ok',
               file=os.path.basename(st['path']), quanti=st['file'])
    else:
        avvisa('Copia dello storico NON riuscita: {guaio}', 'error', guaio=st['errore'])
    return redirect(url_for('impostazioni'))


# ---------------------------------------------------------------- API
@app.route('/api/periodo-successivo')
def api_periodo_successivo():
    """La stessa riga dell'ultima volta, col periodo spostato avanti di un mese.

    Serve agli abbonamenti: il testo lo scrive chi usa l'app, noi tocchiamo
    solo le date. Se il servizio scelto non e' mai stato fatturato a questo
    cliente, o se l'ultima volta non aveva un periodo, non si propone niente."""
    client_id = request.args.get('client_id', type=int)
    scelto = request.args.get('servizio', '')
    con = get_con()
    client = con.execute('SELECT * FROM clients WHERE id=?', (client_id,)).fetchone()
    if not client:
        con.close()
        return jsonify({'found': False})
    righe = con.execute(
        'SELECT i.description d, i.unit_cents u, i.total_cents t '
        'FROM items i JOIN invoices f ON f.id = i.invoice_id '
        'WHERE f.deleted_at IS NULL AND f.client_name LIKE ? '
        'ORDER BY COALESCE(f.number, 0) DESC LIMIT 40',
        (client['name'].split()[0] + '%',)).fetchall()
    con.close()
    riga = next((r for r in righe if srv.stesso_servizio(scelto, r['d'])), None)
    if riga is None:
        return jsonify({'found': False})
    avanzata = srv.avanza_periodo(riga['d'])
    return jsonify({
        'found': True,
        'description': avanzata or riga['d'],
        'advanced': bool(avanzata),
        'previous': riga['d'],
        'unit': fmt_dash(riga['u']) if riga['u'] is not None else '',
        'total': fmt_dash(riga['t']) if riga['t'] is not None else ''})


@app.route('/api/client/<int:cid>')
def api_client(cid):
    con = get_con()
    c = con.execute('SELECT * FROM clients WHERE id=?', (cid,)).fetchone()
    con.close()
    if not c:
        return jsonify({})
    return jsonify({'name': c['name'], 'address1': c['address1'], 'address2': c['address2'],
                    'intestatario': (c['intestatario'] or '').strip()})


@app.route('/apri-cartella', methods=['POST'])
def apri_cartella():
    target = request.form.get('path', INVOICE_DIR)
    if os.path.isdir(target):
        subprocess.Popen(['open', target])
    elif os.path.isfile(target):
        subprocess.Popen(['open', '-R', target])
    return redirect(request.referrer or url_for('dashboard'))


# Il segnale «da quando sta girando questa copia».
# Serve a chi la avvia: i modelli delle pagine restano in memoria, quindi dopo
# un aggiornamento del programma quella accesa e' ancora la versione vecchia e
# non si vedrebbe niente di nuovo. Confrontando questo file con la data dei
# file del programma, l'avviatore capisce da solo se deve ripartire.
# Il nome porta la porta dentro: una copia di prova su un'altra porta scrive il
# suo file e non fa credere all'avviatore che l'app vera sia gia' aggiornata.
def _segnale_avvio(porta):
    return os.path.join(APP_DIR, 'data', '.started-%s' % porta)


def _segna_avvio(porta):
    try:
        with open(_segnale_avvio(porta), 'w') as f:
            f.write(datetime.datetime.now().isoformat(timespec='seconds'))
    except OSError:                                     # pragma: no cover
        pass


def _avvia(porta):
    """Accende il server lasciando pulita la finestra del Terminale.

    Avviato per la via breve di Flask, il server si presenta con tre righe fra
    cui un WARNING rosso sul «development server», e poi ne stampa una per ogni
    pagina aperta. Sono vere ma non riguardano chi usa l'app: qui gira su
    127.0.0.1, un indirizzo che esiste solo dentro questo Mac, per una persona
    sola. Chi accende l'app vedrebbe scorrere righe d'allarme senza avere modo
    di capire che vanno bene cosi'.

    Gli errori veri non si perdono: la pagina li mostra e finiscono comunque in
    data/error.log. Del server restano visibili gli avvisi veri, non il
    resoconto di ogni click.
    """
    from werkzeug.serving import make_server
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    # threaded come fa Flask da sola: senza, una pagina lenta blocca le altre
    server = make_server('127.0.0.1', porta, app, threaded=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:                           # pragma: no cover
        pass


if __name__ == '__main__':
    PORTA = int(db.env('INVOICE_PORT', 'FATTURE_PORT') or 8471)
    # prima di ogni altra cosa: se le cartelle hanno ancora i nomi vecchi le
    # rinomina. Dopo il makedirs qui sotto sarebbe troppo tardi — la cartella
    # nuova esisterebbe gia' vuota e i documenti resterebbero nella vecchia.
    for _prima, _dopo in db.migra_cartelle():
        print('  Cartella «%s» rinominata «%s».' % (_prima, _dopo))
    os.makedirs(INVOICE_DIR, exist_ok=True)
    _segna_avvio(PORTA)
    con = db.init()
    backup.make_backup('avvio')
    # copia completa fuori dal Mac, una volta al giorno
    _dest = db.get_settings(con).get('backup_dir') or backup.DEST_DEFAULT
    if backup.serve_backup_oggi(_dest):
        _e = backup.archivia_fuori(_dest, motivo='avvio')
        print('  Backup esterno: ' + (os.path.basename(_e['path']) if _e['ok']
                                      else 'NON riuscito — ' + _e['errore']))
        # lo storico (129 documenti) si copia solo se e' cambiato
        _s = backup.archivia_storico(db.get_settings(con)['source_folder'], _dest)
        if _s['saltato']:
            print('  Storico: invariato, nessuna copia nuova')
        else:
            print('  Storico: ' + (os.path.basename(_s['path']) if _s['ok']
                                   else 'NON riuscito — ' + _s['errore']))
    # estratti conto: legge la cartella e collega da solo le certezze, cosi' la
    # Dashboard e' gia' aggiornata quando apri l'app
    _mov, _prob, _fatti = _leggi_banca(con)
    if _fatti:
        print('  Banca: %d versamenti collegati da solo (%s)'
              % (len(_fatti), ', '.join('#%s' % x['numero'] for x in _fatti[:8])))
    elif _mov:
        print('  Banca: %d accrediti letti, niente di nuovo da collegare' % len(_mov))
    for _dove, _guaio in _prob:
        print('  Banca: %s: %s' % (_dove, _guaio))
    # primo avvio: se il DB e' vuoto, importa lo storico automaticamente
    n = con.execute('SELECT COUNT(*) c FROM invoices').fetchone()['c']
    if n == 0:
        s = db.get_settings(con)
        if os.path.isdir(s['source_folder']):
            importer.import_all(con, s['source_folder'])
    con.close()
    # la porta si puo' cambiare con INVOICE_PORT: serve per far girare una
    # copia di prova (per esempio un ripristino da backup) accanto all'app vera
    _avvia(PORTA)
