# -*- coding: utf-8 -*-
"""Gli abbonamenti: le fatture che tornano uguali ogni mese.

Su 37 fatture degli ultimi dodici mesi, 20 erano la stessa fattura da 110
franchi ribattuta a mano per tre clienti. Questo modulo serve a non ribatterla
piu' — e a non sbagliare, che qui e' facile e costa caro: una fattura mandata
due volte per lo stesso mese e' una richiesta di soldi non dovuti, e chi la
riceve non pensa «che disattenzione», pensa altro.

Due decisioni tengono in piedi tutto il resto.

UNA SOLA FONTE DELLA VERITA'. Quali mesi siano gia' fatturati NON si tiene
scritto sulla regola: si legge dalle fatture, che sono i fatti. Una regola con
sopra un «ultimo mese fatturato» sarebbe un secondo elenco che puo' litigare
col primo, e quando due elenchi litigano si sbaglia sempre dalla parte peggiore.
Ogni fattura nata da un abbonamento porta addosso il periodo che copre, e
questo modulo guarda quelli. Se la fattura finisce nel Cestino, il mese torna
da fare — che e' esattamente quello che uno si aspetta.

L'APP NON EMETTE NIENTE DA SOLA. Prepara, e confermi tu — come per i versamenti
in banca. Qui non si crea nessuna fattura, nessun numero viene consumato,
nessun file scritto: si dice soltanto quali mesi sono da fare. Il bottone porta
al modulo di sempre, gia' compilato, e la fattura nasce dalla stessa strada
provata di tutte le altre.
"""
import calendar
import datetime
import re

MESE = re.compile(r'^(\d{4})-(0[1-9]|1[0-2])$')

# Un tetto al numero di mesi che si possono elencare in un colpo solo. Non e'
# una troncatura silenziosa: chi chiama riceve anche quanti ne restano fuori,
# e li puo' dire. Serve a non trovarsi una pagina con dentro sei anni di
# arretrati per via di una data d'inizio sbagliata.
MAX_MESI = 36


def valido(mese):
    """Vero se «mese» e' scritto come si deve: 2026-09."""
    return bool(MESE.match(mese or ''))


def mese_di(data):
    """Il mese di una data, nella forma 2026-09."""
    return '%04d-%02d' % (data.year, data.month)


def mese_succ(mese):
    """Il mese dopo. Dicembre passa a gennaio dell'anno nuovo."""
    anno, m = int(mese[:4]), int(mese[5:7])
    return '%04d-%02d' % (anno + 1, 1) if m == 12 else '%04d-%02d' % (anno, m + 1)


def giorno_di_emissione(mese, giorno):
    """Il giorno in cui quel mese diventa da fatturare.

    Il numero si accorcia sui mesi corti: chi fattura il 31 non deve saltare
    febbraio: a febbraio il 31 e' l'ultimo giorno che c'e'.
    """
    anno, m = int(mese[:4]), int(mese[5:7])
    return datetime.date(anno, m, min(int(giorno or 1), calendar.monthrange(anno, m)[1]))


def _campo(regola, nome, ripiego=None):
    """Un campo della regola, che arrivi da un dizionario o dal database.

    Le righe di sqlite non hanno «get», i dizionari si': senza questo, la
    funzione girava nelle prove e falliva sui dati veri — e falliva zitta,
    perche' chi la chiama teneva l'errore per se'.
    """
    try:
        valore = regola[nome]
    except (KeyError, IndexError):
        return ripiego
    return ripiego if valore is None else valore


def mesi_dovuti(regola, gia_fatti=(), oggi=None):
    """I mesi ancora da fatturare, dal piu' vecchio. Ritorna (mesi, restano).

    «gia_fatti» sono i mesi gia' coperti — fatturati o saltati apposta. Un mese
    entra nell'elenco solo quando il suo giorno di emissione e' arrivato: il 14
    del mese, una regola che fattura il 15 non ha ancora niente da dare.

    «restano» dice quanti ne sono rimasti fuori per via del tetto, cosi' chi
    mostra l'elenco puo' dirlo invece di far finta che non ci siano.
    """
    if not _campo(regola, 'attiva', 1):
        return [], 0
    oggi = oggi or datetime.date.today()
    dal = _campo(regola, 'dal') or mese_di(oggi)
    if not valido(dal):
        return [], 0
    gia = set(gia_fatti or ())
    giorno = _campo(regola, 'giorno') or 1

    fuori, mese, restano = [], dal, 0
    for _ in range(600):                  # limite di sicurezza, non un ciclo aperto
        if giorno_di_emissione(mese, giorno) > oggi:
            break
        if mese not in gia:
            if len(fuori) < MAX_MESI:
                fuori.append(mese)
            else:
                restano += 1
        mese = mese_succ(mese)
    return fuori, restano


def descrizione_per(modello, mese, mesi_nella_lingua, giorno=1):
    """La riga della fattura per quel mese, nella lingua del cliente.

    Nel modello si scrive «{mese}» e «{anno}» per il nome del mese e l'anno,
    oppure «{dal}» e «{al}» per le date del periodo coperto. Chi le date le ha
    sempre scritte non deve cambiare quello che il suo cliente legge da anni
    solo perche' adesso la riga la compila l'app: la fattura di settembre
    dev'essere uguale a quella di agosto, o il cliente si chiede cosa sia
    cambiato.

    IL PERIODO NON E' SEMPRE IL MESE SOLARE. Comincia il giorno in cui si
    fattura e finisce il giorno prima del successivo: chi fattura il primo ha
    01.09.26 - 30.09.26, chi fattura il 13 ha 13.09.26 - 12.10.26. E' il caso
    di un abbonamento vero di quest'app, undici fatture di fila; con il solo
    mese solare quelle undici righe sarebbero cambiate forma tutte insieme.
    Il giorno si accorcia sui mesi corti, come il giorno di emissione: chi
    fattura il 31 non salta febbraio.

    Un modello che non nomina niente resta com'e': c'e' chi scrive sempre la
    stessa riga e ha ragione lui.
    """
    anno, m = int(mese[:4]), int(mese[5:7])
    inizio = giorno_di_emissione(mese, giorno)
    fine = giorno_di_emissione(mese_succ(mese), giorno) - datetime.timedelta(days=1)
    try:
        return (modello or '').format(
            mese=mesi_nella_lingua[m - 1], anno=anno,
            dal=inizio.strftime('%d.%m.%y'), al=fine.strftime('%d.%m.%y'))
    except (KeyError, IndexError, ValueError):
        # un modello con una graffa sbagliata non deve far saltare la pagina:
        # meglio la riga cosi' com'e' scritta, che si vede ed e' correggibile
        return modello or ''


# ------------------------------------------------- quello che sa il database
def regole(con):
    """Tutti gli abbonamenti, col nome del cliente accanto."""
    return con.execute(
        'SELECT r.*, c.name AS cliente, c.lingua AS lingua_cliente, '
        '       c.archived AS cliente_archiviato '
        'FROM ricorrenti r JOIN clients c ON c.id = r.client_id '
        'ORDER BY r.attiva DESC, c.name').fetchall()


def periodi_coperti(con, ricorrente_id):
    """I mesi gia' sistemati: quelli fatturati e quelli saltati apposta.

    Le fatture nel Cestino NON contano: se l'hai buttata, quel mese e' di
    nuovo da fare, ed e' quello che chiunque si aspetta.
    """
    fatti = {r['periodo'] for r in con.execute(
        'SELECT periodo FROM invoices WHERE ricorrente_id=? AND periodo<>"" '
        'AND deleted_at IS NULL', (ricorrente_id,))}
    fatti |= {r['periodo'] for r in con.execute(
        'SELECT periodo FROM ricorrenti_saltati WHERE ricorrente_id=?',
        (ricorrente_id,))}
    return fatti


def _fattura_a_mano(con, client_id, mese):
    """Il numero di una fattura che quel cliente ha gia' per quel mese, o None.

    Serve contro la trappola piu' facile di tutte: uno mette come primo mese
    luglio, e l'app gli propone di rifatturare luglio e agosto, che pero' erano
    gia' stati fatti a mano prima che l'abbonamento esistesse. Quelle fatture
    non hanno addosso nessun periodo — sono nate da un modulo compilato a mano —
    quindi il controllo sui periodi non le vede. Questo le vede: guarda la data.

    Non blocca niente, avverte. Un cliente puo' avere due fatture nello stesso
    mese per motivi buoni, e non sta a un controllo automatico decidere di no.
    """
    riga = con.execute(
        'SELECT number FROM invoices WHERE client_id=? AND deleted_at IS NULL '
        'AND substr(date, 1, 7) = ? ORDER BY number LIMIT 1',
        (client_id, mese)).fetchone()
    return riga['number'] if riga else None


def da_fare(con, oggi=None, mesi_per_lingua=None):
    """Che cosa c'e' da fatturare adesso, abbonamento per abbonamento.

    Ritorna una riga per ogni MESE dovuto, non per regola: due mesi arretrati
    dello stesso cliente sono due fatture, e vederle come due righe e' l'unico
    modo di non farne una sola per sbaglio.
    """
    fuori = []
    for reg in regole(con):
        if reg['cliente_archiviato']:
            continue
        mesi, restano = mesi_dovuti(reg, periodi_coperti(con, reg['id']), oggi)
        for mese in mesi:
            nomi = (mesi_per_lingua or {}).get(reg['lingua_cliente'] or 'en') \
                or (mesi_per_lingua or {}).get('en') or []
            fuori.append({
                'regola': reg, 'cliente': reg['cliente'], 'mese': mese,
                'importo_cents': reg['importo_cents'],
                'descrizione': descrizione_per(reg['descrizione'], mese, nomi,
                                               _campo(reg, 'giorno', 1))
                               if nomi else reg['descrizione'],
                'restano': restano,
                'gia_a_mano': _fattura_a_mano(con, reg['client_id'], mese),
            })
    fuori.sort(key=lambda x: (x['mese'], x['cliente']))
    return fuori


def salta(con, ricorrente_id, periodo, quando=None):
    """«Questo mese no»: il buco resta, ma smette di essere una domanda."""
    if not valido(periodo):
        return False
    con.execute('INSERT OR IGNORE INTO ricorrenti_saltati(ricorrente_id, periodo, quando) '
                'VALUES(?,?,?)',
                (ricorrente_id, periodo,
                 quando or datetime.datetime.now().isoformat(timespec='seconds')))
    con.commit()
    return True


def riprendi(con, ricorrente_id, periodo):
    """Annulla un «questo mese no»: il mese torna da fare."""
    con.execute('DELETE FROM ricorrenti_saltati WHERE ricorrente_id=? AND periodo=?',
                (ricorrente_id, periodo))
    con.commit()
