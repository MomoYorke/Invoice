# -*- coding: utf-8 -*-
"""
Invio della fattura al cliente per email.

Due funzioni separate di proposito:

  componi()  costruisce destinatario, oggetto, testo e allegato.
             NON tocca la rete: e' quella che alimenta l'anteprima e quella
             che si prova nei test.
  spedisci() apre la connessione e manda. Unico punto che parla con l'esterno.

Sul perche' non si passa da Gmail: se il tuo dominio dichiara
SPF '-all', cioe' solo il suo server e' autorizzato a spedire a suo nome. Una
mail mandata da Gmail a nome del tuo indirizzo finirebbe in spam.
Attenzione anche al nome dell'host: spesso il certificato TLS copre
'tuodominio.ch' ma NON 'mail.tuodominio.ch', e allora si usa il primo: cosi' il
certificato si verifica davvero e la password non viaggia mai in chiaro.
"""
import os
import re
import ssl
import time
import socket
import smtplib
import mimetypes
from email.message import EmailMessage

from .money import fmt_chf
from . import db
from . import language as L
from . import services as srv

FRASE_ABBONAMENTO = ("Se ha già pagato questo mese con l'ordine permanente, può "
                     'semplicemente tenere il documento allegato per i Suoi archivi.\n')
# "questa fattura del mese" vale per gli abbonamenti mensili; un pacchetto di
# dieci sessioni non e' mensile e dirlo sarebbe sbagliato
APERTURA_MENSILE = 'In allegato la fattura di questo mese per {servizio}.'
APERTURA_SEMPLICE = 'In allegato la Sua fattura per {servizio}.'
# Se il servizio non si riconosce (chi usa l'app vende altro), la frase resta
# corretta senza nominarlo: meglio non dirlo che dirlo sbagliato.
APERTURA_MENSILE_ANONIMA = 'In allegato la fattura di questo mese.'
APERTURA_SEMPLICE_ANONIMA = 'In allegato la Sua fattura.'
APERTURA_MULTIPLA = 'In allegato {quante} fatture.'
QUANTE = {2: 'due', 3: 'tre', 4: 'quattro', 5: 'cinque', 6: 'sei'}

# I due modelli di frase centrale. La chiave e' anche il suffisso
# dell'impostazione che li contiene ('email_corpo_coaching', 'email_corpo_pt'),
# cosi' non esiste una seconda tabella da tenere allineata.
MODELLI = (
    ('coaching', 'Abbonamento'),
    ('pt', 'Pacchetto di sedute'),
)
NOMI_MODELLO = dict(MODELLI)


# --- il mese nell'oggetto ---------------------------------------------------
# L'oggetto del coaching porta il mese coperto dall'abbonamento: «Aug/Sept»
# quando il periodo sta a cavallo di due mesi, «Aug» quando ne copre uno solo.
# Il mese non si inventa mai: prima si legge il periodo scritto nella riga
# della fattura (13.08.26 - 12.09.26, oppure «(August)»), e solo se li' non
# c'e' niente si guarda l'ultima mail andata a quella persona e si avanza di
# un mese. Se non si riesce a dedurlo resta scritto «month», che si vede
# subito e si corregge a mano.

NOMI_MESE = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December')
ABBREVIAZIONI = {i + 1: n[:3] for i, n in enumerate(NOMI_MESE)}
SEGNAPOSTO_MESE = 'month'

RX_PERIODO = re.compile(
    r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})\s*[-\u2013\u2014]\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})')
RX_PAROLA = re.compile(r'[A-Za-z]{3,9}')


def _mese_da_parola(parola):
    """Il numero del mese, se quella parola e' un modo di scriverlo.

    Vale qualunque abbreviazione che sia l'inizio del nome inglese: «Sep»,
    «Sept», «September». Chiedere che sia un inizio, e non solo che cominci
    uguale, tiene fuori le parole che iniziano come un mese senza esserlo
    (Marathon non e' March).
    """
    p = (parola or '').strip('.').lower()
    if len(p) < 3:
        return None
    for i, nome in enumerate(NOMI_MESE):
        if nome.lower().startswith(p):
            return i + 1
    return None


def _mesi_nel_testo(testo):
    """I mesi nominati in un testo, nell'ordine, senza ripetizioni."""
    fuori = []
    for parola in RX_PAROLA.findall(testo or ''):
        m = _mese_da_parola(parola)
        if m and m not in fuori:
            fuori.append(m)
    return fuori


def mesi_da_descrizioni(descrizioni):
    """I mesi coperti dalla fattura, letti dalle sue righe."""
    for desc in descrizioni or ():
        p = RX_PERIODO.search(desc or '')
        if p:
            primo, ultimo = int(p.group(2)), int(p.group(5))
            return (primo,) if primo == ultimo else (primo, ultimo)
    for desc in descrizioni or ():
        mesi = _mesi_nel_testo(desc)
        if mesi:
            return tuple(mesi[:2])
    return ()


def stile_mesi(oggetti):
    """Come abbrevia i mesi: si impara da quello che ha gia' scritto lui.

    Gli oggetti vanno passati dal piu' vecchio al piu' recente, cosi' l'ultima
    forma usata e' quella che vince: se una volta ha scritto «Sept», da li' in
    avanti l'app scrive «Sept» e non «Sep».
    """
    stile = {}
    for og in oggetti or ():
        for parola in RX_PAROLA.findall(og or ''):
            m = _mese_da_parola(parola)
            if m:
                stile[m] = parola
    return stile


def etichetta_mesi(mesi, stile=None):
    stile = stile or {}
    return '/'.join(stile.get(m, ABBREVIAZIONI[m]) for m in mesi or ())


def avanza_mesi(mesi, quanti=1):
    return tuple((m - 1 + quanti) % 12 + 1 for m in mesi or ())


def mese_oggetto(descrizioni=(), oggetti_cliente=(), oggetti_stile=None):
    """Il mese da scrivere nell'oggetto. Stringa vuota se non si sa dedurlo."""
    stile = stile_mesi(oggetti_cliente if oggetti_stile is None else oggetti_stile)
    mesi = mesi_da_descrizioni(descrizioni)
    if not mesi:
        # sulla fattura non c'e' scritto il periodo: si riparte dall'ultima
        # mail mandata a questa persona, avanzando di un mese
        for og in reversed(list(oggetti_cliente or ())):
            precedenti = _mesi_nel_testo(og)
            if precedenti:
                mesi = avanza_mesi(precedenti[:2])
                break
    return etichetta_mesi(mesi, stile)


def oggetto_modello(settings, modello, lingua=None):
    """L'oggetto grezzo del modello scelto, segnaposti compresi."""
    return db.modello_email(settings, 'email_oggetto_' + modello, lingua) or ''


def _riconosciuto(descrizioni, settings):
    """(nome, modello) della prima riga riconosciuta. ('', '') se nessuna."""
    for desc in descrizioni or ():
        nome, modello = srv.riconosci(desc, settings)
        if nome:
            return (nome, modello)
    return ('', '')


def modello_di(descrizioni, settings):
    """Quale dei due modelli usare, dedotto dalle righe della fattura."""
    return _riconosciuto(descrizioni, settings)[1] or 'pt'


def testo_modello(settings, modello, lingua=None):
    return db.modello_email(settings, 'email_corpo_' + modello, lingua) or ''


# Come si chiude la mail. Il testo lo scrive chi usa l'app, in Impostazioni:
# con chi ci si da' del tu ci si firma in un modo, con gli altri in un altro.
def saluto_di(settings, tono, lingua=None):
    chiave = 'email_saluto_formale' if tono == 'formale' else 'email_saluto_informale'
    return db.modello_email(settings, chiave, lingua)


def nome_di_battesimo(nome_completo):
    parti = (nome_completo or '').strip().split()
    return parti[0] if parti else ''


def servizio_di(descrizioni, settings):
    """Il servizio da nominare nell'email, dedotto dalle righe della fattura.
    Vuoto se nessuna regola riconosce le righe.

    Usa le stesse regole della dashboard, quelle scritte in Impostazioni,
    cosi' non esistono due logiche da tenere allineate.
    """
    # Nessuna regola riconosce le righe: chi usa l'app vende altro, o non ha
    # ancora scritto i suoi servizi. Stringa vuota, e l'apertura usa la
    # versione che il servizio non lo nomina.
    return _riconosciuto(descrizioni, settings)[0]


def allegato_di(inv, settings):
    """Il PDF da allegare: quello generato dall'app o, per le fatture
    importate, il documento originale nello storico."""
    if inv['pdf_path'] and os.path.exists(inv['pdf_path']):
        return inv['pdf_path']
    src = inv['source_file'] if 'source_file' in inv.keys() else ''
    if src:
        cand = os.path.join(settings.get('source_folder', ''), src)
        if cand.lower().endswith('.pdf') and os.path.exists(cand):
            return cand
    return None


def componi(inv, cliente, settings, descrizioni=(), corpo=None, allegati_extra=(),
            modello=None, mese=''):
    """Prepara la mail. Ritorna un dizionario con anche l'elenco dei problemi.

    Non manda niente e non solleva: i problemi si mostrano nell'anteprima.
    """
    problemi = []
    destinatario = (cliente['email'] if cliente and 'email' in cliente.keys() else '') or ''
    destinatario = destinatario.strip()
    nome = cliente['name'] if cliente else inv['client_name']
    if not destinatario:
        problemi.append(f"Manca l'indirizzo email di {nome}.")
    elif not re.match(r'^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$', destinatario):
        problemi.append(f"L'indirizzo «{destinatario}» non sembra valido.")

    allegato = allegato_di(inv, settings)
    if not allegato:
        problemi.append('Il PDF della fattura non si trova: senza allegato non ha senso mandarla.')
    allegati = [allegato] if allegato else []
    for extra in allegati_extra or ():
        if extra and extra not in allegati:
            allegati.append(extra)

    # la lingua della mail e' quella del CLIENTE: e' lui che la legge. Si
    # decide per prima, perche' da lei dipende quale modello si va a prendere.
    lingua = L.normalizza_doc(
        cliente['lingua'] if cliente and 'lingua' in cliente.keys() else None)

    abbonato = bool(cliente['abbonamento']) if cliente and 'abbonamento' in cliente.keys() else False
    tono = (cliente['tono'] if cliente and 'tono' in cliente.keys() else '') or 'informale'
    if modello not in NOMI_MODELLO:
        modello = modello_di(descrizioni, settings)
    corpo = testo_modello(settings, modello, lingua) if corpo is None else corpo
    corpo = (corpo or '').strip()

    servizio = servizio_di(descrizioni, settings)
    if len(allegati) > 1:
        quante = QUANTE.get(len(allegati))
        apertura = L.t_doc(APERTURA_MULTIPLA, lingua).format(
            quante=L.t_doc(quante, lingua) if quante else len(allegati))
    elif servizio:
        apertura = L.t_doc(APERTURA_MENSILE if abbonato else APERTURA_SEMPLICE,
                           lingua).format(servizio=servizio)
    else:
        apertura = L.t_doc(APERTURA_MENSILE_ANONIMA if abbonato
                           else APERTURA_SEMPLICE_ANONIMA, lingua)
    oggetto_grezzo = oggetto_modello(settings, modello, lingua)
    valori = {
        'apertura': apertura,
        'mese': mese or SEGNAPOSTO_MESE,
        'nome': nome_di_battesimo(nome),
        'numero': inv['number'],
        'totale': fmt_chf(inv['total_cents']),
        'servizio': servizio,
        'riga_abbonamento': L.t_doc(FRASE_ABBONAMENTO, lingua) if abbonato else '',
        'corpo': corpo,
        'saluto': saluto_di(settings, tono, lingua),
        # la firma non si traduce: e' il suo nome e i suoi recapiti
        'firma': settings.get('email_firma', ''),
    }
    try:
        oggetto = oggetto_grezzo.format(**valori)
        testo = db.modello_email(settings, 'email_body', lingua).format(**valori)
    except KeyError as e:
        problemi.append(f'Nel modello dell\'email c\'e\' un segnaposto sconosciuto: {e}. '
                        'Correggilo in Impostazioni.')
        oggetto, testo = '', ''

    return {'to': destinatario, 'subject': oggetto, 'body': testo,
            'allegato': allegato, 'allegati': allegati, 'problemi': problemi,
            'modello': modello, 'mese': mese, 'lingua': lingua,
            # il personal training il mese non lo nomina: la nota sul mese ha
            # senso solo per il coaching
            'usa_mese': '{mese}' in oggetto_grezzo,
            # l'oggetto vuole un mese e l'app non e' riuscita a dedurlo:
            # non e' un errore, ma va detto perche' lo scriva lui
            'mese_mancante': '{mese}' in oggetto_grezzo and not mese}


def costruisci_messaggio(msg, settings, destinatario=None, copia_a_me=False):
    """Da dizionario a email vera e propria, con il PDF allegato."""
    m = EmailMessage()
    m['From'] = settings.get('email_from') or settings.get('smtp_user', '')
    m['To'] = destinatario or msg['to']
    if copia_a_me:
        # Ccn e non Cc: il cliente non deve vedere che ti mandi una copia.
        # smtplib consegna ai destinatari in Ccn ma non scrive l'intestazione
        # nella mail che parte, quindi resta invisibile.
        m['Bcc'] = settings.get('smtp_user', '')
    m['Subject'] = msg['subject']
    m.set_content(msg['body'])
    for percorso in msg.get('allegati') or ([msg['allegato']] if msg.get('allegato') else []):
        tipo, _ = mimetypes.guess_type(percorso)
        maggiore, minore = (tipo or 'application/pdf').split('/', 1)
        with open(percorso, 'rb') as f:
            m.add_attachment(f.read(), maintype=maggiore, subtype=minore,
                             filename=os.path.basename(percorso))
    return m


def _nascondi(testo, settings):
    """La password non deve comparire in nessun messaggio d'errore."""
    pw = settings.get('smtp_pass') or ''
    return testo.replace(pw, '********') if pw else testo


def spedisci(msg, settings, destinatario=None):
    """Manda davvero.

    Ritorna (ok, motivo, codice). Il codice serve a chi chiama per distinguere
    una password sbagliata (da contare, perche' due di fila fanno scattare il
    blocco anti-forza-bruta del server) da un guasto qualsiasi.
    """
    host = settings.get('smtp_host', '').strip()
    porta = int(settings.get('smtp_port') or 587)
    utente = settings.get('smtp_user', '').strip()
    password = settings.get('smtp_pass') or ''
    if not host or not utente:
        return False, 'Server o utente non configurati: vai in Impostazioni.', 'config'
    if not password:
        return False, ('Manca la password della casella. Va inserita in Impostazioni: '
                       'è l\'unica cosa che l\'app non può scoprire da sola.'), 'config'
    ctx = ssl.create_default_context()
    try:
        # la copia a se stessi ha senso solo quando si scrive a un cliente:
        # su una prova il destinatario e' gia' se stessi
        copia = (settings.get('email_copia_a_me') == '1') and not destinatario
        email = costruisci_messaggio(msg, settings, destinatario, copia_a_me=copia)
        if porta == 465:
            s = smtplib.SMTP_SSL(host, porta, timeout=30, context=ctx)
        else:
            s = smtplib.SMTP(host, porta, timeout=30)
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
        try:
            s.login(utente, password)
            s.send_message(email)
            msg['_inviato'] = email        # serve per la copia in Inviata
        finally:
            try:
                s.quit()
            except Exception:
                pass
        return True, '', 'ok'
    except smtplib.SMTPAuthenticationError:
        return False, ('Il server ha rifiutato utente e password. Controlla la casella '
                       f'«{utente}» e la password in Impostazioni.'), 'auth'
    except ssl.SSLCertVerificationError as e:
        # capita spessissimo: il certificato copre il dominio ma non il
        # sottodominio della posta, e allora basta togliere il prefisso
        senza = re.sub(r'^(mail|smtp|imap)\.', '', host)
        consiglio = (f'Prova con {senza} invece di {host}.' if senza != host
                     else 'Prova col nome del dominio, senza prefissi davanti.')
        return False, (f'Il certificato di {host} non è valido per quel nome '
                       f'({e.verify_message}). {consiglio}'), 'tls'
    except (socket.timeout, TimeoutError):
        return False, diagnosi_timeout(host, porta), 'timeout'
    except (smtplib.SMTPException, OSError) as e:
        return False, _nascondi(f'{type(e).__name__}: {e}', settings), 'altro'


def diagnosi_timeout(host, porta):
    """Un timeout sulla porta della posta ha di solito una spiegazione precisa.

    Se il sito dello stesso server risponde ma la porta SMTP no, non e' il
    server ad essere giu': e' il tuo indirizzo IP ad essere stato bloccato,
    tipicamente dopo qualche tentativo con la password sbagliata.
    """
    vivo = False
    try:
        s = socket.create_connection((host, 443), timeout=6)
        s.close()
        vivo = True
    except OSError:
        pass
    if vivo:
        return (f'Il server {host} risponde sul web ma non sulla porta {porta}: quasi '
                'sicuramente la protezione anti-forza-bruta ha bloccato il tuo indirizzo '
                'IP dopo i tentativi con la password sbagliata. Aspetta una ventina di '
                'minuti senza riprovare, oppure sblocca l\'IP dal pannello del tuo hosting.')
    return (f'Nessuna risposta da {host}: né sulla posta né sul web. Controlla la '
            'connessione a internet.')


# --- la copia in "Inviata" -------------------------------------------------
# SMTP serve solo a consegnare la posta: la copia nella cartella Inviata la
# scrive il programma che spedisce, ognuno per conto suo. E' per questo che le
# mail partite dall'iPhone si vedono in Inviata anche sul Mac. Qui si fa la
# stessa cosa, depositando il messaggio via IMAP.

CARTELLE_INVIATA = ('Sent', 'INBOX.Sent', 'Sent Messages', 'Sent Items',
                    'Gesendet', 'Posta inviata', 'INBOX.Sent Messages')


def _cartelle(imap):
    """Le cartelle della casella, con i loro contrassegni."""
    esito, righe = imap.list()
    if esito != 'OK':
        return []
    out = []
    for riga in righe or ():
        if isinstance(riga, bytes):
            riga = riga.decode('utf-8', errors='replace')
        m = re.match(r'\((?P<flag>[^)]*)\)\s+"?(?P<sep>[^"\s]*)"?\s+(?P<nome>.+)$', riga)
        if m:
            out.append((m.group('flag'), m.group('nome').strip('"')))
    return out


def trova_inviata(imap):
    """Come si chiama qui la cartella Inviata.

    Prima si chiede al server: lo standard prevede che la marchi \\Sent, e in
    quel caso non c'e' da indovinare. Solo se non lo fa si provano i nomi soliti.
    """
    elenco = _cartelle(imap)
    for flag, nome in elenco:
        if '\\Sent' in flag:
            return nome
    nomi = {n for _f, n in elenco}
    for candidato in CARTELLE_INVIATA:
        if candidato in nomi:
            return candidato
    for _f, nome in elenco:
        if nome.lower().split('.')[-1] in ('sent', 'inviata', 'gesendet'):
            return nome
    return None


def archivia_in_inviata(email_msg, settings):
    """Deposita una copia del messaggio nella cartella Inviata della casella.

    Ritorna (ok, motivo, cartella). Non solleva: la mail e' gia' partita, e un
    problema qui non deve trasformarsi in un errore d'invio.
    """
    import imaplib
    host = (settings.get('imap_host') or settings.get('smtp_host') or '').strip()
    porta = int(settings.get('imap_port') or 993)
    utente = (settings.get('smtp_user') or '').strip()
    password = settings.get('smtp_pass') or ''
    if not host or not utente or not password:
        return False, 'IMAP non configurato.', ''
    imap = None
    try:
        ctx = ssl.create_default_context()
        if porta == 143:
            imap = imaplib.IMAP4(host, porta)
            imap.starttls(ssl_context=ctx)
        else:
            imap = imaplib.IMAP4_SSL(host, porta, ssl_context=ctx)
        imap.login(utente, password)
        cartella = (settings.get('imap_cartella') or '').strip() or trova_inviata(imap)
        if not cartella:
            return False, 'Non ho trovato la cartella Inviata sul server.', ''
        ora = imaplib.Time2Internaldate(time.time())
        esito, _ = imap.append(f'"{cartella}"', '\\Seen', ora, email_msg.as_bytes())
        if esito != 'OK':
            return False, f'Il server ha rifiutato la copia in «{cartella}».', cartella
        return True, '', cartella
    except Exception as e:
        return False, _nascondi(f'{type(e).__name__}: {e}', settings), ''
    finally:
        if imap is not None:
            try:
                imap.logout()
            except Exception:
                pass


def verifica_inviata(settings):
    """Controlla che la copia in Inviata sia possibile, senza depositare nulla.

    Serve al pulsante di prova: conferma tutta la catena (IMAP, credenziali,
    nome della cartella) senza riempire la cartella Inviata di prove.
    """
    import imaplib
    host = (settings.get('imap_host') or settings.get('smtp_host') or '').strip()
    porta = int(settings.get('imap_port') or 993)
    utente = (settings.get('smtp_user') or '').strip()
    password = settings.get('smtp_pass') or ''
    if not (host and utente and password):
        return False, 'IMAP non configurato.', ''
    imap = None
    try:
        ctx = ssl.create_default_context()
        if porta == 143:
            imap = imaplib.IMAP4(host, porta)
            imap.starttls(ssl_context=ctx)
        else:
            imap = imaplib.IMAP4_SSL(host, porta, ssl_context=ctx)
        imap.login(utente, password)
        cartella = (settings.get('imap_cartella') or '').strip() or trova_inviata(imap)
        if not cartella:
            return False, 'Non ho trovato la cartella Inviata sul server.', ''
        return True, '', cartella
    except Exception as e:
        return False, _nascondi(f'{type(e).__name__}: {e}', settings), ''
    finally:
        if imap is not None:
            try:
                imap.logout()
            except Exception:
                pass
