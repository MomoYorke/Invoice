# -*- coding: utf-8 -*-
"""
Statistiche finanziarie. Regola d'oro:
- 2022 e 2023: fanno fede gli Excel storici (legacy_year_totals),
  perche' le fatture .docx di quegli anni sono incomplete.
- dal 2024 in poi: fanno fede le fatture nel database.
Tutti i calcoli in centesimi interi.
"""
import datetime
import re

from . import servizi

LEGACY_YEARS = (2022, 2023)


def revenue_by_year(con):
    """dict year -> {'invoiced': cents, 'paid': cents, 'count': n, 'legacy': bool}"""
    out = {}
    for r in con.execute('SELECT year, SUM(invoiced_cents) i, SUM(paid_cents) p, COUNT(*) n '
                         'FROM legacy_year_totals GROUP BY year'):
        out[r['year']] = {'invoiced': r['i'] or 0, 'paid': r['p'] or 0,
                          'count': None, 'legacy': True}
    for r in con.execute('SELECT year, SUM(total_cents) t, COUNT(*) n, '
                         "SUM(CASE WHEN status='pagata' THEN COALESCE(total_cents,0) ELSE 0 END) p "
                         'FROM invoices WHERE deleted_at IS NULL GROUP BY year'):
        if r['year'] in LEGACY_YEARS:
            if r['year'] in out:
                out[r['year']]['count'] = r['n']
            continue
        out[r['year']] = {'invoiced': r['t'] or 0, 'paid': r['p'] or 0,
                          'count': r['n'], 'legacy': False}
    return dict(sorted(out.items()))


def monthly(con, year):
    """Lista di 12 importi (cents) per l'anno dato (solo fatture con data)."""
    months = [0] * 12
    for r in con.execute("SELECT strftime('%m', date) m, SUM(total_cents) t FROM invoices "
                         "WHERE year=? AND date IS NOT NULL AND deleted_at IS NULL GROUP BY m", (year,)):
        if r['m']:
            months[int(r['m']) - 1] = r['t'] or 0
    return months


def by_client(con, year=None):
    """[(nome, invoiced_cents, n_fatture)] ordinato per fatturato."""
    if year in LEGACY_YEARS:
        rows = con.execute('SELECT client name, invoiced_cents t, NULL n FROM legacy_year_totals '
                           'WHERE year=? ORDER BY invoiced_cents DESC', (year,)).fetchall()
        return [(r['name'], r['t'] or 0, r['n']) for r in rows]
    q = ('SELECT client_name name, SUM(COALESCE(total_cents,0)) t, COUNT(*) n FROM invoices '
         + ('WHERE deleted_at IS NULL AND year=? ' if year else 'WHERE deleted_at IS NULL ')
         + 'GROUP BY client_name ORDER BY t DESC')
    rows = con.execute(q, (year,) if year else ()).fetchall()
    return [(r['name'], r['t'], r['n']) for r in rows]


# Righe che NON sono un servizio venduto:
# - sconti: sul documento hanno importo positivo ma vanno SOTTRATTI
#   (es. 2'050 - 50 = 2'000). Non fanno voce a se': lo sconto si
#   scala dal servizio a cui e' stato applicato, sulla stessa fattura.
# - omaggi: sessioni regalate, valgono 0
SCONTI = re.compile(r'discount|sconto|riduzione|rabatt', re.I)
OMAGGI = re.compile(r'gift|bring a friend|referral|free|omaggio|gratis', re.I)
NON_DETTAGLIATO = 'Non dettagliato'


def regole_servizi(con):
    """Le regole di riconoscimento, come le ha scritte chi usa l'app.

    Stavano nel programma: erano i servizi di una persona sola. Ora sono due
    righe di impostazioni, e chi fa un altro mestiere ci mette il suo."""
    fuori = {}
    for k in ('servizi_abbonamento', 'servizi_pacchetto'):
        r = con.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone()
        fuori[k] = (r[0] if r else '') or ''
    return fuori


def _etichetta(desc, regole):
    nome, _modello = servizi.riconosci(desc, regole)
    return nome or 'Altro'


def _servizio_dedotto(con, inv_id, client_name, cents, regole):
    """Servizio di una fattura senza righe di dettaglio.

    Deduce SOLO quando non c'e' margine di errore: tutte le altre fatture
    dello stesso cliente con lo stesso importo esatto devono avere righe
    che portano a un unico servizio. Altrimenti resta 'Non dettagliato'.
    """
    if not cents:
        return NON_DETTAGLIATO
    trovati = set()
    for r in con.execute(
            'SELECT i.description d FROM items i JOIN invoices f ON f.id = i.invoice_id '
            'WHERE f.client_name = ? AND f.total_cents = ? AND f.id != ? '
            'AND f.deleted_at IS NULL', (client_name, cents, inv_id)):
        d = r['d'] or ''
        if SCONTI.search(d) or OMAGGI.search(d):
            continue
        trovati.add(_etichetta(d, regole))
    if len(trovati) == 1:
        etichetta = trovati.pop()
        if etichetta != 'Altro':
            return etichetta
    return NON_DETTAGLIATO


def by_service(con, year):
    """Fatturato dell'anno per tipo di servizio.

    La somma delle voci coincide col fatturato dell'anno:
    - gli sconti si sottraggono dal servizio della stessa fattura
      (niente voce "Sconti" a se' stante);
    - le fatture senza righe di dettaglio vengono ricondotte al loro
      servizio quando e' deducibile senza ambiguita', altrimenti
      finiscono in 'Non dettagliato'.
    """
    regole = regole_servizi(con)
    buckets = {}

    def aggiungi(label, cents):
        buckets[label] = buckets.get(label, 0) + cents

    righe = {}   # invoice_id -> [(etichetta|None se sconto, cents)]
    for r in con.execute(
            'SELECT i.description d, COALESCE(i.total_cents, 0) t, i.invoice_id FROM items i '
            'JOIN invoices f ON f.id = i.invoice_id '
            'WHERE f.year=? AND f.deleted_at IS NULL', (year,)):
        righe.setdefault(r['invoice_id'], []).append((r['d'] or '', r['t'] or 0))

    for inv_id, lines in righe.items():
        locali = {}
        sconto = 0
        for desc, val in lines:
            if SCONTI.search(desc):
                sconto += abs(val)
                continue
            if OMAGGI.search(desc):
                locali['Omaggi'] = locali.get('Omaggi', 0) + val
                continue
            e = _etichetta(desc, regole)
            locali[e] = locali.get(e, 0) + val
        if sconto:
            # lo sconto si scala dal servizio piu' consistente della fattura
            if locali:
                principale = max(locali.items(), key=lambda kv: kv[1])[0]
            else:
                principale = NON_DETTAGLIATO
            locali[principale] = locali.get(principale, 0) - sconto
        for k, v in locali.items():
            aggiungi(k, v)

    # fatture senza righe (importate da PDF, o corrette a mano): non vanno perse
    for inv in con.execute('SELECT id, client_name, COALESCE(total_cents,0) t FROM invoices '
                           'WHERE year=? AND deleted_at IS NULL', (year,)):
        if inv['id'] not in righe and inv['t']:
            aggiungi(_servizio_dedotto(con, inv['id'], inv['client_name'], inv['t'], regole),
                     inv['t'])

    return sorted((kv for kv in buckets.items() if kv[1] != 0), key=lambda kv: -kv[1])


def kpis(con, year=None):
    today = datetime.date.today()
    year = year or today.year
    is_current = (year == today.year)
    cutoff = today.isoformat() if is_current else f'{year}-12-31'
    if is_current:
        try:
            prev_cutoff = today.replace(year=year - 1).isoformat()
        except ValueError:  # 29 feb -> anno non bisestile
            prev_cutoff = today.replace(year=year - 1, day=28).isoformat()
    else:
        prev_cutoff = f'{year - 1}-12-31'

    def total_until(y, cut):
        if y in LEGACY_YEARS:
            r = con.execute('SELECT SUM(invoiced_cents) t FROM legacy_year_totals WHERE year=?',
                            (y,)).fetchone()
            return r['t'] or 0
        r = con.execute('SELECT SUM(total_cents) t FROM invoices WHERE year=? AND deleted_at IS NULL '
                        'AND (date IS NULL OR date <= ?)', (y, cut)).fetchone()
        return r['t'] or 0

    ytd = total_until(year, cutoff)
    prev_same = total_until(year - 1, prev_cutoff)
    growth = None
    if prev_same:
        growth = (ytd - prev_same) * 10000 // prev_same  # in centesimi di %
    r = con.execute('SELECT COUNT(*) n, AVG(total_cents) a, SUM(total_cents) s FROM invoices '
                    'WHERE year=? AND total_cents IS NOT NULL AND deleted_at IS NULL', (year,)).fetchone()
    count, avg = r['n'], int(r['a']) if r['a'] else None
    # incassato / da incassare (per l'anno)
    paid = con.execute("SELECT SUM(total_cents) t FROM invoices WHERE year=? AND status='pagata' AND deleted_at IS NULL",
                       (year,)).fetchone()['t'] or 0
    open_amt = con.execute("SELECT SUM(total_cents) t FROM invoices WHERE year=? AND status!='pagata' AND deleted_at IS NULL",
                           (year,)).fetchone()['t'] or 0
    # proiezione fine anno: media giornaliera YTD * 365 (solo anno corrente)
    projection = None
    if is_current and ytd:
        doy = today.timetuple().tm_yday
        projection = ytd * 365 // doy
    clients = by_client(con, year)
    top = clients[0] if clients else None
    return {
        'year': year, 'ytd': ytd, 'prev_same': prev_same, 'growth_bp': growth,
        'count': count, 'avg': avg, 'paid': paid, 'open': open_amt,
        'projection': projection, 'top_client': top,
    }


def health(con, include_acknowledged=False):
    """Controlli d'integrità. Ritorna una lista di dict:
       {kind, key, msg, fixable, inv_id, missing_amount, missing_date, ...}
    Le anomalie archiviate dall'utente sono escluse (salvo richiesta esplicita).
    'key' è stabile nel tempo: sopravvive al reimport."""
    from .corrections import invoice_key, acknowledged_keys
    issues = []

    # --- numeri duplicati ---
    for r in con.execute('SELECT number, GROUP_CONCAT(client_name, " / ") g, COUNT(*) n '
                         'FROM invoices WHERE number IS NOT NULL AND deleted_at IS NULL '
                         'GROUP BY number HAVING n > 1 ORDER BY number'):
        issues.append({
            'kind': 'duplicato', 'key': f"duplicato:{r['number']}",
            'msg': f"Numero #{r['number']} usato {r['n']} volte: {r['g']}",
            'fixable': False, 'inv_id': None})

    # --- buchi nella numerazione (uno per numero, così si archiviano singolarmente) ---
    nums = [r['number'] for r in con.execute(
        'SELECT DISTINCT number FROM invoices WHERE number IS NOT NULL ORDER BY number')]
    if nums:
        have = set(nums)
        for n in range(nums[0], nums[-1] + 1):
            if n not in have:
                issues.append({
                    'kind': 'buco', 'key': f'buco:{n}',
                    'msg': f"Il numero #{n} non esiste: nessuna fattura con questo numero",
                    'fixable': False, 'inv_id': None})

    # --- dati mancanti (importo e/o data) : UNA riga per fattura ---
    rows = con.execute(
        'SELECT * FROM invoices WHERE deleted_at IS NULL AND (total_cents IS NULL '
        'OR (date IS NULL AND year >= 2024)) ORDER BY year, number').fetchall()
    for inv in rows:
        miss_amount = inv['total_cents'] is None
        miss_date = inv['date'] is None and (inv['year'] or 0) >= 2024
        what = []
        if miss_amount:
            what.append("l'importo")
        if miss_date:
            what.append("la data")
        issues.append({
            'kind': 'dati', 'key': f'dati:{invoice_key(inv)}',
            'msg': (f"#{inv['number'] or '—'} {inv['client_name']} ({inv['year']}): "
                    f"manca {' e '.join(what)}"),
            'detail': inv['source_file'] or 'creata con l\'app',
            'fixable': True, 'inv_id': inv['id'],
            'missing_amount': miss_amount, 'missing_date': miss_date,
            'total_cents': inv['total_cents'], 'date': inv['date'],
            'client': inv['client_name'], 'number': inv['number']})

    if not include_acknowledged:
        done = acknowledged_keys(con)
        issues = [i for i in issues if i['key'] not in done]
    return issues
