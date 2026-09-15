# -*- coding: utf-8 -*-
"""
Batteria di test sui calcoli. Nessuna dipendenza esterna: verifica il motore
matematico (centesimi interi) su casi normali e casi-trappola.
run_all() ritorna (tutti_ok, [risultati]) dove ogni risultato è
(categoria, descrizione, ok, dettaglio).
"""
import io
import os
import re
from decimal import Decimal

from .money import parse_amount, fmt_chf, fmt_dash, parse_qty, line_total
from . import verify
from . import menu


def _check(results, cat, desc, got, expected):
    ok = got == expected
    detail = '' if ok else f'ottenuto {got!r}, atteso {expected!r}'
    results.append((cat, desc, ok, detail))


def _senza_scoppiare(f, *args, **kw):
    """Il valore, oppure il nome del guasto invece del guasto.

    Serve quando la cosa da provare e' proprio che una funzione NON esploda.
    Senza questo, il giorno che esplode davvero l'eccezione porta via l'intera
    batteria: la prova che doveva diventare rossa non diventa niente, e tutte
    quelle dopo di lei non vengono nemmeno eseguite. Una batteria che si
    ferma alla prima crepa non dice dove sono le altre.
    """
    try:
        return f(*args, **kw)
    except Exception as guaio:                             # pragma: no cover
        return '%s: %s' % (type(guaio).__name__, guaio)


def run_all():
    r = []

    # --- lettura importi in tutti i formati che potresti scrivere ---
    parse_cases = [
        ('110.-', 11000), ('110.–', 11000), ('150,00 CHF', 15000),
        ("1'800.00", 180000), ('1.800,00CHF', 180000), ('1800', 180000),
        ('1800.5', 180050), ('CHF 110', 11000), ('110 CHF', 11000),
        ('0.-', 0), ("1'800.-", 180000), ('1.800', 180000), ('150.-', 15000),
        ('24234.3', 2423430), ('1,800.00', 180000), ('2.796,8', 279680),
        ('99.95', 9995), ('  ', None), ('abc', None), (None, None),
        ('12.345,67', 1234567), ("12'345.67", 1234567), ('0', 0),
        ('0.01', 1), ('0,05', 5), ('1000000', 100000000),
    ]
    for txt, exp in parse_cases:
        _check(r, 'Lettura importi', f'"{txt}" → {fmt_chf(exp) if exp is not None else "vuoto"}',
               parse_amount(txt), exp)

    # --- moltiplicazione quantità × prezzo (il cuore della fattura) ---
    mult_cases = [
        (12, 15000, 180000), ('12', 15000, 180000), (1, 11000, 11000),
        (3, 3333, 9999), (10, 9995, 99950), (24, 15000, 360000),
        (0, 15000, 0), (100, 100, 10000),
    ]
    for qty, unit, exp in mult_cases:
        _check(r, 'Quantità × prezzo', f'{qty} × {fmt_dash(unit)} = {fmt_dash(exp)}',
               line_total(qty, unit), exp)

    # --- quantità decimali con arrotondamento corretto ---
    _check(r, 'Arrotondamento', "1.5 × 110.- = 165.-", line_total('1.5', 11000), 16500)
    _check(r, 'Arrotondamento', "0.333 × 100.- = 33.30 (half-up)",
           line_total(parse_qty('0.333'), 10000), 3330)
    _check(r, 'Arrotondamento', "2.5 × 99.99 = 249.98 (half-up sul centesimo)",
           line_total(parse_qty('2.5'), 9999), 24998)

    # --- formattazione (quello che finisce sulla fattura) ---
    fmt_cases = [
        (180000, "1'800.00 CHF"), (2423430, "24'234.30 CHF"),
        (11000, "110.00 CHF"), (0, "0.00 CHF"), (100000000, "1'000'000.00 CHF"),
    ]
    for cents, exp in fmt_cases:
        _check(r, 'Formato CHF', f'{cents} centesimi → {exp}', fmt_chf(cents), exp)

    dash_cases = [(180000, "1'800.-"), (180050, "1'800.50"), (11000, "110.-"),
                  (9995, "99.95"), (0, "0.-")]
    for cents, exp in dash_cases:
        _check(r, 'Formato fattura', f'{cents} centesimi → {exp}', fmt_dash(cents), exp)

    # --- round-trip: leggi ciò che hai scritto e riottieni lo stesso numero ---
    for cents in [11000, 15000, 180000, 2423430, 9995, 1, 100000000]:
        back = parse_amount(fmt_chf(cents))
        _check(r, 'Andata e ritorno', f'{fmt_chf(cents)} riletto = stesso valore', back, cents)

    # --- somma di più righe (nessuna perdita di centesimi) ---
    rows_totals = [180000, 0, 11000, 33330, 9995]
    _check(r, 'Somma righe', "1800 + 0 + 110 + 333.30 + 99.95 = 2343.25",
           sum(rows_totals), 234325)

    # --- coerenza: qty×unit deve dare il totale riga atteso, sempre ---
    consistency_ok = all(
        line_total(q, u) == Decimal(q) * Decimal(u) if isinstance(q, int) else True
        for q, u in [(12, 15000), (3, 3333), (24, 15000), (100, 100)])
    _check(r, 'Coerenza interna', 'quantità intere: nessun arrotondamento spurio',
           consistency_ok, True)

    # ogni famiglia per conto suo: se una si schianta, le altre vanno avanti
    _esegui_famiglie(r, (
        _test_email, _test_oggetto, _test_intestazione_fattura, _test_marchio,
        _test_clienti_crediti, _test_servizi, _test_servizi_riconosciuti, _test_migrazione_servizi,
        _test_sedute_dai_servizi,
        _test_da_fare, _test_lingua, _test_primi_passi, _test_icone, _test_menu,
        _test_etichette, _test_finestra_stretta, _test_calendario,
        _test_storico_al_buio, _test_riferimento_qr, _test_camt_vero,
        _test_gemelli_fra_file, _test_qr_fattura, _test_qr_iban,
        _test_compleanni, _test_modelli_si_compilano, _test_abbonamenti,
        _test_lavoro, _test_nomi_accentati, _test_una_cartella_sola,
        _test_pagine_vuote, _test_qr_di_serie, _test_copie_dal_registro,
        _test_registro_avvio, _test_batteria_regge,
    ))

    all_ok = all(x[2] for x in r)
    return all_ok, r


# La categoria delle famiglie che si fermano a meta'. Quando va tutto bene non
# compare mai: per questo la sua traduzione la controlla _test_batteria_regge.
INTERROTTE = 'Collaudi interrotti'


def _esegui_famiglie(r, famiglie):
    """Fa girare ogni famiglia di collaudi per conto suo.

    Lo stesso principio di _senza_scoppiare, applicato alle famiglie intere:
    una che si schianta a meta' diventa una riga rossa col motivo, e le altre
    vanno avanti lo stesso. Prima un guasto solo faceva cadere la pagina.
    """
    for famiglia in famiglie:
        try:
            famiglia(r)
        except Exception as guaio:
            nome = famiglia.__name__.lstrip('_')
            if nome.startswith('test_'):
                nome = nome[len('test_'):]
            r.append((INTERROTTE,
                      'la famiglia «%s» si è fermata a metà: le prove dopo il '
                      'guasto non sono state fatte' % nome,
                      False, '%s: %s' % (type(guaio).__name__, guaio)))


def _test_registro_avvio(r):
    """Le righe dell'avvio arrivano nel registro mentre succedono, su ogni sistema.

    Aperta dall'icona, sul Mac l'app non ha un terminale: quello che stampa
    finisce in data/start.log. Su un file Python non scrive riga per riga ma a
    blocchi da 8 KB, e le poche righe dell'avvio aspettavano la chiusura
    dell'app. Se a chiuderla era l'avviatore, per rimetterne in piedi una
    aggiornata, non arrivavano proprio: il registro di quella volta restava
    muto, proprio quando serviva a capire com'era andata.

    Su Windows era peggio: l'app parte con pythonw, che un'uscita non ce l'ha
    proprio, e quelle righe non andavano da nessuna parte. Un registro
    d'avvio li' non esisteva.
    """
    import tempfile
    import types
    from . import launcher

    riga = '  Banca: 3 accrediti letti'
    with tempfile.TemporaryDirectory() as tmp:
        # --- Mac: l'uscita e' gia' il file, va solo scritta riga per riga ---
        perc = os.path.join(tmp, 'start.log')
        # aperto come Python apre la sua uscita quando la mandano in un file
        uscita = io.open(perc, 'w', encoding='utf-8')
        try:
            mac = types.SimpleNamespace(stdout=uscita, stderr=uscita)
            launcher.registro_avvio(mac, os.path.join(tmp, 'altro.log'))
            print(riga, file=uscita)
            with io.open(perc, encoding='utf-8') as f:
                letto = f.read()
        finally:
            uscita.close()
        _check(r, 'Registro d’avvio', 'una riga stampata è già nel file, con l’app ancora accesa',
               (letto, mac.stdout is uscita, os.path.exists(os.path.join(tmp, 'altro.log'))),
               (riga + '\n', True, False))

        # --- Windows: nessuna uscita, il registro lo apre l'app ---
        registro = os.path.join(tmp, 'start-win.log')
        with io.open(registro, 'w', encoding='utf-8') as f:
            f.write('avvio di ieri\n')
        win = types.SimpleNamespace(stdout=None, stderr=None)
        esito = _senza_scoppiare(launcher.registro_avvio, win, registro)
        try:
            # scritta a mano: un print(file=None) andrebbe nell'uscita di
            # QUESTA app, cioe' nel registro vero
            if win.stdout is not None:
                win.stdout.write(riga + '\n')
            with io.open(registro, encoding='utf-8') as f:
                righe = f.read().splitlines()
        finally:
            if win.stdout is not None:
                win.stdout.close()
        _check(r, 'Registro d’avvio', 'su Windows, dove pythonw non ha uscita, l’app apre il registro da sé',
               (esito, righe[2:]), (None, [riga]))
        _check(r, 'Registro d’avvio', 'e ci finiscono anche gli avvisi e i guasti',
               win.stderr is not None and win.stderr is win.stdout, True)
        _check(r, 'Registro d’avvio', 'ogni avvio comincia con la sua data, come sul Mac',
               [bool(re.match(r'--- \d{4}-\d\d-\d\d \d\d:\d\d:\d\d ---$', x)) for x in righe[1:2]],
               [True])
        _check(r, 'Registro d’avvio', 'e si aggiunge in fondo, senza cancellare gli avvii di prima',
               righe[:1], ['avvio di ieri'])

        # un registro che non si apre non deve impedire all'app di partire
        chiuso = types.SimpleNamespace(stdout=None, stderr=None)
        _check(r, 'Registro d’avvio', 'e se il registro non si può aprire, l’app parte lo stesso',
               (_senza_scoppiare(launcher.registro_avvio, chiuso, tmp), chiuso.stdout),
               (None, None))

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        programma = f.read()
    avvio = programma[programma.find("if __name__ == '__main__':"):]
    chiamata = avvio.find('launcher.registro_avvio(sys, START_LOG)')
    _check(r, 'Registro d’avvio', 'l’app lo chiede prima di stampare la prima riga',
           (chiamata > 0, chiamata < avvio.find('print(')), (True, True))
    # lo stesso file che sul Mac apre l'avviatore: chi cerca il registro lo
    # trova nello stesso posto su tutt'e due i sistemi
    _check(r, 'Registro d’avvio', 'su Windows è lo stesso data/start.log del Mac',
           "START_LOG = os.path.join(APP_DIR, 'data', 'start.log')" in programma, True)


def _test_batteria_regge(r):
    """Una famiglia di collaudi che si schianta non porta via le altre.

    Prima bastava un guasto in una famiglia sola per far cadere tutta la
    pagina Verifica: «Ops» al posto di 780 risultati, cioe' nessuna notizia
    proprio sul computer dove servivano. Successo sul primo PC Windows vero.
    """
    def prima(rr):
        rr.append(('Prova', 'prima', True, ''))

    def crolla(rr):
        rr.append(('Prova', 'fino al guasto', True, ''))
        raise PermissionError(13, 'file in uso')

    def dopo(rr):
        rr.append(('Prova', 'dopo il guasto', True, ''))

    finti = []
    _check(r, 'Batteria dei collaudi', 'una famiglia che si schianta non ferma la batteria',
           _senza_scoppiare(_esegui_famiglie, finti, (prima, crolla, dopo)), None)
    _check(r, 'Batteria dei collaudi', 'le famiglie dopo il guasto girano lo stesso',
           [x[1] for x in finti if x[0] == 'Prova'],
           ['prima', 'fino al guasto', 'dopo il guasto'])
    rotte = [x for x in finti if x[0] == INTERROTTE]
    _check(r, 'Batteria dei collaudi', 'il guasto diventa una riga rossa, una sola',
           [x[2] for x in rotte], [False])
    _check(r, 'Batteria dei collaudi', 'la riga rossa dice quale famiglia e perché',
           bool(rotte) and 'crolla' in rotte[0][1] and 'PermissionError' in rotte[0][3], True)
    # la categoria dei guasti non compare mai quando va tutto bene, quindi la
    # guardia sui nomi delle famiglie non la vedrebbe: la traduzione si
    # controlla qui
    from . import language as L
    _check(r, 'Batteria dei collaudi', 'anche questi due nomi hanno la traduzione',
           [(x, lingua) for x in (INTERROTTE, 'Batteria dei collaudi')
            for lingua in ('en', 'de') if x not in L.TESTI[lingua]], [])


class _Finta(dict):
    """Una riga di database finta: si comporta come sqlite3.Row."""
    def keys(self):
        return list(super().keys())


def _test_email(r):
    """Il testo dell'email si costruisce senza toccare la rete: si puo' provare."""
    from . import mailer
    from .db import DEFAULT_SETTINGS

    # Chi usa l'app ha scritto i suoi servizi in Impostazioni: e' il caso
    # normale. Le regole non sono piu' nel programma, quindi vanno date.
    S = dict(DEFAULT_SETTINGS)
    # il servizio collegato alla fattura: e' lui a dire il nome e il modello
    RUNNING = {'nome': 'Running Coaching', 'ogni_mese': 1}
    PT = {'nome': 'Personal Training', 'ogni_mese': 0}

    inv = _Finta(number=99, total_cents=110000, pdf_path='', source_file='',
                 client_name='Chiara De Santis')
    mensile = _Finta(name='Chiara De Santis', email='b@esempio.ch',
                     abbonamento=1, tono='informale')
    pacchetto = _Finta(name='Petra Müller', email='d@esempio.ch',
                       abbonamento=0, tono='formale')

    m = mailer.componi(inv, mensile, S, ['Monthly abo: running coaching'], servizio=RUNNING)
    _check(r, 'Email', 'abbonamento: "this month\'s invoice"',
           "this month's invoice for Running Coaching" in m['body'], True)
    _check(r, 'Email', 'abbonamento: c\'è la frase sull\'ordine permanente',
           'standing order' in m['body'], True)
    _check(r, 'Email', 'tono informale: si chiude col saluto informale',
           m['body'].rstrip().endswith('Best,'), True)

    m2 = mailer.componi(inv, pacchetto, S, ['10 Sessions Pack – Personal Training'], servizio=PT)
    _check(r, 'Email', 'pacchetto: NON dice "this month\'s"',
           "this month's" in m2['body'], False)
    _check(r, 'Email', "pacchetto: l'apertura nomina il servizio",
           'your invoice for Personal Training' in m2['body'], True)
    _check(r, 'Email', 'tono formale: si firma per esteso',
           'Best regards,' in m2['body'], True)
    _check(r, 'Email', 'niente frase sull\'ordine permanente se non è abbonato',
           'standing order' in m2['body'], False)

    # --- la richiesta di pagare col codice QR -----------------------------
    # Due condizioni, e servono tutte e due: il codice su QUELLA fattura c'e'
    # davvero, e chi la riceve non ha un ordine permanente. Mandare a cercare
    # un codice che non e' stato stampato, o chiedere di pagare a chi paga gia'
    # da solo, sono due modi diversi di far fare brutta figura all'app.
    con_qr = _Finta(number=99, total_cents=110000, pdf_path='', source_file='',
                    client_name='Petra Müller', qr_ref='RF8399')

    m3 = mailer.componi(con_qr, pacchetto, S, ['10 Sessions Pack – Personal Training'], servizio=PT)
    _check(r, 'Email', 'col codice QR sulla fattura, la mail chiede di usarlo',
           'QR code' in m3['body'], True)
    _check(r, 'Email', 'e lo chiede una volta sola',
           m3['body'].count('QR code'), 1)
    _check(r, 'Email', 'e non resta incollata alla riga dopo',
           '\n\nThank you' in m3['body'].replace(S['email_corpo_pt'], 'Thank you'), True)
    _check(r, 'Email', 'senza codice sulla fattura non si nomina nessun codice',
           'QR code' in m2['body'], False)

    abbonata_con_qr = mailer.componi(con_qr, mensile, S, ['Monthly abo: running coaching'],
                                     servizio=RUNNING)
    _check(r, 'Email', "a chi ha l'ordine permanente il codice QR non si chiede",
           'QR code' in abbonata_con_qr['body'], False)
    _check(r, 'Email', 'e resta la frase sull\'ordine permanente',
           'standing order' in abbonata_con_qr['body'], True)
    _check(r, 'Email', 'le due frasi non escono mai insieme',
           ('QR code' in m3['body'], 'standing order' in m3['body']), (True, False))

    # Una fattura vera arriva dal database, non da un dizionario scritto a
    # mano: se il campo non c'e' proprio, la mail deve uscire lo stesso.
    senza_campo = _Finta(number=99, total_cents=110000, pdf_path='', source_file='',
                         client_name='Petra Müller')
    _check(r, 'Email', 'una fattura senza la colonna del riferimento non fa saltare la mail',
           _senza_scoppiare(lambda: 'QR code' in mailer.componi(
               senza_campo, pacchetto, S, ['10 Sessions Pack'])['body']), False)

    # Il segnaposto nuovo dev'essere ARRIVATO nel modello di chi l'app ce
    # l'aveva gia': senza posto dove scriverla, la frase non comparirebbe mai.
    from .db import _migra_riga_qr
    import sqlite3
    finto = sqlite3.connect(':memory:')
    finto.row_factory = sqlite3.Row
    finto.execute('CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT)')
    finto.executemany('INSERT INTO settings VALUES(?,?)', [
        ('email_body', 'Ciao {nome},\n\n{apertura}\n{riga_abbonamento}{corpo}\n{firma}'),
        ('email_body_de', ''),
        ('email_body_en', 'Hi {nome}, {riga_abbonamento}{corpo}'),
        ('email_oggetto_pt', 'Invoice'),
    ])
    _migra_riga_qr(finto)
    dopo = {x['key']: x['value'] for x in finto.execute('SELECT key, value FROM settings')}
    _check(r, 'Email', 'il segnaposto nuovo entra nel modello che c\'era già',
           '{riga_abbonamento}{riga_qr}' in dopo['email_body'], True)
    _check(r, 'Email', 'entra anche nei modelli per lingua',
           '{riga_abbonamento}{riga_qr}' in dopo['email_body_en'], True)
    _check(r, 'Email', 'un modello vuoto resta vuoto',
           dopo['email_body_de'], '')
    _check(r, "Email", "l'oggetto della mail non viene toccato",
           dopo['email_oggetto_pt'], 'Invoice')
    _migra_riga_qr(finto)
    dopo2 = {x['key']: x['value'] for x in finto.execute('SELECT key, value FROM settings')}
    _check(r, 'Email', 'passarci due volte non lo scrive due volte',
           dopo2['email_body'].count('{riga_qr}'), 1)
    finto.close()

    _check(r, 'Email', 'nome di battesimo dal nome completo',
           mailer.nome_di_battesimo('Chiara De Santis'), 'Chiara')

    # i due modelli: sceglierli da soli e poterli forzare a mano
    prove = dict(S, email_corpo_coaching='TESTO-COACHING', email_corpo_pt='TESTO-PT')
    _check(r, 'Email', 'servizio ogni mese → modello coaching', mailer.modello_di(RUNNING), 'coaching')
    _check(r, 'Email', 'servizio una volta → modello «pacchetto»', mailer.modello_di(PT), 'pt')
    _check(r, 'Email', 'senza servizio → modello «pacchetto», come prima',
           mailer.modello_di(None), 'pt')
    _check(r, 'Email', 'senza servizio non se ne inventa uno', mailer.servizio_di(None), '')
    # «la fattura di questo mese» la decide il servizio, non la casella del cliente
    senza_ordine = _Finta(name='Chiara De Santis', email='b@esempio.ch',
                          abbonamento=0, tono='informale')
    corpo_mese = mailer.componi(inv, senza_ordine, S, [], servizio=RUNNING)['body']
    _check(r, 'Email', 'abbonamento senza ordine permanente: «this month’s invoice» lo stesso',
           "this month's invoice for Running Coaching" in corpo_mese, True)
    _check(r, 'Email', 'e senza la frase sull’ordine permanente',
           'standing order' in corpo_mese, False)
    _check(r, 'Email', 'senza servizio si decide ancora dalla casella del cliente',
           "this month's invoice." in mailer.componi(inv, mensile, S, [])['body'], True)
    _check(r, 'Email', "servizio ignoto: l'apertura non lo nomina",
           mailer.componi(inv, pacchetto, S, ['Pacchetto 10 sedute'])['body'].split('\n')[2],
           'Please find attached your invoice.')
    _check(r, 'Email', "servizio noto: l'apertura lo nomina come prima",
           mailer.componi(inv, pacchetto, S, ['10 Sessions Pack'],
                          servizio=PT)['body'].split('\n')[2],
           'Please find attached your invoice for Personal Training.')
    _check(r, 'Email', 'il modello dedotto finisce nel testo',
           'TESTO-COACHING' in mailer.componi(inv, mensile, prove,
                                              ['Monthly abo: running coaching'],
                                              servizio=RUNNING)['body'], True)
    _check(r, 'Email', 'modello forzato a mano: vince sulla deduzione',
           'TESTO-PT' in mailer.componi(inv, mensile, prove,
                                        ['Monthly abo: running coaching'],
                                        modello='pt', servizio=RUNNING)['body'], True)
    _check(r, 'Email', 'modello inventato: si torna a quello dedotto',
           mailer.componi(inv, mensile, prove, ['Monthly abo: running coaching'],
                          modello='inesistente', servizio=RUNNING)['modello'], 'coaching')
    _check(r, 'Email', 'un testo scritto a mano batte tutti e due i modelli',
           'A MANO' in mailer.componi(inv, mensile, prove,
                                      ['Monthly abo: running coaching'],
                                      corpo='A MANO', servizio=RUNNING)['body'], True)
    _check(r, 'Email', 'senza indirizzo: lo dice invece di mandare a vuoto',
           bool(mailer.componi(inv, _Finta(name='X', email='', abbonamento=0, tono='informale'),
                               S)['problemi']), True)
    _check(r, 'Email', 'indirizzo malscritto: lo dice',
           bool(mailer.componi(inv, _Finta(name='X', email='pippo.esempio', abbonamento=0,
                                           tono='informale'), S)['problemi']), True)
    esito = mailer.spedisci({'to': 'x@y.ch', 'subject': '', 'body': '', 'allegati': []},
                            dict(S, smtp_pass=''))
    _check(r, 'Email', 'senza password non prova nemmeno a collegarsi', esito[0], False)
    _check(r, 'Email', 'il motivo del fallimento è etichettato', esito[2], 'config')
    import smtplib
    m = mailer.costruisci_messaggio({'to': 'cliente@esempio.ch', 'subject': 'x',
                                     'body': 'y', 'allegati': []},
                                    dict(S, smtp_user='io@esempio.ch'), None, copia_a_me=True)

    class _FintoSMTP(smtplib.SMTP):
        def __init__(self):
            self.inviati = []; self.esmtp_features = {}; self.does_esmtp = 0
        def ehlo_or_helo_if_needed(self):
            pass
        def sendmail(self, da, a, testo, *args, **kw):
            self.inviati.append((a, testo.decode() if isinstance(testo, bytes) else testo))
            return {}

    f = _FintoSMTP()
    smtplib.SMTP.send_message(f, m)
    a_chi, spedito = f.inviati[0]
    _check(r, 'Email', 'la copia nascosta arriva anche a te',
           'io@esempio.ch' in a_chi, True)
    _check(r, 'Email', 'il cliente riceve comunque la sua',
           'cliente@esempio.ch' in a_chi, True)
    _check(r, 'Email', 'il cliente NON vede che ti sei mandato una copia',
           'Bcc:' in spedito, False)

    _check(r, 'Email', 'la password non finisce nei messaggi d\'errore',
           'segreta' in mailer._nascondi('errore con segreta dentro',
                                         {'smtp_pass': 'segreta'}), False)


CAL_PROVA = """BEGIN:VCALENDAR
X-WR-CALNAME:Allenamenti
BEGIN:VEVENT
UID:tizio@g
DTSTART;TZID=Europe/Zurich:20260818T073000
SUMMARY:Marco
RRULE:FREQ=WEEKLY;BYDAY=TU
EXDATE;TZID=Europe/Zurich:20260901T073000
END:VEVENT
BEGIN:VEVENT
UID:caio@g
DTSTART;TZID=Europe/Zurich:20260820T093000
SUMMARY:Anna
RRULE:FREQ=WEEKLY;BYDAY=TH
END:VEVENT
BEGIN:VEVENT
UID:caio@g
RECURRENCE-ID;TZID=Europe/Zurich:20260827T093000
DTSTART;TZID=Europe/Zurich:20260827T093000
SUMMARY:Anna
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
UID:sempronio@g
DTSTART;TZID=Europe/Zurich:20260821T074500
SUMMARY:Sara\\, spostata
RECURRENCE-ID;TZID=Europe/Zurich:20260821T074500
END:VEVENT
END:VCALENDAR"""


def _test_oggetto(r):
    """L'oggetto cambia col servizio, e il mese si deduce invece di inventarlo."""
    from . import mailer
    from .db import DEFAULT_SETTINGS as S

    inv = _Finta(number=87, total_cents=11000, pdf_path='', source_file='',
                 client_name='Chiara De Santis')
    cli = _Finta(name='Chiara De Santis', email='b@esempio.ch',
                 abbonamento=1, tono='informale')

    # --- il periodo scritto sulla fattura ---
    _check(r, 'Oggetto email', 'periodo a cavallo di due mesi → i due mesi',
           mailer.mesi_da_descrizioni(
               ['Monthly abo: running coaching 13.08.26 \u2013 12.09.26']), (8, 9))
    _check(r, 'Oggetto email', 'periodo dentro un mese solo → un mese',
           mailer.mesi_da_descrizioni(
               ['Monthly abo: running coaching 01.08.26 \u2013 31.08.26']), (8,))
    _check(r, 'Oggetto email', 'mese scritto a parole',
           mailer.mesi_da_descrizioni(['Monthly abo: running coaching (August)']), (8,))
    _check(r, 'Oggetto email', 'niente periodo → niente mese',
           mailer.mesi_da_descrizioni(['10 Sessions Pack \u2013 Personal Training at Home']), ())
    _check(r, 'Oggetto email', 'una parola che comincia come un mese non è un mese',
           mailer.mesi_da_descrizioni(['Marathon plan, Decathlon, Augmented']), ())
    _check(r, 'Oggetto email', 'il trattino corto vale come quello lungo',
           mailer.mesi_da_descrizioni(['abo 13.08.26 - 12.09.26']), (8, 9))

    # --- come li abbrevia lui ---
    stile = mailer.stile_mesi(['Online Running Coaching \u2013 [Aug/Sept] \u2013 EM'])
    _check(r, 'Oggetto email', 'impara «Sept» da come l\'ha scritto lui', stile.get(9), 'Sept')
    _check(r, 'Oggetto email', 'senza esempi usa l\'abbreviazione di tre lettere',
           mailer.etichetta_mesi((9, 10)), 'Sep/Oct')
    _check(r, 'Oggetto email', 'con l\'esempio scrive come lui',
           mailer.etichetta_mesi((9, 10), stile), 'Sept/Oct')
    _check(r, 'Oggetto email', 'vince la forma usata per ultima',
           mailer.stile_mesi(['[Sept]', '[Sep]']).get(9), 'Sep')

    # --- il mese completo, con e senza aiuto dal passato ---
    _check(r, 'Oggetto email', 'Chiara: 13.08–12.09 → Aug/Sept',
           mailer.mese_oggetto(['Monthly abo: running coaching 13.08.26 \u2013 12.09.26'],
                               ['Online Running Coaching \u2013 [Aug/Sept] \u2013 EM']),
           'Aug/Sept')
    _check(r, 'Oggetto email', 'senza periodo: dall\'ultima mail, avanti di un mese',
           mailer.mese_oggetto(['Monthly abo: running coaching'],
                               ['Online Running Coaching \u2013 [Aug/Sept] \u2013 EM']),
           'Sept/Oct')
    _check(r, 'Oggetto email', 'dicembre passa a gennaio, non al mese 13',
           mailer.mese_oggetto(['abo'], ['[Dec]']), 'Jan')
    _check(r, 'Oggetto email', 'niente da cui dedurre → resta vuoto',
           mailer.mese_oggetto(['10 Sessions Pack'], []), '')

    # --- l'oggetto vero e proprio ---
    coaching = mailer.componi(inv, cli, S, ['abo 13.08.26 \u2013 12.09.26'],
                              modello='coaching', mese='Aug/Sept')
    _check(r, 'Oggetto email', 'abbonamento: oggetto col mese dentro',
           coaching['subject'],
           'Invoice \u2013 [Aug/Sept]')
    pt = mailer.componi(inv, cli, S, ['10 Sessions Pack'], modello='pt')
    _check(r, 'Oggetto email', 'pacchetto di sedute: oggetto senza mese',
           pt['subject'],
           'Invoice')
    _check(r, 'Oggetto email', 'cambiare servizio cambia l\'oggetto',
           coaching['subject'] != pt['subject'], True)
    senza = mailer.componi(inv, cli, S, ['abo'], modello='coaching', mese='')
    _check(r, 'Oggetto email', 'mese ignoto: resta «[month]» da riempire a mano',
           '[month]' in senza['subject'], True)
    _check(r, 'Oggetto email', 'e l\'app lo segnala', senza['mese_mancante'], True)
    _check(r, 'Oggetto email', 'col pacchetto il mese non manca mai',
           pt['mese_mancante'], False)


def _test_intestazione_fattura(r):
    """Chi emette la fattura lo dicono le Impostazioni, non il template Word.

    E' il controllo piu' importante di tutti: se il documento tornasse a
    prendere nome e IBAN dal template, chi usa l'app manderebbe fatture con
    l'IBAN di un altro e i clienti pagherebbero sul conto sbagliato. Un
    errore silenzioso, che si scopre solo quando i soldi non arrivano.
    """
    import tempfile
    from docx import Document
    from . import docgen, pdfgen
    from .db import DEFAULT_SETTINGS

    mio = dict(DEFAULT_SETTINGS,
               business_name='Anna Rossi Fitness', business_uid='CHE-111.222.333',
               business_addr1='Musterstrasse 1', business_addr2='Musterstadt, 8000',
               business_phone='+41 79 000 00 00', business_web='annarossi.ch',
               business_iban='CH5604835012345678009',
               terms='Payable within 10 days net to:')
    voci = [{'qty': 10, 'description': '10 Sessions Pack',
             'unit_cents': 12000, 'total_cents': 120000}]

    with tempfile.TemporaryDirectory() as tmp:
        dx = os.path.join(tmp, 'p.docx')
        pf = os.path.join(tmp, 'p.pdf')
        docgen.build_docx(dx, 7, '23-08-26', 'Mario Bianchi', ['Via Roma 1'], voci, 120000, mio)
        pdfgen.build_pdf(pf, 7, '23-08-26', 'Mario Bianchi', ['Via Roma 1'], voci, 120000, mio)
        d = Document(dx)
        testo = '\n'.join(p.text for p in d.paragraphs)
        for t in d.tables:
            for riga in t.rows:
                for c in riga.cells:
                    testo += '\n' + c.text
        for chiave, atteso in (('nome', 'Anna Rossi Fitness'), ('UID', 'CHE-111.222.333'),
                               ('indirizzo', 'Musterstrasse 1'), ('città', 'Musterstadt, 8000'),
                               ('telefono', '+41 79 000 00 00'), ('sito', 'annarossi.ch'),
                               ('IBAN', 'CH5604835012345678009'),
                               ('condizioni', 'Payable within 10 days net to:')):
            _check(r, 'Intestazione fattura', 'nel .docx c\'è il %s delle Impostazioni' % chiave,
                   atteso in testo, True)
        _check(r, 'Intestazione fattura', 'il ringraziamento nomina l\'attività',
               'Thanks for choosing Anna Rossi Fitness!' in testo, True)
        # se un segnaposto del template sopravvive vuol dire che quel dato non
        # e' stato scritto: meglio accorgersene qui che su una fattura spedita
        rimasti = [x for x in ('Nome attività', 'UID / IDI', 'Indirizzo, via e numero',
                               'CAP e città', 'IBAN: —', 'Nome cliente')
                   if x in testo]
        _check(r, 'Intestazione fattura', 'nel .docx non resta nessun segnaposto',
               rimasti, [])
        # Non basta guardare il testo: Word nasconde roba nei «controlli
        # contenuto» e nelle proprieta' del documento, e python-docx non la
        # mostra. Qui si apre il file come archivio e si guarda dentro tutto.
        import zipfile as _zip
        z = _zip.ZipFile(dx)
        dentro = '\n'.join(z.read(n).decode('utf-8', 'replace')
                           for n in z.namelist() if n.endswith('.xml'))
        # tutto quello che il template si porta dietro di chi l'ha disegnato:
        # non deve sopravvivere in nessuna fattura generata
        _check(r, 'Intestazione fattura', 'del template non resta niente nel file',
               [x for x in _proprieta_docx(_zip.ZipFile(docgen.TEMPLATE))
                if x and x in dentro], [])
        import re as _re
        # il ringraziamento era un campo agganciato alla proprieta' «Azienda»:
        # se resta agganciato, Word lo riempie da solo e il nome esce doppio
        corpo = z.read('word/document.xml').decode('utf-8', 'replace')
        _check(r, 'Intestazione fattura', 'niente campi agganciati alle proprietà',
               _re.findall(r'w:xpath="(.*?)"', corpo), [])
        _check(r, 'Intestazione fattura', 'il nome dell\'attività non esce doppio',
               corpo.count('Anna Rossi Fitness'), 3)
        core = z.read('docProps/core.xml').decode('utf-8', 'replace')
        app = z.read('docProps/app.xml').decode('utf-8', 'replace')
        # chiuso SUBITO: a fine blocco la cartella temporanea si cancella, e
        # Windows (il Mac no) rifiuta di cancellare un file ancora aperto. Qui
        # restava aperto, e sul primo PC vero cadeva l'intera pagina Verifica.
        z.close()
        for etichetta, trovato in (
                ('autore', _re.findall(r'<dc:creator>(.*?)</dc:creator>', core)),
                ('ultimo che ha scritto', _re.findall(r'<cp:lastModifiedBy>(.*?)</cp:lastModifiedBy>', core)),
                ('azienda', _re.findall(r'<Company>(.*?)</Company>', app))):
            _check(r, 'Intestazione fattura',
                   f'nelle proprietà del documento «{etichetta}» è la tua attività',
                   trovato, ['Anna Rossi Fitness'])
        _check(r, 'Intestazione fattura', 'gli importi restano giusti',
               verify.verify_generated(dx, pf, 120000, voci), [])
        # senza Impostazioni (chiamata vecchio stile) la fattura si fa lo stesso:
        # meglio un documento coi segnaposto che nessun documento
        dx2 = os.path.join(tmp, 'q.docx')
        docgen.build_docx(dx2, 8, '23-08-26', 'Mario Bianchi', ['Via Roma 1'], voci, 120000)
        _check(r, 'Intestazione fattura', 'senza Impostazioni non esplode',
               os.path.exists(dx2), True)


def _proprieta_docx(z):
    """Chi ha creato un .docx, chi l'ha modificato per ultimo, per quale azienda.

    Sono tre righe di XML che Word riempie da solo e che nessuno guarda mai:
    e' li' che il nome di chi ha disegnato il template resta appiccicato a ogni
    documento generato da quel template."""
    import re as _re
    fuori = []
    for parte, schema in (('docProps/core.xml', r'<dc:creator>(.*?)</dc:creator>'),
                          ('docProps/core.xml', r'<cp:lastModifiedBy>(.*?)</cp:lastModifiedBy>'),
                          ('docProps/app.xml', r'<Company>(.*?)</Company>')):
        try:
            testo = z.read(parte).decode('utf-8', 'replace')
        except KeyError:
            continue
        fuori += [v.strip() for v in _re.findall(schema, testo) if v.strip()]
    return fuori


def _test_marchio(r):
    """Il logo e il nome dell'attività vengono da chi usa l'app, non da chi
    l'ha scritta. Se il programma condiviso si portasse dietro il logo del
    primo proprietario, ogni utente manderebbe fatture col branding di un altro."""
    import io as _io
    import tempfile
    import zipfile
    from PIL import Image
    from . import branding, docgen
    from .db import DEFAULT_SETTINGS

    for nome, atteso in (('Studio Bianchi Fisioterapia', ('Studio Bianchi', 'Fisioterapia')),
                         ('Anna Rossi Personal Training', ('Anna Rossi', 'Personal Training')),
                         ('Centro Vitale', ('Centro Vitale', '')),
                         ('', ('La tua attività', ''))):
        _check(r, 'Marchio', 'il nome «%s» si spezza bene' % (nome or 'vuoto'),
               branding.due_righe(nome), atteso)

    def _png(colore, misura=(120, 120)):
        buf = _io.BytesIO()
        Image.new('RGBA', misura, colore).save(buf, 'PNG')
        return buf.getvalue()

    vero = branding.PERSONALE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            branding.PERSONALE = os.path.join(tmp, 'logo.png')
            _check(r, 'Marchio', 'senza logo caricato si usa il segnaposto',
                   branding.percorso(), branding.SEGNAPOSTO)
            _check(r, 'Marchio', 'il segnaposto esiste davvero',
                   os.path.exists(branding.SEGNAPOSTO), True)
            # il segnaposto dice «caricalo dalle Impostazioni»: dentro l'app va
            # bene, su una fattura che parte al cliente sarebbe una figuraccia
            vuoto = Image.open(_io.BytesIO(branding.adattato(60, 40)))
            _check(r, 'Marchio', 'senza logo la fattura lascia lo spazio vuoto',
                   vuoto.getbbox(), None)

            _check(r, 'Marchio', 'un file che non è un\'immagine viene rifiutato',
                   branding.salva(b'questo non e\' un png') is not None, True)
            _check(r, 'Marchio', 'un caricamento vuoto viene rifiutato',
                   branding.salva(b'') is not None, True)
            _check(r, 'Marchio', 'un\'immagine enorme viene rifiutata',
                   branding.salva(b'\x89PNG' + b'x' * branding.PESO_MAX) is not None, True)

            # un JPEG entra, ma quello che salviamo e' sempre un PNG: il resto
            # dell'app non deve sapere che formato aveva l'originale
            jpg = _io.BytesIO()
            Image.new('RGB', (900, 300), (200, 30, 30)).save(jpg, 'JPEG')
            _check(r, 'Marchio', 'un JPEG viene accettato', branding.salva(jpg.getvalue()), None)
            _check(r, 'Marchio', 'adesso il logo è quello dell\'utente',
                   branding.percorso(), branding.PERSONALE)
            _check(r, 'Marchio', 'il logo salvato è un PNG',
                   Image.open(branding.PERSONALE).format, 'PNG')
            _check(r, 'Marchio', 'un logo enorme viene rimpicciolito',
                   max(Image.open(branding.PERSONALE).size) <= branding.LATO_MAX, True)

            # dentro il Word lo spazio del logo ha una forma fissa: il logo ci
            # deve entrare con quella forma, ma senza essere stirato ne' rifatto
            branding.salva(_png((0, 0, 255, 255), (300, 300)))
            fuori = Image.open(_io.BytesIO(branding.adattato(200, 150)))
            _check(r, 'Marchio', 'il logo adattato prende la forma dello spazio',
                   round(fuori.width / fuori.height, 3), round(200 / 150, 3))
            _check(r, 'Marchio', 'un logo quadrato non viene schiacciato',
                   fuori.height, 300)
            # un logo gia' della forma giusta non va toccato per niente
            branding.salva(_png((0, 0, 255, 255), (400, 300)))
            uguale = Image.open(_io.BytesIO(branding.adattato(200, 150)))
            _check(r, 'Marchio', 'un logo già della forma giusta resta tale e quale',
                   uguale.size, (400, 300))

            branding.salva(_png((255, 0, 0, 255)))
            with tempfile.TemporaryDirectory() as t2:
                dx = os.path.join(t2, 'p.docx')
                docgen.build_docx(dx, 9, '23-08-26', 'Mario Bianchi', [''],
                                  [{'qty': 1, 'description': 'x', 'unit_cents': 100,
                                    'total_cents': 100}], 100,
                                  dict(DEFAULT_SETTINGS, business_name='Anna Rossi Fitness'))
                dentro = Image.open(_io.BytesIO(
                    zipfile.ZipFile(dx).read('word/media/image1.png'))).convert('RGBA')
                rossi = [p for p in dentro.getdata() if p[3] > 0 and p[0] > 200 and p[1] < 60]
                _check(r, 'Marchio', 'nel .docx finisce il logo dell\'utente',
                       len(rossi) > 1000, True)

            branding.rimuovi()
            _check(r, 'Marchio', 'tolto il logo si torna al segnaposto',
                   branding.percorso(), branding.SEGNAPOSTO)
            _check(r, 'Marchio', 'e la fattura torna a lasciare lo spazio vuoto',
                   Image.open(_io.BytesIO(branding.adattato(60, 40))).getbbox(), None)
    finally:
        branding.PERSONALE = vero

    # il template distribuito non deve contenere niente di nessuno: ne' il logo,
    # ne' il nome di chi l'ha disegnato nelle proprieta' del documento. Word ce
    # lo rimette ogni volta che qualcuno risalva il file.
    _check(r, 'Marchio', 'il template Word non porta il nome di chi l\'ha fatto',
           _proprieta_docx(zipfile.ZipFile(docgen.TEMPLATE)), [])
    interno = zipfile.ZipFile(docgen.TEMPLATE).read('word/media/image1.png')
    atteso = open(branding.SEGNAPOSTO, 'rb').read()
    _check(r, 'Marchio', 'il template Word contiene solo il segnaposto',
           interno == atteso, True)


def _test_clienti_crediti(r):
    """Chi fa le sedute è un cliente come gli altri: la scheda comanda tutto.

    Qui si verifica che la scheda cliente comandi davvero: quali nomi si
    riconoscono nel calendario, come si chiamano i pacchetti, la regola della
    coppia, e che un pacchetto si ritrovi dalla chiave anche se il nome cambia."""
    import datetime
    import tempfile
    from . import db as D
    from . import sessions as S
    cat = 'Clienti a crediti'

    for testo, nome, atteso in (('', 'Giulia Ferrari', ['Giulia']),
                                ('Giuly, Giulia F.', 'Giulia Ferrari', ['Giuly', 'Giulia F.']),
                                (' , ', 'Marco', ['Marco']), ('', '', [])):
        _check(r, cat, f'nel calendario «{testo}» per «{nome}» vuol dire {atteso}',
               _senza_scoppiare(S.nomi_calendario, testo, nome), atteso)

    GIULIA = {'id': 1, 'name': 'Giulia Ferrari', 'nome_calendario': '', 'chiave_sedute': 'giulia',
              'archived': 0, 'intestatario': '', 'compagno': None}
    MARCO = {'id': 2, 'name': 'Marco Bianchi', 'nome_calendario': 'Marco, Marco B.',
             'chiave_sedute': 'marco', 'archived': 0, 'intestatario': 'Giulia Ferrari',
             'compagno': 'giulia'}
    LUCA = {'id': 3, 'name': 'Luca Neri', 'nome_calendario': '', 'chiave_sedute': 'luca',
            'archived': 1, 'intestatario': '', 'compagno': None}
    prima = S._CONFIG
    try:
        S.configura([GIULIA, MARCO, LUCA])
        _check(r, cat, 'gli attivi sono i clienti non archiviati', sorted(S.clienti()),
               ['giulia', 'marco'])
        _check(r, cat, 'chi è archiviato è un ex cliente', S.ex_clienti(), {'luca': 'Luca'})
        _check(r, cat, 'il nome è il primo nome nel calendario',
               [S.nome_cliente(k) for k in ('giulia', 'marco')], ['Giulia', 'Marco'])
        _check(r, cat, 'la fattura va a chi è scritto come intestatario',
               S.cliente('marco')['fattura_a'], 'Giulia Ferrari')

        for titolo, atteso in (('Giulia', 'giulia'), ('Marco B. pt Bike', 'marco'),
                               ('Luca', 'luca'), ('Federico', None), ('Giulia birthday', None),
                               ('Giuliana', None), ('Marco con Giulia', 'marco')):
            _check(r, cat, f'nel calendario «{titolo}» è {atteso}', S.classifica(titolo)[0], atteso)

        vuoto = {'pacchetti': [], 'esclusi': []}
        _check(r, cat, 'la sigla dei pacchetti viene dalla chiave',
               (S.prossimo_id_pacchetto(vuoto, 'giulia'), S.prossimo_id_pacchetto(vuoto, 'marco')),
               ('GIU-01', 'MAR-01'))

        # la regola della coppia: il supplemento vale solo se ci sono tutti e due
        _check(r, cat, 'in coppia il supplemento resta suo',
               S.attribuisci('marco', ['giulia', 'marco'])[0], 'marco')
        _check(r, cat, 'da solo consuma un credito del compagno',
               S.attribuisci('marco', ['marco'])[0], 'giulia')
        _check(r, cat, 'chi non è un supplemento non cambia mai',
               S.attribuisci('giulia', ['giulia'])[0], 'giulia')

        # i pacchetti si ritrovano dalla chiave; quelli scritti prima, dal nome
        reg = {'pacchetti': [
            {'id': 'GIU-01', 'cliente': 'Giulia + Marco', 'crediti': 10, 'fine': '2026-07-30',
             'sessioni': []},
            {'id': 'GIU-02', 'cliente': 'Giulia', 'chiavi': ['giulia'], 'crediti': 12,
             'fine': None, 'sessioni': []},
            {'id': 'MAR-01', 'cliente': 'Marco', 'crediti': 10, 'fine': None, 'sessioni': []},
        ], 'esclusi': []}
        _check(r, cat, 'un pacchetto diviso scritto prima ha due chiavi',
               _senza_scoppiare(S._chiavi_di, reg['pacchetti'][0]), ['giulia', 'marco'])
        _check(r, cat, 'il pacchetto aperto si trova dalla chiave',
               (S.pacchetto_aperto_di(reg, 'giulia') or {}).get('id'), 'GIU-02')
        _check(r, cat, 'e quello senza chiave dal nome',
               (S.pacchetto_aperto_di(reg, 'marco') or {}).get('id'), 'MAR-01')
        S.configura([dict(GIULIA, nome_calendario='Giuly'), MARCO, LUCA])
        _check(r, cat, 'se cambia il nome nel calendario il pacchetto con la chiave resta suo',
               (S.pacchetto_aperto_di(reg, 'giulia') or {}).get('id'), 'GIU-02')

        nuovo = _senza_scoppiare(S.apri_pacchetto, reg, 'giulia', '2026-09-01')
        _check(r, cat, 'un pacchetto nuovo prende la misura dell’ultimo e porta la chiave',
               (nuovo['id'], nuovo['crediti'], nuovo['chiavi']) if isinstance(nuovo, dict) else nuovo,
               ('GIU-03', 12, ['giulia']))
        _check(r, cat, 'oppure la misura detta dalla fattura',
               _senza_scoppiare(lambda: S.apri_pacchetto(reg, 'marco', '2026-09-01', crediti=8)['crediti']),
               8)
        for chi, perche in (('federico', 'a uno sconosciuto'),
                            ('luca', 'senza nessuna misura da cui partire')):
            try:
                S.apri_pacchetto({'pacchetti': [], 'esclusi': []}, chi, '2026-08-23')
                esito = 'non ha protestato'
            except S.SenzaPacchetto:
                esito = 'protesta'
            _check(r, cat, f'non si apre un pacchetto {perche}', esito, 'protesta')

        # chi ha le sedute ma nessun pacchetto non deve fermare la lettura del calendario
        # (Check 1, revisione I1: il motivo dello scarto resta questo, non un
        # KeyError qualsiasi — vedi anche la prova sopra, che ora pretende
        # proprio S.SenzaPacchetto e non un KeyError generico)
        S.configura([GIULIA, MARCO, LUCA])
        import sync_sessions as SY
        evento = {'id': 'e1', 'titolo': 'Giulia', 'data': '2026-09-01', 'ora': '07:00',
                  'stato_google': 'confirmed'}
        rap = _senza_scoppiare(lambda: SY.sincronizza({'pacchetti': [], 'esclusi': []}, [evento],
                                                      oggi=datetime.date(2026, 9, 2)))
        _check(r, cat, 'la seduta di chi non ha né pacchetto né abbonamento va fra gli esclusi, '
                       'e la lettura va avanti',
               ([e['motivo'] for e in rap.get('esclusi_nuovi', [])], rap.get('aggiunte'))
               if isinstance(rap, dict) else rap,
               (['nessun abbonamento in corso'], []))

        # Check 2 (revisione I1): un guaio diverso da «nessun pacchetto» — qui
        # un pacchetto aperto senza 'crediti', dati corrotti — non è una
        # sottoclasse di SenzaPacchetto: non si scarta in silenzio, ferma la
        # lettura come succedeva prima di questo scarto (spec 6.1 punto 7).
        reg_rotto = {'pacchetti': [{'id': 'GIU-01', 'cliente': 'Giulia', 'chiavi': ['giulia'],
                                    'fine': None, 'sessioni': []}], 'esclusi': []}
        evento_rotto = {'id': 'e2', 'titolo': 'Giulia', 'data': '2026-09-01', 'ora': '07:00',
                        'stato_google': 'confirmed'}
        try:
            SY.sincronizza(reg_rotto, [evento_rotto], oggi=datetime.date(2026, 9, 2))
            esito = 'non si è fermata'
        except S.SenzaPacchetto:
            esito = 'scartata per sbaglio'
        except KeyError as guaio:
            esito = ('si è fermata', str(guaio))
        _check(r, cat, 'un pacchetto aperto senza «crediti» (dati corrotti) non si scarta: '
                       'ferma la lettura',
               esito, ('si è fermata', "'crediti'"))

        # elenco vuoto: l'app deve reggere, non spegnersi
        S.configura([])
        _check(r, cat, 'senza nessun cliente la vista è vuota',
               S.vista_crediti({'pacchetti': []}), [])
        _check(r, cat, 'senza nessun cliente non si riconosce nulla',
               S.classifica('Giulia')[0], None)
    finally:
        S._CONFIG = prima

    # --- dal database: i clienti con la chiave, e la chiave che nasce ---
    con = _db_servizi()
    for riga in ((1, 'giulia-ferrari', 'Giulia Ferrari', '', 'giulia', None),
                 (2, 'marco-bianchi', 'Marco Bianchi', 'Marco B.', 'marco', 1),
                 (3, 'sofia-verdi', 'Sofia Verdi', '', '', None),
                 (4, 'sofia-neri', 'Sofia Neri', '', '', None),
                 (5, 'zoe-muller', 'Zoë Müller', '', '', None)):
        con.execute('INSERT INTO clients(id, key, name, nome_calendario, chiave_sedute, '
                    'compagno_id) VALUES(?,?,?,?,?,?)', riga)
    _check(r, cat, 'nel motore entrano solo i clienti con la chiave, col compagno per chiave',
           _senza_scoppiare(lambda: [(x['name'], x['chiave_sedute'], x['compagno'])
                                     for x in D.clienti_sedute(con)]),
           [('Giulia Ferrari', 'giulia', None), ('Marco Bianchi', 'marco', 'giulia')])
    _check(r, cat, 'la chiave nasce dal primo nome, senza accenti',
           _senza_scoppiare(D.assegna_chiave_sedute, con, 5), ('zoe', False))
    _check(r, cat, 'la prima Sofia prende «sofia»',
           _senza_scoppiare(D.assegna_chiave_sedute, con, 3), ('sofia', False))
    _check(r, cat, 'la seconda prende «sofia2», e l’app sa che nel calendario si confondono',
           _senza_scoppiare(D.assegna_chiave_sedute, con, 4), ('sofia2', True))
    _check(r, cat, 'una chiave che c’è già non cambia',
           _senza_scoppiare(D.assegna_chiave_sedute, con, 1), ('giulia', False))
    con.close()

    # --- la scheda del cliente: come si chiama nel calendario, con chi si allena ---
    con = _db_servizi()
    for riga in ((1, 'anna-rossi', 'Anna Rossi', '', 'anna', 0),
                 (2, 'anna-bianchi', 'Anna Bianchi', '', '', 0),
                 (3, 'marco-neri', 'Marco Neri', 'Marco, Marco N.', 'marco', 0),
                 (4, 'luca-verdi', 'Luca Verdi', '', 'luca', 1),
                 (5, 'giulia', 'Giulia', '', '', 0)):
        con.execute('INSERT INTO clients(id, key, name, nome_calendario, chiave_sedute, archived) '
                    'VALUES(?,?,?,?,?,?)', riga)
    _check(r, cat, 'si allena insieme a: si sceglie fra i clienti attivi con le sedute',
           _senza_scoppiare(lambda: [(x['id'], x['name']) for x in D.compagni_possibili(con)]),
           [(1, 'Anna Rossi'), (3, 'Marco Neri')])
    for argomenti, atteso, perche in (
            ((2, '', 'Anna Bianchi'), ('Anna Rossi', 'Anna B.'),
             'lo stesso primo nome di un altro cliente con le sedute non si può, e si propone come distinguerli'),
            ((2, 'Anna B.', 'Anna Bianchi'), None, 'con un nome che li distingue sì'),
            ((2, 'Annina, marco  n.', 'Anna Bianchi'), ('Marco Neri', 'Anna B.'),
             'basta uno dei nomi in comune, maiuscole e spazi a parte'),
            ((2, 'Luca', 'Anna Bianchi'), None, 'un ex cliente non occupa il nome'),
            ((1, '', 'Anna Rossi'), None, 'chi non ha ancora le sedute non occupa il nome'),
            ((3, 'Marco', 'Marco Neri'), None, 'il proprio nome non è un doppione'),
            ((5, 'Anna', 'Giulia'), ('Anna Rossi', ''), 'a chi ha un nome solo non si propone niente')):
        _check(r, cat, perche, _senza_scoppiare(D.nome_calendario_doppio, con, *argomenti), atteso)
    con.close()

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'templates', 'clients.html'), encoding='utf-8') as f:
        scheda = f.read()
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        programma = f.read()
    _check(r, cat, 'la scheda del cliente ha la parte «Sedute» e l’ordine permanente col suo nome',
           ('name="nome_calendario"' in scheda, 'name="compagno_id"' in scheda,
            "_('Paga con ordine permanente')" in scheda,
            'Abbonamento mensile (ordine permanente)' in scheda), (True, True, True, False))
    salva = programma[programma.index('def cliente_salva'):]
    salva = salva[:salva.index('\n@app.route')]
    _check(r, cat, 'salvando la scheda si controllano i doppioni e il motore se ne accorge',
           ('nome_calendario_doppio' in salva, 'assegna_chiave_sedute' in salva,
            'sess.ricarica()' in salva), (True, True, True))
    rimando = programma[programma.index('def crediti_clienti'):]
    rimando = rimando[:rimando.index('\n@app.route')]
    _check(r, cat, '«Clienti a crediti» non c’è più: il vecchio indirizzo porta ai Clienti',
           ("redirect(url_for('clienti'))" in rimando, 'def crediti_cliente_salva' in programma,
            'def crediti_cliente_elimina' in programma,
            os.path.exists(os.path.join(base, 'templates', 'credits_clients.html')),
            hasattr(D, 'crediti_cliente_salva'), hasattr(S, 'prezzi_da_testo'),
            hasattr(S, 'chiave_da_nome')),
           (True, False, False, False, False, False, False))

    # un'app appena installata non ha nessuno storico da ricopiare
    seed = S.SEED
    try:
        S.SEED = os.path.join(tempfile.gettempdir(), 'seed-che-non-esiste.json')
        with tempfile.TemporaryDirectory() as tmp:
            reg = S.carica(os.path.join(tmp, 'r.json'))
            _check(r, cat, 'senza storico il registro nasce vuoto',
                   (reg['pacchetti'], reg['esclusi']), ([], []))
    finally:
        S.SEED = seed


def _test_servizi(r):
    """I servizi proposti li scrive chi usa l'app, e il periodo degli
    abbonamenti lo sposta avanti l'app senza sapere come li hai chiamati."""
    from . import services as SR

    # --- lo schema: le tabelle e le colonne nuove ci sono, e rifare non rompe
    from . import db as D
    con = _db_servizi()

    def colonne(tabella):
        return {x['name'] for x in con.execute('PRAGMA table_info(%s)' % tabella)}

    _check(r, 'Servizi', 'la tabella dei servizi ha i campi della scheda',
           {'id', 'nome', 'prezzo_cents', 'ogni_mese', 'sedute', 'scadenza_mesi',
            'passano', 'massimo', 'attivo', 'pos', 'creato_il'} <= colonne('servizi'), True)
    _check(r, 'Servizi', 'le righe sanno quale servizio vendono',
           'servizio_id' in colonne('items'), True)
    _check(r, 'Servizi', 'i testi già decisi hanno la loro tabella',
           {'testo', 'servizio_id'} <= colonne('servizi_testi'), True)
    _check(r, 'Servizi', 'il cliente sa come si chiama nel calendario e con chi si allena',
           {'nome_calendario', 'chiave_sedute', 'compagno_id'} <= colonne('clients'), True)
    _check(r, 'Servizi', "l'abbonamento sa quale servizio rinnova e come scrive il periodo",
           {'servizio_id', 'stile'} <= colonne('ricorrenti'), True)
    _check(r, 'Servizi', 'aggiornare due volte lo stesso database non rompe niente',
           _senza_scoppiare(D._migrate, con), None)
    con.close()

    for testo, atteso in (
            ('Monthly abo: running coaching 13.07.26 – 12.08.26', 'Monthly abo: running coaching'),
            ('Abbonamento 01.01.2026 - 31.01.2026', 'Abbonamento'),
            ('10 Sessions Pack', '10 Sessions Pack')):
        _check(r, 'Servizi', f'«{testo}» senza il periodo', SR.senza_date(testo), atteso)

    for testo, atteso in (
            ('Monthly abo: running coaching 13.07.26 – 12.08.26',
             'Monthly abo: running coaching 13.08.26 – 12.09.26'),
            ('Abbonamento 01.01.2026 - 31.01.2026', 'Abbonamento 01.02.2026 - 28.02.2026'),
            ('Coaching 01/07/26 - 31/07/26', 'Coaching 01/08/26 - 31/08/26'),
            ('10 Sessions Pack', None),
            ('Coaching (August)', None),
            ('Coaching 32.13.26 - 40.99.26', None)):
        _check(r, 'Servizi', f'un mese avanti: «{testo}»', SR.avanza_periodo(testo), atteso)

    _check(r, 'Servizi', "l'anno a due cifre resta a due cifre",
           SR.avanza_periodo('X 01.12.26 - 31.12.26'), 'X 01.01.27 - 31.01.27')
    _check(r, 'Servizi', 'lo stesso servizio si riconosce nonostante il periodo',
           SR.stesso_servizio('Monthly abo', 'Monthly abo 01.07.26 - 31.07.26'), True)
    _check(r, 'Servizi', 'due servizi diversi non si confondono',
           SR.stesso_servizio('10 Sessions Pack', 'Monthly abo'), False)
    _check(r, 'Servizi', 'una descrizione vuota non somiglia a niente',
           SR.stesso_servizio('', 'Monthly abo'), False)

    # --- la scheda del servizio ---------------------------------------------
    from . import language as L
    con = _db_servizi()
    f = {'nome': ' Monthly  abo ', 'prezzo': '110.-', 'ogni_mese': '1', 'con_sedute': '1',
         'sedute': '4', 'passano': '1', 'massimo': '6', 'scadono': '1', 'scadenza_mesi': '3'}
    d = SR.dal_modulo(f)
    _check(r, 'Servizi', 'il nome si ripulisce dagli spazi', d['nome'], 'Monthly abo')
    _check(r, 'Servizi', 'il prezzo si legge come in fattura', d['prezzo_cents'], 11000)
    _check(r, 'Servizi', 'una domanda che non si vede non vale: ogni mese non scade',
           d['scadenza_mesi'], 0)
    _check(r, 'Servizi', "senza sedute non passano e non c'è massimo",
           {k: v for k, v in SR.dal_modulo(dict(f, con_sedute='0')).items()
            if k in ('sedute', 'passano', 'massimo')},
           {'sedute': 0, 'passano': 0, 'massimo': 0})
    _check(r, 'Servizi', 'la scheda giusta non ha niente da ridire', SR.controlla(con, d), [])
    guasti = (
        (dict(f, nome='  '), 'senza nome non si salva'),
        (dict(f, prezzo=''), 'senza prezzo non si salva'),
        (dict(f, prezzo='boh'), 'un prezzo che non si capisce non si salva'),
        (dict(f, sedute='0'), 'zero sedute con «Sì» non si salva'),
        (dict(f, sedute='100'), 'più di 99 sedute non si salva'),
        (dict(f, massimo='3'), 'un massimo sotto le sedute del mese non si salva'),
        (dict(f, ogni_mese='0', scadenza_mesi='61'), 'più di 60 mesi di scadenza non si salva'),
        (dict(f, ogni_mese='0', scadenza_mesi='0'), 'zero mesi di scadenza non si salva'))
    for guasto, desc in guasti:
        _check(r, 'Servizi', desc, len(SR.controlla(con, SR.dal_modulo(guasto))), 1)

    sid = SR.salva(con, d)
    _check(r, 'Servizi', 'salvato, si rilegge uguale',
           {k: SR.uno(con, sid)[k] for k in ('nome', 'prezzo_cents', 'ogni_mese', 'sedute',
                                              'passano', 'massimo', 'attivo')},
           {'nome': 'Monthly abo', 'prezzo_cents': 11000, 'ogni_mese': 1, 'sedute': 4,
            'passano': 1, 'massimo': 6, 'attivo': 1})
    doppio = SR.controlla(con, SR.dal_modulo(dict(f, nome='MONTHLY ABO')))
    _check(r, 'Servizi', 'lo stesso nome, maiuscole a parte, non si ripete', len(doppio), 1)
    _check(r, 'Servizi', 'ma la scheda stessa si risalva col suo nome',
           SR.controlla(con, d, sid), [])
    frasi = {fr for fr, _v in doppio}
    for guasto, _desc in guasti:
        frasi |= {fr for fr, _v in SR.controlla(con, SR.dal_modulo(guasto))}
    _check(r, 'Servizi', 'ogni rimprovero della scheda è tradotto',
           sorted(x for x in frasi if x not in L.TESTI['en'] or x not in L.TESTI['de']), [])

    SR.archivia(con, sid)
    _check(r, 'Servizi', '«Non lo vendo più» lo toglie dai pulsanti',
           [s['id'] for s in SR.tutti(con, solo_attivi=True)], [])
    _check(r, 'Servizi', 'ma resta nella storia', [s['id'] for s in SR.tutti(con)], [sid])
    _check(r, 'Servizi', 'un servizio che non si vende più libera il nome',
           SR.controlla(con, SR.dal_modulo(dict(f, nome='Monthly abo'))), [])
    altro = SR.salva(con, SR.dal_modulo(dict(f, nome='monthly ABO')))
    _check(r, 'Servizi', 'e non si riprende se il nome ora è di un altro',
           (SR.archivia(con, sid, attivo=1), SR.uno(con, sid)['attivo']), (False, 0))
    con.execute('DELETE FROM servizi WHERE id=?', (altro,))
    _check(r, 'Servizi', 'il massimo proposto è le sedute più la metà, per eccesso',
           [SR.massimo_proposto(n) for n in (0, 1, 4, 5)], [0, 2, 6, 8])
    _check(r, 'Servizi', 'ogni mese scrive come un abbonamento, una volta come un pacchetto',
           (SR.modello({'ogni_mese': 1}), SR.modello({'ogni_mese': 0}), SR.modello(None)),
           ('coaching', 'pt', 'pt'))

    # --- la frase che dice in parole cosa hai scritto ------------------------
    mese = {'prezzo_cents': 11000, 'ogni_mese': 1, 'sedute': 4, 'scadenza_mesi': 0,
            'passano': 1, 'massimo': 6}
    _check(r, 'Servizi', 'la frase della scheda dice tutto in parole', SR.riassunto(mese),
           '110.00 CHF al mese. Ogni mese 4 sedute; quelle non usate passano al mese dopo, '
           'ma in un mese non se ne possono avere più di 6.')
    _check(r, 'Servizi', 'e in inglese', SR.riassunto(mese, 'en'),
           '110.00 CHF a month. Every month 4 sessions; unused ones carry over to the next '
           'month, but no more than 6 can be held in a month.')
    pacco = {'prezzo_cents': 180000, 'ogni_mese': 0, 'sedute': 12, 'scadenza_mesi': 6,
             'passano': 0, 'massimo': 0}
    _check(r, 'Servizi', 'un pacchetto che scade, in tedesco', SR.riassunto(pacco, 'de'),
           "1'800.00 CHF, einmalig. 12 Sitzungen, gültig für 6 Monate.")
    _check(r, 'Servizi', 'una seduta sola si scrive al singolare',
           SR.riassunto(dict(pacco, sedute=1, scadenza_mesi=1)),
           "1'800.00 CHF, una volta. 1 seduta, da usare entro 1 mese.")
    _check(r, 'Servizi', 'che si perdono, senza scadenza',
           (SR.riassunto(dict(mese, passano=0)), SR.riassunto(dict(pacco, scadenza_mesi=0))),
           ('110.00 CHF al mese. Ogni mese 4 sedute; quelle non usate si perdono.',
            "1'800.00 CHF, una volta. 12 sedute, senza scadenza."))
    _check(r, 'Servizi', "la riga dell'elenco è corta",
           (SR.riga_breve(pacco), SR.riga_breve(dict(mese, sedute=0)),
            SR.riga_breve(mese), SR.riga_breve(dict(pacco, prezzo_cents=None))),
           ("1'800.00 CHF · 12 sedute", '110.00 CHF al mese',
            '110.00 CHF al mese · 4 sedute al mese', 'manca il prezzo · 12 sedute'))

    # --- quale servizio vende una riga scritta a mano ------------------------
    pt = SR.salva(con, SR.dal_modulo({'nome': 'Personal Training', 'prezzo': '150',
                                      'ogni_mese': '0', 'con_sedute': '1', 'sedute': '1'}))
    pacco12 = SR.salva(con, SR.dal_modulo({
        'nome': '12 Sessions Pack – Personal Training', 'prezzo': "1'800",
        'ogni_mese': '0', 'con_sedute': '1', 'sedute': '12'}))
    _check(r, 'Servizi', 'il nome dentro il testo collega la riga',
           SR.di_testo(con, 'Personal Training 14.09.26'), pt)
    _check(r, 'Servizi', 'con due nomi dentro vince il più lungo',
           SR.di_testo(con, '"12 Sessions Pack – Personal Training"'), pacco12)
    _check(r, 'Servizi', 'maiuscole, virgolette e date non contano',
           SR.di_testo(con, '«PERSONAL TRAINING» 01.09.26 – 30.09.26'), pt)
    _check(r, 'Servizi', 'un nome dentro una parola più lunga non conta',
           SR.di_testo(con, 'Personal Trainings'), None)
    _check(r, 'Servizi', 'una riga libera resta libera', SR.di_testo(con, 'Consulenza'), None)
    _check(r, 'Servizi', 'uno sconto non vende niente',
           SR.di_testo(con, 'Personal Training discount'), None)
    SR.ricorda(con, 'Consulenza 01.10.26', 0)
    _check(r, 'Servizi', '«nessun servizio» deciso una volta si ricorda',
           SR.di_testo(con, 'consulenza'), 0)
    SR.ricorda(con, 'Pacchetto speciale', pacco12)
    _check(r, 'Servizi', 'e anche un servizio scelto a mano',
           SR.di_testo(con, 'Pacchetto speciale'), pacco12)

    con.execute("INSERT INTO clients(id, key, name) VALUES(1, 'giulia', 'Giulia Ferrari')")
    for n, (data, desc, unit, tot) in enumerate((
            ('2026-07-01', '12 Sessions Pack – Personal Training', 15000, 180000),
            ('2026-08-01', 'Personal Training', 15000, 15000),
            ('2026-09-01', '12 Sessions Pack – Personal Training', 15000, 175000),
            ('2026-09-02', 'Consulenza', 5000, 5000)), 1):
        con.execute('INSERT INTO invoices(id, number, client_id, client_name, date, year, '
                    'total_cents) VALUES(?,?,1,?,?,2026,?)',
                    (n, n, 'Giulia Ferrari', data, tot))
        con.execute('INSERT INTO items(invoice_id, pos, qty, description, unit_cents, '
                    "total_cents) VALUES(?,0,'1',?,?,?)", (n, desc, unit, tot))
    _check(r, 'Servizi', 'collegare le righe scritte a mano le decide tutte',
           SR.collega_righe(con), 4)
    _check(r, 'Servizi', 'ognuna col suo servizio, «nessuno» compreso',
           [x['servizio_id'] for x in con.execute('SELECT servizio_id FROM items ORDER BY id')],
           [pacco12, pt, pacco12, 0])
    _check(r, 'Servizi', 'rifarlo non tocca le righe già decise', SR.collega_righe(con), 0)
    _check(r, 'Servizi', "l'ultima riga di un servizio per quel cliente",
           SR.ultima_riga(con, 1, pacco12)['total_cents'], 175000)
    con.execute("UPDATE invoices SET deleted_at='2026-09-03' WHERE id=3")
    _check(r, 'Servizi', 'una fattura nel Cestino non conta',
           SR.ultima_riga(con, 1, pacco12)['total_cents'], 180000)
    _check(r, 'Servizi', 'un servizio fatturato lo sa', SR.fatturato(con, pt), True)
    con.close()

    # --- la pagina: la scheda mostra quello che poi salva ---------------------
    con = _db_servizi()
    sid = SR.salva(con, SR.dal_modulo({
        'nome': 'Monthly abo', 'prezzo': '110.-', 'ogni_mese': '1', 'con_sedute': '1',
        'sedute': '4', 'passano': '1', 'massimo': '6'}))
    v = SR.per_la_pagina(con)[0]
    _check(r, 'Servizi', 'la scheda riceve il prezzo scritto come in fattura',
           (v['prezzo_testo'], v['con_sedute'], v['scadono'], v['fatturato']),
           ('110.-', True, False, False))
    ripreso = {'nome': v['nome'], 'prezzo': v['prezzo_testo'], 'ogni_mese': str(v['ogni_mese']),
               'con_sedute': '1' if v['con_sedute'] else '0', 'sedute': str(v['sedute']),
               'scadono': '1' if v['scadono'] else '0', 'scadenza_mesi': str(v['scadenza_mesi']),
               'passano': str(v['passano']), 'massimo': str(v['massimo'])}
    _check(r, 'Servizi', 'risalvare la scheda così com’è non trova niente da ridire',
           SR.controlla(con, SR.dal_modulo(ripreso), sid), [])
    SR.salva(con, SR.dal_modulo(ripreso), sid)
    _check(r, 'Servizi', 'e non cambia niente',
           {k: SR.uno(con, sid)[k] for k in ('prezzo_cents', 'sedute', 'passano', 'massimo')},
           {'prezzo_cents': 11000, 'sedute': 4, 'passano': 1, 'massimo': 6})
    con.close()

    # --- i pulsanti della nuova fattura --------------------------------------
    con = _db_servizi()
    mese_id = SR.salva(con, SR.dal_modulo({'nome': 'Monthly abo: running coaching',
                                           'prezzo': '110', 'ogni_mese': '1'}))
    pacco_id = SR.salva(con, SR.dal_modulo({'nome': '12 Sessions Pack', 'prezzo': "1'800",
                                            'ogni_mese': '0', 'con_sedute': '1',
                                            'sedute': '12'}))
    mese, pacco = SR.uno(con, mese_id), SR.uno(con, pacco_id)
    con.execute("INSERT INTO clients(id, key, name) VALUES(1, 'giulia', 'Giulia Ferrari'),"
                " (2, 'marco', 'Marco Neri')")
    _check(r, 'Servizi', 'mai fatturato: il nome e il prezzo del servizio',
           {k: SR.proposta(con, 1, pacco)[k]
            for k in ('description', 'qty', 'unit', 'total', 'servizio_id', 'advanced')},
           {'description': '12 Sessions Pack', 'qty': '1', 'unit': "1'800.-", 'total': '',
            'servizio_id': pacco_id, 'advanced': False})
    _check(r, 'Servizi', 'senza cliente scelto, lo stesso',
           SR.proposta(con, None, pacco)['unit'], "1'800.-")
    for n, (cliente, data, qty, desc, unit, tot, sid) in enumerate((
            (1, '2026-08-13', '12', '12 Sessions Pack', 15000, 180000, pacco_id),
            (1, '2026-08-13', '1', 'Monthly abo: running coaching 13.08.26 – 12.09.26',
             10000, 10000, mese_id),
            (2, '2026-07-01', '1', 'Monthly abo: running coaching 01.07.26 – 31.07.26',
             11000, 11000, None)), 1):
        con.execute('INSERT INTO invoices(id, number, client_id, client_name, date, year, '
                    'total_cents) VALUES(?,?,?,?,?,2026,?)', (n, n, cliente, 'x', data, tot))
        con.execute('INSERT INTO items(invoice_id, pos, qty, description, unit_cents, '
                    'total_cents, servizio_id) VALUES(?,0,?,?,?,?,?)',
                    (n, qty, desc, unit, tot, sid))
    p = SR.proposta(con, 1, pacco)
    _check(r, 'Servizi', 'già fatturato: il prezzo dell’ultima riga, per un pacchetto solo',
           (p['description'], p['qty'], p['unit'], p['total']),
           ('12 Sessions Pack', '1', '150.-', "1'800.-"))
    p = SR.proposta(con, 1, mese)
    _check(r, 'Servizi', 'un abbonamento già fatturato riparte dal mese dopo',
           (p['description'], p['unit'], p['advanced']),
           ('Monthly abo: running coaching 13.09.26 – 12.10.26', '100.-', True))
    p = SR.proposta(con, 2, mese)
    _check(r, 'Servizi', 'una riga vecchia senza collegamento si trova ancora per nome',
           (p['description'], p['unit']),
           ('Monthly abo: running coaching 01.08.26 – 31.08.26', '110.-'))
    _check(r, 'Servizi', 'il pulsante collega la riga anche se il testo cambia',
           SR.servizio_della_riga(con, str(pacco_id), 'Pacchetto di Natale'), (pacco_id, True))
    _check(r, 'Servizi', 'una riga svuotata perde il collegamento',
           SR.servizio_della_riga(con, str(pacco_id), '   '), (None, False))
    _check(r, 'Servizi', 'un servizio che non esiste non si scrive',
           SR.servizio_della_riga(con, '999', 'Consulenza'), (None, False))
    _check(r, 'Servizi', 'un id troppo grande per sqlite non si scrive',
           SR.servizio_della_riga(con, '99999999999999999999', 'Consulenza'), (None, False))
    _check(r, 'Servizi', 'scritta a mano, si collega da sola',
           SR.servizio_della_riga(con, '', '12 Sessions Pack 01.10.26'), (pacco_id, False))
    con.close()

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        sorgente = f.read()
    corpo = sorgente[sorgente.index('def _crea_fattura'):]
    corpo = corpo[:corpo.index('\n# ----')]
    _check(r, 'Servizi', 'la nuova fattura scrive il servizio su ogni riga',
           ('servizio_della_riga' in corpo, 'total_cents,servizio_id)' in corpo), (True, True))

    # --- Performance: il fatturato per servizio collegato ---------------------
    from . import stats as ST
    con = _db_servizi()
    pacco = SR.salva(con, SR.dal_modulo({'nome': '10 Sessions Pack', 'prezzo': '2000',
                                         'ogni_mese': '0'}))
    abo = SR.salva(con, SR.dal_modulo({'nome': 'Monthly abo', 'prezzo': '110',
                                       'ogni_mese': '1'}))
    fatture = (
        (1, 'Giulia', 200000, [('Pacchetto di primavera', 205000, pacco),
                               ('Loyalty discount', 5000, None)]),
        (2, 'Marco', 11000, [('Abbonamento (August)', 11000, abo)]),
        (3, 'Marco', 11000, []),               # senza righe: si deduce dall'altra da 110
        (4, 'Sofia', 5000, [('Consulenza', 5000, 0)]),
        (5, 'Sofia', 0, [('Bring a friend', 0, None)]))
    for n, cliente, tot, linee in fatture:
        con.execute('INSERT INTO invoices(id, number, client_name, date, year, total_cents) '
                    'VALUES(?,?,?,?,2026,?)', (n, n, cliente, '2026-03-0%d' % n, tot))
        for pos, (desc, t, sid) in enumerate(linee):
            con.execute('INSERT INTO items(invoice_id, pos, description, total_cents, '
                        'servizio_id) VALUES(?,?,?,?,?)', (n, pos, desc, t, sid))
    con.execute("UPDATE servizi SET nome='Monthly running coaching' WHERE id=?", (abo,))
    _check(r, 'Servizi', 'Performance raggruppa per servizio collegato, col nome di adesso',
           dict(ST.by_service(con, 2026)),
           {'10 Sessions Pack': 200000, 'Monthly running coaching': 22000, ST.ALTRO: 5000})
    _check(r, 'Servizi', 'il servizio di una fattura è il primo collegato fra le righe',
           (SR.primo_della_fattura(con, 1)['nome'], SR.primo_della_fattura(con, 4)),
           ('10 Sessions Pack', None))
    con.close()
    with io.open(os.path.join(base, 'templates', 'performance.html'), encoding='utf-8') as f:
        pagina = f.read()
    _check(r, 'Servizi', 'Performance manda a Servizi per nomi e prezzi',
           (pagina.count("url_for('servizi')"), 'crediti_clienti' in pagina), (2, False))

    # --- «Righe senza servizio» ------------------------------------------------
    from . import righe_servizio as RS
    con = _db_servizi()
    p12 = SR.salva(con, SR.dal_modulo({'nome': '12 Sessions Pack – Personal Training',
                                       'prezzo': "1'800", 'ogni_mese': '0',
                                       'con_sedute': '1', 'sedute': '12'}))
    SR.salva(con, SR.dal_modulo({'nome': '10 Sessions Pack – Personal Training',
                                 'prezzo': "2'000", 'ogni_mese': '0',
                                 'con_sedute': '1', 'sedute': '10'}))
    for n, (data, qty, desc, tot) in enumerate((
            ('2026-01-10', '12', 'Personal Training Pack', 180000),
            ('2026-02-10', '12', 'Personal Training Pack', 180000),
            ('2026-03-10', '1', 'Loyalty discount', 5000),
            ('2026-03-11', '1', 'Consulenza nutrizionale 11.03.26', 9000),
            ('2026-04-11', '1', 'Consulenza nutrizionale 11.04.26', 9500)), 1):
        con.execute('INSERT INTO invoices(id, number, client_name, date, year, total_cents) '
                    "VALUES(?,?,'x',?,2026,?)", (n, n, data, tot))
        con.execute('INSERT INTO items(invoice_id, pos, qty, description, total_cents) '
                    'VALUES(?,0,?,?,?)', (n, qty, desc, tot))
    elementi = RS.da_decidere(con)
    _check(r, 'Servizi', 'un elemento per testo, senza date e senza sconti',
           [(e['testo'], e['righe']) for e in elementi],
           [('Consulenza nutrizionale', 2), ('Personal Training Pack', 2)])
    servizi_tutti = SR.tutti(con)
    pack = next(e for e in elementi if e['chiave'] == 'personal training pack')
    consulenza = next(e for e in elementi if e['chiave'] == 'consulenza nutrizionale')
    _check(r, 'Servizi', 'a parità di parole vince il servizio con le sedute della quantità',
           RS.ipotesi(pack, servizi_tutti), p12)
    _check(r, 'Servizi', 'se nessuna ipotesi convince resta «Scegli…»',
           RS.ipotesi(consulenza, servizi_tutti), None)
    _check(r, 'Servizi', 'il nuovo servizio prende il nome dal testo e il prezzo dall’ultima riga',
           (RS.per_nuovo_servizio(consulenza)['nome'],
            RS.per_nuovo_servizio(consulenza)['prezzo_testo']),
           ('Consulenza nutrizionale', '95.-'))
    _check(r, 'Servizi', 'e le sedute dal pacchetto collegato a quella fattura',
           RS.per_nuovo_servizio(pack, {'pacchetti': [{'fattura_numero': 2, 'crediti': 12}]})['sedute'],
           12)
    _check(r, 'Servizi', '«Fatto» scrive il servizio su tutte le righe di quel testo',
           RS.decidi(con, 'personal training pack', p12), 2)
    RS.decidi(con, 'consulenza nutrizionale', 0)
    _check(r, 'Servizi', 'e poi non resta niente da decidere', RS.quante(con), 0)
    _check(r, 'Servizi', 'la decisione vale anche per le righe future',
           SR.di_testo(con, 'Consulenza nutrizionale 01.10.26'), 0)
    con.close()


def _db_servizi():
    """Un database in memoria con lo schema vero, colonne nuove comprese.

    Le prove dei servizi e delle sedute non si scrivono le tabelle a mano: un
    database finto con tre colonne passa le prove e si rompe sui dati veri."""
    import sqlite3
    from . import db as D
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(D.SCHEMA)
    D._migrate(con)
    return con


def _test_lingua(r):
    """Le tre lingue.

    Il controllo che conta e' l'ultimo: ogni voce di menu deve esistere in
    tutte le lingue. Senza, il giorno che si aggiunge una pagina il menu esce
    metA' in italiano e meta' in tedesco, e nessuno se ne accorge finche' non
    lo vede un utente.
    """
    from . import language as L
    from . import menu as M

    _check(r, 'Lingua', 'le lingue sono tre', L.CODICI, ('it', 'en', 'de'))
    _check(r, 'Lingua', "un codice che non esiste torna all'italiano",
           L.normalizza('klingon'), 'it')
    _check(r, 'Lingua', 'senza lingua si resta in italiano',
           L.t('Fatture', None), 'Fatture')
    _check(r, 'Lingua', 'una frase mai tradotta resta in italiano invece di sparire',
           L.t('Frase che nessuno ha tradotto', 'de'), 'Frase che nessuno ha tradotto')
    _check(r, 'Lingua', 'tradurre in inglese funziona', L.t('Fatture', 'en'), 'Invoices')
    _check(r, 'Lingua', 'tradurre in tedesco funziona', L.t('Fatture', 'de'), 'Rechnungen')

    # nessuna voce di menu senza traduzione, in nessuna lingua
    da_tradurre = {etichetta for _t, voci in M.GRUPPI for _k, etichetta, _i, _a in voci}
    da_tradurre |= {titolo for titolo, _v in M.GRUPPI if titolo}
    da_tradurre.add(M.PRIMI_PASSI[1])
    for cod in ('en', 'de'):
        _check(r, 'Lingua', 'ogni voce del menu esiste in %s' % cod,
               sorted(f for f in da_tradurre if f not in L.TESTI[cod]), [])
    _check(r, 'Lingua', 'inglese e tedesco conoscono le stesse frasi',
           L.mancanti('en') + L.mancanti('de'), [])

    # Ogni frase che una pagina chiede con _('...') deve stare nei dizionari.
    # E' il controllo che fa crescere la traduzione da sola: chi domani scrive
    # _('Qualcosa di nuovo') e si scorda i dizionari trova subito il collaudo
    # rosso, invece di scoprirlo un utente tedesco.
    _check(r, 'Lingua', 'ogni frase chiesta dalle pagine sta nei dizionari',
           _frasi_senza_traduzione(L), [])

    # Meta' dei messaggi non sta nelle pagine ma nel codice: avvisa('...') e
    # lng.t('...'). Se una di quelle frasi non e' nei dizionari non succede
    # niente di rumoroso — esce in italiano in mezzo all'inglese — quindi la
    # si guarda qui insieme alle altre.
    _check(r, 'Lingua', 'ogni frase chiesta dal codice sta nei dizionari',
           _frasi_codice_senza_traduzione(L), [])

    # ...e le frasi dei primi passi, che non sono ne' l'una ne' l'altra cosa:
    # stanno in welcome.py come dati e le traduce la pagina che le mostra.
    _check(r, 'Lingua', 'ogni frase dei primi passi sta nei dizionari',
           _frasi_dei_primi_passi_senza_traduzione(L), [])

    # Certi moduli non sanno che lingua e' scelta e restituiscono la frase
    # come chiave, da tradurre a chi la mostra. Quelle chiavi non compaiono
    # dentro una chiamata, quindi il controllo qui sopra non le vede: si
    # chiamano le funzioni e si guarda cosa tornano davvero.
    _check(r, 'Lingua', 'anche le frasi che i moduli restituiscono sono tradotte',
           _frasi_restituite_senza_traduzione(L), [])

    # --- i documenti: seconda lingua, altre regole ---
    _check(r, 'Lingua', 'inglese e tedesco conoscono le stesse frasi dei documenti',
           L.mancanti_doc('en') + L.mancanti_doc('de'), [])
    # Un cliente senza lingua scritta NON deve ricevere documenti in italiano:
    # le fatture di quest'app sono sempre uscite in inglese, e un ripiego che
    # cambia la lingua delle fatture gia' spedite non e' un ripiego.
    _check(r, 'Lingua', 'un cliente senza lingua riceve documenti in inglese',
           L.normalizza_doc(None), 'en')
    _check(r, 'Lingua', 'e anche uno con una lingua che non esiste',
           L.normalizza_doc('klingon'), 'en')
    _check(r, 'Lingua', 'la fattura in inglese e\' quella di sempre',
           L.t_doc('QUANTITÀ', 'en'), 'QUANTITY')
    _check(r, 'Lingua', 'la fattura in tedesco parla tedesco',
           L.t_doc('QUANTITÀ', 'de'), 'MENGE')
    # Nei documenti si parla al CLIENTE, e con un cliente si usa il Lei: la
    # regola del tu vale per l'app, non per quello che leggono i suoi clienti.
    _check(r, 'Lingua', 'il tedesco dei documenti da\' del Lei, non del tu',
           _documenti_col_tu(L), [])
    # Le etichette che docgen riscrive nel modello Word devono esistere
    # davvero: se qualcuno rinomina una chiave, la fattura tedesca esce con
    # una colonna in inglese e nessuno se ne accorge.
    _check(r, 'Lingua', 'ogni etichetta del modello Word ha la sua traduzione',
           _etichette_word_senza_traduzione(L), [])

    # I segnaposti sono la parte fragile: {n} che sparisce dalla traduzione fa
    # sparire un numero dalla pagina, {n} scritto storto fa saltare la pagina
    # con un errore. Meglio accorgersene qui.
    _check(r, 'Lingua', 'le traduzioni tengono gli stessi segnaposti',
           _segnaposti_sbagliati(L), [])

    # Le quattro frasi che scrive il browser gliele passa nuova.html: se una
    # non parte, l'inglese vede una scritta italiana in mezzo al modulo.
    _check(r, 'Lingua', 'la pagina passa al browser tutte le frasi che gli servono',
           _frasi_js_non_passate(), [])

    # Il tedesco ha due modi di rivolgersi a chi legge e non si possono
    # mescolare: meta' pagina che da' del Lei e meta' del tu suona sciatta.
    # L'italiano da' del tu, quindi il tedesco fa lo stesso. Se un domani
    # questo controllo si lamenta di un «sie» che vuol dire «loro», si
    # riscrive la frase: e' piu' facile che tenere due registri in testa.
    _check(r, 'Lingua', 'il tedesco da\' del tu dappertutto, come l\'italiano',
           _tedesco_col_lei(L), [])

    # La rete piu' importante: le altre guardie controllano che ogni _('...')
    # abbia la sua traduzione, ma nessuna si accorgeva di una pagina che
    # _() non lo chiama proprio. Sette pagine intere erano rimaste indietro.
    _check(r, 'Lingua', 'nessuna scritta italiana e\' rimasta fuori da _()',
           _testo_non_tradotto(), [])

    # Python accetta due volte la stessa chiave in un dizionario e tiene
    # l'ultima, senza dire niente: la prima traduzione sparirebbe in silenzio.
    _check(r, 'Lingua', 'nessuna frase compare due volte nei dizionari',
           _chiavi_doppie(), [])

    # la pagina Verifica scrive il nome della famiglia con _(cat): nessuna
    # guardia sui template lo vede, perche' li' dentro c'e' una variabile
    _check(r, 'Lingua', 'ogni famiglia di collaudi ha il nome nelle tre lingue',
           _famiglie_senza_traduzione(L, r), [])


def _pagina_dice_gia_pagata():
    """La pagina Banca avverte quando la fattura era gia' spuntata a mano."""
    for pagina, sorgente in _sorgenti_pagine():
        if pagina != 'bank.html':
            continue
        pulito = ' '.join(sorgente.split())
        return 'not c.aperta' in pulito and 'già segnata pagata' in pulito
    return False


def _documenti_col_tu(L):
    """Le frasi di documento che danno del tu al cliente."""
    tu = re.compile(r'\b([Dd]u|[Dd]ein\w*|[Dd]ir|[Dd]ich)\b')
    return sorted(v for v in L.DOCUMENTI['de'].values() if tu.search(v))


def _etichette_word_senza_traduzione(L):
    """Le etichette del modello Word che i dizionari non conoscono."""
    from . import docgen
    return sorted(c for c in docgen.ETICHETTE.values() if c not in L.DOCUMENTI['en'])


def _tedesco_col_lei(L):
    """Le frasi tedesche che danno del Lei invece che del tu.

    Il tedesco scrive «Sie» sia per il Lei sia per «essa»: «Sie liest die
    Datei» vuol dire «la app la legge». Quel «Sie» sta sempre a inizio frase,
    perche' e' soggetto; il «Lei» di cortesia capita quasi sempre in mezzo.
    Quindi «Sie» e «Ihr» si guardano solo a frase iniziata, mentre «Ihre»,
    «Ihnen» e compagnia sono possessivi di cortesia e valgono ovunque.
    """
    ovunque = re.compile(r'\b(Ihnen|Ihre|Ihrem|Ihren|Ihrer|Ihres)\b')
    in_mezzo = re.compile(r'(?<![.!?:]\s)(?<!^)\b(Sie|Ihr)\b')
    fuori = []
    for v in L.TESTI['de'].values():
        if ovunque.search(v) or any(in_mezzo.search(f.strip())
                                    for f in re.split(r'(?<=[.!?:])\s+', v)[1:] or []):
            fuori.append(v)
        elif in_mezzo.search(re.split(r'(?<=[.!?:])\s+', v)[0]):
            fuori.append(v)
    return sorted(fuori)


def _frasi_codice_senza_traduzione(L):
    """[(file, frase)] per ogni avvisa('...') o lng.t('...') mai tradotto."""
    import ast
    import glob
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # i file di collaudo no: dentro ci sono frasi finte apposta, tipo quella
    # che serve a provare che una frase non tradotta esce lo stesso in italiano
    perc = [os.path.join(base, 'app.py')] + [
        p for p in sorted(glob.glob(os.path.join(base, 'core', '*.py')))
        if 'selftest' not in os.path.basename(p)]
    fuori = []
    for p in perc:
        with io.open(p, encoding='utf-8') as f:
            sorgente = f.read()
        for nodo in ast.walk(ast.parse(sorgente)):
            if not isinstance(nodo, ast.Call) or not nodo.args:
                continue
            nome = getattr(nodo.func, 'attr', None) or getattr(nodo.func, 'id', '')
            if nome not in ('avvisa', 't'):
                continue
            for arg in nodo.args[:2]:            # avvisa(frase) e lng.t(frase, lingua)
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and len(arg.value) > 2 and arg.value not in L.TESTI['en'] \
                        and arg.value not in ('en', 'de', 'it'):
                    fuori.append((os.path.basename(p), arg.value))
                break
    return sorted(set(fuori))


def _frasi_dei_primi_passi_senza_traduzione(L):
    """[(passo, campo, lingua)] delle frasi dei primi passi mai tradotte.

    Le due guardie qui sopra hanno un punto cieco in comune. Le frasi dei
    primi passi non stanno in una pagina — stanno in welcome.py come dati —
    e non passano da avvisa() ne' da t(): a tradurle e' la pagina, con
    {{ _(p.titolo) }}, a tempo di esecuzione. Cosi' una frase nuova esce in
    italiano dentro un'app in tedesco, sulla prima pagina che un utente nuovo
    vede, e nessun collaudo dice niente.

    E' successo davvero, aggiungendo il passo del bollettino QR: tre frasi
    nuove, sei traduzioni mancanti, e i controlli tutti verdi.
    """
    import sqlite3
    from . import welcome as B
    from .db import DEFAULT_SETTINGS

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(
        'CREATE TABLE clients(id INTEGER PRIMARY KEY, archived INTEGER DEFAULT 0);'
        'CREATE TABLE invoices(id INTEGER PRIMARY KEY, deleted_at TEXT);'
        'CREATE TABLE servizi(id INTEGER PRIMARY KEY, nome TEXT);')
    try:
        passi = B.passi(con, dict(DEFAULT_SETTINGS))
    finally:
        con.close()
    fuori = []
    for passo in passi:
        for campo in ('titolo', 'perche', 'bottone'):
            frase = passo.get(campo)
            if frase and any(frase not in L.TESTI[cod] for cod in ('en', 'de')):
                fuori.append((passo['chiave'], campo))
    return sorted(set(fuori))


def _frasi_restituite_senza_traduzione(L):
    """Le chiavi che i moduli danno indietro e nessuno ha tradotto."""
    from . import branding
    from . import bank as B
    from . import mailer as M
    # i nomi dei due modelli di mail: la pagina li scrive con _(nome), quindi
    # nessuna guardia sui template puo' vederli
    frasi = [nome for _chiave, nome in M.MODELLI]
    for dati in (b'', b'non e\' un png', b'\x89PNG' + b'x' * branding.PESO_MAX):
        esito = branding.salva(dati)
        if esito:
            frasi.append(esito[0])
    # Le spiegazioni della pagina Banca si raccolgono DA SOLE: ogni costante
    # che si chiama PERCHE_* entra qui senza che nessuno debba ricordarsene.
    # Prima erano elencate a mano, e il 06.09.2026 ne e' bastata una nuova
    # (PERCHE_RIFERIMENTO_RIPETUTO) per scoprire che una guardia che protegge
    # solo cio' che qualcuno ha elencato non protegge niente: la frase nuova
    # non era tradotta e il collaudo era verde lo stesso.
    frasi += [getattr(B, x) for x in dir(B) if x.startswith('PERCHE_')]
    frasi.append(B.CARTELLA_ASSENTE)
    # stessa storia per i motivi per cui la QR-fattura non si puo' fare: sono
    # frasi che finiscono sotto gli occhi di chi usa l'app, ma passano per una
    # variabile e nessun raccoglitore che guardi i «_()» puo' vederle
    from . import qrbill as _qr
    frasi += [getattr(_qr, x) for x in dir(_qr)
              if x.startswith(('SENZA_', 'PREFISSO_'))]
    # i motivi per cui un compleanno scritto a mano non si capisce: stessa
    # strada, costanti COMPLEANNO_* raccolte da sole
    import importlib as _il
    try:
        _bd = _il.import_module('.birthdays', __package__)
        frasi += [getattr(_bd, x) for x in dir(_bd) if x.startswith('COMPLEANNO_')]
    except ImportError:
        pass        # manca il modulo: lo dice da sola _test_compleanni, in rosso
    # finisce nel database e la pagina lo traduce quando lo mostra
    from . import db as _db
    frasi.append(_db.MOTIVO_RICOSTRUITO)
    # le due etichette che l'app mette da sé quando le regole non riconoscono
    # niente: i nomi veri dei servizi li scrive l'utente e non si traducono
    from . import stats as _st
    frasi += [_st.ALTRO, _st.NON_DETTAGLIATO]
    # il perche' di una copia: la sigla sta nel nome del file, le parole no
    from . import backup as _bk
    frasi += [_bk.motivo_in_parole(sigla) for sigla in _bk.MOTIVI]
    frasi.append(_bk.motivo_in_parole(_bk.PRIMA_DI_ELIMINARE + '7').replace('7', '{n}'))
    return sorted(f for f in frasi if f not in L.TESTI['en'])


def _sorgenti_pagine():
    """Il testo di tutti i template, uno per uno."""
    import glob
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'templates')
    for perc in sorted(glob.glob(os.path.join(base, '*.html'))):
        with io.open(perc, encoding='utf-8') as f:
            yield os.path.basename(perc), f.read()


def _frasi_senza_traduzione(L):
    """[(pagina, frase)] per ogni _('...') che i dizionari non conoscono."""
    # solo le frasi scritte per esteso: _(variabile) lo si controlla altrove
    quali = re.compile(r"""_\(\s*('([^']*)'|"([^"]*)")""")
    fuori = []
    for pagina, testo in _sorgenti_pagine():
        for pezzo in quali.finditer(testo):
            frase = pezzo.group(2) if pezzo.group(2) is not None else pezzo.group(3)
            if frase and frase not in L.TESTI['en']:
                fuori.append((pagina, frase))
    return sorted(set(fuori))


# Le pagine sono scritte in italiano e ogni parola che l'utente legge deve
# passare per _(). Restano fuori solo queste: nomi propri, esempi buoni in
# ogni lingua e il nome vero di un file.
TESTO_CHE_PUO_RESTARE = frozenset((
    'Anna',                          # un nome d'esempio
    '8000 Zürich',                   # un indirizzo svizzero d'esempio
    'https://calendar.google.com/calendar/ical/.../basic.ics',
    'vs',                            # si scrive cosi' in tutte e tre
    'CHE-123.456.789',               # la forma di un numero d'impresa svizzero
    'CH00 0000 0000 0000 0000 0',    # la forma di un IBAN svizzero
))
# «IBAN» non e' italiano ne' inglese ne' tedesco: e' la stessa parola nelle tre
# lingue, e sulla fattura vera esce cosi' anche in tedesco. Tradurla vorrebbe
# dire far dire all'anteprima una cosa che il documento non dice.
PAROLE_CHE_PUO_RESTARE = frozenset(('CHF', 'IBAN', 'KB', 'MB', 'PDF', 'ok'))

_ATTRIBUTI_LETTI = re.compile(r'\b(?:placeholder|title|alt)\s*=\s*"([^"]*)"')
_FINESTRELLE = re.compile(r"\b(?:confirm|alert)\(\s*'([^']*)'")
_SOLO_SEGNAPOSTI = re.compile(r'^(?:\{\w+\}|\s|,)+$')
_PAROLA = re.compile(r'[A-Za-zÀ-ÿ]{2,}')
_ETICHETTA_PALLINO = re.compile(r"""pallino\(\s*'[^']*'\s*,\s*('([^']*)'|"([^"]*)")""")


def _pagina_come_la_legge_chi_guarda(testo):
    """La pagina senza le parti che l'utente non vede: commenti, codice,
    e tutto quello che sta dentro {{ }} o {% %} — li' dentro ci sono i dati
    e le _() gia' tradotte."""
    testo = re.sub(r'\{#.*?#\}', ' ', testo, flags=re.S)
    testo = re.sub(r'<script\b.*?</script>', ' ', testo, flags=re.S | re.I)
    testo = re.sub(r'<style\b.*?</style>', ' ', testo, flags=re.S | re.I)
    testo = re.sub(r'\{%.*?%\}', '\n', testo, flags=re.S)
    return re.sub(r'\{\{.*?\}\}', ' ', testo, flags=re.S)


def _frammenti_visibili(testo):
    """Ogni pezzo di scritta che finisce sotto gli occhi di chi usa l'app."""
    ripulito = _pagina_come_la_legge_chi_guarda(testo)
    for pezzo in _ATTRIBUTI_LETTI.findall(ripulito):
        yield pezzo
    # le finestrelle «sei sicuro?» stanno dentro il codice, che qui sopra
    # e' stato buttato via: si ripescano dal testo di partenza
    for pezzo in _FINESTRELLE.findall(re.sub(r'\{\{.*?\}\}', ' ', testo, flags=re.S)):
        yield pezzo
    # l'etichetta del pallino colorato sta dentro {{ }}, dove le regole qui
    # sopra non guardano: e' pero' una scritta che si legge passandoci sopra
    for pezzo in _ETICHETTA_PALLINO.finditer(testo):
        yield pezzo.group(2) if pezzo.group(2) is not None else pezzo.group(3)
    for riga in re.sub(r'<[^>]*>', '\n', ripulito).split('\n'):
        yield riga


def _testo_non_tradotto():
    """[(pagina, scritta)] per ogni frase che la pagina mostra senza _()."""
    fuori = []
    for pagina, testo in _sorgenti_pagine():
        for pezzo in _frammenti_visibili(testo):
            pezzo = ' '.join(pezzo.split())
            if not pezzo or pezzo in TESTO_CHE_PUO_RESTARE:
                continue
            if _SOLO_SEGNAPOSTI.match(pezzo):
                continue            # <code>{mese}</code>: si scrive cosi' e basta
            if [p for p in _PAROLA.findall(pezzo) if p not in PAROLE_CHE_PUO_RESTARE]:
                fuori.append((pagina, pezzo[:70]))
    return sorted(set(fuori))


def _famiglie_senza_traduzione(L, risultati):
    """Le categorie che la pagina Verifica mostrerebbe ancora in italiano."""
    return sorted({cat for cat, _d, _o, _t in risultati if cat not in L.TESTI['en']})


def _chiavi_doppie():
    """[(riga, frase)] per ogni chiave scritta due volte in language.py."""
    import ast
    import collections
    perc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'language.py')
    with io.open(perc, encoding='utf-8') as f:
        albero = ast.parse(f.read())
    fuori = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Dict):
            continue
        viste = collections.Counter(
            k.value for k in nodo.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str))
        fuori += [(nodo.lineno, frase) for frase, n in viste.items() if n > 1]
    return sorted(fuori)


def _segnaposti_sbagliati(L):
    """[(lingua, frase)] dove la traduzione non ha gli stessi {segnaposti}."""
    quali = re.compile(r'\{(\w+)\}')
    fuori = []
    for cod in ('en', 'de'):
        for frase, tradotta in L.TESTI[cod].items():
            if set(quali.findall(frase)) != set(quali.findall(tradotta)):
                fuori.append((cod, frase))
    return sorted(fuori)


def _frasi_js_non_passate():
    """Le chiavi che app.js usa e nuova.html non manda (o viceversa)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'static', 'app.js'), encoding='utf-8') as f:
        js = f.read()
    with io.open(os.path.join(base, 'templates', 'new_invoice.html'), encoding='utf-8') as f:
        pagina = f.read()
    usate = set(re.findall(r'\bT\.(\w+)', js))
    passate = set(re.findall(r'^\s*(\w+):\s*\{\{ _\(', pagina, re.M))
    return sorted(usate ^ passate)



def _db_fatture_finto(righe):
    """Un database in memoria con le sole colonne che il «Da fare» guarda."""
    import sqlite3
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(
        'CREATE TABLE invoices(id INTEGER PRIMARY KEY, number INTEGER, client_name TEXT,'
        ' date TEXT, total_cents INTEGER, status TEXT, paid_at TEXT, deleted_at TEXT,'
        ' year INTEGER, sent_at TEXT, source TEXT, client_id INTEGER,'
        ' ricorrente_id INTEGER, periodo TEXT DEFAULT "", invio_saltato TEXT);'
        'CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);'
        # senza queste due il «Da fare» inciampava sugli abbonamenti e tirava
        # avanti in silenzio: sei prove passavano con quel pezzo mai eseguito
        'CREATE TABLE clients(id INTEGER PRIMARY KEY, name TEXT, lingua TEXT,'
        ' archived INTEGER DEFAULT 0);'
        'CREATE TABLE ricorrenti(id INTEGER PRIMARY KEY, client_id INTEGER,'
        ' descrizione TEXT, importo_cents INTEGER, giorno INTEGER DEFAULT 1,'
        ' dal TEXT, attiva INTEGER DEFAULT 1, creata_il TEXT, servizio_id INTEGER,'
        ' stile TEXT DEFAULT "");'
        'CREATE TABLE ricorrenti_saltati(ricorrente_id INTEGER, periodo TEXT,'
        ' quando TEXT, PRIMARY KEY (ricorrente_id, periodo));')
    for i, r in enumerate(righe, 1):
        con.execute('INSERT INTO invoices(id, number, client_name, date, total_cents, status,'
                    ' paid_at, deleted_at, year, sent_at, source, invio_saltato)'
                    ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (i, i, r.get('cliente', 'X'), r['data'], r.get('cents', 10000),
                     r.get('stato', 'emessa'), r.get('paid_at'), r.get('deleted_at'),
                     int(r['data'][:4]), r.get('sent_at'), r.get('source', 'app'),
                     r.get('invio_saltato')))
    return con


def _test_da_fare(r):
    """La lista «Da fare» della Dashboard.

    Prima la Dashboard mostrava nove riquadri dello stesso peso, e la cosa da
    fare andava cercata. Adesso e' una lista sola, e ogni voce e' un'azione. Il
    punto delicato e' che il numero deve corrispondere a quello che si vede
    cliccando: un contatore che dice 6 e apre una pagina con 3 righe fa perdere
    fiducia in tutti gli altri numeri della pagina.
    """
    import datetime
    from . import overview as C

    oggi = datetime.date.today()
    ieri = (oggi - datetime.timedelta(days=1)).isoformat()
    vecchia = (oggi - datetime.timedelta(days=200)).isoformat()

    def voce(cose, chiave):
        return next((c for c in cose if c['chiave'] == chiave), None)

    # --- niente da fare: la lista e' vuota, e va bene cosi' ---
    con = _db_fatture_finto([{'data': ieri, 'stato': 'pagata', 'paid_at': ieri,
                              'sent_at': ieri}])
    vuoto = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    _check(r, 'Da fare', 'tutto a posto: nessuna voce', vuoto, [])

    # --- la copia fuori dal Mac ------------------------------------------
    # E' l'unica rete di sicurezza che, se cede, non lascia niente da salvare.
    # Prima stava solo nella pagina dei Controlli — che dalla barra e' uscita,
    # quindi da qui in avanti deve farsi vedere dove uno guarda ogni giorno.
    import tempfile, time
    cartella = tempfile.mkdtemp()
    _check(r, 'Da fare', 'senza nessuna copia in giro, lo dice',
           bool(voce(C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()},
                               None, cartella), 'backup')), True)

    zip_vecchio = os.path.join(cartella, 'fatture-app-20260101-000000.zip')
    with io.open(zip_vecchio, 'wb') as f:
        f.write(b'PK')
    quando = time.time() - 9 * 86400
    os.utime(zip_vecchio, (quando, quando))
    v = voce(C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()},
                       None, cartella), 'backup')
    _check(r, 'Da fare', 'una copia di nove giorni fa e\' vecchia, e si dice di quanto',
           (bool(v), '9' in (v or {}).get('dettaglio', '')), (True, True))

    zip_fresco = os.path.join(cartella, 'fatture-app-20260909-000000.zip')
    with io.open(zip_fresco, 'wb') as f:
        f.write(b'PK')
    _check(r, 'Da fare', 'una copia di oggi non disturba nessuno',
           voce(C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()},
                          None, cartella), 'backup'), None)
    _check(r, 'Da fare', 'e senza dire dove sono le copie non si allarma nessuno',
           voce(C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()},
                          None, None), 'backup'), None)

    # --- da quanto aspetta una fattura ------------------------------------
    # Il numero che finisce in rosso nell'elenco delle fatture. Chi decide se
    # una e' in ritardo resta «incassi_mancanti»; qui si conta soltanto, e si
    # conta sui giorni veri.
    finte = [{'id': 1, 'date': (oggi - datetime.timedelta(days=73)).isoformat()},
             {'id': 2, 'date': (oggi - datetime.timedelta(days=1)).isoformat()},
             {'id': 3, 'date': 'non-una-data'},
             {'id': 4, 'date': None}]
    _check(r, 'Da fare', 'conta i giorni solo per quelle in ritardo',
           C.ferme_da(finte, {1}, oggi), {1: 73})
    _check(r, 'Da fare', 'una fattura non in ritardo non compare',
           C.ferme_da(finte, set(), oggi), {})
    _check(r, 'Da fare', 'di ieri e\' un giorno, non zero',
           C.ferme_da(finte, {2}, oggi), {2: 1})
    _check(r, 'Da fare', 'una data storta non fa saltare l\'elenco delle fatture',
           _senza_scoppiare(C.ferme_da, finte, {1, 3, 4}, oggi), {1: 73})
    for f_ in (zip_vecchio, zip_fresco):
        os.remove(f_)
    os.rmdir(cartella)

    # --- il numero e' quello delle fatture aperte, non quello della banca ---
    con = _db_fatture_finto([
        {'data': ieri, 'stato': 'emessa', 'cents': 100000, 'sent_at': ieri},
        {'data': ieri, 'stato': 'emessa', 'cents': 20000, 'sent_at': ieri},
        # pagata ma senza riscontro in banca: NON e' una cosa da fare
        {'data': ieri, 'stato': 'pagata', 'cents': 500000, 'sent_at': ieri},
    ])
    cose = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    inc = voce(cose, 'incassare')
    _check(r, 'Da fare', 'conta le fatture aperte, non quelle senza riscontro in banca',
           inc['quante'], 2)
    _check(r, 'Da fare', "l'importo e' la somma di quelle aperte", inc['importo'], 120000)
    _check(r, 'Da fare', 'il link porta esattamente a quelle contate',
           inc['link'], ('fatture', {'stato': 'emessa', 'anno': ''}))
    _check(r, 'Da fare', 'fatture recenti: in attesa, non in ritardo',
           inc['urgenza'], C.ATTESA)

    # --- gli abbonamenti scaduti arrivano fin sulla Dashboard ---
    con = _db_fatture_finto([{'data': ieri, 'stato': 'pagata', 'paid_at': ieri,
                              'sent_at': ieri}])
    con.execute("INSERT INTO clients(id, name, lingua, archived) "
                "VALUES(1, 'Erika Von Arx', 'en', 0)")
    con.execute("INSERT INTO ricorrenti(id, client_id, descrizione, importo_cents, "
                "giorno, dal, attiva) VALUES(1, 1, 'Personal training', 11000, 1, ?, 1)",
                ('%04d-%02d' % (oggi.year, oggi.month),))
    cose = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    ab = voce(cose, 'abbonamenti')
    _check(r, 'Da fare', "l'abbonamento scaduto compare in Dashboard",
           (ab is not None) and ab['quante'], 1)
    _check(r, 'Da fare', "e porta l'importo che si andra' a fatturare",
           ab['importo'], 11000)
    _check(r, 'Da fare', 'il link porta alla pagina degli abbonamenti',
           ab['link'], ('abbonamenti', {}))
    # una fattura fatta A MANO quel mese, senza periodo addosso: l'app non puo'
    # saperlo dai periodi, ma lo vede dalla data e AVVERTE. Non blocca: due
    # fatture nello stesso mese possono starci, non decide lei.
    con.execute("INSERT INTO invoices(id, number, client_name, client_id, date, "
                "total_cents, status, year, source) "
                "VALUES(98, 77, 'Erika Von Arx', 1, ?, 11000, 'pagata', ?, 'app')",
                (oggi.isoformat(), oggi.year))
    from . import recurring as _ric
    coda = _ric.da_fare(con)
    _check(r, 'Da fare', 'avverte se quel mese il cliente ha già una fattura a mano',
           (len(coda), coda[0]['gia_a_mano'] if coda else None), (1, 77))

    # fatturato DALL'abbonamento: la voce sparisce, non resta a chiedere per sempre
    con.execute("INSERT INTO invoices(id, number, client_name, client_id, date, "
                "total_cents, status, year, source, ricorrente_id, periodo) "
                "VALUES(99, 99, 'Erika Von Arx', 1, ?, 11000, 'pagata', ?, 'app', 1, ?)",
                (oggi.isoformat(), oggi.year, '%04d-%02d' % (oggi.year, oggi.month)))
    cose = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    _check(r, 'Da fare', 'fatturato quel mese, la voce sparisce',
           voce(cose, 'abbonamenti'), None)

    # --- una vecchia, con l'estratto aggiornato: quella e' in ritardo ---
    con = _db_fatture_finto([{'data': vecchia, 'stato': 'emessa', 'cents': 30000,
                              'sent_at': vecchia}])
    cose = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    _check(r, 'Da fare', 'ferma da mesi con estratto aggiornato: in ritardo',
           voce(cose, 'incassare')['urgenza'], C.RITARDO)

    # --- senza estratto non si accusa nessuno di ritardo ---
    con = _db_fatture_finto([{'data': vecchia, 'stato': 'emessa', 'cents': 30000,
                              'sent_at': vecchia}])
    cose = C.da_fare(con, {'banca_ultimo_estratto': ''}, None)
    _check(r, 'Da fare', 'senza estratto nessuna accusa di ritardo',
           voce(cose, 'incassare')['urgenza'], C.ATTESA)
    _check(r, 'Da fare', "senza estratto compare 'caricane uno'",
           voce(cose, 'estratto') is not None, True)

    # --- fatta con l'app e mai spedita ---
    con = _db_fatture_finto([{'data': oggi.isoformat(), 'stato': 'pagata',
                              'paid_at': oggi.isoformat(), 'source': 'app'}])
    cose = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    _check(r, 'Da fare', 'una fattura mai spedita si fa notare',
           voce(cose, 'spedire')['quante'], 1)
    # una storica importata non e' "da spedire": non e' mai partita dall'app
    con = _db_fatture_finto([{'data': oggi.isoformat(), 'stato': 'pagata',
                              'paid_at': oggi.isoformat(), 'source': 'import'}])
    cose = C.da_fare(con, {'banca_ultimo_estratto': oggi.isoformat()}, None)
    _check(r, 'Da fare', 'una fattura storica non conta come da spedire',
           voce(cose, 'spedire'), None)

    # --- l'estratto vecchio ---
    _check(r, 'Da fare', 'estratto di ieri: non si dice niente',
           C._estratto_vecchio(ieri), '')
    _check(r, 'Da fare', 'estratto di 200 giorni fa: si dice',
           '200 giorni fa' in C._estratto_vecchio(vecchia), True)
    _check(r, 'Da fare', 'una data storta non fa saltare la Dashboard',
           C._estratto_vecchio('non-una-data'), '')

    # --- i crediti non devono poter spegnere la Dashboard ---
    _check(r, 'Da fare', 'senza registro crediti, nessuna voce e nessun errore',
           C._crediti_finiti(None), [])
    _check(r, 'Da fare', 'un registro incomprensibile non fa saltare niente',
           C._crediti_finiti('non-un-registro'), [])

    _check(r, 'Da fare', 'senza registro, nessuna seduta in più e nessun errore',
           (_senza_scoppiare(C._sedute_in_piu, None),
            _senza_scoppiare(C._sedute_in_piu, 'non-un-registro')), ([], []))
    reg_piu = {'pacchetti': [], 'esclusi': [], 'mensili': [
        {'id': 'SOF-M01', 'chiavi': ['sofia'], 'cliente': 'Sofia', 'dal': ieri,
         'al': oggi.isoformat(), 'in_piu': 2, 'sessioni': []}]}
    cose = C.da_fare(_db_fatture_finto([]), {'banca_ultimo_estratto': oggi.isoformat()}, reg_piu)
    _check(r, 'Da fare', 'le sedute in più del mese si fanno notare, senza urgenza',
           ((voce(cose, 'in_piu') or {}).get('quante'), (voce(cose, 'in_piu') or {}).get('urgenza')),
           (2, C.ATTESA))


def _test_sedute_dai_servizi(r):
    """Le sedute arrivano dalla riga del servizio venduto, non dall'importo.

    Prima una fattura diventava un pacchetto se il totale era uno dei prezzi
    scritti a mano per quel cliente: bastava uno sconto per perdere le sedute.
    Adesso le porta il servizio: quante sedute, a che prezzo, fino a quando."""
    from decimal import Decimal
    import datetime
    from . import language as L
    from . import services as SR
    from . import sessions as S
    cat = 'Sedute dai servizi'

    PACCHETTO = {'id': 7, 'nome': '12 Sessions Pack', 'prezzo_cents': 180000, 'ogni_mese': 0,
                 'sedute': 12, 'scadenza_mesi': 6, 'passano': 0, 'massimo': 0}
    SENZA_PREZZO = dict(PACCHETTO, id=8, prezzo_cents=None, scadenza_mesi=0)
    frasi = []

    # --- quante sedute compra una riga ---
    for qty, totale, servizio, atteso, perche in (
            (1, 180000, PACCHETTO, 12, 'un pacchetto'),
            (2, 360000, PACCHETTO, 24, 'due pacchetti'),
            (12, 180000, PACCHETTO, 12, '«12 × 150.-»: la quantità conta le sedute'),
            (12, 162000, PACCHETTO, 12, 'dodici sedute a tariffa scontata: restano sedute'),
            (2, 250000, PACCHETTO, 24, 'due pacchetti scontati (il caso del revisore): restano pacchetti'),
            (2, 180000, PACCHETTO, 24, 'un pacchetto a metà prezzo: resta un pacchetto'),
            (Decimal('0.5'), 90000, PACCHETTO, 6, 'mezzo pacchetto'),
            (Decimal('0.05'), 9000, PACCHETTO, 0, 'meno di una seduta: niente'),
            (0, 0, PACCHETTO, 0, 'quantità zero: niente'),
            (-1, -180000, PACCHETTO, 0, 'quantità negativa: niente'),
            (12, None, SENZA_PREZZO, 12, 'senza prezzo, quantità uguale alle sedute'),
            (3, None, SENZA_PREZZO, 36, 'senza prezzo, tre pacchetti'),
            (1, 11000, dict(PACCHETTO, sedute=0), 0, 'un servizio senza sedute')):
        _check(r, cat, f'sedute della riga: {perche}',
               _senza_scoppiare(lambda: S.sedute_della_riga(servizio, qty, totale)), atteso)
    _check(r, cat, 'il pacchetto porta servizio, prezzo a seduta e scadenza',
           _senza_scoppiare(lambda: S.dati_del_servizio(PACCHETTO, '2026-09-14')),
           {'servizio_id': 7, 'prezzo_seduta_cents': 15000, 'scade': '2027-03-14'})
    _check(r, cat, 'senza prezzo niente valore, e senza mesi niente scadenza',
           _senza_scoppiare(lambda: S.dati_del_servizio(SENZA_PREZZO, '2026-09-14')),
           {'servizio_id': 8, 'prezzo_seduta_cents': None, 'scade': None})

    GIULIA = {'id': 1, 'name': 'Giulia Ferrari', 'nome_calendario': '', 'chiave_sedute': 'giulia',
              'archived': 0, 'intestatario': '', 'compagno': None}

    def seduta(n, data):
        return {'n': n, 'data': data, 'titolo': 'Giulia', 'cancellata': False}

    def aperto(crediti, sedute, **altro):
        return dict({'id': 'GIU-01', 'cliente': 'Giulia', 'chiavi': ['giulia'], 'crediti': crediti,
                     'inizio': '2026-08-01', 'fine': None, 'fatturato': 'no',
                     'sessioni': [seduta(i + 1, d) for i, d in enumerate(sedute)]}, **altro)

    prima = S._CONFIG
    try:
        S.configura([GIULIA])

        # --- 1. nessun pacchetto: ne nasce uno, già pagato ---
        reg = {'pacchetti': [], 'esclusi': []}
        esito, (frase, valori) = S.aggancia_pacchetto(reg, 'giulia', 101, '2026-09-14', 12, PACCHETTO)
        frasi.append(frase)
        p = reg['pacchetti'][0] if reg['pacchetti'] else {}
        _check(r, cat, 'senza pacchetto la fattura ne apre uno, già pagato',
               (esito, p.get('id'), p.get('crediti'), p.get('chiavi'), p.get('fattura_numero'),
                p.get('servizio_id'), p.get('prezzo_seduta_cents'), p.get('scade')),
               ('nuovo', 'GIU-01', 12, ['giulia'], 101, 7, 15000, '2027-03-14'))

        # --- 2. pacchetto aperto dal calendario e non pagato: la fattura lo paga ---
        reg = {'pacchetti': [aperto(10, ['2026-09-01', '2026-09-03', '2026-09-08'])], 'esclusi': []}
        esito, (frase, valori) = S.aggancia_pacchetto(reg, 'giulia', 102, '2026-09-10', 12, PACCHETTO)
        frasi.append(frase)
        p = reg['pacchetti'][0]
        _check(r, cat, 'il pacchetto aperto e non pagato lo paga la fattura, con le sedute della riga',
               (esito, len(reg['pacchetti']), p['crediti'], p.get('fattura_numero'),
                valori.get('rimasti')), ('collegato', 1, 12, 102, 9))

        # --- 3. pacchetto aperto e già pagato: la fattura aspetta, con le sue sedute ---
        esito, (frase, valori) = S.aggancia_pacchetto(reg, 'giulia', 103, '2026-09-12', 12, PACCHETTO)
        frasi.append(frase)
        _check(r, cat, 'se il pacchetto è già pagato la fattura resta in attesa, con le sue sedute',
               (esito, reg.get('prepagate')),
               ('in_attesa', {'giulia': [{'numero': 103, 'sedute': 12, 'servizio_id': 7,
                                          'prezzo_seduta_cents': 15000, 'scade': '2027-03-12'}]}))
        p['crediti'] = 3            # tre sedute già fatte: il pacchetto in corso è pieno
        S.aggiungi_sessione(reg, 'giulia', '2026-09-15', 'Giulia', 'ev-4')
        nuovo = reg['pacchetti'][-1]
        _check(r, cat, 'il pacchetto dopo nasce dalla fattura in attesa, con le sue sedute',
               (len(reg['pacchetti']), reg['pacchetti'][0]['fine'], nuovo['crediti'],
                nuovo.get('fattura_numero'), nuovo.get('servizio_id'), nuovo.get('scade'),
                len(nuovo['sessioni']), reg['prepagate'].get('giulia')),
               (2, '2026-09-08', 12, 103, 7, '2027-03-12', 1, None))

        # --- la forma vecchia delle fatture in attesa si legge ancora ---
        reg = {'pacchetti': [aperto(1, ['2026-08-02'], fatturato='si - #88', fattura_numero=88)],
               'esclusi': [], 'prepagate': {'giulia': 90}}
        S.aggiungi_sessione(reg, 'giulia', '2026-08-05', 'Giulia', 'ev-2')
        _check(r, cat, 'una fattura in attesa scritta alla vecchia maniera apre ancora il pacchetto dopo',
               (reg['pacchetti'][-1].get('fattura_numero'), reg['pacchetti'][-1]['crediti'],
                'giulia' in reg['prepagate']), (90, 1, False))

        # --- 4. pacchetto finito: si chiude, e la fattura ne apre uno nuovo ---
        reg = {'pacchetti': [aperto(2, ['2026-08-02', '2026-08-09'])], 'esclusi': []}
        esito, _detto = S.aggancia_pacchetto(reg, 'giulia', 104, '2026-08-10', 12, PACCHETTO)
        _check(r, cat, 'un pacchetto finito si chiude, e la fattura ne apre uno nuovo',
               (esito, reg['pacchetti'][0]['fine'], reg['pacchetti'][-1]['crediti']),
               ('nuovo', '2026-08-09', 12))

        # --- la scadenza ---
        reg = {'pacchetti': [aperto(12, ['2026-09-30'], fatturato='si - #105', fattura_numero=105,
                                    scade='2026-10-01')], 'esclusi': []}
        S.aggiungi_sessione(reg, 'giulia', '2026-10-01', 'Giulia', 'ev-2')
        _check(r, cat, 'il giorno della scadenza la seduta entra ancora',
               (len(reg['pacchetti']), len(reg['pacchetti'][0]['sessioni'])), (1, 2))
        S.aggiungi_sessione(reg, 'giulia', '2026-10-02', 'Giulia', 'ev-3')
        vecchio, nuovo = reg['pacchetti'][0], reg['pacchetti'][-1]
        _check(r, cat, 'il giorno dopo il pacchetto si chiude scaduto, e le sedute rimaste si perdono',
               (vecchio.get('fine'), vecchio.get('scaduto'), vecchio['rimasti'],
                len(vecchio['sessioni'])), ('2026-10-01', True, 10, 2))
        _check(r, cat, 'e la seduta apre il pacchetto dopo, da fatturare',
               (nuovo['id'], nuovo['fatturato'], len(nuovo['sessioni'])), ('GIU-02', 'no', 1))

        # --- la fattura paga meno sedute di quante gia' fatte: le sposta ---
        date_11 = [f'2026-08-{i:02d}' for i in range(1, 12)]
        reg = {'pacchetti': [aperto(12, date_11)], 'esclusi': []}
        reg['pacchetti'][0]['sessioni'][-1].update(event_id='ev-11', ora='09:00',
                                                    nota='doppia seduta')
        esito, (frase, valori) = S.aggancia_pacchetto(reg, 'giulia', 108, '2026-08-20', 10, PACCHETTO)
        frasi.append(frase)
        vecchio, spostato = reg['pacchetti'][0], reg['pacchetti'][1]
        eventi = [s.get('event_id') for p in reg['pacchetti'] for s in p['sessioni'] if s.get('event_id')]
        _check(r, cat, 'la fattura chiude il vecchio pacchetto alle sue sedute',
               (esito, len(reg['pacchetti']), vecchio['crediti'], vecchio.get('fattura_numero'),
                len(vecchio['sessioni']), vecchio['fine']),
               ('collegato', 2, 10, 108, 10, date_11[9]))
        _check(r, cat, 'e sposta la seduta in più nel pacchetto dopo, con i suoi dati intatti',
               (spostato['sessioni'][0]['n'], spostato['sessioni'][0].get('event_id'),
                spostato['sessioni'][0].get('ora'), spostato['sessioni'][0].get('nota'),
                spostato['fatturato'], spostato['crediti']),
               (1, 'ev-11', '09:00', 'doppia seduta', 'no', 10))
        _check(r, cat, 'la frase dice quante sedute passano e a quale pacchetto',
               valori, {'pid': 'GIU-01', 'nome': 'Giulia', 'sedute': 10, 'extra': 1,
                        'nuovo': spostato['id']})
        _check(r, cat, 'nessun event_id compare due volte nel registro',
               len(eventi) == len(set(eventi)), True)

        # --- una seduta dopo la scadenza di una fattura in attesa: il
        # pacchetto nasce gia' scaduto, e si riprova con la prossima ---
        reg = {'pacchetti': [aperto(3, ['2026-09-01', '2026-09-02', '2026-09-03'],
                                    fatturato='si - #110', fattura_numero=110)],
               'esclusi': [],
               'prepagate': {'giulia': [
                   {'numero': 111, 'sedute': 12, 'servizio_id': 7,
                    'prezzo_seduta_cents': 15000, 'scade': '2026-09-10'},
                   {'numero': 112, 'sedute': 12, 'servizio_id': 7,
                    'prezzo_seduta_cents': 15000, 'scade': '2026-12-31'},
               ]}}
        S.aggiungi_sessione(reg, 'giulia', '2026-09-15', 'Giulia', 'ev-20')
        scaduto, pagato = reg['pacchetti'][1], reg['pacchetti'][2]
        _check(r, cat, 'la prima fattura in attesa, gia scaduta, apre un pacchetto nato scaduto',
               (scaduto.get('scaduto'), scaduto['inizio'], scaduto['fine'],
                len(scaduto['sessioni']), scaduto.get('fattura_numero')),
               (True, '2026-09-10', '2026-09-10', 0, 111))
        _check(r, cat, 'la seduta entra nel pacchetto della fattura ancora valida',
               (pagato.get('fattura_numero'), len(pagato['sessioni']), pagato['sessioni'][0]['n']),
               (112, 1, 1))
        _check(r, cat, 'nessuna fattura in attesa e rimasta per quel cliente',
               reg.get('prepagate', {}).get('giulia'), None)

        # --- con una sola fattura in attesa gia' scaduta, si perde e basta ---
        reg = {'pacchetti': [aperto(3, ['2026-09-01', '2026-09-02', '2026-09-03'],
                                    fatturato='si - #120', fattura_numero=120)],
               'esclusi': [],
               'prepagate': {'giulia': [
                   {'numero': 121, 'sedute': 12, 'servizio_id': 7,
                    'prezzo_seduta_cents': 15000, 'scade': '2026-09-10'},
               ]}}
        S.aggiungi_sessione(reg, 'giulia', '2026-09-15', 'Giulia', 'ev-21')
        scaduto2, nuovo2 = reg['pacchetti'][1], reg['pacchetti'][2]
        _check(r, cat, 'con una sola fattura in attesa gia scaduta il pacchetto nasce scaduto lo stesso',
               (scaduto2.get('scaduto'), scaduto2['inizio'], scaduto2['fine'],
                len(scaduto2['sessioni'])),
               (True, '2026-09-10', '2026-09-10', 0))
        _check(r, cat, 'e la seduta apre un pacchetto da fatturare, con la misura di prima',
               (nuovo2['fatturato'], nuovo2['crediti'], len(nuovo2['sessioni']),
                nuovo2['sessioni'][0]['n']),
               ('no', 12, 1, 1))

        # --- dalla fattura: le righe, e le frasi per chi fattura ---
        reg = {'pacchetti': [], 'esclusi': []}
        dette = _senza_scoppiare(lambda: S.sedute_dalla_fattura(
            reg, 'giulia', 106, '2026-09-14', [(PACCHETTO, 1, 180000)]))
        _check(r, cat, 'la fattura col pacchetto apre le sedute e lo dice',
               ([f for f, _v in dette] if isinstance(dette, list) else dette,
                [p['crediti'] for p in reg['pacchetti']]),
               (['Aperto il pacchetto {pid} per {nome}: {crediti} sedute disponibili.'], [12]))
        _check(r, cat, 'una riga che non arriva a una seduta non tocca niente',
               (_senza_scoppiare(lambda: S.sedute_dalla_fattura(
                   reg, 'giulia', 107, '2026-09-14', [(PACCHETTO, Decimal('0.05'), 9000)])),
                len(reg['pacchetti'])), ([], 1))
    finally:
        S._CONFIG = prima

    for frase in sorted(set(frasi)):
        _check(r, cat, f'«{frase[:40]}…» si legge anche in inglese e in tedesco',
               (L.t(frase, 'en') != frase, L.t(frase, 'de') != frase), (True, True))

    # --- quali righe portano sedute ---
    con = _db_servizi()
    for nome, sedute, ogni_mese in (('12 Sessions Pack', 12, 0), ('Abo con sedute', 4, 1),
                                    ('Consulenza', 0, 0)):
        con.execute('INSERT INTO servizi(nome, prezzo_cents, ogni_mese, sedute) VALUES(?,?,?,?)',
                    (nome, 10000, ogni_mese, sedute))
    ids = {x['nome']: x['id'] for x in con.execute('SELECT id, nome FROM servizi')}
    righe = [{'servizio_id': ids['12 Sessions Pack'], 'qty': 1, 'total_cents': 180000},
             {'servizio_id': ids['Consulenza'], 'qty': 1, 'total_cents': 9000},
             {'servizio_id': ids['Abo con sedute'], 'qty': 1, 'total_cents': 11000},
             {'servizio_id': None, 'qty': 1, 'total_cents': 500},
             {'servizio_id': 0, 'qty': 1, 'total_cents': 500}]
    _check(r, cat, 'portano sedute solo le righe di un servizio che le comprende',
           _senza_scoppiare(lambda: [(s['nome'], q, t) for s, q, t in SR.righe_con_sedute(con, righe)]),
           [('12 Sessions Pack', 1, 180000), ('Abo con sedute', 1, 11000)])
    con.close()

    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py'),
              encoding='utf-8') as f:
        sorgente = f.read()
    corpo = sorgente[sorgente.index('def _crea_fattura'):]
    corpo = corpo[:corpo.index('\n@app.route')]
    _check(r, cat, 'la nuova fattura manda le sedute dalle righe, non dall’importo',
           ('sedute_dalla_fattura' in corpo, 'analizza_fattura' in corpo, 'aggancia_fattura' in corpo),
           (True, False, False))
    _check(r, cat, 'il riconoscimento per importo non c’è più',
           [n for n in ('riconosci_pacchetto', 'analizza_fattura', 'aggancia_fattura',
                        '_candidati_per_fattura', 'PAROLE_PACCHETTO') if hasattr(S, n)], [])

    # --- i mesi di sedute degli abbonamenti ---
    from . import mensili as M
    from . import schedule as AG
    ABO = {'id': 9, 'nome': 'Monthly abo', 'prezzo_cents': 22000, 'ogni_mese': 1, 'sedute': 4,
           'scadenza_mesi': 0, 'passano': 1, 'massimo': 6}
    ABO_PERSE = dict(ABO, id=10, passano=0, massimo=0)
    ABO_CORTO = dict(ABO, id=11, nome='Abo corto')

    for argomenti, atteso, perche in (
            (('2026-09-14', '2026-09', 13), ('2026-09-13', '2026-10-12'),
             'da un abbonamento, dal rinnovo al giorno prima del rinnovo dopo'),
            (('2026-09-14',), ('2026-09-14', '2026-10-13'),
             'da una fattura qualsiasi, dalla sua data a un mese dopo'),
            (('2026-02-01', '2026-02', 31), ('2026-02-28', '2026-03-30'),
             'il rinnovo del 31 si accorcia sui mesi corti')):
        _check(r, cat, f'periodo del mese: {perche}',
               _senza_scoppiare(lambda: M.periodo_di(*argomenti)), atteso)

    def reg_vuoto():
        return {'pacchetti': [], 'esclusi': [], 'mensili': []}

    MARCO = dict(GIULIA, id=2, name='Marco Bianchi', chiave_sedute='marco', compagno='giulia')
    prima = S._CONFIG
    try:
        S.configura([GIULIA, MARCO])

        # sedute che passano, col massimo
        reg = reg_vuoto()
        m1 = M.da_fattura(reg, 'giulia', 'Giulia', 201, '2026-09-13', ABO, '2026-09', 13)
        S.aggiungi_sessione(reg, 'giulia', '2026-09-20', 'Giulia', 'ev-1')
        m2 = M.da_fattura(reg, 'giulia', 'Giulia', 202, '2026-10-13', ABO, '2026-10', 13)
        _check(r, cat, 'le sedute passano fino al massimo: 4 al mese, massimo 6, se ne usa 1 '
                       'il mese dopo ne ha 6',
               (m1['id'], m1['usate'], m2['id'], m2['riportate'], m2['disponibili']),
               ('GIU-M01', 1, 'GIU-M02', 3, 6))

        # sedute che si perdono, e sedute in più
        reg = reg_vuoto()
        M.da_fattura(reg, 'giulia', 'Giulia', 203, '2026-09-13', ABO_PERSE, '2026-09', 13)
        S.aggiungi_sessione(reg, 'giulia', '2026-09-20', 'Giulia', 'ev-1')
        m2 = M.da_fattura(reg, 'giulia', 'Giulia', 204, '2026-10-13', ABO_PERSE, '2026-10', 13)
        _check(r, cat, 'se le sedute non passano, il mese dopo riparte da 4',
               (m2['riportate'], m2['disponibili']), (0, 4))
        for i in range(5):
            S.aggiungi_sessione(reg, 'giulia', '2026-10-%02d' % (14 + i), 'Giulia', f'ev-piu-{i}')
        _check(r, cat, 'oltre le disponibili la seduta resta scritta, «in più»',
               (m2['usate'], m2['in_piu'], [s.get('in_piu', False) for s in m2['sessioni']]),
               (4, 1, [False, False, False, False, True]))

        # un mese senza fattura: le rimaste valgono un periodo, poi finiscono
        reg = reg_vuoto()
        M.da_fattura(reg, 'giulia', 'Giulia', 205, '2026-09-13', ABO, '2026-09', 13)
        S.aggiungi_sessione(reg, 'giulia', '2026-09-20', 'Giulia', 'ev-1')
        mese, _nuovo = S.aggiungi_sessione(reg, 'giulia', '2026-10-20', 'Giulia', 'ev-2')
        _check(r, cat, 'un mese senza fattura esiste lo stesso, e ci si usano le rimaste',
               (mese['dal'], mese['al'], mese['fattura_numero'], mese['disponibili'], mese['usate'])
               if mese else None, ('2026-10-13', '2026-11-12', None, 3, 1))
        esito = S.aggiungi_sessione(reg, 'giulia', '2026-11-20', 'Giulia', 'ev-3')
        _check(r, cat, 'dopo un mese senza fattura non c’è più niente: la seduta va fra gli esclusi',
               (esito, reg['esclusi'][-1].get('motivo') if reg['esclusi'] else None,
                len(reg['mensili'])), ((None, False), 'nessun abbonamento in corso', 2))

        # la seduta arrivata prima della fattura rientra quando la fattura arriva
        reg = reg_vuoto()
        S.aggiungi_sessione(reg, 'giulia', '2026-09-13', 'Giulia', 'ev-1')
        m = M.da_fattura(reg, 'giulia', 'Giulia', 206, '2026-09-14', ABO, '2026-09', 13)
        _check(r, cat, 'la seduta del giorno di rinnovo, registrata prima della fattura, rientra nel mese',
               (m['usate'], reg['esclusi']), (1, []))

        # l'ordine: prima quello che scade prima
        reg = reg_vuoto()
        reg['pacchetti'].append({'id': 'GIU-01', 'cliente': 'Giulia', 'chiavi': ['giulia'],
                                 'crediti': 10, 'inizio': '2026-06-01', 'fine': None,
                                 'fatturato': 'si - #150', 'fattura_numero': 150,
                                 'scade': '2026-09-25', 'sessioni': []})
        M.da_fattura(reg, 'giulia', 'Giulia', 207, '2026-09-13', ABO, '2026-09', 13)
        corto = M.da_fattura(reg, 'giulia', 'Giulia', 208, '2026-09-01', ABO_CORTO)
        dove, _n = S.aggiungi_sessione(reg, 'giulia', '2026-09-20', 'Giulia', 'ev-1')
        _check(r, cat, 'il pacchetto che scade prima della fine del mese si usa per primo',
               dove['id'] if dove else None, 'GIU-01')
        reg['pacchetti'][0]['scade'] = '2026-12-31'
        dove, _n = S.aggiungi_sessione(reg, 'giulia', '2026-09-21', 'Giulia', 'ev-2')
        _check(r, cat, 'fra due abbonamenti nello stesso giorno, prima quello che finisce prima',
               (dove['id'] if dove else None, corto['id']), ('GIU-M02', 'GIU-M02'))

        _check(r, cat, 'la regola della coppia non cambia',
               S.attribuisci('marco', ['marco'])[0], 'giulia')

        # dalla fattura, con la frase per chi fattura
        reg = reg_vuoto()
        dette = S.sedute_dalla_fattura(reg, 'giulia', 209, '2026-09-14', [(ABO, 1, 22000)],
                                       '2026-09', 13)
        frasi_mese = [f for f, _v in dette]
        _check(r, cat, 'una fattura «ogni mese» apre il mese di sedute e lo dice',
               (frasi_mese, dette[0][1] if dette else None, len(reg['mensili'])),
               (['Sedute di {nome} dal {dal} al {al}: {sedute}.'],
                {'nome': 'Giulia', 'dal': '13.09.2026', 'al': '12.10.2026', 'sedute': 4}, 1))
        for frase in frasi_mese:
            _check(r, cat, f'«{frase[:40]}…» si legge anche in inglese e in tedesco',
                   (L.t(frase, 'en') != frase, L.t(frase, 'de') != frase), (True, True))

        # spec §7: quantita' zero o negativa su una riga «ogni mese» = nessuna seduta
        for qty_prova, numero_prova, perche in ((0, 210, 'quantità zero'),
                                                 (-1, 211, 'quantità negativa')):
            reg_qty = reg_vuoto()
            dette_qty = S.sedute_dalla_fattura(reg_qty, 'giulia', numero_prova, '2026-09-14',
                                               [(ABO, qty_prova, 22000)], '2026-09', 13)
            _check(r, cat, f'una riga «ogni mese» con {perche} non apre nessun mese e non lo dice',
                   (dette_qty, reg_qty['mensili']), ([], []))

        # il registro sa che quelle sedute ci sono già, e l'Agenda le mostra
        S.aggiungi_sessione(reg, 'giulia', '2026-09-16', 'Giulia', 'ev-agenda')
        _check(r, cat, 'le sedute dei mesi contano per non registrarle due volte',
               ('ev-agenda' in S.id_evento_gia_presente(reg), S.ultima_data_registrata(reg)),
               (True, '2026-09-16'))
        _check(r, cat, 'l’Agenda mostra anche le sedute degli abbonamenti',
               ([x['pacchetto'] for x in AG.elenco(reg, orari={})], AG.anni(reg)),
               (['GIU-M01'], ['2026']))

        # il filtro clienti dell'Agenda non deve perdere chi ha solo un abbonamento
        reg_solo_mensile = {
            'pacchetti': [{'id': 'GIU-01', 'cliente': 'Giulia',
                          'sessioni': [{'data': '2026-09-01', 'titolo': 'Giulia'}]}],
            'mensili': [{'id': 'LUC-M01', 'cliente': 'Luca',
                        'sessioni': [{'data': '2026-09-05', 'titolo': 'Luca'}]}],
        }
        _check(r, cat, 'l’elenco clienti dell’Agenda include anche chi ha solo un abbonamento',
               AG.clienti(reg_solo_mensile), ['Giulia', 'Luca'])
        _check(r, cat, 'l’Agenda filtrata su un cliente solo abbonato mostra le sue sedute dei mesi',
               [x['pacchetto'] for x in AG.elenco(reg_solo_mensile, orari={}, cliente='Luca')],
               ['LUC-M01'])

        # la seduta in più di aggancia_pacchetto, spostata in un mese che ha già
        # una seduta più avanti: deve arrivare sulla seduta giusta, non
        # sull'ultima del mese (l'ordine cambia quando ricalcola_tutti riordina
        # per data — vedi mensili.ricalcola)
        reg = reg_vuoto()
        reg['pacchetti'].append(aperto(10, ['2026-09-01', '2026-09-02', '2026-09-03']))
        reg['pacchetti'][0]['sessioni'][-1]['segno'] = 'quella-vera'
        m3 = M.da_fattura(reg, 'giulia', 'Giulia', 301, '2026-09-01', ABO)
        S.aggiungi_sessione(reg, 'giulia', '2026-09-10', 'Giulia', 'ev-dopo')
        S.aggancia_pacchetto(reg, 'giulia', 302, '2026-09-05', 2, PACCHETTO)
        giusta = next((s for s in m3['sessioni'] if s['data'] == '2026-09-03'), None)
        sbagliata = next((s for s in m3['sessioni'] if s['data'] == '2026-09-10'), None)
        _check(r, cat, 'la seduta in più spostata da un pacchetto in un mese porta i suoi dati '
                       'sulla seduta giusta, non sull’ultima del mese',
               (giusta.get('segno') if giusta else None,
                sbagliata.get('segno') if sbagliata else None),
               ('quella-vera', None))
    finally:
        S._CONFIG = prima

    _check(r, cat, 'la lettura del calendario salva anche quando una seduta va fra gli esclusi',
           "rap.get('esclusi_nuovi')" in sorgente, True)

    # --- guardia: tanti mesi che si riportano non devono raddoppiare il conto ---
    # riportate() chiamava disponibili(reg, p) e poi usate(reg, p), che richiama
    # di nuovo disponibili(reg, p): ogni mese in piu' di catena raddoppiava il
    # lavoro (col revisore, 18 mesi consecutivi = oltre un milione di chiamate,
    # 4.9 secondi per ogni seduta aggiunta). La prova gira anche dentro la
    # pagina Controlli dell'app viva, dove una richiesta concorrente potrebbe
    # incappare in un dato globale toccato dalla prova: percio' qui non si
    # tocca nessun oggetto di core.mensili, si conta il lavoro sui dati di
    # prova stessi, con un dict che si accorge da solo se legge troppe volte.
    import datetime as _dt

    class _ContaLetture(dict):
        """Un dict che conta le sue letture con get(); oltre un tetto largo si
        rifiuta di continuare, cosi' un calcolo tornato esponenziale si vede
        rosso in un attimo invece di restare li' a girare."""
        _letture = [0]
        _tetto = 200000

        def get(self, *a, **k):
            _ContaLetture._letture[0] += 1
            if _ContaLetture._letture[0] > _ContaLetture._tetto:
                raise RuntimeError('troppe letture: il calcolo dei mesi non è più lineare')
            return super().get(*a, **k)

    def _mese_di_prova(i, dal, al):
        return _ContaLetture(
            id=f'GIU-M{i + 1:02d}', chiavi=['giulia'], cliente='Giulia', servizio_id=9,
            fattura_numero=900 + i, dal=dal, al=al, sedute=4, passano=1, massimo=6,
            prezzo_seduta_cents=5500,
            sessioni=[{'data': dal, 'titolo': 'Giulia', 'cancellata': False}])

    def _catena_di_mesi(n):
        reg = {'mensili': [], 'esclusi': []}
        data = '2023-01-13'
        for i in range(n):
            dal, al = M.periodo_di(data)
            reg['mensili'].append(_mese_di_prova(i, dal, al))
            data = (_dt.date.fromisoformat(al) + _dt.timedelta(days=1)).isoformat()
        return reg

    def _numeri_ultimo_mese():
        reg36 = _catena_di_mesi(36)
        M.ricalcola_tutti(reg36)
        ultimo = reg36['mensili'][-1]
        return ultimo['riportate'], ultimo['disponibili'], ultimo['usate'], ultimo['in_piu']

    numeri = _senza_scoppiare(_numeri_ultimo_mese)
    _check(r, cat, 'trentasei mesi consecutivi che si riportano: il calcolo resta limitato, '
                   'e i numeri dell’ultimo mese sono giusti',
           (numeri, _ContaLetture._letture[0] <= _ContaLetture._tetto),
           ((5, 6, 1, 0), True))

    # --- la pagina Crediti e l'avviso della Dashboard ---
    SOFIA = dict(GIULIA, id=3, name='Sofia Verdi', chiave_sedute='sofia')
    ELENA = dict(GIULIA, id=4, name='Elena Rossi', chiave_sedute='elena')
    prima = S._CONFIG
    try:
        S.configura([GIULIA, SOFIA, ELENA, MARCO])
        reg = {'pacchetti': [
            {'id': 'GIU-01', 'cliente': 'Giulia', 'chiavi': ['giulia'], 'crediti': 10,
             'inizio': '2026-09-01', 'fine': None, 'fatturato': 'si - #301', 'fattura_numero': 301,
             'scade': '2027-03-01', 'sessioni': [seduta(1, '2026-09-02')]},
            {'id': 'SOF-01', 'cliente': 'Sofia', 'chiavi': ['sofia'], 'crediti': 10,
             'inizio': '2026-01-01', 'fine': '2026-07-01', 'scade': '2026-07-01', 'scaduto': True,
             'fatturato': 'si - #302', 'fattura_numero': 302,
             'sessioni': [seduta(1, '2026-02-01'), seduta(2, '2026-03-01'), seduta(3, '2026-04-01')]},
        ], 'esclusi': [], 'mensili': []}
        M.da_fattura(reg, 'giulia', 'Giulia', 303, '2026-09-13', ABO, '2026-09', 13)
        S.aggiungi_sessione(reg, 'giulia', '2026-09-20', 'Giulia', 'ev-v1')
        M.da_fattura(reg, 'elena', 'Elena', 304, '2026-09-01', ABO_PERSE)
        for i in range(5):
            S.aggiungi_sessione(reg, 'elena', '2026-09-%02d' % (2 + i), 'Elena', f'ev-e{i}')
        righe = _senza_scoppiare(lambda: S.vista_crediti(reg, datetime.date(2026, 9, 25)))
        vista = {v['chiave']: v for v in righe} if isinstance(righe, list) else {}
        _check(r, cat, 'Crediti mostra solo chi ha pacchetti o abbonamenti con sedute',
               sorted(vista) if vista else righe, ['elena', 'giulia', 'sofia'])
        g, s, e = vista.get('giulia', {}), vista.get('sofia', {}), vista.get('elena', {})
        _check(r, cat, 'accanto al pacchetto, il mese di abbonamento in corso',
               {k: (g.get('mensile') or {}).get(k) for k in (
                   'dal', 'al', 'usate', 'disponibili', 'nuove', 'riportate', 'in_piu',
                   'in_corso', 'fatturato')},
               {'dal': '2026-09-13', 'al': '2026-10-12', 'usate': 1, 'disponibili': 4, 'nuove': 4,
                'riportate': 0, 'in_piu': 0, 'in_corso': True, 'fatturato': True})
        _check(r, cat, 'il pacchetto dice quando scade',
               (g.get('pacchetto'), g.get('scade')), ('GIU-01', '2027-03-01'))
        _check(r, cat, 'uno scaduto dice quante sedute non sono state usate',
               (s.get('scaduto'), s.get('non_usate'), s.get('terminati')), (True, 7, True))
        _check(r, cat, 'chi ha solo l’abbonamento non risulta senza crediti',
               (e.get('pacchetto'), e.get('terminati'), (e.get('mensile') or {}).get('in_piu')),
               (None, False, 1))
        _check(r, cat, 'la vista non porta più l’importo atteso', 'importo_atteso' in g, False)

        _check(r, cat, 'la Dashboard sa delle sedute in più del mese in corso',
               [(v['cliente'], v['in_piu'])
                for v in _senza_scoppiare(lambda: M.in_piu_recenti(reg, datetime.date(2026, 9, 25)))],
               [('Elena', 1)])
        _check(r, cat, 'e dopo due mesi non le ripete più',
               _senza_scoppiare(lambda: M.in_piu_recenti(reg, datetime.date(2026, 12, 20))), [])
    finally:
        S._CONFIG = prima

    # --- la fattura di un pacchetto finita nel Cestino si vede (spec §7) ---
    import app as APP
    con = _db_servizi()
    for numero, stato, cestino in ((301, 'pagata', None), (302, 'emessa', '2026-09-01 10:00:00'),
                                   (303, 'emessa', '2026-09-01 10:00:00'), (303, 'pagata', None)):
        con.execute("INSERT INTO invoices(number, client_name, date, year, status, deleted_at) "
                    "VALUES(?, 'x', '2026-09-01', 2026, ?, ?)", (numero, stato, cestino))
    _check(r, cat, 'Crediti dice se la fattura di un pacchetto è nel Cestino, '
                   'e un numero riusato vale per la fattura nuova',
           _senza_scoppiare(APP._stati_delle_fatture, con),
           {301: 'pagata', 302: 'cestinata', 303: 'pagata'})
    con.close()

    # --- l'Agenda linka anche i mesi (id tipo GIU-M01) a crediti_pacchetto:
    # oggi darebbe 404, perché la pagina cerca solo fra i pacchetti ---
    import json
    import tempfile
    prima_registry = S.REGISTRY
    cartella = tempfile.mkdtemp()
    try:
        S.REGISTRY = os.path.join(cartella, 'sessions.json')
        with open(S.REGISTRY, 'w', encoding='utf-8') as f:
            json.dump({'pacchetti': [], 'esclusi': [], 'mensili': [
                {'id': 'GIU-M01', 'chiavi': ['giulia'], 'cliente': 'Giulia', 'servizio_id': None,
                 'fattura_numero': None, 'dal': '2026-09-13', 'al': '2026-10-12', 'sedute': 4,
                 'passano': 0, 'massimo': 0, 'prezzo_seduta_cents': None,
                 'sessioni': [seduta(1, '2026-09-20')]}]}, f)
        risposta = _senza_scoppiare(lambda: APP.app.test_client().get('/crediti/pacchetto/GIU-M01'))
        corpo = risposta.get_data(as_text=True) if hasattr(risposta, 'get_data') else ''
        _check(r, cat, 'la pagina del pacchetto si apre anche per un mese di abbonamento '
                       '(il link dell’Agenda su un id di mese)',
               (getattr(risposta, 'status_code', None), 'GIU-M01' in corpo), (200, True))
    finally:
        S.REGISTRY = prima_registry


def _test_migrazione_servizi(r):
    """Il listino nasce da quello che c'era, una volta sola, senza perdere niente.

    Prima i servizi stavano in tre caselle delle Impostazioni: i pulsanti della
    nuova fattura e le regole «Nome = parole». La migrazione ne fa la tabella
    dei servizi e collega le righe gia' fatturate. Le prove girano su database
    costruiti qui dentro: mai sui dati di chi usa l'app."""
    import json
    import glob
    import inspect
    import logging
    import sqlite3
    import tempfile
    from . import db as D
    from . import migra_servizi as M
    from . import sessions as S
    from . import stats as ST
    cat = 'Migrazione dei servizi'

    def popola(con, impostazioni, righe):
        for chiave, valore in impostazioni.items():
            con.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)',
                        (chiave, valore))
        for numero, data, testo, cents, cestino in righe:
            fid = con.execute(
                'INSERT INTO invoices(number, client_name, date, year, total_cents, deleted_at) '
                'VALUES(?,?,?,?,?,?)',
                (numero, 'Giulia Ferrari', data, int(data[:4]), cents,
                 '2026-08-06 10:00:00' if cestino else None)).lastrowid
            con.execute('INSERT INTO items(invoice_id, pos, qty, description, unit_cents, '
                        'total_cents) VALUES(?,0,?,?,?,?)', (fid, '1', testo, cents, cents))
        con.commit()

    def con_righe(impostazioni, righe):
        con = _db_servizi()
        popola(con, impostazioni, righe)
        return con

    def listino(con):
        return [(s['nome'], s['prezzo_cents'], s['ogni_mese'], s['sedute'])
                for s in con.execute('SELECT * FROM servizi ORDER BY pos')]

    def servizio_della_riga(con, testo):
        riga = con.execute('SELECT s.nome FROM items i LEFT JOIN servizi s ON s.id = i.servizio_id '
                           'WHERE i.description = ? LIMIT 1', (testo,)).fetchone()
        return riga['nome'] if riga else 'riga assente'

    def forma(con):
        return {t['name']: {c['name'] for c in con.execute('PRAGMA table_info("%s")' % t['name'])}
                for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def leggi_json(percorso):
        with open(percorso, encoding='utf-8') as f:
            return json.load(f)

    def servizi_in_controlli(con):
        return [i['key'] for i in ST.health(con) if i['kind'] == 'servizi']

    PACCHETTO_12 = '12 Sessions Pack – Personal Training at Home'
    PACCHETTO_10 = '10 Sessions Pack – Personal Training at Home'
    MENSILE = 'Monthly abo: running coaching'
    IMPOSTAZIONI = {
        'servizi': '\n'.join((PACCHETTO_12, PACCHETTO_10, MENSILE)),
        'servizi_abbonamento': 'Running Coaching = running coaching\n'
                               'Online Coaching = coaching online',
        'servizi_pacchetto': 'Personal Training = session, personal training, add-on, credit\n'
                             'Yoga di gruppo = yoga',
    }
    RIGHE = [
        (1, '2026-01-10', PACCHETTO_10, 200000, False),
        (2, '2026-03-02', PACCHETTO_12, 180000, False),
        (3, '2026-06-01', MENSILE + ' 01.06.26 - 30.06.26', 11000, False),
        (4, '2026-07-01', MENSILE + ' 01.07.26 - 31.07.26', 11000, False),
        (5, '2026-07-15', 'Coaching online 15.07.26 - 14.08.26', 9000, False),
        (6, '2026-08-01', PACCHETTO_12, 99900, True),        # nel Cestino: non conta
        (7, '2026-08-05', 'Add-on 10 credits', 90000, False),
    ]
    REGISTRO = {'pacchetti': [
        {'id': 'GIU-01', 'cliente': 'Giulia', 'fattura_numero': '1', 'crediti': 10},
        {'id': 'GIU-02', 'cliente': 'Giulia', 'fattura_numero': 2, 'crediti': 12},
        {'id': 'GIU-03', 'cliente': 'Giulia', 'fattura_numero': 6, 'crediti': 99},
    ]}

    with tempfile.TemporaryDirectory() as tmp:
        percorso_registro = os.path.join(tmp, 'sessions.json')
        with open(percorso_registro, 'w', encoding='utf-8') as f:
            json.dump(REGISTRO, f)
        nessun_registro = os.path.join(tmp, 'non-c-e.json')

        # --- con pulsanti e regole ---
        con = con_righe(IMPOSTAZIONI, RIGHE)
        prima = forma(con)
        _check(r, cat, 'la prima volta la migrazione si fa',
               _senza_scoppiare(lambda: M.esegui(con, percorso_registro, fai_copia=False)), True)
        _check(r, cat, 'i pulsanti diventano servizi; delle regole solo quelle che un pulsante '
                       'non contiene e che hanno riconosciuto almeno una riga',
               listino(con), [(PACCHETTO_12, 180000, 0, 12), (PACCHETTO_10, 200000, 0, 10),
                              (MENSILE, 11000, 1, 0), ('Online Coaching', 9000, 1, 0)])
        _check(r, cat, 'le righe col nome del servizio si collegano da sole',
               [servizio_della_riga(con, t)
                for t in (PACCHETTO_10, PACCHETTO_12, MENSILE + ' 01.06.26 - 30.06.26')],
               [PACCHETTO_10, PACCHETTO_12, MENSILE])
        _check(r, cat, 'quelle senza il nome restano da decidere',
               [servizio_della_riga(con, t)
                for t in ('Coaching online 15.07.26 - 14.08.26', 'Add-on 10 credits')],
               [None, None])
        _check(r, cat, 'la migrazione resta segnata come fatta', M.fatta(con), True)
        _check(r, cat, 'la seconda volta non si rifà',
               M.esegui(con, percorso_registro, fai_copia=False), False)
        _check(r, cat, 'e il listino resta quello', len(listino(con)), 4)
        _check(r, cat, 'un listino che c’è già non si tocca',
               M.crea_servizi(con, D.get_settings(con), REGISTRO), 0)
        dopo = forma(con)
        _check(r, cat, 'nessuna tabella e nessuna colonna tolta',
               {t: sorted(c - dopo.get(t, set())) for t, c in prima.items()
                if c - dopo.get(t, set())}, {})
        _check(r, cat, 'le caselle vecchie restano nel database',
               all(D.get_settings(con).get(k) == v for k, v in IMPOSTAZIONI.items()), True)
        con.close()

        # --- senza pulsanti né regole: le descrizioni che si ripetono ---
        con = con_righe({}, [
            (1, '2026-05-01', 'Abbonamento yoga 01.05.26 - 31.05.26', 8000, False),
            (2, '2026-06-01', 'Abbonamento yoga 01.06.26 - 30.06.26', 8500, False),
            (3, '2026-06-10', 'Lezione privata', 12000, False),
            (4, '2026-06-20', 'Lezione privata', 12500, False),
            (5, '2026-06-25', 'Consulenza', 5000, False),
        ])
        M.esegui(con, nessun_registro, fai_copia=False)
        _check(r, cat, 'senza niente di scritto, il listino viene dalle righe che si ripetono '
                       '(con due date è «ogni mese»)',
               sorted(listino(con)),
               [('Abbonamento yoga', 8500, 1, 0), ('Lezione privata', 12500, 0, 0)])
        _check(r, cat, 'una riga usata una volta sola non diventa un servizio',
               servizio_della_riga(con, 'Consulenza'), None)
        con.close()

        # --- un'app appena installata ---
        con = _db_servizi()
        _check(r, cat, 'senza fatture non si crea niente, e la migrazione si segna fatta',
               (M.esegui(con, nessun_registro), listino(con), M.fatta(con)), (True, [], True))
        con.close()

        # --- se qualcosa va storto: niente a metà, e Controlli lo dice ---
        con = con_righe(IMPOSTAZIONI, RIGHE)
        con.execute('DROP TABLE servizi_testi')
        con.commit()
        errori = logging.getLogger('fatture.errori')
        errori.disabled = True      # il guaio qui è voluto: non va nel registro vero
        try:
            riuscita = _senza_scoppiare(lambda: M.esegui(con, percorso_registro, fai_copia=False))
        finally:
            errori.disabled = False
        _check(r, cat, 'se un passo si rompe la migrazione non esplode', riuscita, False)
        _check(r, cat, 'e non lascia servizi a metà', listino(con), [])
        _check(r, cat, 'e non si segna fatta', M.fatta(con), False)
        _check(r, cat, 'Controlli lo dice', servizi_in_controlli(con), ['servizi:migrazione'])
        con.executescript(D.SCHEMA)          # il guaio si ripara da solo
        _check(r, cat, 'al tentativo dopo riesce',
               M.esegui(con, percorso_registro, fai_copia=False), True)
        _check(r, cat, 'e l’avviso in Controlli sparisce', servizi_in_controlli(con), [])
        con.close()

        # --- la copia di sicurezza, prima di toccare qualcosa ---
        percorso_db = os.path.join(tmp, 'fatture.db')
        con = sqlite3.connect(percorso_db)
        con.row_factory = sqlite3.Row
        con.executescript(D.SCHEMA)
        D._migrate(con)
        con.execute("INSERT INTO invoices(number, client_name) VALUES(1, 'Giulia Ferrari')")
        con.commit()
        copie = M.copia_di_sicurezza(con, percorso_registro)
        con.close()
        # os.path.realpath: sqlite risolve i link simbolici del percorso del
        # database (su macOS /var -> /private/var) prima di scriverlo in
        # PRAGMA database_list; senza risolverlo anche qui il confronto
        # fallirebbe per una differenza di sola grafia, non di sostanza.
        cartella = os.path.join(os.path.realpath(tmp), 'backups', M.CARTELLA_COPIE)
        _check(r, cat, 'le copie vanno in una cartella che la pulizia delle copie non tocca',
               sorted(os.path.dirname(c) for c in copie), [cartella, cartella])
        copia_db = next((c for c in copie if c.endswith('.db')), None)
        quante = 0
        if copia_db:
            letto = sqlite3.connect(copia_db)
            quante = letto.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
            letto.close()
        _check(r, cat, 'nella copia del database ci sono le fatture', quante, 1)
        copia_reg = next((c for c in copie if c.endswith('.json')), None)
        _check(r, cat, 'e c’è anche il registro delle sedute',
               leggi_json(copia_reg) if copia_reg else None, REGISTRO)
        _check(r, cat, 'un database in memoria non ha niente da copiare',
               M.copia_di_sicurezza(_db_servizi()), [])

        # --- la copia si fa una volta sola, anche se il guaio si ripete ---
        # Trovato dalla revisione: senza questo controllo, un guaio che si
        # ripete a ogni avvio scrive una copia nuova ogni volta (mai piu'
        # necessaria: un tentativo fallito non cambia il database), riempiendo
        # il disco in una cartella che la pulizia delle copie non tocca.
        percorso_db2 = os.path.join(tmp, 'due-tentativi', 'fatture.db')
        os.makedirs(os.path.dirname(percorso_db2))
        con = sqlite3.connect(percorso_db2)
        con.row_factory = sqlite3.Row
        con.executescript(D.SCHEMA)
        D._migrate(con)
        popola(con, IMPOSTAZIONI, RIGHE)
        con.execute('DROP TABLE servizi_testi')
        con.commit()
        cartella2 = os.path.join(os.path.dirname(percorso_db2), 'backups', M.CARTELLA_COPIE)
        tentativi = []

        def copia_finta(con, registro_path=None):
            # Una copia vera sul disco (cosi' il controllo di esegui() la
            # trova per davvero), ma col nome deciso da qui, non dall'orologio:
            # due chiamate ravvicinate avrebbero lo stesso secondo, e il
            # guasto da vedere rosso non si vedrebbe.
            tentativi.append(1)
            os.makedirs(cartella2, exist_ok=True)
            percorso = os.path.join(cartella2, f'fatture-{len(tentativi)}.db')
            io.open(percorso, 'wb').close()
            return [percorso]

        vera_copia = M.copia_di_sicurezza
        M.copia_di_sicurezza = copia_finta
        errori.disabled = True
        try:
            M.esegui(con, percorso_registro)
            M.esegui(con, percorso_registro)
        finally:
            M.copia_di_sicurezza = vera_copia
            errori.disabled = False
        con.close()
        _check(r, cat, 'due tentativi falliti di fila lasciano una sola copia, non due',
               len(glob.glob(os.path.join(cartella2, 'fatture-*.db'))), 1)

        # --- un tentativo interrotto non lascia mai una copia col nome finale ---
        # Trovato dalla revisione: sqlite3.connect(copia) crea gia' il file
        # fatture-....db, prima ancora che con.backup ne copi una sola
        # pagina; se il tentativo si ferma li' (disco pieno, processo ucciso,
        # database bloccato) quel file resta, e _copia_gia_fatta lo scambia
        # per una copia buona - non se ne fa mai piu' una vera. Qui si
        # interrompe subito dopo che il database e' stato scritto per intero
        # (durante la copia del registro, che viene dopo): anche in questo
        # caso, meno grave di un backup a meta', il nome finale non deve
        # comparire finche' anche il registro non e' stato copiato.
        percorso_db3 = os.path.join(tmp, 'interrotto', 'fatture.db')
        os.makedirs(os.path.dirname(percorso_db3))
        con = sqlite3.connect(percorso_db3)
        con.row_factory = sqlite3.Row
        con.executescript(D.SCHEMA)
        D._migrate(con)
        popola(con, IMPOSTAZIONI, RIGHE)
        cartella3 = os.path.join(os.path.dirname(percorso_db3), 'backups', M.CARTELLA_COPIE)

        vero_copy2 = M.shutil.copy2
        chiamate = []

        def copy2_che_si_rompe(src, dst):
            chiamate.append(1)
            if len(chiamate) == 1:
                raise OSError('disco pieno (simulato)')
            return vero_copy2(src, dst)

        M.shutil.copy2 = copy2_che_si_rompe
        errori.disabled = True
        try:
            interrotta = _senza_scoppiare(lambda: M.esegui(con, percorso_registro))
        finally:
            M.shutil.copy2 = vero_copy2
            errori.disabled = False
        _check(r, cat, 'un tentativo interrotto dopo aver scritto il database non riesce',
               interrotta, False)
        _check(r, cat, 'e non lascia nessun fatture-....db col nome finale',
               glob.glob(os.path.join(cartella3, 'fatture-*.db')), [])
        _check(r, cat, 'il tentativo dopo rifa’ davvero la copia',
               M.esegui(con, percorso_registro), True)
        copie3 = glob.glob(os.path.join(cartella3, 'fatture-*.db'))
        _check(r, cat, 'stavolta il file finale c’è, uno solo', len(copie3), 1)
        vera = sqlite3.connect(copie3[0]) if copie3 else None
        _check(r, cat, 'e si apre come sqlite, con dentro tutte le fatture',
               vera.execute('SELECT COUNT(*) FROM invoices').fetchone()[0] if vera else None,
               len(RIGHE))
        if vera:
            vera.close()
        con.close()

        # --- parte da sola all'avvio ---
        # Le regole vuote con fatture presenti fanno scrivere a _migrate le
        # regole di chi ha scritto l'app: qui si vede che non diventano servizi.
        vero_db, vero_registro = D.DB_PATH, S.REGISTRY
        try:
            D.DB_PATH = os.path.join(tmp, 'avvio', 'fatture.db')
            S.REGISTRY = os.path.join(tmp, 'avvio', 'sessions.json')   # il registro vero non si legge
            os.makedirs(os.path.dirname(D.DB_PATH))
            con = sqlite3.connect(D.DB_PATH)
            con.row_factory = sqlite3.Row
            con.executescript(D.SCHEMA)
            D._migrate(con)
            con.execute("INSERT INTO settings(key, value) VALUES('servizi', 'Lezione privata')")
            fid = con.execute("INSERT INTO invoices(number, client_name, date) "
                              "VALUES(1, 'Giulia Ferrari', '2026-06-10')").lastrowid
            con.execute("INSERT INTO items(invoice_id, description, total_cents) "
                        "VALUES(?, 'Lezione privata', 12000)", (fid,))
            con.commit()
            con.close()
            con = D.init()
            _check(r, cat, 'all’avvio l’app fa la migrazione da sola, con la copia prima',
                   (M.fatta(con), listino(con),
                    os.path.isdir(os.path.join(tmp, 'avvio', 'backups', M.CARTELLA_COPIE))),
                   (True, [('Lezione privata', 12000, 0, 0)], True))
            con.close()
        finally:
            D.DB_PATH, S.REGISTRY = vero_db, vero_registro

    # --- i «clienti a crediti» diventano clienti (spec §4) ---
    con = _db_servizi()
    for riga in (
            (1, 'giulia-ferrari', 'Giulia Ferrari', 'Via Roma 1', '8001 Zürich',
             'giulia@example.com', 'it', 'formale', 'G. Ferrari'),
            (2, 'sofia-verdi', 'Sofia Verdi', '', '', '', 'en', 'informale', ''),
            (3, 'sofia-neri', 'Sofia Neri', '', '', '', 'en', 'informale', ''),
            (4, 'elena-rossi', 'Elena Rossi', '', '', '', 'de', 'informale', '')):
        con.execute('INSERT INTO clients(id, key, name, address1, address2, email, lingua, tono, '
                    'paga_come) VALUES(?,?,?,?,?,?,?,?,?)', riga)
    for numero, cliente in ((4, 1), (5, 3)):
        con.execute("INSERT INTO invoices(number, client_id, client_name, date) "
                    "VALUES(?, ?, 'x', '2026-05-01')", (numero, cliente))
    for riga in (('giulia', 'Giulia', '', '', 1, 0),
                 ('marco', 'Marco', 'Giulia Ferrari', 'giulia', 1, 1),
                 ('sofia', 'Sofia', '', '', 1, 2),
                 ('elena', 'Elena R.', '', '', 1, 3),
                 ('luca', 'Luca', '', '', 0, 4)):
        con.execute('INSERT INTO crediti_clienti(chiave, nome, fattura_a, compagno, attivo, pos) '
                    'VALUES(?,?,?,?,?,?)', riga)
    con.commit()
    REG_CLIENTI = {'pacchetti': [
        {'id': 'GIU-01', 'cliente': 'Giulia + Marco', 'fattura_numero': 4, 'crediti': 10},
        {'id': 'SOF-01', 'cliente': 'Sofia', 'fattura_numero': 5, 'crediti': 12},
    ]}
    _check(r, cat, 'cinque clienti a crediti: tre trovati, un supplemento nuovo, un ex cliente archiviato',
           _senza_scoppiare(lambda: M.clienti_da_crediti(con, REG_CLIENTI)), (3, 1, 1))
    chi = {c['chiave_sedute']: c
           for c in con.execute("SELECT * FROM clients WHERE COALESCE(chiave_sedute, '') <> ''")}
    _check(r, cat, 'chi ha lo stesso primo nome riceve la chiave; il nome nel calendario solo se è '
                   'diverso — e con la vecchia chiave in coda se da sola non si riconoscerebbe più '
                   '(revisione I2)',
           [(k, chi[k]['id'], chi[k]['nome_calendario']) for k in ('giulia', 'elena') if k in chi],
           [('giulia', 1, ''), ('elena', 4, 'Elena R., elena')])
    _check(r, cat, 'fra due Sofia vince quella delle fatture dei suoi pacchetti',
           chi['sofia']['id'] if 'sofia' in chi else None, 3)
    marco = chi.get('marco')
    _check(r, cat, 'il supplemento nasce con indirizzo, email, lingua e tono di chi paga',
           tuple(marco[k] for k in ('name', 'address1', 'address2', 'email', 'lingua', 'tono',
                                    'intestatario', 'paga_come', 'archived')) if marco else None,
           ('Marco', 'Via Roma 1', '8001 Zürich', 'giulia@example.com', 'it', 'formale',
            'Giulia Ferrari', 'G. Ferrari', 0))
    _check(r, cat, 'e si allena con lei', marco['compagno_id'] if marco else None, 1)
    _check(r, cat, 'l’ex cliente nasce archiviato, con solo nome e chiave',
           (chi['luca']['name'], chi['luca']['archived'], chi['luca']['address1'])
           if 'luca' in chi else None, ('Luca', 1, ''))

    # --- revisione I2: i vecchi titoli del calendario si riconoscono ancora ---
    # «Elena R.» è il nome che finisce sulla scheda, ma i vecchi titoli
    # usavano solo la chiave («Elena», «Elena pt»): la migrazione deve
    # tenerli riconoscibili tutti, non solo chi ha gia' il nome giusto.
    prima_config = S._CONFIG
    try:
        S.configura([dict(x) for x in D.clienti_sedute(con)])
        for vecchia_chiave in ('giulia', 'marco', 'sofia', 'elena', 'luca'):
            _check(r, cat, f'dopo la migrazione «{vecchia_chiave.capitalize()}» si riconosce '
                           f'ancora come «{vecchia_chiave}»',
                   S.classifica(vecchia_chiave.capitalize())[0], vecchia_chiave)
        _check(r, cat, 'e anche un titolo come «Elena pt», non solo la chiave da sola',
               S.classifica('Elena pt')[0], 'elena')
    finally:
        S._CONFIG = prima_config

    quanti = con.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
    _check(r, cat, 'la seconda volta non cambia niente',
           (M.clienti_da_crediti(con, REG_CLIENTI),
            con.execute('SELECT COUNT(*) FROM clients').fetchone()[0]), ((0, 0, 0), quanti))
    _check(r, cat, 'la tabella vecchia resta com’era',
           con.execute('SELECT COUNT(*) FROM crediti_clienti').fetchone()[0], 5)

    # --- le chiavi sui pacchetti del registro, dopo il database ---
    with tempfile.TemporaryDirectory() as tmp:
        percorso = os.path.join(tmp, 'sessions.json')
        registro = {'pacchetti': [
            {'id': 'GIU-01', 'cliente': 'Giulia + Marco', 'crediti': 10,
             'sessioni': [{'n': 1, 'data': '2026-08-01', 'titolo': 'Giulia e Marco'}]},
            {'id': 'SOF-01', 'cliente': 'Sofia', 'chiavi': ['sofia'], 'crediti': 12, 'sessioni': []},
            {'id': 'XXX-01', 'cliente': 'Qualcuno', 'crediti': 10, 'sessioni': []},
            # scritto col vecchio nome, non con «Elena R.» che finisce sulla scheda
            # (revisione I2): deve prendere la chiave lo stesso.
            {'id': 'ELE-01', 'cliente': 'Elena', 'crediti': 8, 'sessioni': []},
        ], 'esclusi': []}
        with open(percorso, 'w', encoding='utf-8') as f:
            json.dump(registro, f)
        _check(r, cat, 'un database senza clienti con le sedute non tocca il registro',
               (_senza_scoppiare(M.chiavi_nel_registro, _db_servizi(), percorso),
                leggi_json(percorso)), (0, registro))
        _check(r, cat, 'le chiavi vanno sui pacchetti che non le hanno',
               _senza_scoppiare(M.chiavi_nel_registro, con, percorso), 2)
        dopo = leggi_json(percorso)
        _check(r, cat, 'un pacchetto diviso ne riceve due, e le sedute restano quelle',
               (dopo['pacchetti'][0].get('chiavi'), dopo['pacchetti'][0]['sessioni']),
               (['giulia', 'marco'], registro['pacchetti'][0]['sessioni']))
        _check(r, cat, 'chi le aveva già e chi non si riconosce restano come prima',
               (dopo['pacchetti'][1], 'chiavi' in dopo['pacchetti'][2]),
               (registro['pacchetti'][1], False))
        _check(r, cat, 'un pacchetto scritto col vecchio nome «Elena» prende comunque la sua '
                       'chiave (revisione I2)',
               dopo['pacchetti'][3].get('chiavi'), ['elena'])
        copie = os.path.join(tmp, 'data', 'backups')
        _check(r, cat, 'prima di riscrivere il registro se ne fa la copia',
               len(os.listdir(copie)) if os.path.isdir(copie) else 0, 1)

        # tutto in fila, dalla migrazione: prima il cliente, poi il registro
        con2 = _db_servizi()
        con2.execute("INSERT INTO clients(id, key, name) VALUES(1, 'giulia-ferrari', 'Giulia Ferrari')")
        con2.execute("INSERT INTO crediti_clienti(chiave, nome) VALUES('giulia', 'Giulia')")
        con2.commit()
        percorso2 = os.path.join(tmp, 'altro.json')
        with open(percorso2, 'w', encoding='utf-8') as f:
            json.dump({'pacchetti': [{'id': 'GIU-01', 'cliente': 'Giulia', 'crediti': 10,
                                      'sessioni': []}], 'esclusi': []}, f)
        _senza_scoppiare(M.esegui, con2, percorso2, False)
        _check(r, cat, 'la migrazione dà la chiave al cliente e poi la scrive sui suoi pacchetti',
               (con2.execute('SELECT chiave_sedute FROM clients WHERE id=1').fetchone()[0],
                leggi_json(percorso2)['pacchetti'][0].get('chiavi')), ('giulia', ['giulia']))
        con2.close()
    con.close()

    # --- gli abbonamenti trovano il loro servizio (spec §4) ---
    from . import recurring as RC
    from .language import MESI_DOC
    con = _db_servizi()
    for riga in ((1, 'giulia', 'Giulia Ferrari', 'en'), (2, 'marco', 'Marco Neri', 'de'),
                 (3, 'sofia', 'Sofia Verdi', 'en'), (4, 'luca', 'Luca Bianchi', 'it')):
        con.execute('INSERT INTO clients(id, key, name, lingua) VALUES(?,?,?,?)', riga)
    for nome, prezzo, ogni_mese in ((MENSILE, 11000, 1), ('Coaching', 5000, 1),
                                    ('Online Coaching', 9000, 1), ('Personal training', 12000, 0)):
        con.execute('INSERT INTO servizi(nome, prezzo_cents, ogni_mese, sedute, scadenza_mesi, passano, '
                    "massimo, attivo, pos, creato_il) VALUES(?,?,?,0,0,0,0,1,0,'2026-09-14')",
                    (nome, prezzo, ogni_mese))
    sid = {s['nome']: s['id'] for s in con.execute('SELECT id, nome FROM servizi')}
    for numero, cliente, cents in ((1, 1, 11000), (2, 3, 10000)):
        fid = con.execute("INSERT INTO invoices(number, client_id, client_name, date, year, total_cents) "
                          "VALUES(?, ?, 'x', '2026-08-13', 2026, ?)", (numero, cliente, cents)).lastrowid
        con.execute("INSERT INTO items(invoice_id, pos, qty, description, unit_cents, total_cents, "
                    "servizio_id) VALUES(?, 0, '1', ?, ?, ?, ?)",
                    (fid, MENSILE + ' 13.08.26 – 12.09.26', cents, cents, sid[MENSILE]))
    REGOLE = (
        (1, 1, MENSILE + ' {dal} – {al}', 11000, 13),          # le date, identiche
        (2, 2, 'Online Coaching ({mese})', 9000, 1),           # il mese; vince il nome più lungo
        (3, 3, MENSILE + ' {dal} – {al}', 11000, 13),          # l'ultima riga era scontata
        (4, 4, 'Personal training – {mese} {anno}', 12000, 1),  # solo un servizio «una volta»
        (5, 1, MENSILE + ' {dal} - {al}', 11000, 1),           # trattino corto: non è la forma esatta
    )
    for regola in REGOLE:
        con.execute("INSERT INTO ricorrenti(id, client_id, descrizione, importo_cents, giorno, dal, attiva) "
                    "VALUES(?,?,?,?,?,'2026-01',1)", regola)
    con.commit()
    lingue = {x['id']: x['lingua_cliente'] for x in RC.regole(con)}
    prima_righe = {i: (RC.descrizione_per(testo, '2026-10', MESI_DOC[lingue[i]], giorno), cents)
                   for i, _cliente, testo, cents, giorno in REGOLE}

    _check(r, cat, 'gli abbonamenti trovano il servizio nel testo; lo stile solo se la riga resta identica',
           _senza_scoppiare(M.abbonamenti, con), (4, 2))
    _check(r, cat, 'servizio e stile di ogni regola',
           [(x['id'], x['servizio_id'], x['stile'])
            for x in con.execute('SELECT id, servizio_id, stile FROM ricorrenti ORDER BY id')],
           [(1, sid[MENSILE], 'date'), (2, sid['Online Coaching'], 'mese'), (3, sid[MENSILE], ''),
            (4, None, ''), (5, sid[MENSILE], '')])
    _check(r, cat, 'le righe delle prossime fatture restano quelle di prima, importi compresi',
           _senza_scoppiare(lambda: {x['id']: RC.riga_per(con, x, '2026-10',
                                                          MESI_DOC[x['lingua_cliente']])[:2]
                                     for x in RC.regole(con)}), prima_righe)
    _check(r, cat, 'la seconda volta non cambia niente', _senza_scoppiare(M.abbonamenti, con), (0, 0))
    _check(r, cat, 'la migrazione converte anche gli abbonamenti',
           'abbonamenti(con)' in inspect.getsource(M.esegui), True)
    con.close()

    from . import importer
    _check(r, cat, 'dopo un Reimporta le righe ritrovano il loro servizio',
           _senza_scoppiare(lambda: 'srv.collega_righe(con)' in inspect.getsource(importer.import_all)),
           True)

    # --- Controlli: «So già» non spegne un guaio che si ripara da solo ---
    # Trovato dalla revisione: la chiave di quell'anomalia e' sempre la stessa
    # (stats.py: 'servizi:migrazione'), quindi un solo clic su «So già» ne
    # nasconderebbe ogni guaio futuro, non solo quello di oggi.
    import jinja2
    base_pagine = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'templates')
    with io.open(os.path.join(base_pagine, 'checks.html'), encoding='utf-8') as f:
        sorgente_checks = f.read()
    inizio_ciclo = sorgente_checks.index('{% for i in issues %}')
    fine_ciclo = sorgente_checks.index('{% endfor %}', inizio_ciclo) + len('{% endfor %}')
    ambiente = jinja2.Environment()
    ambiente.globals.update(pallino=lambda *a, **k: '', icona=lambda *a, **k: '',
                             url_for=lambda *a, **k: '#', _=lambda s: s)
    reso = ambiente.from_string(sorgente_checks[inizio_ciclo:fine_ciclo]).render(issues=[
        {'kind': 'servizi', 'key': 'servizi:migrazione',
         'msg': 'Aggiornamento dei servizi non riuscito', 'fixable': False, 'inv_id': None},
        {'kind': 'dati', 'key': 'dati:1', 'msg': 'manca la data', 'detail': '',
         'fixable': True, 'inv_id': 1},
    ])
    blocchi = reso.split('<div class="issue ')[1:]
    _check(r, cat, 'niente pulsante «So già» per l’anomalia dei servizi (si ripara da sola), '
                   'ma per le altre anomalie resta',
           [('So già' in b) for b in blocchi], [False, True])

    # --- chi chiama init() nelle prove non deve leggere il registro vero ---
    # init() fa girare la migrazione da solo (Passo 4): una prova che scambia
    # solo D.DB_PATH e non anche S.REGISTRY fa leggere - e a volte copiare,
    # se il database ha una fattura - il registro delle sedute di chi usa
    # l'app davvero.
    def prove_con_init_senza_registro(sorgente):
        intestazioni = list(re.finditer(r'\ndef (_test_\w+)\(', sorgente))
        fuori = []
        for i, m in enumerate(intestazioni):
            fine = intestazioni[i + 1].start() if i + 1 < len(intestazioni) else len(sorgente)
            corpo = sorgente[m.start():fine]
            if re.search(r'\.init\(', corpo) and '.REGISTRY = ' not in corpo:
                fuori.append(m.group(1))
        return fuori

    with io.open(os.path.abspath(__file__), encoding='utf-8') as f:
        sorgente_prove = f.read()
    _check(r, cat, 'chi chiama init() nelle prove sposta anche il registro delle sedute, '
                   'non solo il database',
           prove_con_init_senza_registro(sorgente_prove), [])


def _test_servizi_riconosciuti(r):
    """Quali servizi l'app riconosce nelle righe della fattura.

    Prima erano tre, scritti nel programma: quelli di chi l'app l'aveva
    scritta per se'. Chiunque altro si vedeva chiamare il proprio lavoro col
    nome del suo. Adesso le regole sono un'impostazione, e questi controlli
    servono a due cose: che chi le scrive ottenga quello che si aspetta, e che
    chi non le ha ancora scritte non si veda inventare niente.
    """
    from . import services as S
    from . import mailer, db

    mio = {'servizi_abbonamento': 'Running Coaching = running coaching\n'
                                  'Online Coaching = coaching online',
           'servizi_pacchetto': 'Personal Training = session, personal training'}

    # --- come si legge una riga ---
    _check(r, 'Servizi', 'la riga «Nome = parole» si legge tutta',
           S._regola('Fisioterapia = seduta, fisio'), ('Fisioterapia', ['seduta', 'fisio']))
    _check(r, 'Servizi', 'senza «=» il nome fa anche da parola',
           S._regola('Osteopatia'), ('Osteopatia', ['osteopatia']))
    _check(r, 'Servizi', 'una riga vuota non e\' una regola', S._regola('   '), None)
    _check(r, 'Servizi', 'gli spazi attorno alle parole non contano',
           S._regola('Massaggio =  a ,  b '), ('Massaggio', ['a', 'b']))

    # --- l'ordine: gli abbonamenti si provano per primi ---
    _check(r, 'Servizi', 'prima gli abbonamenti, poi i pacchetti',
           [n for n, _m, _p in S.regole(mio)],
           ['Running Coaching', 'Online Coaching', 'Personal Training'])
    _check(r, 'Servizi', 'ogni servizio porta con se\' il suo modello',
           [m for _n, m, _p in S.regole(mio)], ['coaching', 'coaching', 'pt'])

    # --- riconoscere ---
    _check(r, 'Servizi', 'riconosce l\'abbonamento e sa che e\' un abbonamento',
           S.riconosci('Monthly abo: running coaching (August)', mio),
           ('Running Coaching', 'coaching'))
    _check(r, 'Servizi', 'riconosce il pacchetto',
           S.riconosci('10 Sessions Pack', mio), ('Personal Training', 'pt'))
    _check(r, 'Servizi', 'le maiuscole non contano',
           S.riconosci('COACHING ONLINE - agosto', mio), ('Online Coaching', 'coaching'))
    _check(r, 'Servizi', 'quello che non e\' scritto non viene riconosciuto',
           S.riconosci('Consulenza nutrizionale', mio), (None, None))
    _check(r, 'Servizi', 'senza regole scritte non si indovina niente',
           S.riconosci('Monthly abo: running coaching', {}), (None, None))
    _check(r, 'Servizi', 'una riga vuota non riconosce niente',
           S.riconosci('', mio), (None, None))

    # --- un altro mestiere, con le sue parole ---
    fisio = {'servizi_abbonamento': 'Riabilitazione = riabilitazione',
             'servizi_pacchetto': 'Fisioterapia = seduta, sedute, fisioterapia'}
    _check(r, 'Servizi', 'un fisioterapista riconosce le proprie righe',
           S.riconosci('Pacchetto 10 sedute di fisioterapia', fisio),
           ('Fisioterapia', 'pt'))
    _check(r, 'Servizi', 'e le sue righe non diventano quelle di un altro',
           S.riconosci('Pacchetto 10 sedute di fisioterapia', mio), (None, None))

    # --- e l'email che ne esce: il nome lo dà il servizio collegato ---
    # Le regole qui sopra servono ormai solo alla migrazione (core/migra_servizi.py).
    inv = _Finta(number=99, total_cents=110000, pdf_path='', source_file='',
                 client_name='Sofia Ferrari')
    cli = _Finta(name='Sofia Ferrari', email='s@esempio.ch', abbonamento=0, tono='informale')
    fisioterapia = {'nome': 'Fisioterapia', 'ogni_mese': 0}
    corpo = mailer.componi(inv, cli, dict(db.DEFAULT_SETTINGS),
                           ['Pacchetto 10 sedute di fisioterapia'], servizio=fisioterapia)['body']
    _check(r, 'Servizi', 'il fisioterapista fattura a nome suo, non di un altro',
           'Please find attached your invoice for Fisioterapia.' in corpo, True)
    vuote = mailer.componi(inv, cli, dict(db.DEFAULT_SETTINGS),
                           ['Pacchetto 10 sedute di fisioterapia'])['body']
    _check(r, 'Servizi', 'senza servizio collegato l\'email non nomina nessun servizio',
           'Please find attached your invoice.' in vuote, True)



def _test_primi_passi(r):
    """Un'app appena installata deve dire da dove si comincia, e smettere di
    dirlo appena non serve piu'."""
    import sqlite3
    import tempfile
    from . import welcome as B, branding
    from .db import DEFAULT_SETTINGS

    # il passo del logo guarda il file vero: qui si guarda altrove, altrimenti
    # il controllo dipende da chi lo sta eseguendo
    logo_vero = branding.PERSONALE
    branding.PERSONALE = os.path.join(tempfile.gettempdir(), 'logo-che-non-esiste.png')
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(
        'CREATE TABLE clients(id INTEGER PRIMARY KEY, archived INTEGER DEFAULT 0);'
        'CREATE TABLE invoices(id INTEGER PRIMARY KEY, deleted_at TEXT);'
        'CREATE TABLE servizi(id INTEGER PRIMARY KEY, nome TEXT);')

    vuoto = B.passi(con, dict(DEFAULT_SETTINGS))
    # Appena installata, l'unica cosa gia' fatta e' quella che ha fatto l'app
    # per te: il bollettino QR, che ora e' acceso di serie. Tutto il resto
    # dipende da chi la usa e deve risultare da fare. La prova e' scritta
    # cosi', e non come «zero fatti», perche' un domani che si spegnesse il
    # bollettino o se ne accendesse un altro, questa riga lo direbbe.
    fatti = [p['chiave'] for p in vuoto if p['fatto']]
    _check(r, 'Primi passi', 'appena installata l’unica cosa fatta è quella che fa l’app',
           fatti, ['qr'])
    _check(r, 'Primi passi', 'e quindi resta da fare tutto il resto',
           B.avanzamento(vuoto), (1, len(vuoto)))
    _check(r, 'Primi passi', 'appena installata manca l\'essenziale',
           B.manca_l_essenziale(vuoto), True)
    _check(r, 'Primi passi', 'ogni passo sa dove mandarti',
           [p['chiave'] for p in vuoto if not p['dove']], [])
    _check(r, 'Primi passi', '«I tuoi servizi» porta a Servizi, e i pacchetti non sono più un passo a parte',
           ({p['chiave']: p['dove'] for p in vuoto}.get('servizi'),
            [p['chiave'] for p in vuoto if p['chiave'] == 'crediti']), ('servizi', []))

    # --- dove ti manda il primo passo ------------------------------------
    # Mandava in Impostazioni: 61 campi, sei schermate, cinque bottoni Salva,
    # e tocca a te trovare i sette che servono. E' il motivo per cui installare
    # quest'app a qualcun altro e' stato difficile. Adesso c'e' una pagina che
    # chiede quei sette e nient'altro, e i due passi obbligatori portano li'.
    dove = {p['chiave']: p['dove'] for p in vuoto}
    _check(r, 'Primi passi', 'i due passi obbligatori portano alla pagina corta',
           (dove.get('attivita'), dove.get('iban')), ('primi_dati', 'primi_dati'))
    _check(r, 'Primi passi', 'e il logo arriva sul suo riquadro, non in cima a tutto',
           [p.get('ancora') for p in vuoto if p['chiave'] == 'logo'], ['logo'])

    # La pagina corta deve chiedere TUTTO quello che finisce sulla fattura e
    # sul bollettino QR. Se un domani si aggiunge una riga alla testata e ci si
    # dimentica di questa pagina, chi installa l'app si trova una fattura
    # incompleta e nessuno glielo dice: e' il guasto che questa prova esiste
    # per impedire.
    from . import docgen as _dg
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'templates', 'first_setup.html'),
                 encoding='utf-8') as f:
        modulo = f.read()
    chiesti = set(re.findall(r'name="([a-z_0-9]+)"', modulo))
    servono = set(_dg.RIGHE_MITTENTE.values()) | {'business_iban'}
    _check(r, 'Primi passi', 'la pagina corta chiede tutto quello che va sulla fattura',
           sorted(servono - chiesti), [])
    _check(r, 'Primi passi', 'e non chiede nient\'altro che i dati e il tuo nome',
           sorted(chiesti - servono - {'torna', 'owner_first_name', 'owner_last_name'}), [])

    # i dati dell'attivita' senza IBAN non bastano: la fattura uscirebbe senza
    # il conto su cui incassare
    mezzo = dict(DEFAULT_SETTINGS, business_name='Studio Bianchi',
                 business_addr1='Via Roma 1', business_addr2='6900 Lugano')
    _check(r, 'Primi passi', "senza IBAN manca ancora l'essenziale",
           B.manca_l_essenziale(B.passi(con, mezzo)), True)

    pieno = dict(mezzo, business_iban='CH5604835012345678009')
    passi = B.passi(con, pieno)
    _check(r, 'Primi passi', "con nome, indirizzo e IBAN l'essenziale c'è",
           B.manca_l_essenziale(passi), False)
    _check(r, 'Primi passi', 'ma resta ancora qualcosa da fare',
           len(B.da_fare(passi)) > 0, True)

    # Le due righe qui sopra dicono che in quel momento le due domande danno
    # risposte OPPOSTE: «puo' gia' fare una fattura?» si', «ha finito tutti i
    # passi?» no. Quindi chi saluta l'utente dopo il salvataggio deve fare la
    # prima, non la seconda — se no il messaggio che dice «sei pronto» non
    # compare mai, perche' fra i passi ce n'e' uno che si chiama «La prima
    # fattura» e prima di farla non puo' essere fatto.
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        sorgente = f.read()
    saluto = re.search(r'if torna in RITORNI:(.{0,400}?)avvisa\(', sorgente, re.S)
    _check(r, 'Primi passi', 'dopo il salvataggio si chiede se puoi fatturare, non se hai finito',
           ('manca_l_essenziale' in saluto.group(1),
            'da_fare' in saluto.group(1)), (True, False))

    # le cose non essenziali si spuntano da sole quando succedono
    con.execute('INSERT INTO clients(id, archived) VALUES(1, 0)')
    con.execute('INSERT INTO invoices(id, deleted_at) VALUES(1, NULL)')
    con.execute("INSERT INTO servizi(nome) VALUES('Lezione privata')")
    dopo = {p['chiave']: p['fatto'] for p in B.passi(con, pieno)}
    for chiave in ('clienti', 'fattura', 'servizi'):
        _check(r, 'Primi passi', f'«{chiave}» si spunta da solo', dopo[chiave], True)
    # un cliente archiviato non conta come cliente
    con.execute('UPDATE clients SET archived = 1')
    _check(r, 'Primi passi', 'un cliente archiviato non conta',
           {p['chiave']: p['fatto'] for p in B.passi(con, pieno)}['clienti'], False)
    branding.PERSONALE = logo_vero
    con.close()


def _sorgenti(cartella, estensione):
    """Il testo di tutti i file di un tipo, con il nome davanti."""
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cartella)
    fuori = {}
    for nome in sorted(os.listdir(base)):
        if nome.endswith(estensione):
            with io.open(os.path.join(base, nome), encoding='utf-8') as f:
                fuori[nome] = f.read()
    return fuori


def _test_icone(r):
    """I disegni al posto delle emoji.

    Il rischio di un'icona sbagliata non e' che si veda male: e' che non si
    veda affatto, perche' icona() con un nome che non esiste non disegna
    niente pur di non far saltare la pagina. Qui si controlla che tutti i nomi
    usati nelle pagine esistano davvero.
    """
    import xml.etree.ElementTree as ET
    from . import icons as I

    modelli = _sorgenti('templates', '.html')
    tutto = '\n'.join(modelli.values())

    # ogni disegno e' un pezzo di XML valido, dentro la stessa cornice
    rotti, fuori_cornice = [], []
    for nome in I.nomi():
        try:
            ET.fromstring('<svg>%s</svg>' % I.DISEGNI[nome])
        except Exception:
            rotti.append(nome)
        marcatura = str(I.icona(nome))
        if 'viewBox="0 0 24 24"' not in marcatura or 'stroke="currentColor"' not in marcatura:
            fuori_cornice.append(nome)
    _check(r, 'Icone', 'tutti i disegni sono XML valido', rotti, [])
    _check(r, 'Icone', 'tutti stanno nello stesso quadrato e prendono il colore del testo',
           fuori_cornice, [])

    # ogni nome usato nelle pagine esiste
    usati = set(re.findall(r"icona\(\s*'([a-z_]+)'", tutto))
    usati |= {v[2] for v in menu.voci()}
    usati |= set(re.findall(r"'(?:fattura|email|errore|sessione|crediti)':\s*'([a-z_]+)'", tutto))
    _check(r, 'Icone', 'nessuna pagina chiede un disegno che non esiste',
           sorted(usati - set(I.nomi())), [])
    _check(r, 'Icone', 'ci sono disegni da usare', len(usati) > 15, True)

    # niente disegni tenuti da parte «per dopo»
    # «voci()» e non «GRUPPI»: le pagine di servizio sono uscite dalla barra ma
    # esistono ancora, e le loro icone si vedono da Impostazioni.
    citati = {n for n in I.nomi() if ("'%s'" % n) in tutto or n in str(menu.voci())}
    _check(r, 'Icone', 'nessun disegno rimasto inutilizzato',
           sorted(set(I.nomi()) - citati), [])

    # un nome sbagliato non fa saltare la pagina
    _check(r, 'Icone', 'un nome inventato non rompe la pagina', str(I.icona('nonesiste')), '')

    # Un disegno e' un pezzo di SVG pieno di virgolette. Se lo si infila dentro
    # un attributo (data-icona="{{ icona(...) }}") la prima virgoletta chiude
    # l'attributo e il browser butta via il resto, disegno e frase insieme. E'
    # gia' successo una volta e non se n'e' accorto nessuno per mesi: il
    # riquadro non compariva e basta.
    dentro_attributo = []
    for pagina, sorgente in _sorgenti_pagine():
        for pezzo in re.finditer(r'[a-z-]+="[^"]*\{\{[^}]*icona\(', sorgente):
            dentro_attributo.append((pagina, pezzo.group(0)[:40]))
    _check(r, 'Icone', 'nessun disegno infilato dentro un attributo',
           sorted(dentro_attributo), [])

    # i pallini di stato
    _check(r, 'Icone', 'il pallino verde ha la sua classe',
           'class="pallino verde"' in str(I.pallino('verde')), True)
    _check(r, 'Icone', 'il pallino spiega cosa vuol dire',
           'title="ha pagato"' in str(I.pallino('verde', 'ha pagato')), True)
    _check(r, 'Icone', 'un colore inventato ripiega sul pallino vuoto',
           'pallino vuoto' in str(I.pallino('fucsia')), True)
    _check(r, 'Icone', 'il titolo del pallino non puo\' iniettare marcatura',
           '<b>' in str(I.pallino('verde', '<b>x</b>')), False)

    # nelle pagine non devono restare emoji colorate
    faccine = re.compile('[\U0001F300-\U0001FAFF\U0001F004-\U0001F0CF]')
    # la pagina dell'errore tiene la sua faccina: li' non e' un'icona, e' il
    # tono con cui l'app si scusa, ed e' l'unico punto dove serve una faccia
    with_emoji = sorted(n for n, t in modelli.items()
                        if n != 'error.html' and faccine.search(t))
    _check(r, 'Icone', 'nessuna emoji colorata rimasta nelle pagine', with_emoji, [])
    _check(r, 'Icone', "la faccina resta solo nella pagina dell'errore",
           bool(faccine.search(modelli['error.html'])), True)
    js = _sorgenti('static', '.js')
    _check(r, 'Icone', 'nessuna emoji colorata rimasta nel codice delle pagine',
           sorted(n for n, t in js.items() if faccine.search(t)), [])


def _test_menu(r):
    """Il menu di sinistra: gruppi, ordine e voce accesa."""
    from . import menu as M

    endpoint = [v[0] for v in M.voci()]
    _check(r, 'Menu', 'nessuna voce ripetuta', len(endpoint), len(set(endpoint)))

    # ogni voce punta a una pagina che esiste davvero
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        programma = f.read()
    pagine = set(re.findall(r'^def ([a-z_0-9]+)\(', programma, re.M))
    _check(r, 'Menu', 'ogni voce porta a una pagina che esiste',
           sorted(set(endpoint) - pagine), [])

    # una pagina non puo' accendere due voci insieme
    acceso = {}
    doppie = []
    for e, _etichetta, _disegno, attivo in M.voci():
        for pagina in attivo:
            if pagina in acceso:
                doppie.append(pagina)
            acceso[pagina] = e
    _check(r, 'Menu', 'nessuna pagina accende due voci insieme', sorted(doppie), [])
    _check(r, 'Menu', 'ogni voce accende almeno se stessa',
           [e for e, _t, _d, a in M.voci() if e not in a], [])

    # le pagine di dettaglio devono accendere la voce del loro elenco:
    # senza, aprendo una fattura il menu si spegne e non si capisce dove si e'
    _check(r, 'Menu', 'la scheda di una fattura accende «Fatture»',
           acceso.get('fattura'), 'fatture')
    _check(r, 'Menu', "l'email di una fattura accende «Fatture»",
           acceso.get('fattura_email'), 'fatture')
    _check(r, 'Menu', 'una mail letta accende «Email inviate»',
           acceso.get('email_letta'), 'email_inviate')
    _check(r, 'Menu', 'un pacchetto accende «Crediti»',
           acceso.get('crediti_pacchetto'), 'crediti')
    _check(r, 'Menu', '«Clienti a crediti» non è più una pagina: non accende niente',
           acceso.get('crediti_clienti'), None)
    _check(r, 'Menu', 'le righe senza servizio accendono «Servizi»',
           acceso.get('servizi_righe'), 'servizi')

    _check(r, 'Menu', 'le voci stanno in gruppi con un titolo',
           [t for t, _ in M.GRUPPI if t], ['Fatturare', 'Chi segui', 'Incassi e fisco', "L'app"])
    chi_segui = next(v for t, v in M.GRUPPI if t == 'Chi segui')
    _check(r, 'Menu', 'Servizi sta fra Clienti e Crediti',
           [e for e, _t, _d, _a in chi_segui], ['clienti', 'servizi', 'crediti', 'agenda'])
    _check(r, 'Menu', 'la Dashboard sta in cima, fuori dai gruppi',
           M.GRUPPI[0][0] is None and M.GRUPPI[0][1][0][0] == 'dashboard', True)
    _check(r, 'Menu', 'i primi passi stanno fuori dai gruppi fissi',
           M.PRIMI_PASSI[0], 'benvenuto')

    # --- la barra dice solo quello che serve oggi -------------------------
    # Un posto fisso in barra si legge tutte le volte. Le pagine di
    # manutenzione ci stavano dentro per farsi aprire tre volte l'anno, e
    # «Controlli» ci stava anche quando non aveva niente da dire — che e' il
    # modo migliore perche' nessuno lo guardi il giorno che ne ha.
    def in_barra(n=0):
        return [v[0] for _titolo, elenco in M.gruppi(n) for v in elenco]

    _check(r, 'Menu', 'a conti in ordine la barra non nomina i controlli',
           'controlli' in in_barra(0), False)
    _check(r, 'Menu', 'con un\'anomalia i controlli tornano in barra',
           'controlli' in in_barra(1), True)
    _check(r, 'Menu', 'e portano scritto quante ne hanno trovate',
           [v[1] for _t, elenco in M.gruppi(3) for v in elenco if v[0] == 'controlli'],
           ['Controlli (3)'])
    _check(r, 'Menu', 'compaiono in fondo, nel gruppo dell\'app',
           [v[0] for t, elenco in M.gruppi(2) if t == "L'app" for v in elenco],
           ['controlli', 'impostazioni'])
    _check(r, 'Menu', 'la verifica dei calcoli non sta in barra',
           'verifica' in in_barra(9), False)
    _check(r, 'Menu', 'e nemmeno il cestino',
           'cestino' in in_barra(9), False)
    _check(r, 'Menu', 'ma restano pagine vere, con nome e icona',
           sorted(v[0] for v in M.FUORI_MENU), ['cestino', 'controlli', 'verifica'])
    _check(r, 'Menu', 'e i controlli le conoscono lo stesso',
           {'cestino', 'verifica'} <= {v[0] for v in M.voci()}, True)
    _check(r, 'Menu', 'la barra tranquilla ha tredici voci, tre meno di prima',
           len(in_barra(0)), 13)


def _etichette_scollegate():
    """[(pagina, quante)] per le etichette che non nominano nessun campo.

    Un <label> vale qualcosa solo se e' legato al suo campo: o lo avvolge, o
    ha un «for» che punta al suo id. Senza, a schermo si vede lo stesso — ed
    e' per questo che nessuno se ne accorge — ma cliccarlo non porta il cursore
    nel campo, e chi legge la pagina con la voce invece che con gli occhi si
    trova davanti a caselle senza nome.
    """
    import glob
    etichetta = re.compile(r'<label(?![^>]*\bfor=)([^>]*)>((?:(?!</label>).)*)</label>', re.S)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuori = []
    for percorso in sorted(glob.glob(os.path.join(base, 'templates', '*.html'))):
        with io.open(percorso, encoding='utf-8') as f:
            testo = f.read()
        quante = sum(1 for m in etichetta.finditer(testo)
                     if not re.search(r'<(input|select|textarea)', m.group(2)))
        if quante:
            fuori.append((os.path.basename(percorso), quante))
    return fuori


def _id_ripetuti():
    """{pagina: [id scritti due volte]}. Due campi con lo stesso id sono peggio
    di nessun id: il clic sull'etichetta porta sempre sul primo dei due, e il
    secondo campo resta muto per chi legge la pagina con la voce.

    Si guardano solo gli id scritti per intero. Quelli che finiscono con un
    {{ ... }} cambiano a ogni giro del ciclo o a ogni chiamata del macro,
    quindi vederli due volte nel sorgente non vuol dire niente: a quelli
    pensa la regola qui sotto.
    """
    fissi = lambda testo: [i for i in re.findall(r'\bid="([^"]*)"', testo)
                           if '{{' not in i]
    modelli = _sorgenti('templates', '.html')
    di_base = fissi(modelli.get('base.html', ''))
    fuori = {}
    for nome, testo in modelli.items():
        suoi = fissi(testo)
        if nome != 'base.html' and "extends 'base.html'" in testo:
            suoi = suoi + di_base       # la pagina eredita anche gli id di base
        doppi = sorted(k for k in set(suoi) if suoi.count(k) > 1)
        if doppi:
            fuori[nome] = doppi
    return fuori


def _id_fissi_nei_cicli():
    """{pagina: [id scritti dentro un ciclo senza farli variare]}.

    E' il modo piu' facile di crearsi un id doppio senza accorgersene: uno lo
    scrive una volta sola, ma la pagina lo stampa per ogni cliente in elenco.
    """
    fuori = {}
    for nome, testo in _sorgenti('templates', '.html').items():
        prof, dentro = 0, []
        for m in re.finditer(r'\{%-?\s*(for|endfor)\b|\bid="([^"]*)"', testo):
            if m.group(1) == 'for':
                prof += 1
            elif m.group(1) == 'endfor':
                prof -= 1
            elif prof > 0 and '{{' not in (m.group(2) or ''):
                dentro.append(m.group(2))
        if dentro:
            fuori[nome] = dentro
    return fuori


def _campi_senza_nome():
    """{pagina: [campi che non hanno nessun nome addosso]}.

    Il setaccio delle etichette guarda le etichette, e quindi non vede il caso
    opposto e piu' grave: un campo su cui nessuno ha mai scritto un'etichetta.
    E' successo davvero, nella barra dei filtri di «Fatture»: tre caselle —
    anno, stato, cerca — che a occhio si capiscono benissimo, e che chi legge
    la pagina con la voce sentiva annunciare come «menu a tendina», punto.

    Un nome vale, in qualunque delle quattro forme: l'etichetta col «for»,
    l'etichetta che avvolge il campo, aria-label, title.
    """
    campo = re.compile(r'<(input|select|textarea)\b([^>]*)>', re.S)

    def valore(tag, nome):
        m = re.search(r'\b%s="([^"]*)"' % nome, tag)
        return m.group(1) if m else None

    fuori = {}
    for pagina, testo in _sorgenti('templates', '.html').items():
        nominati = set(re.findall(r'<label[^>]*\bfor="([^"]*)"', testo))
        senza = []
        for m in campo.finditer(testo):
            tag = m.group(0)
            if valore(tag, 'type') in ('hidden', 'submit', 'button'):
                continue        # non sono campi da riempire
            suo_id = valore(tag, 'id')
            ha_nome = ((suo_id and suo_id in nominati)
                       or valore(tag, 'aria-label') or valore(tag, 'title'))
            if not ha_nome:      # ...o e' l'etichetta stessa a contenerlo
                prima = testo[:m.start()]
                ha_nome = prima.rfind('<label') > prima.rfind('</label>')
            if not ha_nome:
                senza.append(re.sub(r'\s+', ' ', tag)[:90])
        if senza:
            fuori[pagina] = senza
    return fuori


def _parole_del_vuoto(pezzo):
    """Il testo che una pagina dice quando non ha niente da elencare.

    Delle frasi tradotte tiene il contenuto e butta l'involucro: _('...')
    e' quello che l'utente legge, i tag e i {% %} no.
    """
    frasi = re.findall(r"""_\(\s*(['"])(.+?)\1""", pezzo, re.S)
    return ' '.join(f[1] for f in frasi).strip()


def _cicli_di_tabella_scoperti():
    """{pagina: [cicli che, se non hanno niente da stampare, non dicono nulla]}.

    Una tabella con le intestazioni e nessuna riga sotto non e' «vuota»: e'
    muta. Chi ha appena installato l'app non sa se e' rotta, se sta ancora
    caricando o se ha sbagliato qualcosa lui. Il primo giorno succedeva in
    «Fatture» e in «Clienti», che sono due delle prime pagine che si aprono.

    Un ciclo e' a posto in due modi, e valgono uguale: un {% else %} che dice
    cosa non c'e' ancora, oppure un {% if %} intorno che fa sparire tutta la
    sezione — se non c'e' niente da mostrare, non mostrare niente e' una
    risposta onesta.
    """
    etichetta = re.compile(r'\{%-?\s*(for|else|endfor|if|elif|endif)\b.*?-?%\}', re.S)
    fuori = {}
    for pagina, testo in _sorgenti('templates', '.html').items():
        pila_if, pila_for, scoperti = [], [], []
        for m in etichetta.finditer(testo):
            tipo, a, b = m.group(1), m.start(), m.end()
            if tipo == 'if':
                pila_if.append(a)
            elif tipo == 'endif':
                if pila_if:
                    pila_if.pop()
            elif tipo == 'for':
                pila_for.append({'a': a, 'corpo': b, 'else': False,
                                 'in_if': len(pila_if)})
            elif tipo == 'else':
                # l'else di un if non e' l'else del for: contano solo quelli
                # allo stesso livello di annidamento
                if pila_for and pila_for[-1]['in_if'] == len(pila_if):
                    pila_for[-1]['else'] = b
            elif tipo == 'endfor':
                if not pila_for:
                    continue
                blocco = pila_for.pop()
                if '<tr' not in testo[blocco['corpo']:a] or blocco['in_if']:
                    continue
                # un {% else %} che non dice niente lascia la pagina muta
                # uguale: quello che conta e' la frase, non il ramo
                detto = _parole_del_vuoto(testo[blocco['else']:a]) if blocco['else'] else ''
                if len(detto) < 40:
                    scoperti.append(testo[blocco['a']:blocco['corpo']].strip()
                                    + (' (else muto)' if blocco['else'] else ''))
        if scoperti:
            fuori[pagina] = scoperti
    return fuori


# Le pagine che si aprono col menu il primo giorno, quando dentro non c'e'
# ancora niente. Qui la tabella E' la pagina: nasconderla lascerebbe il vuoto
# assoluto, quindi ci vuole per forza una frase che dica cosa succedera'.
PAGINE_DEL_PRIMO_GIORNO = ('invoices.html', 'clients.html', 'accountant.html',
                           'sessions.html', 'email_sent.html',
                           'services.html', 'subscriptions.html')


def _test_qr_di_serie(r):
    """Il bollettino QR e\' acceso di serie — ma solo per chi installa oggi.

    Il bollettino e\' la cosa che rende svizzera quest\'app, e finche\' era
    spento chi la comprava non sapeva nemmeno che ci fosse. Ora e\' acceso di
    default. Il punto delicato e\' l\'altro meta\': init() rifa\' l\'INSERT OR
    IGNORE dei default a OGNI avvio, non solo al primo, quindi un default
    nuovo si propaga da solo anche a chi usa l\'app da mesi — e i suoi clienti
    si troverebbero in mano un documento diverso senza che nessuno gliel\'abbia
    detto. Il bollettino lo accende chi fattura, non un aggiornamento.

    Le cinque situazioni, tutte reali:
    """
    import sqlite3
    import shutil
    import tempfile
    from . import db as D
    from . import sessions as S

    fattura = ("INSERT INTO invoices(id, number, client_name) "
               "VALUES(1, 1, 'Tizio');")
    casi = [
        ('appena installata',                    '',                              '1'),
        ('configurata, nessuna fattura ancora',
         "INSERT INTO settings(key,value) VALUES('business_name','X');",          '1'),
        ('gia\' in uso, casella mai toccata',
         "INSERT INTO settings(key,value) VALUES('business_name','A');" + fattura, '0'),
        ('gia\' in uso, acceso a mano',
         "INSERT INTO settings(key,value) VALUES('qr_fattura','1');" + fattura,   '1'),
        ('gia\' in uso, spento a mano apposta',
         "INSERT INTO settings(key,value) VALUES('qr_fattura','0');" + fattura,   '0'),
    ]
    vero = D.DB_PATH
    vero_registro = S.REGISTRY
    cartella = tempfile.mkdtemp()
    try:
        S.REGISTRY = os.path.join(cartella, 'sessions.json')   # il registro vero non si legge
        for i, (nome, prima, atteso) in enumerate(casi):
            D.DB_PATH = os.path.join(cartella, 'p%d.db' % i)
            if prima:
                con = sqlite3.connect(D.DB_PATH)
                con.executescript(D.SCHEMA)
                con.executescript(prima)
                con.commit()
                con.close()
            con = D.init()
            avuto = D.get_settings(con).get('qr_fattura')
            con.close()
            _check(r, 'QR di serie', nome, avuto, atteso)
    finally:
        D.DB_PATH = vero
        S.REGISTRY = vero_registro
        shutil.rmtree(cartella, ignore_errors=True)

    # ...e la prova che il caso «appena installata» non e\' truccato: su un
    # database nuovo in settings una riga c\'e\' gia\', messa da una migrazione.
    # Guardare «c\'e\' qualcosa in settings?» per capire se l\'app e\' gia\' in uso
    # spegnerebbe quindi anche le installazioni nuove. Ci sono cascato davvero.
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'core', 'db.py'), encoding='utf-8') as f:
        sorgente = f.read()
    corpo = sorgente[sorgente.index('def _migra_qr_gia_installato'):]
    corpo = corpo[:corpo.index('def init(')]
    _check(r, 'QR di serie', 'per capire se l\'app e\' in uso guarda le fatture, non le impostazioni',
           ('FROM invoices' in corpo, 'FROM settings LIMIT' in corpo), (True, False))


def _test_pagine_vuote(r):
    """Il primo giorno nessuna di queste pagine deve restare muta."""
    scoperti = _cicli_di_tabella_scoperti()
    for pagina in PAGINE_DEL_PRIMO_GIORNO:
        _check(r, 'Primo giorno', 'in %s il vuoto e\' spiegato, non subito' % pagina,
               scoperti.get(pagina, []), [])

    # Le altre otto sono tabelle che vuote non ci vanno mai — le righe della
    # verifica, quelle di una fattura, le voci della salute. Il numero puo'
    # solo scendere: se sale, e' comparsa una tabella nuova che tace.
    _check(r, 'Primo giorno', 'i cicli scoperti non aumentano',
           sum(len(v) for v in scoperti.values()) <= 8, True)


def _test_etichette(r):
    """Le etichette dei moduli devono nominare davvero il loro campo."""
    # Non piu' «quasi tutte» e non piu' solo nelle pagine principali: in tutta
    # l'app ogni etichetta nomina il suo campo. Le ultime sono state le piu'
    # noiose, perche' stavano dentro un ciclo e li' l'id deve cambiare riga
    # per riga; le due che restavano non nominavano un campo ma un gruppo di
    # caselle, e per quelle il tag giusto e' <legend> dentro un <fieldset>.
    _check(r, 'Etichette', 'nessuna etichetta scollegata, in nessuna pagina',
           _etichette_scollegate(), [])

    # ...cosa che sarebbe vera anche se il setaccio si fosse rotto e non
    # trovasse piu' niente. Le etichette ci sono, e sono tante.
    _check(r, 'Etichette', 'il setaccio le etichette continua a vederle',
           sum(t.count('<label') for t in
               _sorgenti('templates', '.html').values()) > 80, True)

    # Legare l'etichetta al campo con un id apre un guaio nuovo, e queste due
    # regole lo chiudono prima che nasca.
    _check(r, 'Etichette', 'nessun id ripetuto nella stessa pagina',
           _id_ripetuti(), {})
    _check(r, 'Etichette', 'nessun id che dentro un ciclo resta sempre uguale',
           _id_fissi_nei_cicli(), {})

    # E il caso opposto, quello che il setaccio delle etichette non poteva
    # vedere: un campo su cui nessuno ha mai scritto un'etichetta.
    _check(r, 'Etichette', 'nessun campo senza un nome addosso',
           _campi_senza_nome(), {})


def _test_finestra_stretta(r):
    """Cosa deve reggere quando la finestra e' stretta.

    L'app non si apre dal telefono, ma la finestra si tiene volentieri a meta'
    schermo. Il guaio non e' che diventi brutta: e' che la pagina scorra di
    lato, perche' allora il menu scompare e per leggere l'ultima colonna devi
    trascinare tutto. Qui si controllano le tre cose da cui dipende.
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'static', 'style.css'), encoding='utf-8') as f:
        stile = f.read()

    def regola(selettore):
        m = re.search(re.escape(selettore) + r'\s*\{(.*?)\}', stile, re.S)
        return m.group(1) if m else ''

    # 1. senza min-width:0 un elemento flessibile non si stringe sotto la
    #    larghezza del suo contenuto, e una tabella larga allarga la pagina
    _check(r, 'Finestra stretta', 'la parte centrale puo\' stringersi',
           'min-width: 0' in regola('main'), True)

    # 2. il contenuto troppo largo deve scorrere dentro il suo riquadro
    _check(r, 'Finestra stretta', 'i riquadri fanno scorrere dentro di se\'',
           'overflow-x: auto' in regola('.panel'), True)

    # 3. ...il che serve a qualcosa solo se le tabelle stanno nei riquadri
    modelli = _sorgenti('templates', '.html')
    sfuse = {n: _tabelle_fuori_dai_riquadri(t) for n, t in modelli.items()}
    _check(r, 'Finestra stretta', 'ogni tabella sta dentro un riquadro',
           sorted(n for n, q in sfuse.items() if q), [])
    _check(r, 'Finestra stretta', 'di tabelle ce ne sono, non e\' un controllo a vuoto',
           sum(t.count('<table') for t in modelli.values()) > 20, True)

    # le soglie: dalla piu' larga alla piu' stretta, senza buchi
    soglie = [int(x) for x in re.findall(r'@media \(max-width: (\d+)px\)', stile)]
    _check(r, 'Finestra stretta', 'le soglie sono in ordine dalla piu\' larga',
           soglie, sorted(soglie, reverse=True))
    _check(r, 'Finestra stretta', 'il menu diventa una colonnina di icone',
           1040 in soglie, True)


def _tabelle_fuori_dai_riquadri(testo):
    """Quante tabelle non hanno un «panel» sopra di loro."""
    senza_jinja = re.sub(r'\{[%{].*?[%}]\}', '', testo, flags=re.S)
    pila, fuori = [], 0
    for m in re.finditer(r'<(/?)(div|table)\b([^>]*)>', senza_jinja):
        chiusura, tag, attr = m.groups()
        if tag == 'table':
            if not chiusura and not any('panel' in c for c in pila):
                fuori += 1
        elif chiusura:
            if pila:
                pila.pop()
        elif not attr.rstrip().endswith('/'):
            cls = re.search(r'class="([^"]*)"', attr)
            pila.append(cls.group(1) if cls else '')
    return fuori


def _test_calendario(r):
    """L'iCal descrive le serie in modo compatto: espanderle bene e' delicato."""
    import datetime
    from . import calendar_feed as C

    # il nome del calendario lo dice il calendario: cosi' nel programma non
    # resta scritto come si chiama quello di nessuno
    _check(r, 'Calendario', 'il calendario dice come si chiama', C.nome(CAL_PROVA),
           'Allenamenti')
    _check(r, 'Calendario', 'un calendario senza nome non ne inventa uno',
           C.nome('BEGIN:VCALENDAR\nEND:VCALENDAR'), '')

    # --- il fuso orario, che su Windows non c'e' di serie ---
    # Un DTSTART che finisce per Z e' in UTC e va riportato all'ora di Zurigo.
    # Serve il database dei fusi: il Mac e Linux ce l'hanno di sistema, Windows
    # NO. Senza, «FUSO» resta None e l'ora torna in UTC senza dirlo: una
    # sessione delle 07:30 comparirebbe alle 05:30. Un errore che non si vede.
    _check(r, 'Calendario', 'un orario in UTC diventa l’ora di Zurigo (estate, +2)',
           C._ora('20260414T053000Z'), '07:30')
    _check(r, 'Calendario', 'e d’inverno +1',
           C._ora('20260114T053000Z'), '06:30')
    _check(r, 'Calendario', 'un orario già locale non si tocca',
           C._ora('20260414T073000'), '07:30')
    _check(r, 'Calendario', 'il fuso c’è davvero, non si è ripiegato sul niente',
           C.FUSO is not None, True)
    # Questo e' l'unico che protegge Windows: qui il fuso funziona comunque,
    # perche' il database ce l'ha il sistema. Su Windows arriva solo se
    # «tzdata» resta fra le librerie richieste — e questo lo si vede solo
    # guardando il file, non facendo girare il programma.
    _requisiti = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
    with io.open(_requisiti, encoding='utf-8') as _f:
        _elenco = _f.read()
    _check(r, 'Calendario', 'e su Windows ci arriva, perché «tzdata» è fra le librerie',
           any(x.strip().startswith('tzdata') for x in _elenco.splitlines()), True)
    _check(r, 'Calendario', 'il nome si legge anche se la riga e\' spezzata in due',
           C.nome('BEGIN:VCALENDAR\nX-WR-CALNAME:Alle\n namenti PT\nEND:VCALENDAR'),
           'Allenamenti PT')

    ev = C.leggi(CAL_PROVA, datetime.date(2026, 8, 20), datetime.date(2026, 9, 10),
                 e_testo=True)
    date = lambda t: sorted(e['data'] for e in ev if e['titolo'].startswith(t))

    _check(r, 'Calendario', 'i martedì di Marco si espandono',
           date('Marco'), ['2026-08-25', '2026-09-08'])
    _check(r, 'Calendario', 'la data in EXDATE (01.09) non compare',
           '2026-09-01' in date('Marco'), False)
    _check(r, 'Calendario', 'la sessione disdetta resta ma marcata cancellata',
           [e['stato_google'] for e in ev if e['data'] == '2026-08-27'], ['cancelled'])
    _check(r, 'Calendario', 'la virgola scritta come \\, torna normale',
           any(', spostata' in e['titolo'] for e in ev), True)
    _check(r, 'Calendario', "l'identificativo è UID + data, non solo UID",
           [e['id'] for e in ev if e['data'] == '2026-08-25'], ['tizio@g::2026-08-25'])
    _check(r, 'Calendario', 'rileggere lo stesso calendario dà gli stessi id '
           '(niente doppi conteggi)',
           [e['id'] for e in C.leggi(CAL_PROVA, datetime.date(2026, 8, 20),
                                     datetime.date(2026, 9, 10), e_testo=True)],
           [e['id'] for e in ev])
    _check(r, 'Calendario', 'fuori finestra non si legge niente',
           C.leggi(CAL_PROVA, datetime.date(2026, 1, 1), datetime.date(2026, 1, 31),
                   e_testo=True), [])
    _check(r, 'Calendario', 'un file illeggibile non fa esplodere niente',
           C.leggi('roba a caso', datetime.date(2026, 8, 20),
                   datetime.date(2026, 8, 31), e_testo=True), [])

    # --- l'ora, che serve all'Agenda ---
    _check(r, 'Calendario', "l'ora di inizio si legge dalla serie",
           [e['ora'] for e in ev if e['data'] == '2026-08-25'], ['07:30'])
    _check(r, 'Calendario', "ogni ripetizione eredita l'ora della serie",
           sorted({e['ora'] for e in ev if e['titolo'].startswith('Marco')}), ['07:30'])
    _check(r, 'Calendario', 'ora scritta in UTC riportata a quella svizzera',
           C._ora('20260825T053000Z'), '07:30')
    _check(r, 'Calendario', 'ora con fuso esplicito presa così com\'è',
           C._ora('20260825T073000'), '07:30')
    _check(r, 'Calendario', 'evento di sola giornata: nessuna ora inventata',
           C._ora('20260825'), None)

    # --- le serie che finiscono ---
    # Quando una serie con un fuso ha una fine, ogni calendario la scrive in
    # UTC: Google, Apple e Outlook, come vuole lo standard. dateutil non
    # mescola un inizio senza fuso con una fine in UTC, e la serie intera si
    # riduceva alla sua prima seduta: le altre non venivano mai contate.
    def serie(corpo):
        testo = ('BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:serie@prova\r\nSUMMARY:Anna\r\n'
                 + corpo + 'END:VEVENT\r\nEND:VCALENDAR\r\n')
        return [e['data'] for e in C.leggi(testo, datetime.date(2026, 8, 1),
                                           datetime.date(2026, 9, 30), e_testo=True)]

    _check(r, 'Calendario', 'una serie che finisce conta tutte le sue sedute, non solo la prima',
           serie('DTSTART;TZID=Europe/Zurich:20260803T070000\r\n'
                 'RRULE:FREQ=WEEKLY;UNTIL=20260830T215959Z;BYDAY=MO\r\n'),
           ['2026-08-03', '2026-08-10', '2026-08-17', '2026-08-24'])
    # Outlook scrive come fine l'inizio esatto dell'ultima seduta: quella c'e'
    _check(r, 'Calendario', 'l’ultima seduta resta dentro anche se la fine è la sua ora esatta',
           serie('DTSTART;TZID=W. Europe Standard Time:20260804T070000\r\n'
                 'RRULE:FREQ=WEEKLY;UNTIL=20260825T050000Z;INTERVAL=1;BYDAY=TU;WKST=MO\r\n'),
           ['2026-08-04', '2026-08-11', '2026-08-18', '2026-08-25'])
    # le 22:30 in UTC del 25 sono le 00:30 del 26 a Zurigo: conta il giorno svizzero
    _check(r, 'Calendario', 'la fine scritta in UTC si legge col giorno svizzero',
           serie('DTSTART;TZID=Europe/Zurich:20260805T003000\r\n'
                 'RRULE:FREQ=WEEKLY;UNTIL=20260825T223000Z\r\n'),
           ['2026-08-05', '2026-08-12', '2026-08-19', '2026-08-26'])
    _check(r, 'Calendario', 'una serie di giornate intere arriva fino al suo ultimo giorno',
           serie('DTSTART;VALUE=DATE:20260821\r\nRRULE:FREQ=WEEKLY;UNTIL=20260904\r\n'),
           ['2026-08-21', '2026-08-28', '2026-09-04'])

    # --- i link di Apple ---
    # Il calendario pubblico di iCloud da' un indirizzo webcal://, che e'
    # https:// con un altro nome. urllib non lo conosce e lo rifiutava.
    _check(r, 'Calendario', 'un link webcal:// (Apple) si scarica come https://',
           _senza_scoppiare(lambda: [C._da_scaricare(u) for u in (
               'webcal://p01-caldav.icloud.com/published/2/abc',
               'WEBCAL://esempio.ch/sedute.ics',
               'webcals://esempio.ch/sedute.ics',
               'https://calendar.google.com/calendar/ical/x/basic.ics')]),
           ['https://p01-caldav.icloud.com/published/2/abc',
            'https://esempio.ch/sedute.ics',
            'https://esempio.ch/sedute.ics',
            'https://calendar.google.com/calendar/ical/x/basic.ics'])
    # e scarica() lo usa davvero: dove nessuno risponde deve fallire perche'
    # non trova nessuno, non perche' non capisce l'indirizzo
    _check(r, 'Calendario', 'e il download lo usa davvero',
           'unknown url type' in _senza_scoppiare(C.scarica, 'webcal://127.0.0.1:9/sedute.ics', 1),
           False)

    _test_agenda(r)


def _test_agenda(r):
    """L'agenda mette insieme due fonti: registro (quali) e calendario (a che ora)."""
    from . import schedule as A

    reg = {'pacchetti': [
        {'id': 'X-01', 'cliente': 'Tizia', 'crediti': 10, 'fattura_numero': 7,
         'sessioni': [
             {'n': 1, 'data': '2026-08-18', 'titolo': 'Tizia', 'cancellata': False},
             {'n': 2, 'data': '2026-08-20', 'titolo': 'Tizia', 'cancellata': True},
             {'n': 3, 'data': '2026-08-20', 'titolo': 'Tizia', 'cancellata': False,
              'ora': '18:00'},
         ]},
        {'id': 'Y-01', 'cliente': 'Caio', 'crediti': 12, 'sessioni': [
            {'n': 1, 'data': '2025-03-01', 'titolo': 'Caio', 'cancellata': False}]},
    ]}
    orari = {A._chiave('2026-08-18', 'Tizia'): '07:30'}
    righe = A.elenco(reg, orari)

    _check(r, 'Agenda', 'ci sono tutte le sessioni del registro', len(righe), 4)
    _check(r, 'Agenda', 'la più recente sta in cima', righe[0]['data'], '2026-08-20')
    _check(r, 'Agenda', "l'ora arriva dall'indice del calendario",
           [x['ora'] for x in righe if x['data'] == '2026-08-18'], ['07:30'])
    _check(r, 'Agenda', "l'ora scritta nella sessione batte l'indice",
           righe[0]['ora'], '18:00')
    _check(r, 'Agenda', 'senza ora non se ne inventa una',
           [x['ora'] for x in righe if x['data'] == '2025-03-01'], [None])
    _check(r, 'Agenda', 'la sessione annullata resta (ha consumato il credito)',
           sum(1 for x in righe if x['cancellata']), 1)
    _check(r, 'Agenda', 'il numero di fattura del pacchetto arriva in riga',
           righe[0]['fattura'], 7)
    _check(r, 'Agenda', 'filtro per cliente',
           [x['cliente'] for x in A.elenco(reg, orari, cliente='caio')], ['Caio'])
    _check(r, 'Agenda', 'filtro per anno',
           len(A.elenco(reg, orari, anno='2026')), 3)
    _check(r, 'Agenda', 'gli anni disponibili sono quelli veri',
           A.anni(reg), ['2026', '2025'])
    _check(r, 'Agenda', 'il riepilogo conta le sessioni con orario',
           A.riepilogo(righe)['con_ora'], 2)

    _test_registro_email(r)


def _test_registro_email(r):
    """Il registro delle email si prova su un database usa e getta."""
    import sqlite3
    from .db import SCHEMA

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    ins = ('INSERT INTO email_log(sent_at, destinatario, fatture, prova, esito, motivo, '
           'ccn, corpo) VALUES(?,?,?,?,?,?,?,?)')
    con.execute(ins, ('2026-08-21T10:00:00', 'a@b.ch', '84', 0, 'ok', '', 'io@b.ch',
                      'Dear X,\n\nriga due\n'))
    con.execute(ins, ('2026-08-21T11:00:00', 'io@b.ch', '84', 1, 'ok', '', '', 'prova'))
    con.execute(ins, ('2026-08-21T12:00:00', 'a@b.ch', '85', 0, 'errore', 'timeout', '', ''))

    conta = lambda q: con.execute('SELECT COUNT(*) c FROM email_log' + q).fetchone()['c']
    _check(r, 'Email inviate', 'la tabella esiste e accetta le righe', conta(''), 3)
    _check(r, 'Email inviate', 'le prove si separano da quelle ai clienti',
           conta(' WHERE prova=0'), 2)
    _check(r, 'Email inviate', 'i tentativi falliti restano scritti',
           conta(" WHERE esito='errore'"), 1)
    _check(r, 'Email inviate', 'la più recente viene per prima',
           con.execute('SELECT sent_at FROM email_log ORDER BY sent_at DESC, id DESC '
                       'LIMIT 1').fetchone()['sent_at'], '2026-08-21T12:00:00')
    prima = con.execute('SELECT * FROM email_log ORDER BY id LIMIT 1').fetchone()
    _check(r, 'Email inviate', 'il testo si rilegge tale e quale, a capo compresi',
           prima['corpo'], 'Dear X,\n\nriga due\n')
    _check(r, 'Email inviate', 'la copia nascosta resta scritta', prima['ccn'], 'io@b.ch')
    con.close()

    # le intestazioni salvate sono quelle vere, e la prova non ha la copia nascosta
    import app as APP
    from .db import DEFAULT_SETTINGS as S
    msg = {'body': 'ciao'}
    i = APP._intestazioni(msg, dict(S, email_copia_a_me='1'), None)
    _check(r, 'Email inviate', "l'invio al cliente registra la copia nascosta",
           i['ccn'], S['smtp_user'])
    i2 = APP._intestazioni(msg, dict(S, email_copia_a_me='1'), 'io@esempio.ch')
    _check(r, 'Email inviate', 'la prova a te stesso non ha copia nascosta da registrare',
           i2['ccn'], '')
    i3 = APP._intestazioni(msg, dict(S, email_copia_a_me='0'), None)
    _check(r, 'Email inviate', 'copia nascosta spenta: non si scrive niente', i3['ccn'], '')

    _test_cruscotto(r)
    _test_invio_saltato(r)


def _test_invio_saltato(r):
    """«Questa non va spedita»: una fattura che esiste ma non parte.

    Non tutte le fatture sono fatte per essere mandate. Una emessa perche' il
    cliente aveva pagato di piu' serve alla contabilita', non a lui. Senza un
    modo di dirlo, l'app ricorda per sempre di spedire una cosa che hai deciso
    di non spedire — e un promemoria che si sbaglia insegna a non guardare i
    promemoria, il che rovina anche quelli giusti.
    """
    from . import overview as C
    import datetime
    oggi = datetime.date.today()
    ieri = (oggi - datetime.timedelta(days=1)).isoformat()

    def da_mandare(righe):
        return C.stato_fatture(_db_fatture_finto(righe), oggi.year)['da_mandare']

    _check(r, 'Non va spedita', 'una fattura fatta qui e mai spedita e\' da fare',
           da_mandare([{'data': ieri}]), 1)
    _check(r, 'Non va spedita', 'segnata «non va spedita», smette di esserlo',
           da_mandare([{'data': ieri, 'invio_saltato': '2026-09-09 10:00'}]), 0)
    _check(r, 'Non va spedita', 'e il ripensamento la rimette fra le cose da fare',
           da_mandare([{'data': ieri, 'invio_saltato': None}]), 1)
    _check(r, 'Non va spedita', 'una colonna vuota vale come non decisa',
           da_mandare([{'data': ieri, 'invio_saltato': ''}]), 1)
    _check(r, 'Non va spedita', 'una gia\' spedita non torna da fare per questo',
           da_mandare([{'data': ieri, 'sent_at': ieri,
                        'invio_saltato': '2026-09-09 10:00'}]), 0)
    _check(r, 'Non va spedita', 'e una importata non e\' mai stata da fare',
           da_mandare([{'data': ieri, 'source': 'import'}]), 0)

    # Il conto della Dashboard e il riquadro «Fatte e non ancora spedite» sono
    # la stessa cosa: se il primo scende a zero, il secondo deve sparire.
    voci = C.da_fare(_db_fatture_finto(
        [{'data': ieri, 'stato': 'pagata', 'paid_at': ieri,
          'invio_saltato': '2026-09-09 10:00'}]),
        {'banca_ultimo_estratto': oggi.isoformat()}, None)
    _check(r, 'Non va spedita', 'e il riquadro della Dashboard sparisce con lei',
           [v['chiave'] for v in voci if v['chiave'] == 'spedire'], [])


def _test_cruscotto(r):
    """I tre riquadri della Dashboard: contano e ordinano, non inventano."""
    import sqlite3
    import datetime
    from . import overview as C
    from . import db as _db
    from .db import SCHEMA, DEFAULT_SETTINGS as S

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)          # le colonne aggiunte dopo (sent_at, email...) servono qui
    ins = ('INSERT INTO invoices(number, client_name, date, year, total_cents, status, '
           'source, created_at, sent_at) VALUES(?,?,?,?,?,?,?,?,?)')
    con.execute(ins, (1, 'A', '2026-01-10', 2026, 100, 'pagata', 'app',
                      '2026-01-10T09:00:00', '2026-01-10T10:00:00'))
    con.execute(ins, (2, 'B', '2026-02-10', 2026, 100, 'emessa', 'app',
                      '2026-02-10T09:00:00', None))
    con.execute(ins, (3, 'C', '2026-03-10', 2026, 100, 'emessa', 'storico',
                      '2026-03-10T09:00:00', None))
    con.execute(ins, (4, 'D', '2025-03-10', 2025, 100, 'pagata', 'app',
                      '2025-03-10T09:00:00', None))
    # dicembre dell'anno prima: serve a provare che a gennaio il confronto
    # scavalchi l'anno invece di trovare zero
    con.execute(ins, (5, 'E', '2025-12-15', 2025, 700, 'pagata', 'app',
                      '2025-12-15T09:00:00', None))
    con.commit()

    st = C.stato_fatture(con, 2026)
    _check(r, 'Cruscotto', "l'anno chiesto è l'unico contato", st['totali'], 3)
    _check(r, 'Cruscotto', 'pagate e da incassare fanno il totale',
           st['pagate'] + st['da_incassare'], st['totali'])
    _check(r, 'Cruscotto', 'spedite: solo quelle con la data di invio', st['inviate'], 1)
    _check(r, 'Cruscotto', 'da mandare: le storiche non si contano (non si spediscono)',
           st['da_mandare'], 1)

    # salute: senza cartella di destinazione il backup è un problema, non un dettaglio
    sal = C.salute(con, dict(S, smtp_pass='', calendario_ics=''),
                   '/questa/cartella/non/esiste')
    voce = next(v for v in sal['voci'] if v['nome'] == 'Copia fuori dal Mac')
    _check(r, 'Cruscotto', 'backup mancante: rosso, non verde', voce['stato'], C.ROSSO)
    _check(r, 'Cruscotto', 'basta una voce rossa perché il riquadro lo dica',
           sal['stato'], C.ROSSO)

    reg = {'pacchetti': [{'id': 'X-01', 'cliente': 'Tizia', 'crediti': 10, 'rimasti': 0,
                          'fine': '2026-02-20', 'sessioni': [
                              {'n': 1, 'data': '2026-02-20', 'titolo': 'Tizia',
                               'cancellata': False, 'ora': '18:30'}]}]}
    voci = C.attivita(con, reg, quante=10)
    _check(r, 'Cruscotto', 'le fonti diverse finiscono in ordine di tempo',
           [v['quando'][:10] for v in voci], sorted([v['quando'][:10] for v in voci],
                                                    reverse=True))
    sess_ = next(v for v in voci if v['tipo'] == 'sessione')
    _check(r, 'Cruscotto', "l'ora vera della sessione arriva nel diario",
           sess_['quando'][11:16], '18:30')
    _check(r, 'Cruscotto', "il pacchetto finito compare senza un'ora inventata",
           next(v['ora_nota'] for v in voci if v['tipo'] == 'crediti'), False)
    _check(r, 'Cruscotto', 'un tempo di un\'ora si dice al singolare',
           C._eta((datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat())[1],
           'un’ora fa')

    # Il mese in corso accanto a quello prima. Le fatture qui sopra sono una
    # per mese da 1.00: gennaio, febbraio e marzo 2026, piu' marzo 2025.
    from . import stats as _stats
    m = _stats.mese_su_mese(con, 2026, 3)
    _check(r, 'Cruscotto', 'il mese si confronta con quello prima, non con l\'anno',
           (m['ora'], m['prima'], m['mese_prima']), (100, 100, 2))
    _check(r, 'Cruscotto', 'due mesi uguali danno una variazione di zero',
           m['delta_bp'], 0)
    g = _stats.mese_su_mese(con, 2026, 1)
    _check(r, 'Cruscotto', 'a gennaio il confronto guarda dicembre dell\'anno prima',
           (g['mese_prima'], g['anno_prima'], g['prima']), (12, 2025, 700))
    v = _stats.mese_su_mese(con, 2026, 6)
    _check(r, 'Cruscotto', 'senza un mese prima non si inventa una percentuale',
           v['delta_bp'], None)
    con.close()

    _test_saluto(r)

    _test_incassi(r)
    _test_banca(r)


def _test_saluto(r):
    """Il nome di chi usa l'app: e' suo, e non si ricava dall'attivita'."""
    from .db import DEFAULT_SETTINGS as S
    from . import language as L

    # Se sparissero da qui, il modulo delle Impostazioni smetterebbe di
    # salvarli senza dire niente: il salvataggio gira su DEFAULT_SETTINGS.
    _check(r, 'Cruscotto', 'nome e cognome sono due impostazioni vere',
           ('owner_first_name' in S, 'owner_last_name' in S), (True, True))
    _check(r, 'Cruscotto', 'di partenza sono vuoti, non inventati',
           (S.get('owner_first_name', '(manca)'), S.get('owner_last_name', '(manca)')),
           ('', ''))
    # «Ciao» da solo esiste apposta: senza nome la pagina non deve
    # scrivere «Ciao ,» con la virgola appesa al nulla.
    _check(r, 'Cruscotto', 'il saluto senza nome ha una frase sua',
           ('Ciao' in L.TESTI['en'], 'Ciao {nome}' in L.TESTI['en']), (True, True))
    # I mesi finiscono dentro una frase («su luglio»): l'italiano li vuole
    # minuscoli, il tedesco maiuscoli. Sbagliarlo si vede.
    _check(r, 'Cruscotto', 'i mesi dell\'app stanno dentro una frase, con la giusta iniziale',
           (L.mesi_app('it')[6], L.mesi_app('de')[6], L.mesi_app('en')[6]),
           ('luglio', 'Juli', 'July'))
    _check(r, 'Cruscotto', 'una lingua che non esiste torna ai mesi italiani',
           L.mesi_app('klingon')[0], 'gennaio')
    # Il titolo di un primo passo finisce dentro una frase della Dashboard.
    # Prima ci finiva in italiano e tutto minuscolo: in tedesco è sbagliato,
    # e una sigla come IBAN veniva rovinata.
    _check(r, 'Cruscotto', 'un titolo dentro una frase scende di maiuscola, ma non in tedesco',
           tuple(L.in_frase(L.t('Il tuo logo', c), c) for c in ('it', 'en', 'de')),
           ('il tuo logo', 'your logo', 'Dein Logo'))
    _check(r, 'Cruscotto', 'una sigla non si abbassa affatto',
           L.in_frase('IBAN e conto', 'it'), 'IBAN e conto')

    _check(r, 'Cruscotto', 'i giorni per esteso esistono in tutte e tre',
           tuple(L.giorni_app(c)[1] for c in ('it', 'en', 'de')),
           ('martedì', 'Tuesday', 'Dienstag'))
    # ogni lingua dispone la data come vuole: il tedesco vuole la virgola
    # dopo il giorno e il punto dopo il numero
    f = 'Ecco come vanno le cose oggi, {giorno} {n} {mese}.'
    _check(r, 'Cruscotto', 'la data del saluto si compone come vuole ogni lingua',
           L.t(f, 'de').format(giorno=L.giorni_app('de')[1], n=25, mese=L.mesi_app('de')[7]),
           'So stehen die Dinge heute, Dienstag, 25. August.')


CSV_PROVA = """Estratto conto;;;
Conto;CH93 0076 2011 6238 5295 7;;
;;;
Data contabile;Data valuta;Descrizione;Accredito;Addebito
02.08.2026;02.08.2026;E-Banking Auftrag Sofia Ferrari;110.00;
05.08.2026;05.08.2026;LSV Krankenkasse;;432.10
14.08.2026;14.08.2026;Zahlung Mueller Petra;2'000.00;
20.08.2026;20.08.2026;Gutschrift unbekannt;110.00;
"""

CAMT_PROVA = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.04"><BkToCstmrDbtCdtNtfctn><Ntfctn>
 <Ntry><Amt Ccy="CHF">1800.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-06-05</Dt></BookgDt>
  <NtryDtls><TxDtls><RltdPties><Dbtr><Nm>Bruno Keller</Nm></Dbtr></RltdPties></TxDtls></NtryDtls>
 </Ntry>
 <Ntry><Amt Ccy="CHF">55.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
  <BookgDt><Dt>2026-06-06</Dt></BookgDt></Ntry>
</Ntfctn></BkToCstmrDbtCdtNtfctn></Document>
"""


def _test_incassi(r):
    """La differenza fra «non pagata» e «non ancora verificabile»."""
    import sqlite3
    from . import db as _db
    from . import overview as C
    from .db import SCHEMA

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)
    ins = ('INSERT INTO invoices(number, client_name, date, year, total_cents, status, '
           'source) VALUES(?,?,?,?,?,?,"app")')
    con.execute(ins, (10, 'Tizia', '2026-01-10', 2026, 11000, 'emessa'))   # vecchia, scoperta
    con.execute(ins, (11, 'Tizia', '2026-07-25', 2026, 11000, 'emessa'))   # troppo recente
    con.execute(ins, (12, 'Tizia', '2026-08-20', 2026, 11000, 'emessa'))   # dopo l'estratto
    con.commit()

    m = C.incassi_mancanti(con, '2026-07-31')
    _check(r, 'Incassi', 'una fattura vecchia e scoperta è un ritardo vero',
           [x['number'] for x in m['in_ritardo']], [10])
    _check(r, 'Incassi', 'una fattura recente non è in ritardo, è solo da verificare',
           sorted(x['number'] for x in m['da_verificare']), [11, 12])
    _check(r, 'Incassi', 'il confine sono 45 giorni prima dell\'ultimo estratto',
           m['limite'], '2026-06-16')

    con.execute('UPDATE invoices SET paid_at="2026-02-01" WHERE number=10')
    con.commit()
    _check(r, 'Incassi', 'incassata: sparisce dai ritardi',
           C.incassi_mancanti(con, '2026-07-31')['in_ritardo'], [])

    senza = C.incassi_mancanti(con, '')
    _check(r, 'Incassi', 'senza estratti non si accusa nessuno di ritardo',
           senza['in_ritardo'], [])
    con.close()


def _test_intestatario(r):
    """Chi fa le sedute e chi riceve la fattura possono essere due persone diverse."""
    import sqlite3
    from . import db as _db
    from .db import SCHEMA

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)
    con.execute("INSERT INTO clients(key, name, address1, address2, file_label, intestatario) "
                "VALUES('anna','Anna','Via delle Prove 1','8000 Cittanova','Anna','Luca Conti')")
    con.execute("INSERT INTO clients(key, name, address1, address2, file_label) "
                "VALUES('sara','Sara Bernasconi','Via delle Prove 2','8000 Cittanova','Sara B')")
    con.commit()

    def intestata_a(chiave):
        c = con.execute('SELECT * FROM clients WHERE key=?', (chiave,)).fetchone()
        return (c['intestatario'] or '').strip() or c['name']

    def nome_file(chiave):
        c = con.execute('SELECT * FROM clients WHERE key=?', (chiave,)).fetchone()
        return (c['file_label'] or c['name']).strip()

    _check(r, 'Intestatario', 'con intestatario: la fattura va a lui',
           intestata_a('anna'), 'Luca Conti')
    _check(r, 'Intestatario', 'ma il nome del file resta quello del cliente',
           nome_file('anna'), 'Anna')
    _check(r, 'Intestatario', 'senza intestatario: la fattura va al cliente',
           intestata_a('sara'), 'Sara Bernasconi')
    _check(r, 'Intestatario', 'campo con soli spazi vale come vuoto',
           (lambda: (con.execute("UPDATE clients SET intestatario='   ' WHERE key='sara'"),
                     intestata_a('sara'))[1])(), 'Sara Bernasconi')
    con.close()


def _test_banca(r):
    """Leggere l'estratto e accostarlo: qui un errore costa caro, si prova bene."""
    _test_intestatario(r)
    _test_pacchetto(r)
    _test_pacchetto_lingua(r)
    _test_modelli_lingua(r)
    _test_cartelle(r)
    _test_avviatore(r)
    _test_avviatore_windows(r)
    _test_windows(r)
    _test_invoice_app(r)
    _test_spegnimento(r)
    _test_trasloco(r)
    _test_backup_illeggibile(r)
    _test_niente_dati_veri(r)
    import os
    import sqlite3
    import tempfile
    from . import bank as B
    from . import db as _db
    from .db import SCHEMA

    _check(r, 'Banca', "1'234.50 svizzero", B._importo("1'234.50"), 123450)
    _check(r, 'Banca', '1.234,50 all\'italiana', B._importo('1.234,50'), 123450)
    _check(r, 'Banca', 'importo negativo riconosciuto', B._importo('-45.00'), -4500)
    _check(r, 'Banca', 'cella vuota non è zero', B._importo('  '), None)
    _check(r, 'Banca', 'data svizzera 02.08.2026', B._data('02.08.2026'), '2026-08-02')
    _check(r, 'Banca', 'data ISO 2026-08-02', B._data('2026-08-02'), '2026-08-02')

    cartella = tempfile.mkdtemp()
    with open(os.path.join(cartella, 'e.csv'), 'w', encoding='utf-8') as f:
        f.write(CSV_PROVA)
    with open(os.path.join(cartella, 'e.xml'), 'w', encoding='utf-8') as f:
        f.write(CAMT_PROVA)
    mov, problemi = B.leggi_cartella(cartella)

    _check(r, 'Banca', 'nessun problema sui due formati standard', problemi, [])
    _check(r, 'Banca', 'legge sia il CSV sia il camt', len(mov), 4)
    _check(r, 'Banca', 'gli addebiti non entrano (non sono incassi)',
           [m for m in mov if m['importo_cents'] < 0], [])
    _check(r, 'Banca', "l'addebito della cassa malati è escluso",
           any('Krankenkasse' in m['descrizione'] for m in mov), False)
    _check(r, 'Banca', 'il camt dà il nome di chi ha pagato',
           [m['nome'] for m in mov if m['importo_cents'] == 180000], ['Bruno Keller'])
    _check(r, 'Banca', 'lo stesso file letto due volte non raddoppia i movimenti',
           len(B.leggi_cartella(cartella)[0]), 4)

    _check(r, 'Banca', 'la dieresi scritta «ue» dalla banca si riconosce',
           B.somiglianza_nome('Zahlung Mueller Petra', 'Petra Müller'), 1.0)
    _check(r, 'Banca', 'la dieresi scritta senza nulla si riconosce',
           B.somiglianza_nome('Zahlung Muller Petra', 'Petra Müller'), 1.0)
    _check(r, 'Banca', 'una causale anonima non somiglia a nessuno',
           B.somiglianza_nome('Gutschrift unbekannt', 'Sofia Ferrari'), 0.0)

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)
    ins = ('INSERT INTO invoices(number, client_name, date, year, total_cents, status, '
           'source) VALUES(?,?,?,?,?,?,"app")')
    con.execute(ins, (82, 'Sofia Ferrari', '2026-07-24', 2026, 11000, 'emessa'))
    con.execute(ins, (83, 'Chiara De Santis', '2026-07-25', 2026, 11000, 'emessa'))
    con.execute(ins, (60, 'Nadia Rossi', '2026-07-20', 2026, 11000, 'pagata'))
    con.commit()

    versamento = next(m for m in mov if m['data'] == '2026-08-02')
    cand = B.candidati_per(con, versamento)
    _check(r, 'Banca', 'il nome nella causale mette la fattura giusta in cima',
           cand[0]['inv']['number'], 82)
    _check(r, 'Banca', 'la fattura col nome giusto è «probabile»',
           cand[0]['grado'], B.PROBABILE)
    _check(r, 'Banca', "quelle con lo stesso importo ma altro nome restano «possibile»",
           {c['grado'] for c in cand[1:]}, {B.POSSIBILE})
    # le fatture gia' spuntate a mano restano candidate: confermarle non cambia
    # lo stato ma scrive la data vera del versamento
    pagata = next(c for c in cand if c['inv']['number'] == 60)
    _check(r, 'Banca', 'una fattura già pagata a mano resta proponibile',
           pagata['aperta'], False)
    # la frase la mette la pagina, non bank.py: cosi' si puo' tradurre. Il
    # controllo resta lo stesso — la riga deve dirlo — solo guardato dove
    # adesso la frase vive davvero.
    _check(r, 'Banca', 'e la riga lo dice, invece di far credere a un incasso nuovo',
           _pagina_dice_gia_pagata(), True)
    _check(r, 'Banca', 'a parità di indizi la fattura ancora aperta viene prima',
           cand[1]['aperta'], True)

    anonimo = next(m for m in mov if 'unbekannt' in m['descrizione'])
    _check(r, 'Banca', 'senza nome nessun candidato è «probabile»',
           [c for c in B.candidati_per(con, anonimo) if c['grado'] != B.POSSIBILE], [])
    _check(r, 'Banca', 'due candidati deboli NON fanno una proposta automatica',
           B.proposte(con, [anonimo])[0]['chiaro'], False)
    _check(r, 'Banca', 'un candidato che stacca gli altri sì',
           B.proposte(con, [versamento])[0]['chiaro'], True)

    # la data della fattura scritta nella causale (alcuni clienti fanno cosi')
    _check(r, 'Banca', 'la data citata «21-04-26» si legge',
           '2026-04-21' in B.date_citate('INVOICE 21-04-26'), True)
    _check(r, 'Banca', 'anche scritta «04.09.25»',
           '2025-09-04' in B.date_citate('INVOICE 04.09.25'), True)
    _check(r, 'Banca', 'una data impossibile non si inventa',
           B.date_citate('INVOICE 45-99-26'), set())
    con.execute(ins, (95, 'Tizia Rossi', '2026-07-20', 2026, 50000, 'emessa'))
    con.execute(ins, (96, 'Tizia Rossi', '2026-07-28', 2026, 50000, 'emessa'))
    con.commit()
    due_uguali = dict(versamento, importo_cents=50000,
                      descrizione='Accredito Tizia Rossi INVOICE 28-07-26')
    cd = B.candidati_per(con, due_uguali)
    _check(r, 'Banca', 'fra due mensilità identiche vince quella con la data citata',
           cd[0]['inv']['number'], 96)
    _check(r, 'Banca', 'e diventa una proposta da confermare con un click',
           B.proposte(con, [due_uguali])[0]['chiaro'], True)

    # una mensilita' gia' spuntata a mano ma del mese giusto deve battere quella
    # ancora aperta del mese dopo (caso Nadia: versamento del 30.06)
    con.execute(ins, (97, 'Tizia Rossi', '2026-06-20', 2026, 33000, 'pagata'))
    con.execute(ins, (98, 'Tizia Rossi', '2026-07-01', 2026, 33000, 'emessa'))
    con.commit()
    fine_mese = dict(versamento, data='2026-06-30', importo_cents=33000,
                     descrizione='Accredito Tizia Rossi')
    cf = B.candidati_per(con, fine_mese)
    _check(r, 'Banca', 'il versamento va alla fattura emessa PRIMA, non a quella dopo',
           cf[0]['inv']['number'], 97)
    _check(r, 'Banca', "e non basta che l'altra sia ancora aperta per scavalcarla",
           cf[0]['aperta'], False)
    con.execute('DELETE FROM invoices WHERE number IN (97,98)')
    con.commit()

    # un bonifico che paga due fatture insieme
    con.execute(ins, (90, 'Tizia Rossi', '2026-07-10', 2026, 200000, 'emessa'))
    con.execute(ins, (91, 'Tizia Rossi', '2026-07-10', 2026, 135000, 'emessa'))
    con.execute(ins, (92, 'Caio Bianchi', '2026-07-10', 2026, 335000, 'emessa'))
    con.commit()
    insieme = dict(versamento, importo_cents=335000,
                   descrizione='Accredito Tizia Rossi Via Roma 1')
    g = B.gruppi_per(con, insieme)
    _check(r, 'Banca', 'due fatture che insieme fanno il bonifico si trovano',
           sorted(i['number'] for i in g[0]['fatture']) if g else [], [90, 91])
    _check(r, 'Banca', 'il gruppo si cerca solo fra le fatture di chi ha pagato',
           any(92 in [i['number'] for i in x['fatture']] for x in g), False)
    _check(r, 'Banca', 'se una fattura da sola basta, non si cercano gruppi',
           B.proposte(con, [dict(versamento, importo_cents=335000,
                                 descrizione='Accredito Caio Bianchi')])[0]['gruppi'], [])

    # il numero della fattura scritto a mano: e' l'unica via per i pagamenti
    # che l'app non puo' proporre (arrivati mesi dopo, o di importo diverso)
    doppio = con.execute('SELECT COUNT(*) c FROM invoices WHERE number=82').fetchone()['c']
    _check(r, 'Banca', 'partenza pulita per la prova del numero doppio', doppio, 1)
    con.execute(ins, (82, 'Caio Bianchi', '2026-07-24', 2026, 11000, 'emessa'))
    con.commit()
    stesso = con.execute('SELECT * FROM invoices WHERE number=82').fetchall()
    _check(r, 'Banca', 'due fatture possono avere lo stesso numero (succede)',
           len(stesso), 2)
    suoi = [t for t in stesso
            if B.somiglianza_nome('Accredito Sofia Ferrari', t['client_name']) >= 0.5]
    _check(r, 'Banca', 'il nome di chi versa scioglie il numero doppio',
           [t['client_name'] for t in suoi], ['Sofia Ferrari'])
    con.execute('DELETE FROM invoices WHERE number=82 AND client_name="Caio Bianchi"')
    con.commit()

    fuori_finestra = dict(versamento, data='2027-08-02')
    _check(r, 'Banca', 'un versamento di un anno dopo non si attacca a niente',
           B.candidati_per(con, fuori_finestra), [])

    # il riferimento non si deduce dal numero: sarebbe un "certo" inventato
    con_rif = dict(versamento, riferimento='000000000000000000000000082')
    _check(r, 'Banca', 'nessun «certo» finché le fatture non hanno un riferimento vero',
           [c for c in B.candidati_per(con, con_rif) if c['grado'] == B.CERTO], [])
    con.close()

    import shutil
    shutil.rmtree(cartella, ignore_errors=True)


def _test_pacchetto(r):
    """Il PDF che finisce nel pacchetto e' quello di quella fattura li'.

    Nell'archivio storico lo stesso documento ha due nomi (Word e PDF) che non
    coincidono, e una rinumerazione lascia sul disco due file con lo stesso
    numero intestati a due persone diverse. Sbagliare qui vuol dire mandare
    alla commercialista la fattura di uno col numero di un altro.
    """
    import shutil
    import tempfile
    from . import exports as E

    cartella = tempfile.mkdtemp(prefix='prova-pacchetto-')
    def crea(*nomi):
        for n in nomi:
            with io.open(os.path.join(cartella, n), 'w', encoding='utf-8') as f:
                f.write('x')
    def gemello(nome):
        t = E.pdf_gemello(os.path.join(cartella, nome))
        return os.path.basename(t) if t else None

    # la rinumerazione: la #58 di uno e' diventata #59, ma sul disco si chiama
    # ancora 58, e nella stessa cartella c'e' la vera #58 di un'altra persona
    crea('Sofia #58.docx', 'Sofia ^N58.pdf',
         'Caio Bianchi#58.docx', 'Caio Bianchi^N58.pdf')
    _check(r, 'Pacchetto commercialista',
           'con due «58» di due persone, ognuna prende il proprio PDF',
           (gemello('Sofia #58.docx'), gemello('Caio Bianchi#58.docx')),
           ('Sofia ^N58.pdf', 'Caio Bianchi^N58.pdf'))

    # I segni che l'archivio mette davanti al numero, tutti diversi. Ogni
    # numero ha apposta un secondo PDF intestato a un altro: se no il PDF
    # giusto si troverebbe solo perche' e' l'unico con quel numero, e questo
    # test non direbbe niente sui segni.
    crea('Tizio R #38.docx', 'Tizio R ^LN38.pdf', 'Anna B #38.docx', 'Anna B ^N38.pdf',
         'Marta L #33.docx', 'Marta L ^33.pdf', 'Anna B #33.docx', 'Anna B ^N33.pdf',
         'Sofia #37.docx', 'Sofia#37.pdf', 'Anna B #37.docx', 'Anna B ^N37.pdf',
         'Marta L_47.docx', 'Marta L_47.pdf')
    _check(r, 'Pacchetto commercialista',
           'il PDF si trova anche se il segno davanti al numero cambia',
           (gemello('Tizio R #38.docx'), gemello('Marta L #33.docx'),
            gemello('Sofia #37.docx'), gemello('Marta L_47.docx')),
           ('Tizio R ^LN38.pdf', 'Marta L ^33.pdf',
            'Sofia#37.pdf', 'Marta L_47.pdf'))

    # la #6 non deve prendersi il PDF della #56
    crea('Tizio #6.docx', 'Tizio ^N56.pdf')
    _check(r, 'Pacchetto commercialista',
           'la #6 non si prende il PDF della #56', gemello('Tizio #6.docx'), None)

    # nome diverso ma un solo PDF con quel numero: non c'e' da sbagliarsi
    crea('Caio #91.docx', 'Caio Bianchi ^N91.pdf')
    _check(r, 'Pacchetto commercialista',
           'se il PDF con quel numero è uno solo, il nome può essere diverso',
           gemello('Caio #91.docx'), 'Caio Bianchi ^N91.pdf')

    # nome diverso e due candidati: meglio nessun PDF che quello sbagliato
    crea('Tizia #92.docx', 'Alfa ^N92.pdf', 'Beta ^N92.pdf')
    _check(r, 'Pacchetto commercialista',
           'nel dubbio fra due PDF non ne sceglie nessuno',
           gemello('Tizia #92.docx'), None)

    shutil.rmtree(cartella, ignore_errors=True)

    # dentro il pacchetto il nome del file combacia col registro: e' l'unico
    # modo per ritrovare la riga giusta guardando il PDF
    _check(r, 'Pacchetto commercialista',
           'la copia porta il numero della fattura, non quello del file vecchio',
           E._nome_copia(_Finta(number=59, client_name='Sofia Ferrari'),
                         '/x/Sofia ^N58.pdf'),
           '#59 Sofia Ferrari.pdf')
    _check(r, 'Pacchetto commercialista',
           'una fattura senza numero tiene il nome che ha',
           E._nome_copia(_Finta(number=None, client_name='Marta L'),
                         '/x/Marta 16.01.24.pdf'),
           'Marta 16.01.24.pdf')


def _test_pacchetto_lingua(r):
    """Il pacchetto per la commercialista parla la lingua dell'app.

    Le cifre no: quelle non cambiano mai lingua, e questo va provato, perche'
    un registro che cambia i totali quando cambi lingua sarebbe un disastro
    silenzioso.
    """
    import sqlite3
    import tempfile
    import openpyxl
    from . import exports as E
    from . import language as L
    from . import db as _db
    from .db import SCHEMA

    _check(r, 'Pacchetto commercialista',
           'i mesi dell’elenco tengono la maiuscola, quelli da frase no',
           (L.mesi_elenco('it')[0], L.mesi_app('it')[0]), ('Gennaio', 'gennaio'))
    _check(r, 'Pacchetto commercialista', 'e cambiano con la lingua dell’app',
           (L.mesi_elenco('en')[0], L.mesi_elenco('de')[0]), ('January', 'Januar'))

    # la lingua del pacchetto e' quella di chi lo legge, non quella dell'app
    _check(r, 'Pacchetto commercialista', 'di serie il pacchetto segue l’app',
           ('accountant_lingua' in _db.DEFAULT_SETTINGS,
            _db.DEFAULT_SETTINGS.get('accountant_lingua', '(manca)'),
            E.lingua_pacchetto({}, 'de')),
           (True, '', 'de'))
    _check(r, 'Pacchetto commercialista',
           'ma se la commercialista legge un’altra lingua vince la sua',
           E.lingua_pacchetto({'accountant_lingua': 'it'}, 'en'), 'it')

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)
    con.execute("""INSERT INTO invoices(number, client_name, date, year, total_cents,
                                        status) VALUES(?,?,?,?,?,?)""",
                (1, 'Sofia Ferrari', '2026-01-15', 2026, 180000, 'pagata'))
    con.commit()
    impostazioni = dict(_db.DEFAULT_SETTINGS, business_name='Studio Prova',
                        accountant_name='Anna Rossi', accountant_city='Zurigo',
                        business_uid='CHE-000.000.000', business_iban='CH00')

    cartella = tempfile.mkdtemp(prefix='prova-registro-')
    letto = {}
    for lg in ('it', 'de'):
        p = os.path.join(cartella, lg + '.xlsx')
        E.build_excel(con, 2026, p, impostazioni, lg)
        wb = openpyxl.load_workbook(p)
        ws = wb[wb.sheetnames[0]]
        letto[lg] = {
            'foglio': wb.sheetnames[0],
            'intestazioni': [ws.cell(row=4, column=i).value for i in range(1, 7)],
            'stato': ws.cell(row=5, column=6).value,
            'importo': ws.cell(row=5, column=5).value,
            'numero': ws.cell(row=5, column=1).value,
        }
    con.close()
    import shutil
    shutil.rmtree(cartella, ignore_errors=True)

    _check(r, 'Pacchetto commercialista', 'in italiano il registro resta com’era',
           (letto['it']['foglio'], letto['it']['intestazioni'][0],
            letto['it']['intestazioni'][4], letto['it']['stato']),
           ('Registro fatture', 'Nr.', 'Importo CHF', 'pagata'))
    _check(r, 'Pacchetto commercialista', 'in tedesco parla tedesco, anche lo stato',
           (letto['de']['foglio'], letto['de']['intestazioni'][1],
            letto['de']['intestazioni'][4], letto['de']['stato']),
           ('Rechnungsregister', 'Datum', 'Betrag CHF', 'bezahlt'))
    _check(r, 'Pacchetto commercialista',
           'i soldi e il numero della fattura non cambiano lingua',
           (letto['it']['importo'], letto['de']['importo'],
            letto['it']['numero'], letto['de']['numero']),
           (1800.0, 1800.0, '#1', '#1'))


def _test_modelli_lingua(r):
    """I modelli della mail hanno una versione per lingua, e la firma no.

    Due cose vanno provate insieme: che scrivendo il tedesco la mail esca in
    tedesco, e che NON scrivendolo esca esattamente come prima. La seconda
    conta di piu': le mail che manda oggi non devono cambiare di una virgola.
    """
    import sqlite3
    from . import mailer as M
    from . import db as _db
    from .db import SCHEMA

    # --- il ripiego: senza versione per quella lingua vale quella per tutti ---
    s = {'email_corpo_pt': 'per tutti', 'email_corpo_pt_de': 'auf Deutsch',
         'email_corpo_pt_it': '   '}
    _check(r, 'Modelli della mail', 'la versione nella lingua del cliente vince',
           _db.modello_email(s, 'email_corpo_pt', 'de'), 'auf Deutsch')
    _check(r, 'Modelli della mail', 'se quella lingua non è scritta si usa quella per tutti',
           _db.modello_email(s, 'email_corpo_pt', 'en'), 'per tutti')
    _check(r, 'Modelli della mail', 'e anche se è scritta ma è solo spazi',
           _db.modello_email(s, 'email_corpo_pt', 'it'), 'per tutti')
    _check(r, 'Modelli della mail', 'una lingua che non esiste non inventa una chiave',
           _db.chiave_modello('email_corpo_pt', 'klingon'), 'email_corpo_pt')

    # --- la migrazione: la firma esce dal modello e la mail resta uguale ---
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    vecchio = 'Dear {nome},\n\n{apertura}\n{corpo}\n\n{saluto}Anna Muster\n+41 00 000 00 00\n'
    con.execute("INSERT INTO settings(key, value) VALUES('email_body', ?)", (vecchio,))
    con.commit()
    _db._migra_firma_email(con)
    con.commit()
    def leggi(k):
        x = con.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone()
        return x['value'] if x else None
    _check(r, 'Modelli della mail', 'la firma esce dal modello e diventa sua',
           (leggi('email_body'), leggi('email_firma')),
           ('Dear {nome},\n\n{apertura}\n{corpo}\n\n{saluto}{firma}',
            'Anna Muster\n+41 00 000 00 00\n'))
    valori = {'nome': 'Anna', 'apertura': 'A.', 'corpo': 'C.', 'saluto': 'Best,\n',
              'firma': leggi('email_firma')}
    _check(r, 'Modelli della mail', 'e la mail che ne esce è identica a prima',
           leggi('email_body').format(**valori), vecchio.format(**valori))

    # girata due volte non deve staccare la firma una seconda volta
    _db._migra_firma_email(con)
    con.commit()
    _check(r, 'Modelli della mail', 'rifarla non rovina niente',
           leggi('email_body'),
           'Dear {nome},\n\n{apertura}\n{corpo}\n\n{saluto}{firma}')

    # un modello riscritto senza {saluto} non si tocca: meglio non staccarla
    con.execute("UPDATE settings SET value='Ciao {nome}' WHERE key='email_body'")
    con.execute("DELETE FROM settings WHERE key='email_firma'")
    con.commit()
    _db._migra_firma_email(con)
    con.commit()
    _check(r, 'Modelli della mail', 'un modello senza {saluto} resta com’è',
           (leggi('email_body'), leggi('email_firma')), ('Ciao {nome}', None))
    con.close()

    # --- la mail vera, composta in due lingue ---
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)
    con.execute("""INSERT INTO invoices(number, client_name, date, year, total_cents,
                                        status, pdf_path) VALUES(?,?,?,?,?,?,?)""",
                (1, 'Anna Muster', '2026-01-15', 2026, 11000, 'emessa', ''))
    con.commit()
    inv = con.execute('SELECT * FROM invoices WHERE number=1').fetchone()
    imp = dict(_db.DEFAULT_SETTINGS,
               email_body='Dear {nome},\n{corpo}\n{saluto}{firma}',
               email_corpo_pt='Thank you.', email_saluto_informale='Best,\n',
               email_firma='Anna Muster', email_corpo_pt_de='Vielen Dank.',
               email_body_de='Guten Tag {nome}\n{corpo}\n{saluto}{firma}')
    cliente = _Finta(name='Anna Muster', email='a@b.ch', abbonamento=0,
                     tono='informale', lingua='de', intestatario='')
    tedesca = M.componi(inv, cliente, imp)['body']
    cliente['lingua'] = 'en'
    inglese = M.componi(inv, cliente, imp)['body']
    _check(r, 'Modelli della mail', 'al cliente tedesco arriva la mail tedesca',
           tedesca, 'Guten Tag Anna\nVielen Dank.\nBest,\nAnna Muster')
    _check(r, 'Modelli della mail', 'e all’inglese la sua, invariata',
           inglese, 'Dear Anna,\nThank you.\nBest,\nAnna Muster')
    # la firma sta in una chiave sola: in ogni lingua compare una volta e
    # basta, e non serve ricopiarla in ogni modello tradotto
    _check(r, 'Modelli della mail', 'la firma compare una volta sola in tutte e due',
           (tedesca.count('Anna Muster'), inglese.count('Anna Muster')), (1, 1))
    con.close()


def _test_cartelle(r):
    """Le cartelle dei dati cambiano nome senza che si perda niente.

    E' la migrazione piu' delicata di tutte: sposta i documenti veri. Il caso
    da non sbagliare non e' la rinomina — e' quando esistono tutt'e due le
    cartelle, perche' li' unire e' una decisione di chi ha i file davanti.
    """
    import shutil
    import sqlite3
    import tempfile
    from . import db as _db
    from .db import SCHEMA

    base = tempfile.mkdtemp(prefix='prova-cartelle-')
    def scrivi(*pezzi):
        p = os.path.join(base, *pezzi)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, 'w', encoding='utf-8') as f:
            f.write('x')
        return p

    scrivi('Fatture', '2026', 'una.pdf')
    scrivi('Estratti conto', 'estratto.pdf')
    fatte = _db.migra_cartelle(base)
    _check(r, 'Cartelle', 'le cartelle vecchie prendono il nome nuovo',
           sorted(fatte), [('Estratti conto', 'Bank statements'),
                           ('Fatture', 'Invoices')])
    _check(r, 'Cartelle', 'e i documenti sono dentro quella nuova',
           (os.path.exists(os.path.join(base, 'Invoices', '2026', 'una.pdf')),
            os.path.exists(os.path.join(base, 'Fatture'))), (True, False))
    _check(r, 'Cartelle', 'rifarla una seconda volta non fa niente',
           _db.migra_cartelle(base), [])

    # il caso pericoloso: ci sono tutt'e due. Rinominare sopra vorrebbe dire
    # sovrascrivere o mischiare, e nessuna delle due e' una migrazione.
    scrivi('Cestino', 'vecchia.pdf')
    scrivi('Trash', 'nuova.pdf')
    _check(r, 'Cartelle', 'con tutt’e due le cartelle non tocca niente',
           _db.migra_cartelle(base), [])
    _check(r, 'Cartelle', 'e nessuno dei due file si perde',
           (os.path.exists(os.path.join(base, 'Cestino', 'vecchia.pdf')),
            os.path.exists(os.path.join(base, 'Trash', 'nuova.pdf'))), (True, True))
    shutil.rmtree(base, ignore_errors=True)

    # --- i percorsi salvati nel database ---
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _db._migrate(con)
    vecchio = os.path.join(_db.APP_DIR, 'Fatture', '2026', 'inesistente.pdf')
    con.execute("""INSERT INTO invoices(number, client_name, date, year,
                                        total_cents, status, pdf_path)
                   VALUES(?,?,?,?,?,?,?)""",
                (1, 'Anna Muster', '2026-01-15', 2026, 11000, 'emessa', vecchio))
    con.commit()
    _db._migra_percorsi(con)
    con.commit()
    _check(r, 'Cartelle', 'un percorso che non porta a niente resta com’è',
           con.execute('SELECT pdf_path FROM invoices WHERE number=1').fetchone()[0],
           vecchio)

    # ora il file nuovo c'e' davvero: il percorso va raddrizzato
    nuovo = os.path.join(_db.APP_DIR, 'Invoices', 'prova-migrazione.pdf')
    os.makedirs(os.path.dirname(nuovo), exist_ok=True)
    with io.open(nuovo, 'w', encoding='utf-8') as f:
        f.write('x')
    con.execute('UPDATE invoices SET pdf_path=? WHERE number=1',
                (os.path.join(_db.APP_DIR, 'Fatture', 'prova-migrazione.pdf'),))
    con.commit()
    _db._migra_percorsi(con)
    con.commit()
    _check(r, 'Cartelle', 'il percorso alla cartella vecchia viene raddrizzato',
           con.execute('SELECT pdf_path FROM invoices WHERE number=1').fetchone()[0],
           nuovo)
    os.remove(nuovo)
    con.close()

    # --- il vecchio nome delle variabili d'ambiente ---
    os.environ['FATTURE_PROVA'] = 'vecchio'
    _check(r, 'Cartelle', 'il vecchio nome di una variabile funziona ancora',
           _db.env('INVOICE_PROVA', 'FATTURE_PROVA'), 'vecchio')
    os.environ['INVOICE_PROVA'] = 'nuovo'
    _check(r, 'Cartelle', 'ma il nome nuovo passa davanti',
           _db.env('INVOICE_PROVA', 'FATTURE_PROVA'), 'nuovo')
    del os.environ['FATTURE_PROVA'], os.environ['INVOICE_PROVA']


def _test_avviatore(r):
    """L'avviatore sa distinguere i quattro modi in cui una copia puo' stare
    rispetto a quella pubblicata.

    Quello che conta e' «diverged»: succede quando la storia pubblicata viene
    riscritta, e senza quel ramo l'app di chi ha la copia vecchia smetterebbe
    di aggiornarsi PER SEMPRE, e in silenzio — perche' la regola «solo in
    avanti» non sarebbe mai piu' vera. Qui si controlla che i quattro casi
    siano ancora tutti previsti; che facciano la cosa giusta e' stato provato
    su repository veri, e si rifa' cosi' se qualcuno tocca l'avviatore.
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    perc = os.path.join(base, 'Start Invoice.command')
    try:
        with io.open(perc, encoding='utf-8') as f:
            testo = f.read()
    except OSError:
        testo = ''
    _check(r, 'Avviatore', 'l’avviatore c’è e si chiama in inglese',
           bool(testo), True)
    # due controlli e non uno: la prima volta ne avevo scritto uno solo, che
    # accettava «o lo sa dire o lo sa trattare» — e restava verde anche
    # togliendo del tutto il caso dalla funzione che lo decide
    _check(r, 'Avviatore', 'sa dire tutti e quattro i casi',
           sorted(c for c in ('none', 'forward', 'ahead', 'diverged')
                  if 'echo %s' % c in testo),
           ['ahead', 'diverged', 'forward', 'none'])
    _check(r, 'Avviatore', 'e sa cosa fare per ognuno',
           ('none|ahead)' in testo, 'forward)' in testo, 'diverged)' in testo),
           (True, True, True))
    # servono tutt'e due i confronti: con uno solo «piu' avanti» e «storia
    # riscritta» si confonderebbero, e a una copia piu' avanti non si tocca
    _check(r, 'Avviatore', 'guarda la parentela nei due versi',
           testo.count('merge-base --is-ancestor'), 2)
    _check(r, 'Avviatore', 'una storia riscritta non aggiorna di nascosto: chiede',
           'Line up with the published version?' in testo, True)
    _check(r, 'Avviatore', 'e prima di sostituire i file fa una copia dei dati',
           "backup.make_backup('prima-aggiornamento')" in testo, True)



def _avviatori():
    """I due avviatori letti dal disco, in byte: cosi' si puo' guardare anche
    COM'E' scritto il file, non solo cosa dice."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuori = {}
    for nome in ('Start Invoice.command', 'Start Invoice.bat'):
        try:
            with io.open(os.path.join(base, nome), 'rb') as f:
                fuori[nome] = f.read()
        except OSError:
            fuori[nome] = b''
    return fuori


def _test_avviatore_windows(r):
    """L'avviatore di Windows e quello del Mac fanno lo stesso mestiere in due
    linguaggi diversi: e' esattamente la situazione in cui uno impara qualcosa
    e l'altro resta indietro senza che nessuno se ne accorga.

    Il .bat da un Mac non si puo' FAR GIRARE: non c'e' nessun cmd.exe. Si puo'
    pero' provare tutto il resto, e non e' poco, perche' su Windows questi
    sbagli non danno errore — saltano il pezzo in silenzio: che il file sia
    scritto in un modo che Windows sa leggere, che ogni salto abbia la sua
    etichetta, che ogni domanda fatta a launcher.py sia una domanda che quello
    sa davvero rispondere, e che i due avviatori continuino a dire le stesse
    cose sulle stesse cose.
    """
    a = _avviatori()
    grezzo = a['Start Invoice.bat']
    win = grezzo.decode('ascii', 'replace')
    mac = a['Start Invoice.command'].decode('utf-8', 'replace')

    _check(r, 'Avviatore Windows', 'c’è', bool(grezzo), True)
    # cmd.exe non legge UTF-8: una lettera accentata o una virgoletta bassa
    # arriverebbe sullo schermo come uno scarabocchio
    _check(r, 'Avviatore Windows', 'scritto in ASCII, che cmd.exe sa leggere',
           max(bytearray(grezzo) or [0]) < 128, True)
    # con le sole LF, cmd puo' leggere male etichette e salti
    _check(r, 'Avviatore Windows', 'righe che finiscono come vuole Windows (CRLF)',
           (grezzo.count(b'\n') > 0, grezzo.count(b'\n') == grezzo.count(b'\r\n')),
           (True, True))

    righe = win.split('\r\n')
    etichette = set()
    for x in righe:
        m = re.match(r':(\w+)', x.strip())
        if m:
            etichette.add(m.group(1).lower())
    mete = {m.group(1).lower() for x in righe
            for m in re.finditer(r'\b(?:goto|call)\s+:(\w+)', x, re.I)}
    # un salto verso un'etichetta che non c'e' non da' errore: cmd salta il
    # pezzo e tira dritto, e il pezzo saltato e' proprio quello che serviva
    _check(r, 'Avviatore Windows', 'ogni salto ha la sua etichetta',
           sorted(mete - etichette - {'eof'}), [])
    _check(r, 'Avviatore Windows', 'e nessuna etichetta è rimasta orfana',
           sorted(etichette - mete), [])
    _check(r, 'Avviatore Windows', 'parentesi aperte e chiuse in pari',
           (sum(x.count('(') - x.count('^(') for x in righe),
            sum(x.count(')') - x.count('^)') for x in righe)),
           (sum(x.count(')') - x.count('^)') for x in righe),
            sum(x.count(')') - x.count('^)') for x in righe)))
    # «set NOME=valore» senza virgolette si porta dentro lo spazio che ha in
    # coda: «none » non e' «none», e il confronto dopo fallisce per sempre
    _check(r, 'Avviatore Windows', 'nessun «set» senza virgolette',
           [x.strip() for x in righe
            if re.match(r'\s*set\s+[A-Za-z_]', x) and '"' not in x], [])

    # --- le domande a launcher.py -------------------------------------------
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'core', 'launcher.py'), encoding='utf-8') as f:
        sorgente_launcher = f.read()
    usate = sorted(set(re.findall(r'core\.launcher\s+([a-z-]+)', win)))
    note = set(re.findall(r"domanda == '([a-z-]+)'", sorgente_launcher))
    _check(r, 'Avviatore Windows', 'chiede a launcher.py i sei conti difficili',
           usate, ['aggiornato', 'controllato-da-poco', 'in-salute',
                   'requisiti-a-posto', 'scrivi-impronta', 'tocca'])
    _check(r, 'Avviatore Windows', 'e ogni domanda è una che launcher.py sa rispondere',
           sorted(set(usate) - note), [])
    # il nome del segnale d'accensione lo scrive app.py e lo legge launcher.py:
    # se uno dei due lo cambia da solo, l'app risulta sempre «da riavviare»
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        sorgente_app = f.read()
    firma = "'data', '.started-%s' % porta"
    _check(r, 'Avviatore Windows', 'app.py e launcher.py chiamano allo stesso modo il segnale d’accensione',
           (firma in sorgente_app, firma in sorgente_launcher), (True, True))

    # --- i quattro casi, anche qui ------------------------------------------
    _check(r, 'Avviatore Windows', 'sa dire tutti e quattro i casi',
           sorted(c for c in ('none', 'forward', 'ahead', 'diverged')
                  if 'set "KIND=%s"' % c in win),
           ['ahead', 'diverged', 'forward', 'none'])
    _check(r, 'Avviatore Windows', 'e sa cosa fare per ognuno',
           ('"%KIND%"=="none"' in win, '"%KIND%"=="ahead"' in win,
            '"%KIND%"=="diverged"' in win, 'call :ask_and_apply "  Install it?"' in win),
           (True, True, True, True))
    _check(r, 'Avviatore Windows', 'guarda la parentela nei due versi',
           win.count('merge-base --is-ancestor'), 2)

    # --- e adesso i due, a confronto ----------------------------------------
    def porta(testo):
        m = re.search(r'PORT=(\d+)', testo)
        return m.group(1) if m else None
    _check(r, 'I due avviatori', 'parlano della stessa porta',
           (porta(mac), porta(win)), ('8471', '8471'))

    def librerie(testo):
        m = re.search(r'import (flask[a-zA-Z0-9_, ]*)"', testo)
        return sorted(x.strip() for x in m.group(1).split(',')) if m else []
    _check(r, 'I due avviatori', 'controllano le stesse librerie', librerie(win), librerie(mac))
    _check(r, 'I due avviatori', 'e la lista non è vuota', len(librerie(mac)), 7)

    # Il programma «pip» dentro l'ambiente ha il percorso della cartella scritto
    # dentro di se': appena la cartella si sposta smette di partire. Verificato
    # dal vero il 28.08.2026 spostando la cartella dalla Scrivania a casa —
    # «./venv/bin/pip» cercava ancora la Scrivania. «python -m pip» invece il
    # percorso lo ricava da dove si trova, e regge il trasloco.
    def comandi(testo, *inizi_di_commento):
        vive = []
        for riga in testo.split('\n'):
            nuda = riga.strip().lower()
            if nuda and not any(nuda.startswith(i) for i in inizi_di_commento):
                vive.append(riga)
        return '\n'.join(vive).lower()
    mac_c, win_c = comandi(mac, '#'), comandi(win, 'rem ', '::')
    _check(r, 'I due avviatori', 'nessuno dei due chiama «pip» come programma a sé',
           ('bin/pip' in mac_c, 'scripts\\pip' in win_c), (False, False))
    _check(r, 'I due avviatori', 'tutt’e due installano con «python -m pip»',
           (mac_c.count('-m pip install'), win_c.count('-m pip install')), (2, 2))

    for nome in ('.last-update-check', '.previous-version'):
        _check(r, 'I due avviatori', 'tutt’e due usano «data/%s»' % nome,
               (nome in mac, nome in win), (True, True))
    _check(r, 'I due avviatori', 'tutt’e due offrono di riallinearsi dopo una riscrittura',
           ('Line up with the published version?' in mac,
            'Line up with the published version?' in win), (True, True))
    _check(r, 'I due avviatori', 'tutt’e due copiano i dati prima di sostituire i file',
           ("backup.make_backup('prima-aggiornamento')" in mac,
            "backup.make_backup('prima-aggiornamento')" in win), (True, True))
    # una finestra lasciata aperta per sbaglio non deve tenere in ostaggio
    # l'app per sempre: senza risposta, dopo due minuti si va avanti
    _check(r, 'I due avviatori', 'tutt’e due aspettano una risposta al massimo 120 secondi',
           ('read -t 120' in mac, '/t 120' in win), (True, True))
    # --- e che su Windows la finestra si tolga di mezzo ---
    # pythonw e' il Python senza console: avviato con «start» sopravvive alla
    # chiusura di questa finestra. Senza, la finestra nera resta obbligatoria
    # e chiuderla spegne l'app in mezzo al lavoro.
    _check(r, 'Avviatore Windows', 'lancia l’app col Python senza finestra',
           ('pythonw.exe' in win, 'start "" "%VPYW%" app.py' in win), (True, True))
    _check(r, 'Avviatore Windows', 'e se pythonw non c’è ripiega su quello normale',
           'if not exist "%VPYW%" set "VPYW=%VPY%"' in win, True)
    # se si chiudesse subito, un'app che non parte non avrebbe piu' nessun
    # posto dove dirlo: questa finestra e' l'ultimo
    _check(r, 'Avviatore Windows', 'aspetta che risponda prima di chiudersi',
           ('core.launcher in-salute' in win, 'goto :running' in win,
            'The app did not start' in win), (True, True, True))
    _check(r, 'Avviatore Windows', 'e non chiede più di tenere aperta la finestra',
           'Leave this window open' in win, False)
    # «timeout» si rifiuta di partire con l'ingresso deviato, e un rifiuto
    # farebbe scorrere l'attesa in un lampo dichiarando un guasto inesistente
    _check(r, 'Avviatore Windows', 'l’attesa non può essere saltata per sbaglio',
           ('ping -n' in win, 'timeout /t' in win), (True, False))

    _check(r, 'I due avviatori', 'tutt’e due ricontrollano gli aggiornamenti ogni 6 ore',
           ('HOURS_BETWEEN_CHECKS=6' in mac,
            'controllato-da-poco "data\\.last-update-check" 6' in win), (True, True))


def _test_windows(r):
    """Le scelte che cambiano da un sistema all'altro, provate una per una.

    Sono tutte scritte in modo da poter chiedere «e su Windows cosa faresti?»
    da un Mac: la decisione e' separata dal farla davvero, cosi' si puo'
    verificare senza avere il computer sotto mano.
    """
    from . import desktop as dk

    # --- far vedere un file o una cartella ---
    _check(r, 'Windows', 'sul Mac una cartella si APRE nel Finder, non si lancia',
           dk.comando_apri('/x', 'darwin', cartella=True), ['open', '-a', 'Finder', '/x'])
    _check(r, 'Windows', 'sul Mac un file si MOSTRA, non si apre',
           dk.comando_apri('/x/y.pdf', 'darwin', cartella=False), ['open', '-R', '/x/y.pdf'])
    _check(r, 'Windows', 'su Windows la cartella la apre Explorer',
           dk.comando_apri('C:/a', 'win32', cartella=True), ['explorer', 'C:\\a'])
    # senza spazio dopo la virgola, se no Explorer apre Documenti e buonanotte
    _check(r, 'Windows', 'su Windows il file arriva evidenziato, «/select,» attaccato',
           dk.comando_apri('C:/a/b.pdf', 'win32', cartella=False),
           ['explorer', '/select,C:\\a\\b.pdf'])
    _check(r, 'Windows', 'a Explorer non arrivano mai barre all’americana',
           '/' in dk.comando_apri('C:/a/b.pdf', 'win32', cartella=False)[1].split(',', 1)[1],
           False)
    _check(r, 'Windows', 'altrove si apre la cartella che contiene il file',
           dk.comando_apri('/x/y.pdf', 'linux', cartella=False), ['xdg-open', '/x'])

    # --- dove finiscono le copie di sicurezza ---
    mac = dk.cartella_backup('darwin', casa='/C')
    _check(r, 'Windows', 'sul Mac le copie vanno su iCloud',
           ('com~apple~CloudDocs' in mac, mac.endswith(dk.NOME_BACKUP)), (True, True))
    con_nube = dk.cartella_backup('win32', casa='C:/u', esiste=lambda p: True,
                                  ambiente={'OneDrive': 'C:/u/OneDrive'})
    _check(r, 'Windows', 'su Windows le copie vanno su OneDrive, se c’è',
           con_nube.startswith(os.path.join('C:/u/OneDrive', '')), True)
    senza_nube = dk.cartella_backup('win32', casa='C:/u', ambiente={}, esiste=lambda p: False)
    _check(r, 'Windows', 'senza OneDrive si ripiega su Documenti',
           'Documents' in senza_nube, True)
    # la variabile puo' esserci ancora e la cartella no: chi ha spento OneDrive
    # se la ritroverebbe puntata su una cartella che non esiste, e il backup
    # fallirebbe ogni volta in silenzio
    _check(r, 'Windows', 'un OneDrive dichiarato ma sparito non si usa',
           dk.cartella_backup('win32', casa='C:/u', esiste=lambda p: False,
                              ambiente={'OneDrive': 'C:/u/OneDrive'}), senza_nube)
    _check(r, 'Windows', 'anche l’OneDrive aziendale va bene',
           dk.cartella_backup('win32', casa='C:/u', esiste=lambda p: True,
                              ambiente={'OneDriveCommercial': 'C:/u/OneDrive - Ditta'}),
           os.path.join('C:/u/OneDrive - Ditta', dk.NOME_BACKUP))

    # --- i nomi dei file, che Windows accetta meno del Mac ---
    _check(r, 'Windows', 'una barra nel nome non fa più un file impossibile',
           dk.nome_file_sicuro('Studio 4/5'), 'Studio 4-5')
    _check(r, 'Windows', 'e nemmeno due punti, virgolette, asterischi',
           dk.nome_file_sicuro('a<b>c:d"e|f?g*h\\i'), 'a-b-c-d-e-f-g-h-i')
    # e non deve ripulire piu' del necessario: «J. R.» e' un nome, non un guaio
    _check(r, 'Windows', 'ma un nome normale resta identico',
           (dk.nome_file_sicuro('J. R.'), dk.nome_file_sicuro('Café & Co. GmbH')),
           ('J. R.', 'Café & Co. GmbH'))
    from . import exports as _ex
    _check(r, 'Windows', 'anche il PDF per la commercialista prende un nome che Windows accetta',
           _ex._nome_copia({'number': 12, 'client_name': 'Studio 4/5'}, '/x/y.pdf'),
           '#12 Studio 4-5.pdf')

    # --- e che nessuno scavalchi desktop.py ---
    import ast as _ast
    import glob as _glob
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    perc = ([os.path.join(base, 'app.py')]
            + sorted(_glob.glob(os.path.join(base, 'core', '*.py'))))
    lancia, a_mano, sorgenti = [], [], {}
    for p in perc:
        nome = os.path.basename(p)
        with io.open(p, encoding='utf-8') as f:
            testo = f.read()
        sorgenti[nome] = testo
        for nodo in _ast.walk(_ast.parse(testo)):
            if isinstance(nodo, _ast.Import) and any(x.name == 'subprocess' for x in nodo.names):
                lancia.append(nome)
        # i file di collaudo no: qui quei percorsi ci sono per forza, scritti
        # apposta per confrontarli
        if 'selftest' not in nome and ('~/Library' in testo or 'Mobile Documents' in testo):
            a_mano.append(nome)
    _check(r, 'Windows', 'i comandi di sistema li lancia solo desktop.py',
           sorted(set(lancia)), ['desktop.py'])
    _check(r, 'Windows', 'i percorsi del Mac stanno solo dentro desktop.py',
           sorted(set(a_mano)), ['desktop.py'])
    # i due punti che trasformano il nome di un cliente in un nome di file:
    # se uno dei due se ne dimentica, l'errore compare solo su Windows e solo
    # per quel cliente li'
    _check(r, 'Windows', 'tutt’e due i punti che fanno nomi di file lo usano',
           sorted(n for n in ('app.py', 'exports.py')
                  if 'desktop.nome_file_sicuro' in sorgenti.get(n, '')),
           ['app.py', 'exports.py'])


def _test_invoice_app(r):
    """Il pacchetto che si apre senza terminale, e il bottone per chiuderlo.

    Un «.app» sul Mac non e' un programma: e' una cartella con dentro uno
    script e una scheda che dice al sistema «eseguimi tu». Basta poco perche'
    smetta di funzionare, e quando smette non lo dice: il doppio clic non fa
    semplicemente niente. Qui si controlla che quel poco ci sia ancora.
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pacco = os.path.join(base, 'Invoice.app', 'Contents')
    scheda = os.path.join(pacco, 'Info.plist')
    porta = os.path.join(pacco, 'MacOS', 'Invoice')

    _check(r, 'Invoice.app', 'il pacchetto c’è, con scheda e programma',
           (os.path.isfile(scheda), os.path.isfile(porta)), (True, True))
    # senza il permesso di esecuzione il doppio clic non fa proprio niente
    _check(r, 'Invoice.app', 'e il programma dentro è eseguibile',
           os.access(porta, os.X_OK), True)

    testo_scheda = ''
    if os.path.isfile(scheda):
        with io.open(scheda, encoding='utf-8') as f:
            testo_scheda = f.read()
    # Senza questo il Mac fa partire tutto tradotto da Rosetta anche su Apple
    # Silicon, e Python non riesce piu' a caricare le sue librerie: l'app non
    # parte e l'errore non dice niente di comprensibile. Costato mezz'ora.
    # si guarda dentro l'elenco e non in tutto il file: i commenti qui sopra
    # nominano x86_64 prima di arm64, e un confronto ingenuo li scambierebbe
    # per l'ordine vero
    elenco = re.search(r'<key>LSArchitecturePriority</key>\s*<array>(.*?)</array>',
                       testo_scheda, re.S)
    ordine = re.findall(r'<string>([^<]+)</string>', elenco.group(1)) if elenco else []
    _check(r, 'Invoice.app', 'chiede l’architettura nativa prima della traduzione',
           ordine, ['arm64', 'x86_64'])
    _check(r, 'Invoice.app', 'e dichiara il nome del programma da eseguire',
           '<key>CFBundleExecutable</key>' in testo_scheda
           and '<string>Invoice</string>' in testo_scheda, True)

    testo_porta = ''
    if os.path.isfile(porta):
        with io.open(porta, encoding='utf-8') as f:
            testo_porta = f.read()
    # il pacchetto non deve RIFARE l'avviatore: deve chiamarlo. Se un giorno
    # qualcuno ci copiasse dentro la logica, i due prenderebbero strade
    # diverse senza che nessuno se ne accorga
    _check(r, 'Invoice.app', 'la porta chiama l’avviatore vero, non lo rifà',
           ('Start Invoice.command' in testo_porta,
            'INVOICE_NO_TERMINAL' in testo_porta,
            len(testo_porta.splitlines()) < 20),
           (True, True, True))

    # --- l'avviatore quando nessuno lo ascolta ---
    a = _avviatori()
    mac = a['Start Invoice.command'].decode('utf-8', 'replace')
    _check(r, 'Invoice.app', 'l’avviatore sa di non avere un terminale',
           ('no_terminal()' in mac, 'INVOICE_NO_TERMINAL' in mac), (True, True))
    # Qui l'ordine e' tutto. Dentro Scrivania, Documenti o Download macOS non
    # lascia nemmeno CREARE il file di registro: mettendo il controllo dopo la
    # deviazione dell'uscita, lo script muore sulla riga prima e non spiega
    # niente a nessuno. E' successo davvero.
    dove_guardia = mac.find('touch data/.writable')
    dove_registro = mac.find('exec >>"data/start.log"')
    _check(r, 'Invoice.app', 'controlla di poter scrivere PRIMA di scrivere il registro',
           (dove_guardia > 0, dove_registro > 0, dove_guardia < dove_registro),
           (True, True, True))
    _check(r, 'Invoice.app', 'e se non può, lo dice con un riquadro invece di morire zitto',
           ('display dialog' in mac, 'Desktop, Documents or Downloads' in mac), (True, True))
    # un riquadro che nessuno vede non deve restare in mezzo allo schermo per
    # sempre: ogni domanda e ogni avviso ha una scadenza
    # non basta contarle nel file: un «giving up after» dentro un commento
    # non chiude nessun riquadro. Si guarda che ogni richiamo ce l'abbia
    # dentro, prima che il comando finisca.
    senza_scadenza = []
    for m in re.finditer(r'display dialog', mac):
        pezzo = mac[m.start():m.start() + 400]
        if 'giving up after' not in pezzo.split('>/dev/null')[0]:
            senza_scadenza.append(mac[:m.start()].count('\n') + 1)
    _check(r, 'Invoice.app', 'nessun riquadro può restare aperto per sempre',
           senza_scadenza, [])
    # senza questa, uscendo dal Dock il pacchetto se ne va e l'app resta
    # accesa dietro, con la porta occupata e nessuno che la guardi
    _check(r, 'Invoice.app', 'uscendo dal Dock si porta dietro anche l’app',
           "trap 'kill $APP_PID 2>/dev/null' TERM INT HUP" in mac, True)


def _test_spegnimento(r):
    """Il bottone «Chiudi l'app»: l'unico modo di fermarla, senza finestra."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        programma = f.read()
    with io.open(os.path.join(base, 'templates', 'base.html'), encoding='utf-8') as f:
        barra = f.read()
    with io.open(os.path.join(base, 'templates', 'spento.html'), encoding='utf-8') as f:
        congedo = f.read()

    _check(r, 'Spegnimento', 'la rotta c’è, e solo in POST',
           ("@app.route('/spegni', methods=['POST'])" in programma,
            'def spegni(' in programma), (True, True))
    # senza tenersi il server da parte non ci sarebbe niente da fermare
    _check(r, 'Spegnimento', 'il motore acceso resta raggiungibile',
           ('_SERVER = None' in programma,
            "server = _SERVER = make_server" in programma), (True, True))
    # Fermarlo dentro la richiesta stessa lascerebbe il browser con una pagina
    # a meta': prima si consegna il congedo, poi si spegne.
    _check(r, 'Spegnimento', 'prima consegna la pagina, poi spegne',
           'threading.Timer' in programma and '_SERVER.shutdown' in programma, True)
    _check(r, 'Spegnimento', 'e se non sa quale motore fermare, lo dice',
           'si_spegne=_SERVER is not None' in programma, True)

    _check(r, 'Spegnimento', 'il bottone è nella barra e chiede conferma',
           ("url_for('spegni')" in barra, 'onsubmit="return confirm' in barra),
           (True, True))
    # La pagina di congedo non puo' ereditare da base.html: il menu porterebbe
    # a pagine che fra un istante non rispondono piu', e nemmeno il foglio di
    # stile esterno arriverebbe in tempo.
    _check(r, 'Spegnimento', 'la pagina di congedo non dipende da un server già spento',
           ("{% extends" not in congedo, '<style>' in congedo), (True, True))

    # Senza finestra un guasto all'AVVIO non ha dove comparire: error.log
    # raccoglie solo i guai dentro le pagine, che una pagina ce l'hanno.
    # Questa rete e' l'unica traccia che resta a chi apre Invoice.app o il
    # pythonw di Windows e vede... niente.
    _check(r, 'Spegnimento', 'un guasto all’avvio finisce comunque scritto',
           ('sys.excepthook = _errore_fatale' in programma,
            "err_logger.error('Avvio non riuscito'" in programma), (True, True))
    _check(r, 'Spegnimento', 'ma Ctrl+C non viene scambiato per un guasto',
           'issubclass(tipo, KeyboardInterrupt)' in programma, True)


def _test_trasloco(r):
    """Spostare la cartella dell'app non deve staccare le fatture dai loro file.

    Su macOS lo spostamento non e' un capriccio: dentro Scrivania, Documenti o
    Download il sistema non lascia lavorare l'app. Ma i percorsi dei PDF sono
    scritti per intero nel database, quindi dopo il trasloco puntano a una casa
    che non c'e' piu' e le fatture non si allegano piu' a niente.
    """
    import sqlite3
    import tempfile
    from . import db as _db

    with tempfile.TemporaryDirectory() as tmp:
        nuova = os.path.join(tmp, 'nuova', 'Invoices')
        os.makedirs(os.path.join(nuova, '2026'))
        buono = os.path.join(nuova, '2026', 'Tizio #1.pdf')
        io.open(buono, 'w').close()
        vecchia = os.path.join(tmp, 'vecchia', 'Invoices')
        os.makedirs(os.path.join(vecchia, '2026'))
        ancora = os.path.join(vecchia, '2026', 'Ancora #2.pdf')
        io.open(ancora, 'w').close()

        prima = _db.DIR_FATTURE
        _db.DIR_FATTURE = nuova
        try:
            _check(r, 'Trasloco', 'riconosce il pezzo da «Invoices» in giù',
                   _db._ricolloca(os.path.join(vecchia, '2026', 'Tizio #1.pdf')), buono)
            # una cartella dell'app dentro una che si chiama a sua volta
            # «Invoices» non deve mandare fuori strada: vale l'ultima
            _check(r, 'Trasloco', 'e guarda l’ultima volta che il nome compare',
                   _db._ricolloca('/x/Invoices/app/Invoices/2026/Tizio #1.pdf'),
                   os.path.join(nuova, '2026', 'Tizio #1.pdf'))
            # anche i nomi italiani: un database vecchio li ha ancora dentro
            _check(r, 'Trasloco', 'e capisce anche i nomi vecchi in italiano',
                   _db._ricolloca('/x/Fatture/2024/Tizio #1.pdf'),
                   os.path.join(nuova, '2024', 'Tizio #1.pdf'))
            _check(r, 'Trasloco', 'un percorso che non riconosce lo lascia stare',
                   _db._ricolloca('/x/foto/gatto.png'), None)

            con = sqlite3.connect(':memory:')
            con.executescript(_db.SCHEMA)
            sparito = os.path.join(vecchia, '2026', 'Sparito #9.pdf')
            # Il caso pericoloso: lo STESSO nome esiste in tutt'e due i posti.
            # Se qui si guardasse solo «il nuovo esiste», la fattura verrebbe
            # spostata su un file che non e' il suo — ed e' esattamente il
            # genere di scambio che ha gia' fatto finire il PDF di una persona
            # dentro la fattura di un'altra.
            os.makedirs(os.path.join(nuova, '2025'))
            doppio_vecchio = os.path.join(vecchia, '2026', 'Doppio #3.pdf')
            io.open(doppio_vecchio, 'w').close()
            os.makedirs(os.path.join(nuova, '2026'), exist_ok=True)
            io.open(os.path.join(nuova, '2026', 'Doppio #3.pdf'), 'w').close()
            casi = [
                (1, os.path.join(vecchia, '2026', 'Tizio #1.pdf'), buono),
                (2, ancora, ancora),          # il percorso vecchio funziona ancora
                (3, sparito, sparito),        # il file non c'e' da nessuna parte
                (4, doppio_vecchio, doppio_vecchio),   # esiste di qua E di la'
            ]
            for i, p, _a in casi:
                con.execute('INSERT INTO invoices (id, client_name, pdf_path) VALUES (?,?,?)',
                            (i, 'X', p))
            _db._migra_trasloco(con)
            fuori = []
            for i, _p, atteso in casi:
                v = con.execute('SELECT pdf_path FROM invoices WHERE id=?', (i,)).fetchone()[0]
                if v != atteso:
                    fuori.append(i)
            con.close()
            # tre regole in un colpo: ripara chi si e' spostato, non tocca chi
            # sta bene, e non inventa un percorso per un file che non esiste
            _check(r, 'Trasloco', 'ripara solo dove il file c’è davvero, e non tocca il resto',
                   fuori, [])
        finally:
            _db.DIR_FATTURE = prima

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'core', 'db.py'), encoding='utf-8') as f:
        sorgente = f.read()
    # una migrazione che nessuno chiama e' un commento lungo
    _check(r, 'Trasloco', 'e viene davvero chiamata all’avvio',
           '    _migra_trasloco(con)' in sorgente, True)


def _test_una_cartella_sola(r):
    """Dove vanno le copie lo deve decidere UNA riga sola.

    La regola vera e' scritta in _cartella_backup(): se c'e' INVOICE_BACKUP
    vince quello, se no l'impostazione salvata, se no iCloud. Il primo pezzo
    esiste per una ragione precisa: un'app di prova parte quasi sempre da una
    copia del database vero, e quella copia si porta dietro l'indirizzo della
    cartella vera. Senza l'interruttore, la prova scrive in mezzo ai backup
    buoni.

    E' successo. La regola era scritta in tre punti e due la sbagliavano: la
    pagina Impostazioni mostrava l'elenco delle copie vere anche a un'app di
    prova, e — peggio — l'avvio ci scriveva dentro. Una regola copiata tre
    volte non e' una regola: sono tre regole che per un po' si assomigliano.
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        sorgente = f.read()

    # il corpo di _cartella_backup(): da li' fino alla riga seguente che
    # comincia a colonna zero, cioe' fino a quando finisce la funzione
    inizio = sorgente.index('def _cartella_backup(')
    resto = sorgente[inizio:]
    fine = len(resto)
    for m in re.finditer(r'\n(?=[^\s#])', resto):
        if m.start() > 0:
            fine = m.start()
            break
    dentro, fuori = resto[:fine], sorgente[:inizio] + resto[fine:]

    for parola in ("'backup_dir'", 'DEST_DEFAULT'):
        _check(r, 'Copie', 'in app.py «%s» si nomina solo dentro _cartella_backup' % parola,
               parola in dentro and parola not in fuori, True)

    # ...e chi ha bisogno della cartella la chiede a lei. L'avvio compreso:
    # e' il momento in cui la copia si fa da sola, senza nessuno che guardi.
    _check(r, 'Copie', 'anche l’avvio chiede la cartella alla regola',
           '    _dest = _cartella_backup()' in sorgente, True)
    _check(r, 'Copie', 'INVOICE_BACKUP passa davanti all’impostazione salvata',
           dentro.index("db.env('INVOICE_BACKUP'") < dentro.index("'backup_dir'"), True)

    # Nessuno storico da copiare non e' un guasto: e' il primo giorno.
    import tempfile
    from . import backup as _bk
    esito = _bk.archivia_storico('', tempfile.gettempdir())
    _check(r, 'Copie', 'senza cartella storica non si grida al guasto',
           (esito['ok'], esito['errore'], esito.get('niente')), (True, '', True))
    esito2 = _bk.archivia_storico('/cartella/che/non/esiste/davvero',
                                  tempfile.gettempdir())
    _check(r, 'Copie', 'ma una cartella scritta male resta un guasto',
           (esito2['ok'], bool(esito2['errore'])), (False, True))


def _test_backup_illeggibile(r):
    """Una cartella di backup che non si riesce a leggere non deve far cadere l'app.

    Su macOS capita per davvero: iCloud Drive e' protetto, e a un'app non
    firmata il sistema nega l'ELENCO pur lasciando scrivere e rileggere i
    singoli file. Peggio, os.path.isdir intanto risponde di si', quindi il
    controllo non se ne accorge e l'errore salta fuori piu' avanti — all'avvio,
    prima ancora che l'app apra una pagina.

    Qui la lettura si intercetta invece di giocare coi permessi del disco:
    cosi' la prova vale uguale su ogni sistema, e prova la strada vera del
    codice invece di una sua imitazione.
    """
    import tempfile
    from . import backup as _bk

    with tempfile.TemporaryDirectory() as tmp:
        chiusa = os.path.join(tmp, 'chiusa')
        os.makedirs(chiusa)
        io.open(os.path.join(chiusa, 'fatture-app-20260101-000000.zip'), 'w').close()
        aperta = os.path.join(tmp, 'aperta')
        os.makedirs(aperta)
        io.open(os.path.join(aperta, 'fatture-app-20260101-000000.zip'), 'w').close()
        mai = os.path.join(tmp, 'mai-esistita')

        vero = os.listdir
        # il registro delle copie di una prova sta nella prova: quello vero e'
        # dell'utente, e una Verifica non ci scrive dentro
        vero_registro = _bk.REGISTRO
        _bk.REGISTRO = os.path.join(tmp, 'registro.json')

        def nega(percorso, *a, **k):
            if percorso == chiusa:
                raise PermissionError(1, 'Operation not permitted')
            return vero(percorso, *a, **k)

        os.listdir = nega
        try:
            def prova(f, *a):
                try:
                    return f(*a)
                except Exception as e:
                    return 'CADUTA: %s' % type(e).__name__
            # la caduta all'avvio era esattamente qui
            _check(r, 'Backup illeggibile', 'elencare una cartella negata non fa cadere niente',
                   prova(_bk.elenco_esterni, chiusa), [])
            _check(r, 'Backup illeggibile', 'e nemmeno chiedersi se serve una copia oggi',
                   prova(_bk.serve_backup_oggi, chiusa), True)
            # senza distinguere i due casi, «non c'e' nessuna copia» e «non
            # riesco a vedere se c'e'» sembrerebbero la stessa cosa, e la
            # seconda passerebbe sotto silenzio per sempre
            _check(r, 'Backup illeggibile', 'ma la differenza fra negata e vuota si vede',
                   (prova(_bk.destinazione_leggibile, chiusa),
                    prova(_bk.destinazione_leggibile, aperta),
                    prova(_bk.destinazione_leggibile, mai)),
                   (False, True, True))
            _check(r, 'Backup illeggibile', 'e una cartella normale si legge come sempre',
                   len(prova(_bk.elenco_esterni, aperta)), 1)
        finally:
            os.listdir = vero
            _bk.REGISTRO = vero_registro

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        programma = f.read()
    # l'avvio affida la copia del giorno a copia_del_giorno, che la fa anche con
    # l'elenco negato e lo dice. Se l'avvio tornasse a decidere da se', potrebbe
    # tornare a saltarla — era il difetto (vedi _test_copie_dal_registro)
    _check(r, 'Backup illeggibile', 'l’avvio affida la copia del giorno a copia_del_giorno',
           'backup.copia_del_giorno(_dest' in programma, True)

    # E una guardia sulla forma, non sul comportamento: nel modulo dei backup
    # NESSUNA lettura di cartella puo' stare allo scoperto. Un solo «listdir»
    # dimenticato in un ramo poco battuto — la rotazione dello storico, per
    # dirne uno — rimetterebbe l'app in condizione di cadere, e proprio in quel
    # ramo li', dove nessun collaudo passa. Questo controllo non ha bisogno di
    # attraversarli tutti: li vede.
    import ast as _ast
    with io.open(os.path.join(base, 'core', 'backup.py'), encoding='utf-8') as f:
        albero = _ast.parse(f.read())
    # «dentro un try» non basta come definizione di protetto: la rotazione
    # dello storico sta gia' dentro un try, che pero' ingoierebbe l'intero
    # backup e non solo l'elenco. Quindi si e' precisi: in questo modulo
    # possono leggere una cartella soltanto le funzioni scritte per reggere il
    # rifiuto. Chiunque altro e' un ramo che tornerebbe a cadere.
    AMMESSE = {'_nomi_in', '_copie_in', 'destinazione_leggibile'}
    scoperte = []
    for nodo in _ast.walk(albero):
        if not isinstance(nodo, _ast.FunctionDef):
            continue
        for sotto in _ast.walk(nodo):
            if (isinstance(sotto, _ast.Call) and isinstance(sotto.func, _ast.Attribute)
                    and sotto.func.attr == 'listdir' and nodo.name not in AMMESSE):
                scoperte.append('%s() riga %d' % (nodo.name, sotto.lineno))
    _check(r, 'Backup illeggibile', 'solo le funzioni fatte apposta leggono le cartelle',
           sorted(set(scoperte)), [])


def _test_storico_al_buio(r):
    """Il guaio peggiore che possa capitare a un backup non e' fallire: e'
    riuscire per finta.

    os.walk, se non gli si passa «onerror», ingoia i rifiuti del sistema
    operativo e prosegue come se la cartella fosse vuota. Con quella riga
    sola, una cartella vietata da macOS produceva un archivio vuoto,
    verificato integro e dichiarato riuscito — e uno se ne accorge il giorno
    in cui gli serve, cioe' il giorno peggiore.

    Provato dal vero il 28.08.2026: la cartella dello storico sta sulla
    Scrivania, che macOS protegge, e l'app lanciata dall'icona non ci entra.
    """
    import shutil, tempfile
    from . import backup

    base = tempfile.mkdtemp(prefix='invoice-storico-')
    vero_registro = backup.REGISTRO
    backup.REGISTRO = os.path.join(base, 'registro.json')
    try:
        sorg = os.path.join(base, 'Clients Invoices')
        dest = os.path.join(base, 'Backup')
        os.makedirs(sorg)
        os.makedirs(dest)
        with io.open(os.path.join(sorg, 'fattura.txt'), 'w', encoding='utf-8') as h:
            h.write('x' * 32)

        e = backup.archivia_storico(sorg, dest)
        _check(r, 'Storico al buio', 'quando si legge tutto, la copia si fa',
               (e['ok'], e['saltato'], e['file']), (True, False, 1))

        # la stessa chiamata, subito dopo: niente e' cambiato, non si ricopia
        e = backup.archivia_storico(sorg, dest)
        _check(r, 'Storico al buio', 'e la seconda volta non si ricopia per niente',
               (e['ok'], e['saltato']), (True, True))

        # --- ora il sistema operativo dice di no ---
        vero_walk = backup.os.walk

        def walk_negato(percorso, onerror=None, **kw):
            if onerror:
                onerror(OSError(1, 'Operation not permitted', percorso))
            return iter(())

        def quanti_archivi():
            return len([n for n in os.listdir(dest) if n.startswith('storico-')])

        prima = quanti_archivi()
        backup.os.walk = walk_negato
        try:
            e = backup.archivia_storico(sorg, dest, forza=True)
        finally:
            backup.os.walk = vero_walk
        _check(r, 'Storico al buio', 'cartella vietata: NON si dichiara riuscito',
               (e['ok'], e['file']), (False, 0))
        _check(r, 'Storico al buio', 'e si dice perche\u0301',
               'non si riesce a leggere' in e['errore'], True)
        _check(r, 'Storico al buio', 'e non ha lasciato in giro un archivio finto',
               quanti_archivi(), prima)

        # --- e se e' il SEGNO a non leggersi (l'ha scritto l'app partita in
        #     un altro modo)? Il rifiuto si intercetta invece di togliere i
        #     permessi al file: chmod su Windows non toglie la lettura, e la
        #     prova la' diceva il falso ---
        # non si conta quanti archivi ci sono: due copie nello stesso secondo
        # prendono lo stesso nome e il conteggio non si muove. Quello che
        # distingue una copia da un salto e' «path», che sul salto resta vuoto.
        firma = os.path.abspath(os.path.join(dest, backup.FIRMA))

        def segno_altrui(percorso, *a, **k):
            if os.path.abspath(os.fspath(percorso)) == firma:
                raise PermissionError(1, 'Operation not permitted', percorso)
            return io.open(percorso, *a, **k)

        def storico_col_segno_altrui():
            backup.open = segno_altrui
            try:
                return backup.archivia_storico(sorg, dest)
            finally:
                del backup.open

        # il registro ricorda la firma dell'ultima copia: se quella copia c'e'
        # ancora non si rifanno 7 MB a ogni avvio dall'icona
        e = storico_col_segno_altrui()
        _check(r, 'Storico al buio', 'segno illeggibile, ma registro e archivio ci sono: non si ricopia',
               (e['ok'], e['saltato']), (True, True))
        # ...il registro da solo pero' non basta: senza l'archivio si copia
        for nome in os.listdir(dest):
            if nome.startswith('storico-'):
                os.remove(os.path.join(dest, nome))
        e = storico_col_segno_altrui()
        _check(r, 'Storico al buio', 'segno illeggibile e archivio sparito: si copia invece di saltare',
               (e['ok'], e['saltato'], bool(e['path'])), (True, False, True))
        _check(r, 'Storico al buio', 'e se il segno non si scrive, la copia resta buona',
               (e['ok'], bool(e['nota'])), (True, True))
        # e senza nessun registro, come prima: nel dubbio si copia
        os.remove(backup.REGISTRO)
        e = storico_col_segno_altrui()
        _check(r, 'Storico al buio', 'segno illeggibile e nessun registro: si copia',
               (e['ok'], e['saltato'], bool(e['path'])), (True, False, True))
    finally:
        backup.REGISTRO = vero_registro
        shutil.rmtree(base, ignore_errors=True)


def _test_copie_dal_registro(r):
    """Con l'elenco della cartella negato le copie fuori si fanno, e si ritrovano.

    Sul Mac, all'app partita dall'icona il sistema nega l'elenco della cartella
    iCloud dei backup, ma le lascia scrivere uno zip nuovo, rileggerlo e
    chiedere se un nome esiste: misurato il 13.09.2026 con un'app di prova non
    firmata. L'avvio pero' guardava l'elenco, lo trovava vuoto e saltava la
    copia del giorno, e la Dashboard diceva «mai fatta» con la cartella piena.
    Ora l'app si segna le copie in un registro accanto al database.
    """
    import datetime
    import shutil
    import sqlite3
    import tempfile
    from . import backup as B
    from . import overview

    base = tempfile.mkdtemp(prefix='invoice-registro-')
    dest = os.path.join(base, 'Backup')
    sorg = os.path.join(base, 'Storico')
    os.makedirs(dest)
    os.makedirs(sorg)
    with io.open(os.path.join(sorg, 'vecchia.txt'), 'w', encoding='utf-8') as f:
        f.write('x' * 16)
    # un database finto con una fattura: la copia e la sua verifica sono vere,
    # ma quello dell'utente non si apre
    finto = os.path.join(base, 'fatture.db')
    con = sqlite3.connect(finto)
    con.execute('CREATE TABLE invoices (id INTEGER, deleted_at TEXT)')
    con.execute('INSERT INTO invoices VALUES (1, NULL)')
    con.commit()
    con.close()

    vero = {'REGISTRO': B.REGISTRO, '_sorgenti': B._sorgenti,
            '_conta_fatture': B._conta_fatture}
    vero_listdir = os.listdir
    negata = os.path.abspath(dest)

    def nega(percorso='.', *a, **k):
        if os.path.abspath(os.fspath(percorso)) == negata:
            raise PermissionError(1, 'Operation not permitted', percorso)
        return vero_listdir(percorso, *a, **k)

    def zip_veri():
        return sorted(n for n in vero_listdir(dest) if n.startswith('fatture-app-'))

    def nomi_di(copie):
        return [c['name'] for c in copie] if isinstance(copie, list) else copie

    estranea = os.path.join(dest, 'fatture-app-20260901-080000.zip')
    B.REGISTRO = os.path.join(base, 'registro.json')
    B._sorgenti = lambda: [(finto, 'fatture.db')]
    B._conta_fatture = lambda: 1
    os.listdir = nega
    try:
        # --- primo avvio dall'icona: nessuna copia nota, elenco negato ---
        righe = _senza_scoppiare(B.copia_del_giorno, dest, sorg)
        _check(r, 'Backup illeggibile', 'elenco negato: la copia del giorno si fa lo stesso',
               len(zip_veri()), 1)
        _check(r, 'Backup illeggibile', 'e l’avvio dice che l’elenco è negato',
               isinstance(righe, list) and any('elenco' in x for x in righe), True)
        _check(r, 'Backup illeggibile', 'la copia appena fatta si ritrova senza elenco',
               nomi_di(_senza_scoppiare(B.elenco_esterni, dest)), zip_veri())
        _check(r, 'Backup illeggibile', 'quindi oggi non se ne fa un’altra',
               _senza_scoppiare(B.serve_backup_oggi, dest), False)
        prima = sorted(vero_listdir(dest))
        _senza_scoppiare(B.copia_del_giorno, dest, sorg)
        _check(r, 'Backup illeggibile', 'e un secondo avvio nello stesso giorno non rifà niente',
               sorted(vero_listdir(dest)), prima)
        memoria = sqlite3.connect(':memory:')
        memoria.execute('CREATE TABLE invoices (id INTEGER, deleted_at TEXT)')
        memoria.execute('INSERT INTO invoices VALUES (1, NULL)')
        _check(r, 'Backup illeggibile', 'la Dashboard non avvisa di una copia mancante',
               _senza_scoppiare(overview._backup_vecchio, memoria, dest), '')
        memoria.close()

        # --- una copia cancellata da qualcuno non si conta piu' ---
        for nome in zip_veri():
            os.remove(os.path.join(dest, nome))
        _check(r, 'Backup illeggibile', 'una copia sparita dalla cartella non si conta più',
               _senza_scoppiare(B.ultimo_esterno, dest), None)

        # --- sfoltire senza elenco: si tolgono solo copie che il registro conosce ---
        nomi = ['fatture-app-20260902-080000.zip', 'fatture-app-20260903-080000.zip',
                'fatture-app-20260904-080000.zip']
        for i, nome in enumerate(nomi + [os.path.basename(estranea)]):
            p = os.path.join(dest, nome)
            io.open(p, 'wb').close()
            quando = datetime.datetime(2026, 9, 2 + i if i < 3 else 1, 8).timestamp()
            os.utime(p, (quando, quando))
            if nome in nomi:
                _senza_scoppiare(B._ricorda, dest, nome)
        _senza_scoppiare(B.prune_esterni, dest, 1)
        _check(r, 'Backup illeggibile', 'sfoltire senza elenco: restano la più nuova e la prima del mese',
               sorted(n for n in vero_listdir(dest) if n in nomi), [nomi[0], nomi[2]])
        _check(r, 'Backup illeggibile', 'e quella tolta non si conta più',
               nomi_di(_senza_scoppiare(B.elenco_esterni, dest)), [nomi[2], nomi[0]])
        _check(r, 'Backup illeggibile', 'una copia che il registro non conosce non si tocca',
               os.path.exists(estranea), True)
    finally:
        os.listdir = vero_listdir
        B._sorgenti = vero['_sorgenti']
        B._conta_fatture = vero['_conta_fatture']

    try:
        # --- con l'elenco concesso il registro si riallinea da solo ---
        _senza_scoppiare(B.elenco_esterni, dest)
        os.listdir = nega
        try:
            visti = nomi_di(_senza_scoppiare(B.elenco_esterni, dest))
        finally:
            os.listdir = vero_listdir
        _check(r, 'Backup illeggibile', 'con l’elenco concesso il registro impara anche le copie che non ha fatto',
               isinstance(visti, list) and os.path.basename(estranea) in visti, True)
    finally:
        B.REGISTRO = vero['REGISTRO']
        shutil.rmtree(base, ignore_errors=True)
    _check(r, 'Backup illeggibile', 'e la Verifica non ha toccato il registro vero',
           B.REGISTRO, vero['REGISTRO'])


CAMT_RIFERIMENTI = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"><BkToCstmrStmt><Stmt>
 <Ntry><Amt Ccy="CHF">200.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-09-01</Dt></BookgDt>
  <NtryDtls><TxDtls>
   <RltdPties><Dbtr><Nm>Vera Buergi</Nm></Dbtr></RltdPties>
   <RmtInf><Strd><CdtrRefInf><Tp><CdOrPrtry><Cd>SCOR</Cd></CdOrPrtry></Tp>
    <Ref>RF18539007547034</Ref></CdtrRefInf></Strd></RmtInf>
  </TxDtls></NtryDtls>
 </Ntry>
 <Ntry><Amt Ccy="CHF">110.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-09-02</Dt></BookgDt>
  <NtryDtls><TxDtls>
   <RltdPties><Dbtr><Nm>Céline Favre</Nm></Dbtr></RltdPties>
   <RmtInf><Strd><AddtlRmtInf>RF18539007547034 me lo ha detto lui</AddtlRmtInf></Strd></RmtInf>
  </TxDtls></NtryDtls>
 </Ntry>
</Stmt></BkToCstmrStmt></Document>
"""


def _test_riferimento_qr(r):
    """La strada che porta al pallino verde, che nessuno aveva mai percorso.

    Fino al 06.09.2026 l'unico estratto conto finto della batteria non aveva
    dentro NESSUN riferimento: tutto il codice che deve rendere «certo» un
    accostamento non era mai stato messo alla prova. Ed era il codice su cui
    poggia la QR-fattura.

    Le due trappole, tutt'e due vere e tutt'e due trovate guardando un camt.053
    autentico, scaricato da una banca svizzera:

    - «AddtlRmtInf» e' testo libero, scritto da chi paga. Prima finiva nello
      stesso paniere del riferimento vero, e bastava che qualcuno ci copiasse
      dentro un codice perche' l'app dicesse «certo».
    - il confronto teneva solo le CIFRE. Il riferimento QRR e' fatto di 27
      numeri e sopravviveva, ma il SCOR — quello che va su ogni IBAN normale —
      comincia per «RF» e porta lettere: due riferimenti diversi diventavano
      lo stesso.
    """
    import shutil, tempfile
    from . import bank as B

    cartella = tempfile.mkdtemp(prefix='invoice-rif-')
    try:
        with io.open(os.path.join(cartella, 'rif.xml'), 'w', encoding='utf-8') as h:
            h.write(CAMT_RIFERIMENTI)
        mov, problemi = B.leggi_cartella(cartella)
        per_importo = {m['importo_cents']: m for m in mov}

        _check(r, 'Riferimento QR', 'il camt viene letto senza intoppi',
               (problemi, sorted(per_importo)), ([], [11000, 20000]))
        _check(r, 'Riferimento QR', 'il riferimento strutturato arriva intero',
               per_importo[20000]['riferimento'], 'RF18539007547034')
        # la trappola: stesso codice, ma scritto in una frase
        _check(r, 'Riferimento QR', 'il testo libero NON vale come riferimento',
               per_importo[11000]['riferimento'], '')

        certo = per_importo[20000]
        _check(r, 'Riferimento QR', 'lo stesso riferimento, spazi a parte, e\u0300 una certezza',
               B._riferimento_uguale(certo, {'qr_ref': 'RF18 5390 0754 7034'}), True)
        _check(r, 'Riferimento QR', 'un riferimento diverso non conclude niente',
               B._riferimento_uguale(certo, {'qr_ref': 'RF18539007547035'}), False)
        # due SCOR che differiscono SOLO per una lettera: tenendo le sole
        # cifre sarebbero stati lo stesso riferimento
        _check(r, 'Riferimento QR', 'due riferimenti che cambiano solo per una lettera restano diversi',
               B._riferimento_uguale({'riferimento': 'RF18AB0754'}, {'qr_ref': 'RF18XB0754'}), False)
        _check(r, 'Riferimento QR', 'e il QRR a 27 cifre combacia lo stesso',
               B._riferimento_uguale({'riferimento': '21 00000 00003 13947 14300 09017'},
                                     {'qr_ref': '210000000003139471430009017'}), True)
        # una fattura senza riferimento stampato non puo' MAI dare una certezza
        _check(r, 'Riferimento QR', 'senza riferimento sulla fattura non si conclude niente',
               (B._riferimento_uguale(certo, {'numero': 84}),
                B._riferimento_uguale(certo, {'qr_ref': None})), (False, False))
    finally:
        shutil.rmtree(cartella, ignore_errors=True)


# Un camt.053 come lo manda DAVVERO la banca. La differenza con CAMT_PROVA e
# CAMT_RIFERIMENTI non e' un dettaglio di stile: e' esattamente il punto in cui
# il lettore era cieco, e nessuna delle due prove precedenti poteva vederlo,
# perche' tutt'e due erano scritte con la forma vecchia dentro un'intestazione
# nuova. Un file finto che non somiglia a quello vero non e' una prova.
CAMT_BANCA = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"><BkToCstmrStmt><Stmt>
 <Ntry><Amt Ccy="CHF">110.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-08-03</Dt></BookgDt>
  <NtryDtls><TxDtls><RltdPties>
    <Dbtr><Pty><Nm>Petra Müller</Nm>
     <PstlAdr><StrtNm>Bahnhofstrasse</StrtNm><TwnNm>Zug</TwnNm></PstlAdr></Pty></Dbtr>
    <Cdtr><Pty><Nm>Anna Rossi</Nm></Pty></Cdtr>
  </RltdPties></TxDtls></NtryDtls>
  <AddtlNtryInf>Accredito Petra Müller</AddtlNtryInf>
 </Ntry>
 <Ntry><Amt Ccy="CHF">1800.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-08-04</Dt></BookgDt>
  <NtryDtls><TxDtls><RltdPties><Dbtr><Nm>Bruno Keller</Nm></Dbtr></RltdPties>
   <RmtInf><Ustrd>Pacchetto 10 sedute</Ustrd></RmtInf>
  </TxDtls></NtryDtls>
 </Ntry>
 <Ntry><Amt Ccy="CHF">0.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-08-05</Dt></BookgDt>
  <NtryDtls><TxDtls><Amt Ccy="CHF">0.00</Amt></TxDtls></NtryDtls>
  <AddtlNtryInf>Importo di chiusura dal 30.06.2026 al 30.09.2026</AddtlNtryInf>
 </Ntry>
 <Ntry><Amt Ccy="CHF">2.73</Amt><CdtDbtInd>CRDT</CdtDbtInd>
  <BookgDt><Dt>2026-08-06</Dt></BookgDt>
  <NtryDtls><TxDtls><Cdtr><Pty><Nm>Anna Rossi</Nm></Pty></Cdtr></TxDtls></NtryDtls>
  <AddtlNtryInf>Accredito correzione tasso di cambio
nuovo corso 0.7953</AddtlNtryInf>
 </Ntry>
</Stmt></BkToCstmrStmt></Document>
"""


def _test_camt_vero(r):
    """Il lettore del camt messo davanti a un camt vero.

    Il 06.09.2026, aperto il primo estratto conto XML autentico (Raiffeisen,
    camt.053.001.08), il lettore ha restituito 35 versamenti e ZERO nomi. Non
    un caso limite: zero su trentacinque, cioe' non funzionava affatto. Due
    cause, tutt'e due invisibili alle prove che c'erano:

    - il nome di chi paga non e' «Dbtr/Nm» ma «Dbtr/Pty/Nm». Fra il camt.053
      .001.04 e il .001.08 la banca ha infilato di mezzo un «Pty», e il codice
      cercava un figlio DIRETTO.
    - «AddtlNtryInf», la riga che scrive la banca («Accredito Erika von
      Arx»), e' figlia della VOCE, non del dettaglio: si cercava dentro
      TxDtls, dove non e' mai stata.

    Il risultato era un versamento senza nome e senza causale, che non puo'
    somigliare a nessun cliente: tutti da smistare a mano.
    """
    import shutil, tempfile
    from . import bank as B

    cartella = tempfile.mkdtemp(prefix='invoice-camt-')
    try:
        with io.open(os.path.join(cartella, 'banca.xml'), 'w', encoding='utf-8') as h:
            h.write(CAMT_BANCA)
        mov, problemi = B.leggi_cartella(cartella)
        per_importo = {m['importo_cents']: m for m in mov}

        _check(r, 'Camt vero', 'il file viene letto senza intoppi', problemi, [])
        _check(r, 'Camt vero', 'il nome sotto «Dbtr/Pty/Nm» arriva',
               per_importo.get(11000, {}).get('nome'), 'Petra Müller')
        _check(r, 'Camt vero', 'e la forma vecchia «Dbtr/Nm» continua ad arrivare',
               per_importo.get(180000, {}).get('nome'), 'Bruno Keller')
        _check(r, 'Camt vero', 'la riga scritta dalla banca entra nella causale',
               'Accredito' in per_importo.get(11000, {}).get('descrizione', ''), True)
        _check(r, 'Camt vero', 'e la causale scritta da chi paga anche',
               'Pacchetto 10 sedute' in per_importo.get(180000, {}).get('descrizione', ''), True)
        # il nome c'e' gia' dentro «Accredito Petra Müller»: ripeterlo davanti
        # farebbe una riga che si legge male e non aggiunge niente
        _check(r, 'Camt vero', 'il nome non viene ripetuto due volte',
               per_importo.get(11000, {}).get('descrizione'), 'Accredito Petra Müller')
        # la trappola vera: accanto a chi paga c'e' SEMPRE il creditore, che sei
        # tu. Pescare il primo «Nm» che capita vorrebbe dire intestare a te ogni
        # versamento — e su una correzione della banca, dove il pagante non
        # c'e', succederebbe di sicuro.
        _check(r, 'Camt vero', 'il tuo nome non viene mai preso per quello di chi paga',
               [m['nome'] for m in mov if 'Rossi' in (m['nome'] or '')], [])
        _check(r, 'Camt vero', 'una correzione della banca resta senza nome',
               per_importo.get(273, {}).get('nome'), '')
        # un accredito di zero franchi non e' un pagamento: e' la riga di
        # chiusura del trimestre, e chiederne conto e' solo rumore
        _check(r, 'Camt vero', 'un accredito di 0.00 non è un versamento',
               sorted(per_importo), [273, 11000, 180000])
        # le istruzioni lasciate nella cartella non sono un estratto conto, e
        # segnalarle come file rotto a ogni apertura insegna a non leggere gli
        # avvisi — compresi quelli che invece contano
        with io.open(os.path.join(cartella, 'README.txt'), 'w', encoding='utf-8') as h:
            h.write('Metti qui gli estratti scaricati dall\'e-banking.\n')
        _check(r, 'Camt vero', 'le istruzioni nella cartella non sono un file rotto',
               B.leggi_cartella(cartella)[1], [])
    finally:
        shutil.rmtree(cartella, ignore_errors=True)


def _test_gemelli_fra_file(r):
    """Lo stesso versamento visto in due file diversi non si decide due volte.

    Il 06.09.2026, scaricato il primo estratto in XML accanto ai PDF che
    c'erano gia', la pagina Banca ha chiesto conto di 35 versamenti: 29 erano
    pagamenti gia' smistati mesi prima, ricomparsi soltanto perche' letti da un
    altro file. L'impronta di un movimento e' fatta anche sulla causale, e la
    causale della stessa operazione cambia da un formato all'altro — «Accredito
    Erika von Arx Musterweg 9, 6300 Zug 110.00» nel PDF,
    «Accredito Erika von Arx» nell'XML. Due impronte, un pagamento solo.

    La regola qui sotto riconosce il gemello, ma NON tira a indovinare: il
    30.04.2026 sul conto vero sono arrivati due versamenti da 110 franchi lo
    stesso giorno, e collassarli in uno vorrebbe dire far sparire un incasso.
    Si accostano solo quando l'accostamento e' l'unico possibile.
    """
    import sqlite3
    from . import bank as B
    from . import db as _db
    from .db import SCHEMA

    def conto(*decisi):
        con = sqlite3.connect(':memory:')
        con.row_factory = sqlite3.Row
        con.executescript(SCHEMA)
        _db._migrate(con)
        for m in decisi:
            con.execute('INSERT INTO movimenti(impronta, data, importo_cents, '
                        "descrizione, file, stato) VALUES(?,?,?,?,?,'collegato')",
                        (m['impronta'], m['data'], m['importo_cents'],
                         m['descrizione'], m['file']))
        return con

    def da_decidere(con, movimenti):
        return [p['m']['file'] for p in B.proposte(con, movimenti) if not p['deciso']]

    petra_pdf = B._movimento('2026-08-03', 11000,
                             'Accredito Petra Müller Bahnhofstrasse 4, 6300 Zug 110.00',
                             'estratto.pdf', 'Petra Müller')
    petra_xml = B._movimento('2026-08-03', 11000, 'Accredito Petra Müller',
                             'estratto.xml', 'Petra Müller')
    _check(r, 'Gemelli', 'due formati danno impronte diverse (è il guaio da curare)',
           petra_pdf['impronta'] == petra_xml['impronta'], False)

    con = conto(petra_pdf)
    _check(r, 'Gemelli', 'il gemello di un versamento già deciso non si richiede',
           da_decidere(con, [petra_pdf, petra_xml]), [])
    # e lo dice: sparire in silenzio da una pagina di conti non va mai bene
    p = next(x for x in B.proposte(con, [petra_pdf, petra_xml]) if x['deciso'])
    _check(r, 'Gemelli', 'e la riga superstite dice da quale altro file arriva',
           p.get('anche_in'), ['estratto.xml'])
    con.close()

    # due versamenti uguali lo stesso giorno: il caso vero del 30.04.2026
    bruno_pdf = B._movimento('2026-08-03', 11000, 'Accredito Bruno Keller 110.00',
                             'estratto.pdf', 'Bruno Keller')
    bruno_xml = B._movimento('2026-08-03', 11000, 'Accredito Bruno Keller',
                             'estratto.xml', 'Bruno Keller')
    con = conto(petra_pdf, bruno_pdf)
    _check(r, 'Gemelli', 'due versamenti gemelli lo stesso giorno si separano per nome',
           da_decidere(con, [petra_pdf, bruno_pdf, petra_xml, bruno_xml]), [])
    con.close()

    # gli stessi due, ma senza nome: qui non si sa chi è chi, e non si indovina
    muto_a = B._movimento('2026-08-03', 11000, 'Versamento', 'muto.xml')
    muto_b = B._movimento('2026-08-03', 11000, 'Versamento e-banking', 'muto.xml')
    con = conto(petra_pdf, bruno_pdf)
    _check(r, 'Gemelli', 'senza nome non si accosta niente: si chiede',
           da_decidere(con, [petra_pdf, bruno_pdf, muto_a, muto_b]),
           ['muto.xml', 'muto.xml'])
    con.close()

    # DUE PAGAMENTI VERI nello stesso file: non sono gemelli, sono due incassi
    con = conto(petra_pdf)
    _check(r, 'Gemelli', 'due incassi uguali nello stesso file restano due incassi',
           da_decidere(con, [petra_pdf, bruno_pdf]), ['estratto.pdf'])
    con.close()

    # un versamento nuovo, che non somiglia a niente di deciso, resta da fare
    con = conto(petra_pdf)
    nuovo = B._movimento('2026-08-09', 20000, 'Accredito Bruno Keller',
                         'estratto.xml', 'Bruno Keller')
    _check(r, 'Gemelli', 'un versamento davvero nuovo non viene inghiottito',
           da_decidere(con, [petra_pdf, petra_xml, nuovo]), ['estratto.xml'])
    con.close()


def _test_qr_fattura(r):
    """La QR-fattura: il riferimento, il contenuto del codice, il foglio.

    Qui dentro un errore non si vede: esce un bollettino che sembra buono, il
    cliente lo inquadra e la sua banca dice di no — oppure, peggio, dice di si'
    e i soldi vanno da un'altra parte. Percio' si prova contro numeri VERI:
    l'esempio del Creditor Reference pubblicato con lo standard, e le posizioni
    delle righe nel codice, che sono fisse e non si possono spostare di una.
    """
    import tempfile
    from . import qrbill as Q
    from . import pdfgen
    from .db import DEFAULT_SETTINGS

    # --- il riferimento -------------------------------------------------
    # RF18539007547034 e' l'esempio che gira nella documentazione ufficiale:
    # se le cifre di controllo tornano su questo, l'algoritmo e' quello giusto
    _check(r, 'QR-fattura', 'le cifre di controllo del riferimento sono quelle vere',
           Q.riferimento_scor('539007547034'), 'RF18539007547034')
    _check(r, 'QR-fattura', 'e il riferimento che ne esce si riconosce valido',
           Q.scor_valido('RF18539007547034'), True)
    # cambiando UNA cifra di controllo il riferimento non deve piu' passare:
    # e' esattamente il servizio che quelle due cifre rendono a chi paga
    _check(r, 'QR-fattura', 'un riferimento con il controllo storto viene respinto',
           Q.scor_valido('RF19539007547034'), False)
    _check(r, 'QR-fattura', 'e quello che l\'app compone da sola si controlla da solo',
           all(Q.scor_valido(Q.riferimento_per(n)) for n in (1, 7, 87, 1042, 99999)), True)

    # --- che tipo di riferimento si puo' usare --------------------------
    # QRR vuole un QR-IBAN; l'IBAN normale in uso qui NON lo e', e sbagliare
    # questa riga vorrebbe dire stampare bollettini che la banca rifiuta
    _check(r, 'QR-fattura', 'un IBAN normale non è un QR-IBAN',
           Q.e_qr_iban('CH5800791123000889012'), False)
    _check(r, 'QR-fattura', 'un IBAN con istituto 30000-31999 sì',
           (Q.e_qr_iban('CH4431999123000889012'), Q.e_qr_iban('CH5630000123000889012')),
           (True, True))

    # --- il contenuto del codice ----------------------------------------
    mio = Q.indirizzo_strutturato('Musterstrasse 45', 'Musterstadt, 8000')
    suo = Q.indirizzo_strutturato('Musterweg 9', '6300 Zug')
    _check(r, 'QR-fattura', 'il CAP scritto DOPO la località si legge lo stesso',
           (mio or {}).get('cap'), '8000')
    dati = Q.dati_qr('CH58 0079 1123 0008 8901 2', 'Anna Rossi Fitness',
                     mio, 180000, 'RF8087', 'Fattura 87',
                     debitore_nome='Erika Von Arx', debitore_ind=suo)
    tutte = dati.split('\n')
    # se il codice esce piu' corto del dovuto, le righe che mancano devono dare
    # una prova ROSSA, non far saltare la batteria: una prova che si schianta
    # ferma anche tutte quelle che vengono dopo, e allora non si sa piu' niente
    righe = tutte + ['(manca)'] * (40 - len(tutte))
    # le posizioni sono fisse: una riga in piu' o in meno sposta tutto quello
    # che viene dopo, e il codice diventa un altro codice
    _check(r, 'QR-fattura', 'il codice ha le 31 righe dello standard', len(tutte), 31)
    _check(r, 'QR-fattura', 'apre con SPC, versione 0200, codifica 1',
           righe[:3], ['SPC', '0200', '1'])
    _check(r, 'QR-fattura', "l'IBAN entra senza spazi", righe[3], 'CH5800791123000889012')
    _check(r, 'QR-fattura', "l'indirizzo è del tipo strutturato",
           (righe[4], righe[6], righe[7], righe[8], righe[9]),
           ('S', 'Musterstrasse', '45', '8000', 'Musterstadt'))
    _check(r, 'QR-fattura', 'le sette righe del creditore finale restano vuote',
           righe[11:18], [''] * 7)
    _check(r, 'QR-fattura', "l'importo è in franchi e centesimi",
           (righe[18], righe[19]), ('1800.00', 'CHF'))
    _check(r, 'QR-fattura', 'il tipo di riferimento è SCOR e il riferimento lo segue',
           (righe[27], righe[28]), ('SCOR', 'RF8087'))
    _check(r, 'QR-fattura', 'e chiude con EPD', righe[30], 'EPD')
    _check(r, 'QR-fattura', 'il codice sta nei 997 caratteri concessi',
           len(dati) <= Q.MAX_CARATTERI, True)

    # senza il pagante le sue sette righe restano vuote MA ci sono: e' la
    # differenza fra un campo lasciato in bianco e un codice sfasato
    senza = Q.dati_qr('CH5800791123000889012', 'Anna Rossi Fitness',
                      mio, 11000, 'RF5388').split('\n')
    _check(r, 'QR-fattura', 'senza il pagante le righe ci sono lo stesso, vuote',
           (len(senza), (senza + ['(manca)'] * 40)[20:27]), (31, [''] * 7))

    # --- quello che NON si deve fare ------------------------------------
    def _rifiuta(f):
        try:
            f()
            return False
        except ValueError:
            return True
    _check(r, 'QR-fattura', 'senza indirizzo del creditore non si stampa niente',
           _rifiuta(lambda: Q.dati_qr('CH5800791123000889012', 'X', None, 100, 'RF5388')),
           True)
    _check(r, 'QR-fattura', 'un riferimento inventato non entra nel codice',
           _rifiuta(lambda: Q.dati_qr('CH5800791123000889012', 'X', mio, 100, 'RF99123')),
           True)
    _check(r, 'QR-fattura', 'una moneta che non sia CHF o EUR non entra',
           _rifiuta(lambda: Q.dati_qr('CH5800791123000889012', 'X', mio, 100,
                                      'RF5388', moneta='USD')), True)

    # --- gli indirizzi che NON si capiscono -----------------------------
    # sono indirizzi veri, presi dall'archivio: se il lettore li indovinasse,
    # finirebbero stampati su un documento di pagamento
    for riga1, riga2 in (('Ireland', ''), ('Address', 'Address'),
                         ('Musterweg 227', 'Kilchberg, Zurich'),
                         ('Musterweg', '8802 Kilchberg')):
        _check(r, 'QR-fattura', 'non indovina l\'indirizzo «%s / %s»' % (riga1, riga2),
               Q.indirizzo_strutturato(riga1, riga2), None)

    # --- dalle impostazioni ---------------------------------------------
    buone = dict(DEFAULT_SETTINGS, business_name='Anna Rossi Fitness',
                 business_iban='CH5604835012345678009',
                 business_addr1='Musterstrasse 1', business_addr2='8000 Musterstadt',
                 qr_fattura='1')
    ok, motivo = Q.da_impostazioni(buone)
    _check(r, 'QR-fattura', 'con le impostazioni a posto il creditore si compone',
           (bool(ok), motivo), (True, ''))
    for cosa, valore in (('business_iban', 'CH94'), ('business_name', ''),
                         ('business_addr1', 'Ireland')):
        dati_r, perche = Q.da_impostazioni(dict(buone, **{cosa: valore}))
        _check(r, 'QR-fattura', 'senza «%s» dice cosa manca invece di provarci' % cosa,
               (dati_r, bool(perche)), (None, True))

    # --- il foglio dentro il PDF ----------------------------------------
    from pypdf import PdfReader
    voci = [{'qty': 10, 'description': '10 Sessions Pack',
             'unit_cents': 12000, 'total_cents': 120000}]
    with tempfile.TemporaryDirectory() as tmp:
        # non «con.pdf»: CON e' un nome riservato di Windows, come NUL e PRN,
        # e un file che si chiama cosi' li' non si puo' creare
        acceso = os.path.join(tmp, 'acceso.pdf')
        spento = os.path.join(tmp, 'spento.pdf')
        pdfgen.build_pdf(acceso, 7, '23-08-26', 'Mario Bianchi',
                         ['Musterweg 3', '8001 Zürich'], voci, 120000, buone)
        pdfgen.build_pdf(spento, 7, '23-08-26', 'Mario Bianchi',
                         ['Musterweg 3', '8001 Zürich'], voci, 120000,
                         dict(buone, qr_fattura='0'))
        _check(r, 'QR-fattura', 'acceso, la fattura ha il foglio del bollettino in coda',
               len(PdfReader(acceso).pages), 2)
        _check(r, 'QR-fattura', 'spento, la fattura resta di una pagina sola',
               len(PdfReader(spento).pages), 1)
        testo = '\n'.join(p.extract_text() or '' for p in PdfReader(acceso).pages)
        _check(r, 'QR-fattura', 'sul foglio ci sono ricevuta e sezione pagamento',
               ('Ricevuta' in testo, 'Sezione pagamento' in testo), (True, True))
        _check(r, 'QR-fattura', 'e il riferimento stampato è quello della fattura #7',
               Q._a_gruppi(Q.riferimento_per(7)) in testo, True)
        # la verifica automatica legge il PDF per ricavarne il totale: con una
        # pagina in piu' dentro, e un altro importo scritto sopra, deve
        # continuare a trovare lo stesso numero. Se non torna, la fattura non
        # verrebbe salvata affatto — e nessuno capirebbe perche'.
        from . import verify
        _check(r, 'QR-fattura', 'la verifica automatica regge la pagina in più',
               verify._pdf_total_cents(acceso), 120000)


def _test_qr_iban(r):
    """Chi ha un QR-IBAN deve poter mandare un bollettino che la banca accetta.

    Fino al 10.09.2026 l'app stampava sempre un riferimento RF. Su un IBAN
    normale va benissimo; su un QR-IBAN, quello col numero d'istituto fra
    30000 e 31999, lo standard vuole il riferimento QR di 27 cifre, e un RF
    viene rifiutato. La funzione che riconosce il QR-IBAN esisteva gia', ma non
    la chiamava nessuno: per chi ha scritto l'app non c'era niente da vedere,
    perche' il suo IBAN e' normale. Per chi la compra con un QR-IBAN ogni
    bollettino sarebbe stato carta.

    Le prove seguono il riferimento da un capo all'altro: come si calcola,
    quale tipo sceglie l'IBAN, cosa entra nel codice, come si legge sul
    foglio, e che il PDF vero lo porti davvero.
    """
    import logging
    import re
    import tempfile
    from . import qrbill as Q
    from . import pdfgen
    from .db import DEFAULT_SETTINGS

    QR_IBAN = 'CH4431999123000889012'         # istituto 31999: e' un QR-IBAN
    IBAN = 'CH5800791123000889012'            # istituto 00791: IBAN normale
    ESEMPIO = '210000000003139471430009017'   # l'esempio delle linee guida SIX

    # --- il riferimento QR, calcolato ---------------------------------------
    _check(r, 'QR-IBAN', 'la cifra di controllo è quella dell’esempio ufficiale',
           _senza_scoppiare(lambda: Q.riferimento_qrr(ESEMPIO[:26])), ESEMPIO)
    _check(r, 'QR-IBAN', 'e l’esempio ufficiale si riconosce valido, spazi o no',
           _senza_scoppiare(lambda: (Q.qrr_valido(ESEMPIO),
                                     Q.qrr_valido('21 00000 00003 13947 14300 09017'))),
           (True, True))
    _check(r, 'QR-IBAN', 'una cifra sbagliata viene respinta',
           _senza_scoppiare(lambda: Q.qrr_valido(ESEMPIO[:-1] + '8')), False)
    corto = _senza_scoppiare(lambda: Q.riferimento_qrr('87'))
    _check(r, 'QR-IBAN', 'un riferimento QR ha sempre 27 cifre, anche da un numero corto',
           _senza_scoppiare(lambda: (len(corto), corto.isdigit(), Q.qrr_valido(corto))),
           (27, True, True))

    # --- il tipo lo decide l'IBAN -------------------------------------------
    rif_qr = _senza_scoppiare(lambda: Q.riferimento_per(87, QR_IBAN))
    _check(r, 'QR-IBAN', 'con un QR-IBAN la fattura prende un riferimento QR',
           _senza_scoppiare(lambda: Q.qrr_valido(rif_qr)), True)
    _check(r, 'QR-IBAN', 'e il numero della fattura si ritrova in fondo, prima del controllo',
           str(rif_qr)[:-1].lstrip('0'), '87')
    # questa e' verde gia' prima: e' la guardia che il cambio non tocchi chi
    # ha un IBAN normale, cioe' quasi tutti — e chi ha scritto l'app
    _check(r, 'QR-IBAN', 'con un IBAN normale il riferimento resta l’RF di sempre',
           _senza_scoppiare(lambda: Q.riferimento_per(87, IBAN)), Q.riferimento_scor(87))
    con_prefisso = _senza_scoppiare(lambda: Q.riferimento_per(87, QR_IBAN, '123456'))
    _check(r, 'QR-IBAN', 'il numero dato dalla banca apre il riferimento',
           _senza_scoppiare(lambda: (con_prefisso[:6], Q.qrr_valido(con_prefisso),
                                     con_prefisso[:-1].endswith('87'))),
           ('123456', True, True))

    # --- nel codice QR non entra mai una coppia sbagliata --------------------
    mio = Q.indirizzo_strutturato('Musterstrasse 45', 'Musterstadt, 8000')

    def _rifiuta(f):
        try:
            f()
        except ValueError:
            return True
        except Exception:
            return False
        return False

    testo = _senza_scoppiare(lambda: Q.dati_qr(QR_IBAN, 'Anna Rossi Fitness', mio,
                                               11000, ESEMPIO))
    _check(r, 'QR-IBAN', 'su un QR-IBAN il codice dichiara QRR e porta le 27 cifre',
           '\nQRR\n%s\n' % ESEMPIO in str(testo), True)
    _check(r, 'QR-IBAN', 'un RF su un QR-IBAN non si stampa: la banca lo rifiuterebbe',
           _rifiuta(lambda: Q.dati_qr(QR_IBAN, 'X', mio, 100, 'RF18539007547034')), True)
    _check(r, 'QR-IBAN', 'un riferimento QR su un IBAN normale nemmeno',
           _rifiuta(lambda: Q.dati_qr(IBAN, 'X', mio, 100, ESEMPIO)), True)
    _check(r, 'QR-IBAN', 'e un QR-IBAN senza riferimento neppure',
           _rifiuta(lambda: Q.dati_qr(QR_IBAN, 'X', mio, 100, '')), True)
    _check(r, 'QR-IBAN', 'mentre un RF su un IBAN normale continua a passare',
           '\nSCOR\nRF18539007547034\n' in str(_senza_scoppiare(
               lambda: Q.dati_qr(IBAN, 'X', mio, 100, 'RF18539007547034'))), True)

    # --- sul foglio si legge come lo standard lo scrive ---------------------
    _check(r, 'QR-IBAN', 'il riferimento QR si legge a gruppi di cinque, contati da destra',
           Q._a_gruppi(ESEMPIO), '21 00000 00003 13947 14300 09017')
    _check(r, 'QR-IBAN', 'l’RF resta a gruppi di quattro',
           Q._a_gruppi('RF18539007547034'), 'RF18 5390 0754 7034')
    _check(r, 'QR-IBAN', 'e l’IBAN pure',
           Q._a_gruppi(QR_IBAN), 'CH44 3199 9123 0008 8901 2')

    # --- il numero che alcune banche vogliono in testa al riferimento --------
    _check(r, 'QR-IBAN', 'il numero della banca accetta cifre, anche scritte a gruppi',
           _senza_scoppiare(lambda: Q.prefisso_qrr(' 12 34 56 ')), ('123456', ''))
    _check(r, 'QR-IBAN', 'lasciato vuoto non è un errore',
           _senza_scoppiare(lambda: Q.prefisso_qrr('')), ('', ''))
    for sbagliato in ('12A456', '1' * 17):
        esito = _senza_scoppiare(lambda: Q.prefisso_qrr(sbagliato))
        _check(r, 'QR-IBAN', 'e «%s» viene respinto dicendo perché' % sbagliato[:8],
               isinstance(esito, tuple) and esito[0] is None and bool(esito[1]), True)

    # --- dalle impostazioni alla fattura ------------------------------------
    buone = dict(DEFAULT_SETTINGS, business_name='Anna Rossi Fitness',
                 business_iban=QR_IBAN, business_addr1='Musterstrasse 1',
                 business_addr2='8000 Musterstadt', qr_fattura='1')
    _check(r, 'QR-IBAN', 'le impostazioni hanno il posto per il numero della banca',
           'qr_prefisso' in DEFAULT_SETTINGS, True)
    della = _senza_scoppiare(
        lambda: Q.riferimento_della_fattura(7, dict(buone, qr_prefisso='123456')))
    _check(r, 'QR-IBAN', 'la fattura nuova prende il riferimento dalle impostazioni vere',
           _senza_scoppiare(lambda: (Q.qrr_valido(della), della[:6])), (True, '123456'))
    _check(r, 'QR-IBAN', 'e col bollettino spento non ne prende nessuno',
           _senza_scoppiare(lambda: Q.riferimento_della_fattura(7, dict(buone, qr_fattura='0'))),
           '')

    from pypdf import PdfReader
    voci = [{'qty': 10, 'description': '10 Sessions Pack',
             'unit_cents': 12000, 'total_cents': 120000}]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, 'qr-iban.pdf')
        rif = _senza_scoppiare(lambda: Q.riferimento_della_fattura(7, buone))
        pdfgen.build_pdf(pdf, 7, '10-09-26', 'Mario Bianchi',
                         ['Musterweg 3', '8001 Zürich'], voci, 120000, buone, None, rif)
        pagine = PdfReader(pdf).pages
        testo_pdf = '\n'.join(p.extract_text() or '' for p in pagine)
        # contare le pagine NON basta: se il codice non si compone, oggi resta
        # lo stesso una mezza pagina con l'intestazione e niente da staccare
        _check(r, 'QR-IBAN', 'con un QR-IBAN il PDF vero ha il bollettino in coda',
               (len(pagine), 'Ricevuta' in testo_pdf, 'Sezione pagamento' in testo_pdf),
               (2, True, True))
        _check(r, 'QR-IBAN', 'e sul foglio c’è il riferimento QR della fattura, a gruppi',
               _senza_scoppiare(lambda: Q.qrr_valido(rif) and Q._a_gruppi(rif) in testo_pdf),
               True)
        # il PDF sa anche calcolarselo da solo, quando non glielo passano: e
        # anche li' deve guardare l'IBAN, se no rimette dentro un RF
        senza = os.path.join(tmp, 'qr-iban-senza-rif.pdf')
        pdfgen.build_pdf(senza, 7, '10-09-26', 'Mario Bianchi',
                         ['Musterweg 3', '8001 Zürich'], voci, 120000, buone)
        testo_senza = '\n'.join(p.extract_text() or '' for p in PdfReader(senza).pages)
        _check(r, 'QR-IBAN', 'anche quando il PDF il riferimento se lo calcola da solo',
               _senza_scoppiare(lambda: Q._a_gruppi(Q.riferimento_della_fattura(7, buone))
                                in testo_senza), True)

        # un riferimento che non va con l'IBAN non si stampa: e non deve
        # restare nemmeno la pagina cominciata per lui
        storto = os.path.join(tmp, 'qr-iban-rif-storto.pdf')
        # il guaio va nel registro degli errori, come deve: qui pero' e' voluto,
        # e non deve finire nel registro vero di chi usa l'app
        registro = logging.getLogger('fatture.errori')
        registro.disabled = True
        try:
            pdfgen.build_pdf(storto, 7, '10-09-26', 'Mario Bianchi',
                             ['Musterweg 3', '8001 Zürich'], voci, 120000, buone,
                             None, 'RF18539007547034')
        finally:
            registro.disabled = False
        _check(r, 'QR-IBAN', 'un riferimento che non va con l’IBAN non lascia una mezza pagina',
               len(PdfReader(storto).pages), 1)

    # Il riferimento vive solo se c'e' il bollettino. Oggi si salva anche
    # quando il foglio non si puo' fare, e la mail dice al cliente di pagare
    # «soltanto con il codice QR in fondo alla fattura»: un codice che non c'e'.
    _check(r, 'QR-IBAN', 'senza i dati per il bollettino la fattura non si porta dietro un riferimento',
           _senza_scoppiare(lambda: Q.riferimento_della_fattura(
               7, dict(buone, business_addr1='Ireland'))), '')

    # --- e il codice dell'app passa davvero di qui --------------------------
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sorgenti = {}
    for nome in ('app.py', os.path.join('core', 'pdfgen.py')):
        with io.open(os.path.join(base, nome), encoding='utf-8') as f:
            sorgenti[nome] = f.read()
    _check(r, 'QR-IBAN', 'app e PDF chiedono il riferimento sapendo l’IBAN',
           [n for n, testo_s in sorted(sorgenti.items())
            if 'riferimento_della_fattura(' not in testo_s
            or re.search(r'riferimento_per\(\s*number\s*\)', testo_s)], [])
    _check(r, 'QR-IBAN', 'e il numero della banca passa dal controllo prima di essere salvato',
           'prefisso_qrr(' in sorgenti['app.py'], True)


def _test_compleanni(r):
    """I compleanni dei clienti, sulla Dashboard una settimana prima.

    Chiesto il 10.09.2026: un riquadro che dica chi compie gli anni, a partire
    da sette giorni prima. Sembra aritmetica da niente, e ha le sue trappole,
    tutte vere il giorno che capitano: il capodanno in mezzo (il 28 dicembre il
    compleanno del 2 gennaio e' fra cinque giorni, non fra un anno meno
    qualcosa), il 29 febbraio negli anni che non ce l'hanno, e chi l'anno di
    nascita non lo dice, che e' quasi tutti.
    """
    import datetime
    import importlib
    import shutil
    import sqlite3
    import tempfile

    def B():
        return importlib.import_module('.birthdays', __package__)

    # --- come si scrive: come lo scrive la gente ---------------------------
    for scritto, atteso in (('15.03', '03-15'), ('15.3.1986', '1986-03-15'),
                            (' 5/3 ', '03-05'), ('1986-03-15', '1986-03-15'),
                            ('29.02', '02-29'), ('', '')):
        _check(r, 'Compleanni', '«%s» si legge %s' % (scritto.strip(), atteso or 'vuoto'),
               _senza_scoppiare(lambda: B().leggi_compleanno(scritto)), (atteso, ''))
    for sbagliato in ('31.02', '15.13', 'domani', '29.02.1985', '15.03.1850', '15.03.2999'):
        esito = _senza_scoppiare(lambda: B().leggi_compleanno(sbagliato))
        _check(r, 'Compleanni', '«%s» viene respinto dicendo perché' % sbagliato,
               isinstance(esito, tuple) and esito[0] is None and bool(esito[1]), True)
    _check(r, 'Compleanni', 'e sulla scheda si rilegge come lo si era scritto',
           _senza_scoppiare(lambda: (B().da_mostrare('03-15'), B().da_mostrare('1986-03-15'),
                                     B().da_mostrare(''))),
           ('15.03', '15.03.1986', ''))

    # --- chi compare, e quando ---------------------------------------------
    oggi = datetime.date(2026, 9, 10)
    clienti = [
        {'id': 1, 'name': 'Vera Buergi', 'compleanno': '09-10', 'archived': 0},       # oggi
        {'id': 2, 'name': 'Ivan Steiner', 'compleanno': '1986-09-12', 'archived': 0},  # fra 2
        {'id': 3, 'name': 'Nina', 'compleanno': '09-17', 'archived': 0},              # fra 7
        {'id': 4, 'name': 'Elena', 'compleanno': '09-18', 'archived': 0},             # fra 8
        {'id': 5, 'name': 'Jonas', 'compleanno': '09-09', 'archived': 0},             # ieri
        {'id': 6, 'name': 'Pierre', 'compleanno': '09-11', 'archived': 1},            # archiviato
        {'id': 7, 'name': 'Céline Favre', 'compleanno': '', 'archived': 0},           # non si sa
    ]
    arrivo = _senza_scoppiare(lambda: B().in_arrivo(clienti, oggi))
    _check(r, 'Compleanni', 'compaiono da oggi a sette giorni, i più vicini prima',
           _senza_scoppiare(lambda: [(c['nome'], c['tra']) for c in arrivo]),
           [('Vera Buergi', 0), ('Ivan Steiner', 2), ('Nina', 7)])
    _check(r, 'Compleanni', 'chi ha detto l’anno compie i suoi anni, chi no resta senza',
           _senza_scoppiare(lambda: [c['anni'] for c in arrivo]), [None, 40, None])
    _check(r, 'Compleanni', 'e il giorno è quello di quest’anno',
           _senza_scoppiare(lambda: arrivo[1]['quando']), datetime.date(2026, 9, 12))
    # la trappola che in quest'app ha gia' morso: nelle prove i clienti sono
    # dizionari, sui dati veri righe di sqlite, che «get» non ce l'hanno
    finto = sqlite3.connect(':memory:')
    finto.row_factory = sqlite3.Row
    finto.execute('CREATE TABLE clients(id INT, name TEXT, compleanno TEXT, archived INT)')
    finto.execute("INSERT INTO clients VALUES(1, 'Vera Buergi', '09-12', 0)")
    righe = finto.execute('SELECT * FROM clients').fetchall()
    _check(r, 'Compleanni', 'le righe vere del database si leggono come i dizionari',
           _senza_scoppiare(lambda: [c['tra'] for c in B().in_arrivo(righe, oggi)]), [2])

    # --- le trappole del calendario ----------------------------------------
    _check(r, 'Compleanni', 'a fine dicembre il compleanno di gennaio è fra pochi giorni',
           _senza_scoppiare(lambda: [(c['quando'], c['tra'], c['anni']) for c in B().in_arrivo(
               [{'id': 1, 'name': 'Nina', 'compleanno': '1990-01-02', 'archived': 0}],
               datetime.date(2026, 12, 28))]),
           [(datetime.date(2027, 1, 2), 5, 37)])
    _check(r, 'Compleanni', 'il 29 febbraio, negli anni che non ce l’hanno, si festeggia il 28',
           _senza_scoppiare(lambda: [(c['quando'], c['tra']) for c in B().in_arrivo(
               [{'id': 1, 'name': 'Nina', 'compleanno': '02-29', 'archived': 0}],
               datetime.date(2027, 2, 25))]),
           [(datetime.date(2027, 2, 28), 3)])
    _check(r, 'Compleanni', 'e negli anni bisestili il 29, com’è giusto',
           _senza_scoppiare(lambda: [(c['quando'], c['tra']) for c in B().in_arrivo(
               [{'id': 1, 'name': 'Nina', 'compleanno': '02-29', 'archived': 0}],
               datetime.date(2028, 2, 25))]),
           [(datetime.date(2028, 2, 29), 4)])

    # --- il posto nel database ---------------------------------------------
    from . import db as D
    from . import sessions as S
    vero = D.DB_PATH
    vero_registro = S.REGISTRY
    cartella = tempfile.mkdtemp()
    try:
        S.REGISTRY = os.path.join(cartella, 'sessions.json')   # il registro vero non si legge
        D.DB_PATH = os.path.join(cartella, 'nuovo.db')
        con = D.init()
        colonne = [x[1] for x in con.execute('PRAGMA table_info(clients)')]
        con.close()
        _check(r, 'Compleanni', 'un’installazione nuova ha il posto per il compleanno',
               'compleanno' in colonne, True)
        # una vecchia, con un cliente dentro e senza la colonna: la colonna
        # arriva, e il cliente resta dov'era
        D.DB_PATH = os.path.join(cartella, 'vecchio.db')
        vecchio = sqlite3.connect(D.DB_PATH)
        vecchio.executescript(D.SCHEMA)
        vecchio.execute("INSERT INTO clients(id, name, key) VALUES(1, 'Vera Buergi', 'vb')")
        vecchio.commit()
        vecchio.close()
        con = D.init()
        dopo = ('compleanno' in [x[1] for x in con.execute('PRAGMA table_info(clients)')],
                con.execute('SELECT name FROM clients').fetchall()[0][0])
        con.close()
        _check(r, 'Compleanni', 'su un database già in uso arriva senza toccare i clienti',
               dopo, (True, 'Vera Buergi'))
    finally:
        D.DB_PATH = vero
        S.REGISTRY = vero_registro
        shutil.rmtree(cartella, ignore_errors=True)

    # --- la Dashboard e la scheda del cliente passano davvero di qui -------
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def leggi(*pezzi):
        with io.open(os.path.join(base, *pezzi), encoding='utf-8') as f:
            return f.read()
    sorgente_app = leggi('app.py')
    _check(r, 'Compleanni', 'la Dashboard chiede i compleanni in arrivo e li mostra',
           ('birthdays.in_arrivo(' in sorgente_app, 'compleanni=' in sorgente_app,
            'compleanni' in leggi('templates', 'dashboard.html')),
           (True, True, True))
    _check(r, 'Compleanni', 'e la scheda del cliente lo salva passando dal controllo',
           ('birthdays.leggi_compleanno(' in sorgente_app,
            'name="compleanno"' in leggi('templates', 'clients.html')),
           (True, True))


def _test_modelli_si_compilano(r):
    """Ogni pagina si compila: un tag lasciato aperto non arriva a chi usa l'app.

    Trovato il 10.09.2026. Nel riquadro nuovo dei compleanni mancava un
    «endif»: la batteria era verde, 780 su 780, e la Dashboard dava errore 500
    appena aperta. Nessuna prova apriva davvero i modelli: li leggevano tutte
    come testo, cercando etichette e frasi. Un errore di sintassi in un modello
    non si vede finche' qualcuno non apre quella pagina — e la Dashboard e' la
    prima pagina che si apre.
    """
    import re
    import jinja2
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'templates')
    ambiente = jinja2.Environment(loader=jinja2.FileSystemLoader(base))
    # I filtri dell'app («chf», «dateit», ...) Jinja li vuole gia' quando compila,
    # non solo quando disegna: in un ambiente vuoto ogni pagina sembrerebbe rotta.
    # Si prendono i NOMI da come l'app li registra davvero, cosi' un filtro usato
    # in una pagina e mai registrato resta quello che e': un errore vero.
    with io.open(os.path.join(os.path.dirname(base), 'app.py'), encoding='utf-8') as f:
        sorgente_app = f.read()
    registrati = re.findall(r"jinja_env\.(?:filters|tests)\[['\"](\w+)['\"]\]", sorgente_app)
    registrati += re.findall(r"template_(?:filter|test)\(\s*['\"](\w+)['\"]", sorgente_app)
    for nome in registrati:
        ambiente.filters[nome] = ambiente.tests[nome] = lambda *a, **k: ''
    nomi = sorted(n for n in os.listdir(base) if n.endswith('.html'))
    rotti = []
    for nome in nomi:
        try:
            ambiente.get_template(nome)
        except jinja2.TemplateSyntaxError as guaio:
            rotti.append('%s:%s %s' % (nome, guaio.lineno, guaio.message))
    _check(r, 'Modelli', 'ogni pagina si compila, senza tag lasciati aperti', rotti, [])
    # una guardia che non trova le pagine sarebbe verde per sbaglio
    _check(r, 'Modelli', 'e le pagine controllate sono davvero tutte (%d)' % len(nomi),
           len(nomi) >= 20, True)


def _test_abbonamenti(r):
    """L'aritmetica dei mesi degli abbonamenti.

    E' il posto dove i guai nascono senza farsi vedere: un mese contato due
    volte e' una fattura mandata due volte per lo stesso periodo, cioe' una
    richiesta di soldi non dovuti. Chi la riceve non pensa a una disattenzione.

    Le trappole vere sono tre, e ci sono tutte qui sotto: il passaggio d'anno,
    i mesi corti (chi fattura il 31 non deve saltare febbraio) e il mese che
    non e' ancora arrivato al suo giorno.
    """
    import datetime
    from . import recurring as A

    def reg(**kw):
        base = {'attiva': 1, 'giorno': 1, 'dal': '2026-01'}
        base.update(kw)
        return base

    d = datetime.date
    _check(r, 'Abbonamenti', 'il mese dopo dicembre è gennaio dell\'anno nuovo',
           A.mese_succ('2025-12'), '2026-01')
    _check(r, 'Abbonamenti', 'e dentro l\'anno si va avanti di uno',
           (A.mese_succ('2026-01'), A.mese_succ('2026-09')), ('2026-02', '2026-10'))

    # il giorno 31 su un mese che non ce l'ha: l'ultimo giorno che c'e'
    _check(r, 'Abbonamenti', 'chi fattura il 31 non salta febbraio',
           A.giorno_di_emissione('2026-02', 31), d(2026, 2, 28))
    _check(r, 'Abbonamenti', 'e nemmeno un febbraio bisestile',
           A.giorno_di_emissione('2028-02', 31), d(2028, 2, 29))
    _check(r, 'Abbonamenti', 'sui mesi lunghi il giorno resta quello',
           A.giorno_di_emissione('2026-03', 31), d(2026, 3, 31))

    # --- quali mesi sono da fare -----------------------------------------
    mesi, _ = A.mesi_dovuti(reg(dal='2026-07'), [], d(2026, 9, 7))
    _check(r, 'Abbonamenti', 'da luglio a settembre sono tre mesi da fare',
           mesi, ['2026-07', '2026-08', '2026-09'])
    mesi, _ = A.mesi_dovuti(reg(dal='2026-07'), ['2026-07', '2026-08'], d(2026, 9, 7))
    _check(r, 'Abbonamenti', 'i mesi già fatturati non tornano',
           mesi, ['2026-09'])
    # il mese in mezzo saltato torna da fare: e' un buco, e i buchi si vedono
    mesi, _ = A.mesi_dovuti(reg(dal='2026-07'), ['2026-07', '2026-09'], d(2026, 9, 7))
    _check(r, 'Abbonamenti', 'un mese saltato in mezzo resta da fare',
           mesi, ['2026-08'])

    # il giorno non ancora arrivato: il 14, una regola del 15 non da' niente
    _check(r, 'Abbonamenti', 'il giorno prima, il mese corrente non è ancora dovuto',
           A.mesi_dovuti(reg(dal='2026-09', giorno=15), [], d(2026, 9, 14))[0], [])
    _check(r, 'Abbonamenti', 'il giorno stesso sì',
           A.mesi_dovuti(reg(dal='2026-09', giorno=15), [], d(2026, 9, 15))[0], ['2026-09'])

    # a cavallo dell'anno
    mesi, _ = A.mesi_dovuti(reg(dal='2025-11'), [], d(2026, 1, 3))
    _check(r, 'Abbonamenti', 'il passaggio d\'anno non perde né inventa mesi',
           mesi, ['2025-11', '2025-12', '2026-01'])

    # una regola spenta non chiede niente, e nemmeno una che comincia dopo
    _check(r, 'Abbonamenti', 'una regola spenta non chiede niente',
           A.mesi_dovuti(reg(attiva=0, dal='2020-01'), [], d(2026, 9, 7))[0], [])
    _check(r, 'Abbonamenti', 'una regola che comincia il mese prossimo non chiede niente',
           A.mesi_dovuti(reg(dal='2026-10'), [], d(2026, 9, 7))[0], [])

    # arretrati a valanga: si elencano fino al tetto e si DICE quanti restano,
    # invece di troncare in silenzio
    mesi, restano = A.mesi_dovuti(reg(dal='2015-01'), [], d(2026, 9, 7))
    _check(r, 'Abbonamenti', 'una data d\'inizio sbagliata non riempie la pagina',
           (len(mesi), restano > 0), (A.MAX_MESI, True))
    _check(r, 'Abbonamenti', 'e i mesi elencati più quelli rimasti fuori tornano',
           len(mesi) + restano, 12 * 11 + 9)

    # una data scritta male non deve far saltare niente
    _check(r, 'Abbonamenti', 'un mese scritto male non produce fatture',
           A.mesi_dovuti(reg(dal='settembre'), [], d(2026, 9, 7)), ([], 0))
    _check(r, 'Abbonamenti', 'e si riconosce come scritto male',
           (A.valido('2026-09'), A.valido('2026-13'), A.valido('26-09')),
           (True, False, False))

    # --- la riga della fattura -------------------------------------------
    from .language import MESI_DOC
    _check(r, 'Abbonamenti', 'la riga porta il mese nella lingua del cliente',
           A.descrizione_per('Personal training – {mese} {anno}', '2026-09',
                             MESI_DOC['it']),
           'Personal training – Settembre 2026')
    _check(r, 'Abbonamenti', 'e in tedesco è il mese tedesco',
           A.descrizione_per('Personal Training – {mese} {anno}', '2026-03',
                             MESI_DOC['de']),
           'Personal Training – März 2026')
    _check(r, 'Abbonamenti', 'un modello senza segnaposti resta com\'è',
           A.descrizione_per('Abbonamento mensile', '2026-09', MESI_DOC['it']),
           'Abbonamento mensile')
    # una graffa sbagliata e' un errore di chi scrive, non un motivo per
    # spegnere la pagina: si mostra la riga com'e' e si vede subito
    _check(r, 'Abbonamenti', 'un segnaposto sbagliato non fa saltare la pagina',
           A.descrizione_per('Training {mesee}', '2026-09', MESI_DOC['it']),
           'Training {mesee}')

    # Chi ha sempre scritto le date sulla riga deve poter continuare: la
    # fattura di settembre dev'essere uguale a quella di agosto, o il cliente
    # si chiede cosa sia cambiato.
    _check(r, 'Abbonamenti', 'la riga può portare le date invece del nome del mese',
           A.descrizione_per('Monthly abo: running coaching {dal} – {al}', '2026-09',
                             MESI_DOC['en']),
           'Monthly abo: running coaching 01.09.26 – 30.09.26')
    _check(r, 'Abbonamenti', "l'ultimo giorno è quello vero del mese, non il 30",
           A.descrizione_per('{dal} – {al}', '2026-08', MESI_DOC['en']),
           '01.08.26 – 31.08.26')
    _check(r, 'Abbonamenti', 'febbraio è di 28 giorni',
           A.descrizione_per('{al}', '2026-02', MESI_DOC['en']), '28.02.26')
    _check(r, 'Abbonamenti', 'e negli anni bisestili di 29',
           A.descrizione_per('{al}', '2028-02', MESI_DOC['en']), '29.02.28')
    _check(r, 'Abbonamenti', 'date e nome del mese possono stare insieme',
           A.descrizione_per('{mese}: {dal}-{al}', '2026-12', MESI_DOC['en']),
           'December: 01.12.26-31.12.26')

    # Un abbonamento non e' per forza un mese solare: ce n'e' uno, in questa
    # app, che va dal 13 al 12 e ha undici fatture di fila scritte cosi'.
    _check(r, 'Abbonamenti', 'il periodo comincia il giorno in cui si fattura',
           A.descrizione_per('Monthly abo: running coaching {dal} – {al}', '2026-09',
                             MESI_DOC['en'], 13),
           'Monthly abo: running coaching 13.09.26 – 12.10.26')
    _check(r, 'Abbonamenti', 'e a cavallo di dicembre passa all\'anno nuovo',
           A.descrizione_per('{dal} – {al}', '2026-12', MESI_DOC['en'], 13),
           '13.12.26 – 12.01.27')
    _check(r, 'Abbonamenti', 'chi fattura il primo ha il mese solare, come prima',
           A.descrizione_per('{dal} – {al}', '2026-09', MESI_DOC['en'], 1),
           '01.09.26 – 30.09.26')
    _check(r, 'Abbonamenti', 'e senza dire il giorno vale il primo',
           A.descrizione_per('{dal} – {al}', '2026-09', MESI_DOC['en']),
           '01.09.26 – 30.09.26')
    _check(r, 'Abbonamenti', 'il 31 si accorcia sui mesi che non ce l\'hanno',
           A.descrizione_per('{dal} – {al}', '2026-09', MESI_DOC['en'], 31),
           '30.09.26 – 30.10.26')

    # --- la riga e l'importo dal servizio (spec §4) --------------------------
    from . import services as SR
    con = _db_servizi()
    for riga in ((1, 'giulia', 'Giulia Ferrari', 'en'), (2, 'marco', 'Marco Neri', 'de'),
                 (3, 'sofia', 'Sofia Verdi', 'it')):
        con.execute('INSERT INTO clients(id, key, name, lingua) VALUES(?,?,?,?)', riga)
    mensile = SR.salva(con, SR.dal_modulo({'nome': 'Monthly abo: running coaching',
                                           'prezzo': '110', 'ogni_mese': '1'}))
    online = SR.salva(con, SR.dal_modulo({'nome': 'Online Coaching', 'prezzo': '90',
                                          'ogni_mese': '1'}))
    graffe = SR.salva(con, SR.dal_modulo({'nome': 'Coaching {pro}', 'ogni_mese': '1'}))

    def regola(**campi):
        base = {'id': 1, 'client_id': 1, 'descrizione': '', 'importo_cents': 0, 'giorno': 13,
                'servizio_id': mensile, 'stile': 'date'}
        base.update(campi)
        return base

    def riga_di(regola, mese='2026-09', lingua='en'):
        return _senza_scoppiare(A.riga_per, con, regola, mese, MESI_DOC[lingua])

    _check(r, 'Abbonamenti', 'con le date: il nome del servizio e il periodo, come le righe scritte a mano',
           riga_di(regola()), ('Monthly abo: running coaching 13.09.26 – 12.10.26', 11000, mensile))
    _check(r, 'Abbonamenti', 'col mese: il nome del servizio e il mese fra parentesi, nella lingua del cliente',
           riga_di(regola(client_id=2, servizio_id=online, stile='mese', giorno=1), '2026-03', 'de'),
           ('Online Coaching (März)', 9000, online))
    _check(r, 'Abbonamenti', 'senza i nomi dei mesi (la Dashboard) la riga con le date si scrive lo stesso',
           _senza_scoppiare(lambda: A.riga_per(con, regola(), '2026-09', [])[0]),
           'Monthly abo: running coaching 13.09.26 – 12.10.26')
    for numero, cliente, cents in ((1, 1, 10000), (2, 2, 12000)):
        fid = con.execute("INSERT INTO invoices(number, client_id, client_name, date, year, total_cents) "
                          "VALUES(?, ?, 'x', '2026-08-13', 2026, ?)", (numero, cliente, cents)).lastrowid
        con.execute("INSERT INTO items(invoice_id, pos, qty, description, unit_cents, total_cents, "
                    "servizio_id) VALUES(?, 0, '1', 'x', ?, ?, ?)", (fid, cents, cents, mensile))
    _check(r, 'Abbonamenti', 'l’importo è quello dell’ultima riga di quel servizio fatturata a quel cliente',
           riga_di(regola())[1], 10000)
    _check(r, 'Abbonamenti', 'chi non l’ha mai avuto paga il prezzo del servizio, non quello di un altro cliente',
           riga_di(regola(client_id=3))[1], 11000)
    _check(r, 'Abbonamenti', 'un testo libero resta com’era, e porta il servizio sulla riga',
           riga_di(regola(stile='', descrizione='Personal training – {mese} {anno}', importo_cents=8000),
                   '2026-09', 'it'),
           ('Personal training – Settembre 2026', 8000, mensile))
    _check(r, 'Abbonamenti', 'un nome con le graffe non rompe la riga',
           riga_di(regola(servizio_id=graffe, stile='mese', giorno=1), '2026-03')[0],
           'Coaching {pro} (March)')
    _check(r, 'Abbonamenti', 'un servizio senza prezzo e mai fatturato lascia l’importo da scrivere',
           riga_di(regola(servizio_id=graffe, stile='mese'))[1], None)
    _check(r, 'Abbonamenti', 'se il servizio non c’è più, restano il testo e l’importo della regola',
           riga_di(regola(servizio_id=999, descrizione='Coaching {mese}', importo_cents=7000, giorno=1)),
           ('Coaching September', 7000, None))
    con.execute("INSERT INTO ricorrenti(id, client_id, descrizione, importo_cents, giorno, dal, attiva, "
                "servizio_id, stile) VALUES(1, 1, '', 0, 13, '2026-09', 1, ?, 'date')", (mensile,))
    _check(r, 'Abbonamenti', 'la lista da fatturare usa la riga del servizio',
           _senza_scoppiare(lambda: [(x['descrizione'], x['importo_cents'])
                                     for x in A.da_fare(con, d(2026, 9, 14), MESI_DOC)]),
           [('Monthly abo: running coaching 13.09.26 – 12.10.26', 10000)])

    # --- la fattura preparata da un abbonamento porta l'importo e il servizio
    # veri, non quelli scritti sulla regola (altrimenti l'anteprima mentirebbe) ---
    import app as APP
    con.execute("INSERT INTO ricorrenti(id, client_id, descrizione, importo_cents, giorno, dal, "
                "attiva, servizio_id, stile) VALUES(2, 1, 'Coaching {mese}', 7000, 1, "
                "'2026-01', 1, 999, 'date')")

    def precompilato(ric_id, mese='2026-09'):
        with APP.app.test_request_context():
            pre = APP._precompila_abbonamento(con, ric_id, mese)
        return (pre['descrizione'], pre['importo'], pre['servizio_id'], pre['client_id'])

    _check(r, 'Abbonamenti', "la fattura preparata porta l'importo e il servizio del "
                             "servizio, non l'importo scritto sulla regola",
           _senza_scoppiare(precompilato, 1),
           ('Monthly abo: running coaching 13.09.26 – 12.10.26', fmt_dash(10000), mensile, 1))
    _check(r, 'Abbonamenti', "se il servizio non c'è più, la fattura preparata tiene testo "
                             "e importo della regola, senza servizio",
           _senza_scoppiare(precompilato, 2),
           ('Coaching September', fmt_dash(7000), None, 1))
    con.close()

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(base, 'app.py'), encoding='utf-8') as f:
        programma = f.read()
    with io.open(os.path.join(base, 'templates', 'subscriptions.html'), encoding='utf-8') as f:
        pagina = f.read()

    def corpo(nome):
        c = programma[programma.index('def %s(' % nome):]
        return c[:c.index('\n\n\n')]

    _check(r, 'Abbonamenti', 'il modulo chiede cliente, servizio, rinnovo, primo mese e come scrivere il periodo',
           (all('name="%s"' % n in pagina for n in ('client_id', 'servizio_id', 'giorno', 'dal', 'stile')),
            'name="descrizione"' in pagina, 'name="importo"' in pagina), (True, False, False))
    _check(r, 'Abbonamenti', 'un abbonamento nuovo si salva col servizio e lo stile',
           ('servizio_id' in corpo('abbonamenti_nuovo'), 'stile' in corpo('abbonamenti_nuovo')),
           (True, True))
    _check(r, 'Abbonamenti', 'la fattura preparata da un abbonamento porta il servizio sulla riga',
           ('riga_per' in corpo('_precompila_abbonamento'),
            "'servizio_id'" in corpo('_precompila_abbonamento')), (True, True))


def _test_lavoro(r):
    """Le sedute per mese e quanto valgono.

    Qui l'errore non fa perdere soldi, fa perdere fiducia: chi guarda un
    grafico non ha modo di accorgersi che una seduta e' finita nel mese
    sbagliato o che il prezzo a seduta e' quello di un altro cliente. Un
    numero storto in una pagina di statistiche nessuno lo va a controllare,
    e per questo va provato con piu' cura di uno che si vede.
    """
    from . import lavoro as L

    listino = [
        {'nome': 'Ivan', 'prezzi': [180000, 150000], 'crediti': 12},   # 150
        {'nome': 'Elena', 'prezzi': [200000], 'crediti': 10},         # 200
        {'nome': 'Jonas', 'prezzi': '135000', 'crediti': 10},        # 135, riga grezza
        {'nome': 'Nina', 'prezzi': [180000], 'crediti': 12},         # 150
        {'nome': 'Pierre', 'prezzi': [], 'crediti': 0},                # non lo si sa
    ]

    # --- il prezzo a seduta: il pacchetto diviso i crediti -----------------
    for nome, atteso in (('Ivan', 15000), ('Elena', 20000), ('Jonas', 13500)):
        cfg = next(c for c in listino if c['nome'] == nome)
        _check(r, 'Lavoro', f'{nome}: il listino diviso i crediti fa {atteso // 100}',
               L.prezzo_a_seduta(cfg), atteso)
    _check(r, 'Lavoro', 'i prezzi scritti come li tiene il database si leggono uguale',
           L.prezzo_a_seduta({'prezzi': "180000,150000", 'crediti': 12}), 15000)
    # senza listino non si inventa uno zero: uno zero in pagina sembra un fatto
    _check(r, 'Lavoro', 'senza prezzo non si risponde zero, non si risponde',
           L.prezzo_a_seduta({'nome': 'Pierre', 'prezzi': [], 'crediti': 0}), None)
    _check(r, 'Lavoro', 'e nemmeno con il prezzo ma senza crediti',
           L.prezzo_a_seduta({'prezzi': [180000], 'crediti': 0}), None)

    # La trappola che in quest'app ha gia' morso una volta: nelle prove i dati
    # sono dizionari scritti a mano, sui dati veri sono righe di database — e
    # le righe di sqlite non hanno «get». Una prova coi soli dizionari non se
    # ne accorge mai, e il guasto arriva all'utente invece che qui.
    import sqlite3
    finto_db = sqlite3.connect(':memory:')
    finto_db.row_factory = sqlite3.Row
    finto_db.execute('CREATE TABLE crediti_clienti(nome TEXT, prezzi TEXT, crediti INT)')
    finto_db.execute("INSERT INTO crediti_clienti VALUES('Ivan', '180000,150000', 12)")
    righe_vere = finto_db.execute('SELECT * FROM crediti_clienti').fetchall()
    _check(r, 'Lavoro', 'una riga vera di database si legge come un dizionario',
           _senza_scoppiare(L.prezzo_a_seduta, righe_vere[0]), 15000)
    _check(r, 'Lavoro', 'e il pacchetto ci trova dentro il suo listino',
           _senza_scoppiare(L.prezzo_del_pacchetto, {'cliente': 'Ivan'}, righe_vere), 15000)

    # --- da quale listino prende un pacchetto ------------------------------
    _check(r, 'Lavoro', 'un pacchetto in due prende il listino di chi ce l\'ha',
           L.prezzo_del_pacchetto({'cliente': 'Nina + Pierre'}, listino), 15000)
    _check(r, 'Lavoro', 'e uno solo prende il suo',
           L.prezzo_del_pacchetto({'cliente': 'Elena'}, listino), 20000)
    # la trappola dei nomi corti: «Ivan» non deve pescare dentro «Ivana»
    _check(r, 'Lavoro', '«Ivan» non finisce dentro «Ivana»',
           L.prezzo_del_pacchetto({'cliente': 'Ivana'}, listino), None)
    # due prezzi diversi nello stesso pacchetto: non si sceglie, si tace
    _check(r, 'Lavoro', 'due listini diversi nello stesso pacchetto: non si indovina',
           L.prezzo_del_pacchetto({'cliente': 'Ivan + Elena'}, listino), None)
    _check(r, 'Lavoro', 'un cliente che non e\' in listino non vale zero, vale niente',
           L.prezzo_del_pacchetto({'cliente': 'Ignoto'}, listino), None)

    # --- il registro finto -------------------------------------------------
    reg = {'pacchetti': [
        {'cliente': 'Ivan', 'sessioni': [
            {'data': '2025-12-30', 'titolo': 'Ivan'},          # dicembre
            {'data': '2026-01-02', 'titolo': 'Ivan'},          # gennaio: altro anno
            {'data': '2026-03-10', 'titolo': 'Ivan'},
            {'data': '2026-03-11', 'titolo': 'Ivan cancelled'},   # consuma, non allena
            {'data': 'non una data', 'titolo': 'Ivan'},        # non deve far saltare
        ]},
        {'cliente': 'Elena', 'sessioni': [
            {'data': '2026-03-12', 'titolo': 'Elena'},
        ]},
        {'cliente': 'Ignoto', 'sessioni': [                   # senza listino: vale 0
            {'data': '2026-03-13', 'titolo': 'Ignoto'},
        ]},
    ], 'esclusi': [
        {'data': '2026-03-14', 'titolo': 'Bike with Ivan'},
        {'data': '2025-12-18', 'titolo': 'Ivan'},
    ]}
    for s in reg['pacchetti'][0]['sessioni']:
        s['cancellata'] = 'cancelled' in s['titolo']

    mesi = L.per_mese(reg, listino, 2026)
    _check(r, 'Lavoro', "l'anno ha dodici mesi anche quando non succede niente",
           len(mesi), 12)
    _check(r, 'Lavoro', 'un mese vuoto e\' a zero, non manca',
           mesi[10], {'sedute': 0, 'cancellate': 0, 'esclusi': 0, 'cents': 0})

    marzo = mesi[2]
    # 3 fatte (Ivan, Elena, Ignoto) + 1 cancellata; il guadagno e' 150+200+150,
    # perche' Ignoto non ha listino e la cancellata il credito lo ha consumato
    _check(r, 'Lavoro', 'marzo: tre sedute fatte, la cancellata non e\' un allenamento',
           marzo['sedute'], 3)
    _check(r, 'Lavoro', 'ma la cancellata si conta a parte, non sparisce',
           marzo['cancellate'], 1)
    _check(r, 'Lavoro', 'e nel guadagno c\'e\', perche\' il credito e\' andato',
           marzo['cents'], 15000 + 20000 + 15000)
    _check(r, 'Lavoro', 'chi non ha listino non porta franchi ma si conta lo stesso',
           (marzo['sedute'], marzo['cents']), (3, 50000))
    _check(r, 'Lavoro', 'gli esclusi si contano a parte',
           marzo['esclusi'], 1)

    # la trappola del confine d'anno: due sedute a tre giorni di distanza,
    # una per parte. Se cadessero nello stesso secchio non se ne accorgerebbe
    # nessuno guardando il grafico.
    _check(r, 'Lavoro', 'il 30 dicembre resta a dicembre, dell\'anno suo',
           (L.per_mese(reg, listino, 2025)[11]['sedute'],
            L.per_mese(reg, listino, 2025)[11]['esclusi']), (1, 1))
    _check(r, 'Lavoro', 'e il 2 gennaio va a gennaio, dell\'anno dopo',
           mesi[0]['sedute'], 1)
    # nel 2026 il registro ha cinque sedute a credito: una a gennaio, tre piu'
    # una cancellata a marzo. La sesta riga ha una data illeggibile e resta
    # fuori da tutti i mesi, senza far saltare niente.
    _check(r, 'Lavoro', 'una data storta resta fuori invece di far saltare la pagina',
           sum(m['sedute'] + m['cancellate'] for m in mesi), 5)

    # --- i totali dell'anno ------------------------------------------------
    t = L.totali(mesi)
    _check(r, 'Lavoro', "l'anno somma quello che c'e' nei mesi",
           (t['sedute'], t['cancellate'], t['esclusi']), (4, 1, 1))
    _check(r, 'Lavoro', 'la media si fa sulle sedute che hanno consumato un credito',
           t['media_cents'], (15000 + 50000) // 5)
    vuoto = L.totali(L.per_mese(reg, listino, 1999))
    _check(r, 'Lavoro', 'un anno senza sedute non vale zero franchi a seduta',
           vuoto['media_cents'], None)
    _check(r, 'Lavoro', 'e i suoi dodici mesi ci sono lo stesso, tutti a zero',
           vuoto['cents'], 0)

    # --- da quando i conti valgono ----------------------------------------
    _check(r, 'Lavoro', 'il registro sa da che anno comincia a sapere',
           L.primo_anno(reg), 2025)
    _check(r, 'Lavoro', 'un registro vuoto non finge di sapere da quando',
           L.primo_anno({'pacchetti': [], 'esclusi': []}), None)

    # --- i pacchetti nati da una fattura, e i mesi di abbonamento ----------
    nuovi = {'pacchetti': [
        {'cliente': 'Ivan', 'prezzo_seduta_cents': 16000,
         'sessioni': [{'data': '2026-04-02', 'titolo': 'Ivan'}]},
        {'cliente': 'Elena', 'prezzo_seduta_cents': None,
         'sessioni': [{'data': '2026-04-03', 'titolo': 'Elena'}]},
    ], 'mensili': [
        {'cliente': 'Sofia', 'prezzo_seduta_cents': 5500, 'sessioni': [
            {'data': '2026-04-04', 'titolo': 'Sofia'},
            {'data': '2026-04-05', 'titolo': 'Sofia', 'in_piu': True}]},
    ], 'esclusi': []}
    aprile = L.per_mese(nuovi, listino, 2026)[3]
    _check(r, 'Lavoro', 'le sedute dei mesi di abbonamento contano, anche quelle in più',
           aprile['sedute'], 4)
    _check(r, 'Lavoro', 'un pacchetto nato da una fattura vale il prezzo scritto sul pacchetto '
                        '(niente, se non ce l’ha); una seduta in più non vale niente',
           aprile['cents'], 16000 + 5500)
    _check(r, 'Lavoro', 'il registro sa da quando ci sono i mesi di abbonamento',
           L.primo_anno({'pacchetti': [], 'esclusi': [], 'mensili': [
               {'sessioni': [{'data': '2024-05-01', 'titolo': 'Sofia'}]}]}), 2024)


def _test_nomi_accentati(r):
    """I nomi con gli accenti, che il computer sa scrivere in due modi.

    «Bürgi» si scrive con la dieresi attaccata alla u (un carattere) o
    staccata (due). A schermo sono identici, per il database no. macOS chiama
    i file nel secondo modo e l'app scrive nel primo: dieci fatture importate
    dalle cartelle e una fatta dall'app hanno diviso in due la stessa cliente
    dentro «Top clienti», con meta' del suo fatturato per parte. Nessuno se
    n'e' accorto per due anni, perche' non c'era niente da vedere.

    Non e' un caso raro: succede a ogni cliente con un accento nel cognome, e
    quest'app la useranno anche svizzeri tedeschi e francesi.
    """
    from . import importer as I

    staccato = 'Bu\u0308rgi'          # u + dieresi: due caratteri
    attaccato = 'B\u00fcrgi'          # ü: uno solo
    _check(r, 'Nomi con accenti', 'i due modi di scrivere il cognome sono davvero diversi',
           staccato == attaccato, False)

    _check(r, 'Nomi con accenti', 'il nome preso dal file esce in una forma sola',
           _senza_scoppiare(I.client_from_filename, '/Fatture/2024/Vera %s 33.docx' % staccato),
           'Vera %s' % attaccato)
    _check(r, 'Nomi con accenti', 'e chi era gia\' scritto bene non cambia',
           _senza_scoppiare(I.client_from_filename, '/Fatture/2024/Vera %s 33.docx' % attaccato),
           'Vera %s' % attaccato)
    _check(r, 'Nomi con accenti', "cosi' le due grafie finiscono sullo stesso nome",
           _senza_scoppiare(I.client_from_filename, '/x/Vera %s 1.docx' % staccato)
           == _senza_scoppiare(I.client_from_filename, '/x/Vera %s 1.docx' % attaccato),
           True)
    _check(r, 'Nomi con accenti', 'un nome senza accenti resta quello che era',
           _senza_scoppiare(I.client_from_filename, '/x/Ivan Steiner 12.docx'), 'Ivan Steiner')
    _check(r, 'Nomi con accenti', 'e il pettine non si arrabbia se non gli danno testo',
           _senza_scoppiare(I.pettinato, None), None)

    # L'indirizzo sta accanto al nome sulla fattura: se «Zurich» si sdoppia,
    # si sdoppia sulla busta.
    _check(r, 'Nomi con accenti', "anche l'indirizzo esce in una forma sola",
           _senza_scoppiare(I.pettinato, '8050 Zu\u0308rich'), '8050 Z\u00fcrich')


# ---------------------------------------------------------------------------
# L'ANAGRAFE DEI PERSONAGGI DELLE PROVE
#
# Il codice di quest'app sta su un repository pubblico, e la storia di git non
# dimentica niente. Un nome vero copiato qui dentro esce dal Mac e non rientra
# piu'. E succede sempre per lo stesso motivo, che e' pure un buon motivo: il
# caso da provare veniva da un cliente vero, e il modo piu' rapido di provarlo
# era incollarlo com'era.
#
# Non e' una sbadataggine da poco. Nome, indirizzo e conto dei clienti sono
# dati di terzi: pubblicarli e' un problema legale (LPD in Svizzera, GDPR
# nell'UE), non un refuso. E il proprio indirizzo di casa, messo li' come
# esempio, finisce sotto gli occhi di chiunque scarichi l'app.
#
# Percio' l'anagrafe sta scritta qui, per esteso. Il controllo legge i
# sorgenti, tira fuori i nomi e gli indirizzi dai punti dove stanno i dati, e
# pretende che siano tutti in queste liste. Per aggiungere un personaggio
# bisogna scriverlo qui: un gesto piccolo, che pero' obbliga a guardarlo.
GENTE_FINTA = {
    'Anna', 'Anna Rossi', 'Bruno Keller', 'Caio', 'Céline Favre', 'Elena',
    'Erika Von Arx', 'Giulia', 'giulia', 'Ignoto', 'Ivan', 'Ivan + Elena',
    'Ivana', 'Jonas', 'Luca', 'Marco', 'Nina', 'Nina + Pierre', 'Petra Müller',
    'Pierre', 'Tizia', 'Vera Buergi',
    'client', 'Kunde',            # non persone: «cliente» tradotto
    'Monthly abo', 'Monthly  abo', 'Personal Training',
    '12 Sessions Pack – Personal Training',  # non persone: servizi finti (Compito 2)
    '12 Sessions Pack', 'Monthly abo: running coaching',  # servizi finti (Compito 4)
    '10 Sessions Pack', 'Running Coaching', 'Fisioterapia',  # servizi finti (Compito 5)
    '10 Sessions Pack – Personal Training',  # servizio finto (Compito 6)
    'Giulia + Marco', 'Sofia', 'Qualcuno', 'giulia-ferrari',  # clienti finti (Compito 8)
    'Online Coaching', 'Coaching {pro}',  # servizi finti (Compito 13)
}
CONTI_FINTI = {
    'CH5800791123000889012',      # IBAN normale d'esempio
    'CH4431999123000889012',      # QR-IBAN d'esempio (istituto 31999)
    'CH5630000123000889012',      # QR-IBAN al bordo di sotto (istituto 30000)
    'CH9300762011623852957',      # l'IBAN svizzero d'esempio piu' citato
    'CH5604835012345678009',      # quello di Anna Rossi, sulle fatture finte
    'CH0000000000000000000',      # volutamente falso: serve a farsi rifiutare
}
CASE_FINTE = {
    'Bahnhofstrasse 1', 'Bahnhofstrasse 4', 'Musterstrasse 1', 'Musterstrasse 45',
    'Musterweg 3', 'Musterweg 8a', 'Musterweg 9', 'Musterweg 227',
}
LUOGHI_FINTI = {
    '6300 Zug', '6900 Lugano', '8000 Cittanova', '8000 Musterstadt',
    '8000 Zürich', '8001 Zürich', '8802 Kilchberg',
}

# ANAGRAFE:INIZIO - quello che sta fra questo segno e ANAGRAFE:FINE non
# viene setacciato: sono gli schemi stessi, e uno schema somiglia sempre a
# cio' che cerca. Senza questi due segni la guardia pesca se stessa.
# I punti del codice dove ci sta un nome di persona: i campi del camt, i
# dizionari delle prove, le righe infilate nel database finto.
_DOVE_STANNO_I_NOMI = [
    r'<Nm>([^<]+)</Nm>',
    r"'nome': '([^']+)'",
    r"'cliente': '([^']+)'",
    r"debitore_nome='([^']+)'",
    r"creditore_nome='([^']+)'",
    r"client_name[^)]*VALUES\([^)]*?'([A-ZÀ-Þ][^']*)'",
    r"INSERT INTO clients\([^)]*\)\s*.?\s*.?\s*VALUES\(\d+,\s*'([^']+)'",
]
_UN_IBAN = r'\bCH\d{2}[\d ]{15,25}\b'
_UNA_VIA = r'\b([A-ZÄÖÜ][\wäöüéèà-]{3,}(?:strasse|weg|gasse|platz))\s+(\d+[a-z]?)\b'
_UN_LUOGO = r'(?:CH-)?\b(\d{4})\s+([A-ZÄÖÜÉ][\wäöüéèàç-]{2,})'
# Moltissime vie svizzere non finiscono in -strasse, -weg o -platz: sono un
# nome e basta, e restano vie. Fuori da un indirizzo «parola + numero» e' troppo
# comune per dire qualcosa (basta «Fattura 87»); ATTACCATA A UN CAP, no.
_UNA_VIA_COL_CAP = (r'\b([A-ZÄÖÜÉ][\wäöüéèàç-]{2,}\s+\d+\s*[a-z]?)'
                    r'[,\s]+(?:CH-)?\d{4}\s+[A-ZÄÖÜÉ]')
# ANAGRAFE:FINE


def _tutto_il_codice():
    """Il testo di ogni file che finisce nel pacchetto, nome per nome."""
    import glob
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuori = {}
    for schema in ('*.py', os.path.join('core', '*.py'),
                   os.path.join('templates', '*.html')):
        for perc in sorted(glob.glob(os.path.join(base, schema))):
            with io.open(perc, encoding='utf-8') as f:
                fuori[os.path.relpath(perc, base)] = f.read()
    return fuori


def _test_niente_dati_veri(r):
    """Nel codice che si pubblica non abita nessuno di vero.

    Trovato il 09.09.2026 guardando il pacchetto con gli occhi di chi lo compra:
    dentro il repository pubblico c'erano l'IBAN di chi ha scritto l'app, il suo
    indirizzo di casa — messo pure come esempio nel testo che l'app mostra
    all'utente, in tre lingue — e nome e indirizzo di casa di una cliente, piu'
    i nomi di altri cinque. Nessuno li aveva messi li' apposta: erano i casi
    veri da cui il codice era nato.

    Il controllo non sa cosa sia «vero»: sa cosa e' DICHIARATO. Tutto quello
    che somiglia a una persona, a un conto o a un indirizzo dev'essere in una
    delle liste qui sopra. Chi incolla un dato vero non lo trova dichiarato, e
    la prova diventa rossa prima che il dato esca dal Mac.

    Quello che questo controllo NON vede: un nome di battesimo lasciato cadere
    dentro un commento in prosa. Li' non c'e' una forma da riconoscere, e
    inventarsene una vorrebbe dire riempire di rosso le prove di chi compra.
    """
    import re
    codice = _tutto_il_codice()

    nomi, conti, vie, luoghi = set(), set(), set(), set()
    for testo in codice.values():
        if '# ANAGRAFE:INIZIO' in testo:
            testo = (testo[:testo.index('# ANAGRAFE:INIZIO')]
                     + testo[testo.index('# ANAGRAFE:FINE'):])
        for schema in _DOVE_STANNO_I_NOMI:
            nomi.update(m.group(1).strip() for m in re.finditer(schema, testo))
        for m in re.finditer(_UN_IBAN, testo):
            senza_spazi = m.group(0).replace(' ', '')
            if len(senza_spazi) == 21:
                conti.add(senza_spazi)
        vie.update('%s %s' % m.groups() for m in re.finditer(_UNA_VIA, testo))
        vie.update(' '.join(m.group(1).split())
                   for m in re.finditer(_UNA_VIA_COL_CAP, testo))
        luoghi.update('%s %s' % m.groups() for m in re.finditer(_UN_LUOGO, testo))

    _check(r, 'Dati veri', "nel codice non c'e' nessuno fuori anagrafe",
           sorted(nomi - GENTE_FINTA), [])
    _check(r, 'Dati veri', "nessun conto oltre quelli d'esempio",
           sorted(conti - CONTI_FINTI), [])
    _check(r, 'Dati veri', 'nessuna via che non sia inventata',
           sorted(vie - CASE_FINTE), [])
    _check(r, 'Dati veri', "nessun CAP con localita' fuori elenco",
           sorted(luoghi - LUOGHI_FINTI), [])
    # un setaccio che non pesca niente sarebbe verde per sbaglio: qui si
    # controlla che stia davvero guardando dentro qualcosa
    _check(r, 'Dati veri', 'e il setaccio guarda davvero (%d nomi, %d conti, %d indirizzi)'
           % (len(nomi), len(conti), len(vie) + len(luoghi)),
           (len(codice) >= 50, len(nomi) >= 20, len(conti) >= 5,
            len(vie) >= 6, len(luoghi) >= 5),
           (True, True, True, True, True))

