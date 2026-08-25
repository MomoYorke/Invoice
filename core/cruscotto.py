# -*- coding: utf-8 -*-
"""
I tre riquadri della Dashboard che raccontano lo stato delle cose.

- stato_fatture(): quante sono, e soprattutto quante NON sono ancora partite.
- salute():        le reti di sicurezza che lavorano in silenzio. Vanno mostrate
                   proprio perche' funzionano da sole: il giorno che smettono,
                   senza un posto dove guardare non se ne accorge nessuno.
- attivita():      cos'e' successo da quando non guardavi, in un'unica colonna.
"""
import os
import datetime

from . import backup
from . import agenda

VERDE, GIALLO, ROSSO = 'ok', 'attenzione', 'guai'
GIORNI_BACKUP_VECCHIO = 3        # oltre, il riquadro diventa giallo
ORE_CALENDARIO_VECCHIO = 48


def _quando(iso):
    try:
        return datetime.datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def _eta(iso_o_data):
    """Da quanto tempo, in parole."""
    q = _quando(iso_o_data) if isinstance(iso_o_data, str) else iso_o_data
    if q is None:
        return None, None
    delta = datetime.datetime.now() - q
    ore = delta.total_seconds() / 3600
    if ore < 1:
        return q, 'pochi minuti fa'
    if ore < 24:
        n = int(ore)
        return q, "un'ora fa" if n == 1 else f'{n} ore fa'
    giorni = int(ore // 24)
    return q, 'ieri' if giorni == 1 else f'{giorni} giorni fa'


# ------------------------------------------------------------- stato fatture
def stato_fatture(con, anno):
    """Quattro numeri, ognuno con il filtro che porta all'elenco giusto."""
    def conta(dove, args=()):
        sql = 'SELECT COUNT(*) c FROM invoices WHERE deleted_at IS NULL AND year=?'
        return con.execute(sql + dove, (anno,) + tuple(args)).fetchone()['c']

    return {
        'totali': conta(''),
        'pagate': conta(" AND status='pagata'"),
        'da_incassare': conta(" AND status<>'pagata'"),
        'inviate': conta(' AND sent_at IS NOT NULL'),
        # solo quelle fatte con l'app: le storiche sono documenti Word vecchi,
        # non si spediscono da qui e contarle come "da mandare" sarebbe falso
        'da_mandare': conta(" AND sent_at IS NULL AND source='app'"),
    }


# Quanto tempo si concede a un cliente prima di considerare un incasso «in
# ritardo». I suoi pagano fra i 4 e i 47 giorni dalla fattura, quindi sotto i
# 45 giorni gridare al ritardo sarebbe solo rumore.
GIORNI_PAZIENZA = 45
GIORNI_ESTRATTO_VECCHIO = 40


def incassi_mancanti(con, ultimo_estratto):
    """Le fatture senza incasso, divise fra «non si può ancora sapere» e «manca».

    La distinzione e' tutto: una fattura di ieri non e' in ritardo, e' solo piu'
    recente dell'ultimo estratto scaricato. Senza questa separazione l'elenco
    dei ritardi sarebbe pieno di falsi allarmi e smetteresti di guardarlo.
    """
    righe = con.execute(
        'SELECT id, number, client_name, date, total_cents FROM invoices '
        'WHERE deleted_at IS NULL AND (paid_at IS NULL OR paid_at = "") '
        'AND date >= ? ORDER BY date', ('2025-01-01',)).fetchall()
    if not ultimo_estratto:
        return {'in_ritardo': [], 'da_verificare': [r for r in righe], 'limite': None}
    try:
        limite = (datetime.date.fromisoformat(ultimo_estratto)
                  - datetime.timedelta(days=GIORNI_PAZIENZA)).isoformat()
    except ValueError:
        return {'in_ritardo': [], 'da_verificare': list(righe), 'limite': None}
    ritardo = [r for r in righe if r['date'] <= limite]
    attesa = [r for r in righe if r['date'] > limite]
    return {'in_ritardo': ritardo, 'da_verificare': attesa, 'limite': limite}


# ------------------------------------------------------------------- salute
def salute(con, settings, cartella_backup=None):
    """Lo stato delle reti di sicurezza. Ogni voce dice anche se e' tranquilla."""
    voci = []
    peggio = VERDE

    def aggiungi(nome, valore, dettaglio, stato):
        nonlocal peggio
        voci.append({'nome': nome, 'valore': valore, 'dettaglio': dettaglio, 'stato': stato})
        if (stato == ROSSO) or (stato == GIALLO and peggio == VERDE):
            peggio = stato

    # su un'app appena installata non c'e' ancora niente da salvare: dire
    # «mai fatta» in rosso spaventa e non serve a niente
    vuota = not con.execute(
        'SELECT COUNT(*) FROM invoices WHERE deleted_at IS NULL').fetchone()[0]
    ultimo = backup.ultimo_esterno(cartella_backup)
    if ultimo is None and vuota:
        aggiungi('Copia fuori dal Mac', 'non ancora',
                 "Se ne fa una da sola appena emetti la prima fattura.", GIALLO)
    elif ultimo is None:
        aggiungi('Copia fuori dal Mac', 'mai fatta',
                 'Nessuno zip nella cartella di destinazione.', ROSSO)
    else:
        _, eta = _eta(ultimo['when'])
        giorni = (datetime.datetime.now() - ultimo['when']).days
        aggiungi('Copia fuori dal Mac', eta,
                 f"{ultimo['name']} · {ultimo['size'] // 1024} KB · verificata alla creazione",
                 VERDE if giorni < GIORNI_BACKUP_VECCHIO else GIALLO)

    quante = len(backup.elenco_esterni(cartella_backup))
    aggiungi('Copie conservate', f'{quante}',
             'Le ultime 30, più la prima di ogni mese che non si cancella mai.',
             VERDE if quante else (GIALLO if vuota else ROSSO))

    if not (settings.get('calendario_ics') or '').strip():
        aggiungi('Calendario', 'non collegato',
                 "Le sessioni vanno registrate a mano finché manca l'indirizzo iCal.", GIALLO)
    else:
        q, eta = _eta(settings.get('calendario_ultimo'))
        if q is None:
            aggiungi('Calendario', 'mai letto', 'Collegato, ma non ancora interrogato.', GIALLO)
        else:
            ore = (datetime.datetime.now() - q).total_seconds() / 3600
            aggiungi('Calendario', eta, 'Si rilegge da solo aprendo la pagina Crediti.',
                     VERDE if ore < ORE_CALENDARIO_VECCHIO else GIALLO)

    esito = settings.get('autotest_esito', '')
    q, eta = _eta(settings.get('autotest_quando'))
    if not esito:
        aggiungi('Verifica dei calcoli', 'mai eseguita',
                 'Si lancia dalla pagina Verifica calcoli.', GIALLO)
    else:
        passati, totali = (esito.split('/') + ['?'])[:2]
        ok = passati == totali
        aggiungi('Verifica dei calcoli', f'{esito} controlli',
                 f'Ultima {eta}.' if eta else '', VERDE if ok else ROSSO)

    ultimo_estratto = settings.get('banca_ultimo_estratto') or ''
    if not ultimo_estratto:
        aggiungi('Estratto conto', 'mai letto',
                 'Scarica i movimenti dall\'e-banking e mettili in «Estratti conto».', GIALLO)
    else:
        try:
            giorni = (datetime.date.today()
                      - datetime.date.fromisoformat(ultimo_estratto)).days
        except ValueError:
            giorni = 999
        aggiungi('Estratto conto', f'fino al {ultimo_estratto[8:10]}.{ultimo_estratto[5:7]}.'
                 f'{ultimo_estratto[:4]}',
                 ('Da lì in poi l\'app non sa chi ti ha pagato: scaricane uno nuovo.'
                  if giorni > GIORNI_ESTRATTO_VECCHIO
                  else 'I versamenti fino a quella data sono stati esaminati.'),
                 VERDE if giorni <= GIORNI_ESTRATTO_VECCHIO else GIALLO)

    if not (settings.get('smtp_pass') or ''):
        aggiungi('Posta', 'senza password',
                 'Le fatture non possono partire finché manca in Impostazioni.', GIALLO)
    else:
        r = con.execute('SELECT COUNT(*) c FROM email_log '
                        "WHERE esito='errore'").fetchone()['c']
        ultima = con.execute("SELECT sent_at FROM email_log WHERE esito='ok' "
                             'ORDER BY sent_at DESC LIMIT 1').fetchone()
        _, eta = _eta(ultima['sent_at']) if ultima else (None, None)
        aggiungi('Posta', 'configurata',
                 (f'Ultima mail partita {eta}. ' if eta else '')
                 + (f'{r} tentativi falliti in archivio.' if r else 'Nessun invio fallito.'),
                 VERDE)

    return {'voci': voci, 'stato': peggio, 'spazio': _spazio(con)}


def _spazio(con):
    """Quanto occupa tutto, in chiaro. Non e' un limite, e' una misura."""
    from . import db as _db
    def peso(percorso):
        if not percorso or not os.path.exists(percorso):
            return 0
        if os.path.isfile(percorso):
            return os.path.getsize(percorso)
        tot = 0
        for radice, _d, files in os.walk(percorso):
            for f in files:
                try:
                    tot += os.path.getsize(os.path.join(radice, f))
                except OSError:
                    pass
        return tot

    dati = os.path.dirname(_db.DB_PATH)
    fatture = os.environ.get('FATTURE_DIR') or os.path.join(
        os.path.dirname(dati), 'Fatture')
    db_byte = peso(_db.DB_PATH)
    return {
        'database': db_byte,
        'fatture': peso(fatture),
        'backup_locali': peso(os.path.join(dati, 'backups')),
        'email_kb': round((con.execute(
            'SELECT COALESCE(SUM(LENGTH(corpo)), 0) t FROM email_log').fetchone()['t']) / 1024, 1),
    }


# ---------------------------------------------------------------- attivita
def attivita(con, reg, quante=12):
    """Le ultime cose successe, da fonti diverse, in una lista sola."""
    voci = []

    for r in con.execute('SELECT id, number, client_name, created_at, total_cents '
                         'FROM invoices WHERE deleted_at IS NULL AND created_at IS NOT NULL '
                         'ORDER BY created_at DESC LIMIT ?', (quante,)):
        voci.append({'quando': r['created_at'], 'ora_nota': True, 'tipo': 'fattura',
                     'testo': f"Fattura #{r['number']} a {r['client_name']}",
                     'link': ('fattura', {'inv_id': r['id']})})

    for r in con.execute('SELECT id, invoice_id, sent_at, destinatario, fatture, esito, prova '
                         'FROM email_log ORDER BY sent_at DESC LIMIT ?', (quante,)):
        if r['prova']:
            testo = f"Prova su di te{' — non è partita' if r['esito'] != 'ok' else ''}"
        elif r['esito'] != 'ok':
            testo = f"Invio fallito della #{r['fatture']}"
        else:
            a_chi = f" a {r['destinatario']}" if r['destinatario'] else ''
            testo = f"Fattura #{r['fatture']} spedita{a_chi}"
        voci.append({'quando': r['sent_at'], 'ora_nota': True,
                     'tipo': 'errore' if r['esito'] != 'ok' else 'email',
                     'testo': testo, 'link': ('email_letta', {'log_id': r['id']})})

    # le sessioni passano dall'agenda, che sa anche l'ora: qui non se ne inventa
    # nessuna, e quando non si conosce si mostra solo il giorno
    for s in agenda.elenco(reg)[:quante]:
        voci.append({'quando': f"{s['data']}T{s['ora'] or ''}",
                     'ora_nota': bool(s['ora']), 'tipo': 'sessione',
                     'testo': f"Sessione di {s['cliente']}"
                              + (' (annullata)' if s['cancellata'] else ''),
                     'link': ('agenda', {})})

    for p in reg.get('pacchetti', []):
        if p.get('rimasti') == 0 and p.get('fine'):
            voci.append({'quando': f"{p['fine']}T23:59", 'ora_nota': False, 'tipo': 'crediti',
                         'testo': f"Crediti finiti: {p['id']} ({p.get('cliente', '')})",
                         'link': ('crediti', {})})

    voci.sort(key=lambda v: v['quando'] or '', reverse=True)
    return voci[:quante]


# ------------------------------------------------------------------ da fare
# La Dashboard risponde a una domanda sola: che cosa richiede la mia attenzione
# adesso. Percio' ogni voce qui e' un'AZIONE, non un'informazione: ha un numero,
# un importo quando ha senso, e il posto dove si va a farla. Le informazioni
# belle da guardare stanno in Performance, le reti di sicurezza in Controlli.
#
# Se la lista viene vuota e' un buon risultato, e deve sembrarlo: nessun
# riquadro d'allarme spento, una riga sola che dice che non c'e' niente.

RITARDO, ATTESA, CALMO = 'ritardo', 'attesa', 'calmo'


def da_fare(con, settings, registro=None):
    """Le cose in sospeso, dalla piu' urgente alla meno.

    Non ci mettiamo i versamenti da confermare: per contarli bisognerebbe
    rileggere i file degli estratti a ogni apertura della Dashboard. Al loro
    posto una cosa che costa una lettura sola e dice la stessa cosa, cioe' da
    quanto l'app non sa piu' chi ti ha pagato.
    """
    voci = []

    # Le fatture ancora aperte secondo il loro stato, non secondo la banca: il
    # numero deve corrispondere a quello che si vede cliccando. Il riscontro
    # bancario serve solo a dire QUALI sono in ritardo.
    aperte = con.execute(
        'SELECT id, total_cents FROM invoices '
        "WHERE deleted_at IS NULL AND status <> 'pagata'").fetchall()
    if aperte:
        mancanti = incassi_mancanti(con, settings.get('banca_ultimo_estratto'))
        in_ritardo = {r['id'] for r in mancanti['in_ritardo']}
        tardi = sum(1 for r in aperte if r['id'] in in_ritardo)
        voci.append({
            'chiave': 'incassare', 'icona': 'soldi',
            'titolo': 'Da incassare',
            'quante': len(aperte),
            'unita': 'fatture' if len(aperte) != 1 else 'fattura',
            'importo': sum(r['total_cents'] or 0 for r in aperte),
            'dettaglio': (f'{tardi} ferme da oltre {GIORNI_PAZIENZA} giorni'
                          if tardi else 'nessuna in ritardo, sono tutte recenti'),
            'urgenza': RITARDO if tardi else ATTESA,
            'link': ('fatture', {'stato': 'emessa', 'anno': ''}),
        })

    stato = stato_fatture(con, datetime.date.today().year)
    if stato['da_mandare']:
        voci.append({
            'chiave': 'spedire', 'icona': 'email',
            'titolo': 'Fatte e non ancora spedite',
            'quante': stato['da_mandare'],
            'unita': 'fatture' if stato['da_mandare'] != 1 else 'fattura',
            'importo': None,
            'dettaglio': "sono nell'app ma non sono partite per email",
            'urgenza': ATTESA,
            'link': ('fatture', {'invio': 'da-mandare', 'anno': ''}),
        })

    finiti = _crediti_finiti(registro)
    if finiti:
        voci.append({
            'chiave': 'crediti', 'icona': 'crediti',
            'titolo': 'Pacchetti finiti',
            'quante': len(finiti),
            'unita': 'clienti' if len(finiti) != 1 else 'cliente',
            'importo': None,
            'dettaglio': ', '.join(finiti[:4]) + (' e altri' if len(finiti) > 4 else '')
                         + ' — va emessa la prossima fattura',
            'urgenza': RITARDO,
            'link': ('crediti', {}),
        })

    vecchio = _estratto_vecchio(settings.get('banca_ultimo_estratto'))
    if vecchio:
        voci.append({
            'chiave': 'estratto', 'icona': 'banca',
            'titolo': 'Estratto conto da aggiornare',
            'quante': None, 'unita': '', 'importo': None,
            'dettaglio': vecchio,
            'urgenza': ATTESA,
            'link': ('banca_pagina', {}),
        })

    return voci


def _crediti_finiti(registro):
    """I clienti che hanno consumato il pacchetto: vanno rifatturati."""
    if registro is None:
        return []
    try:
        from . import sessions
        return [r.get('cliente') or r.get('chiave')
                for r in sessions.vista_crediti(registro) if r.get('terminati')]
    except Exception:
        return []          # i crediti non devono poter spegnere la Dashboard


def _estratto_vecchio(ultimo):
    """Da quanto l'app non sa piu' chi ti ha pagato. '' se e' aggiornato."""
    if not ultimo:
        return "non ne hai ancora caricato nessuno: l'app non sa chi ti ha pagato"
    try:
        giorni = (datetime.date.today() - datetime.date.fromisoformat(ultimo)).days
    except ValueError:
        return ''
    if giorni <= GIORNI_ESTRATTO_VECCHIO:
        return ''
    return (f"l'ultimo arriva al {ultimo[8:10]}.{ultimo[5:7]}.{ultimo[:4]}, "
            f'{giorni} giorni fa')
