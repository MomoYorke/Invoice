# -*- coding: utf-8 -*-
"""Quanto vale un mese di lavoro: un'altra cosa da quanto si e' fatturato.

La pagina Performance sa dire quanto e' entrato in fattura, mese per mese. Non
sa dire quanto si e' LAVORATO, e per chi vende pacchetti le due cose non
cadono mai nello stesso mese: un pacchetto da dodici sedute si fattura in un
giorno e si consuma in tre mesi. Guardando solo il fatturato, il mese in cui
arriva il pacchetto sembra enorme e i due dopo sembrano vuoti.

Qui si contano le sedute e si da' loro un valore, per rispondere a due domande
che il fatturato non risponde: in che periodi dell'anno si allena di piu', e
quanto vale davvero un mese di lavoro.

IL PREZZO A SEDUTA SI LEGGE DAL LISTINO, NON SI DEDUCE DALLE FATTURE.
E' la decisione che e' costata di piu' arrivarci, quindi vale la pena scriverla.
Sembra piu' furbo dividere la fattura del pacchetto per i crediti del
pacchetto: e' un dato vero, e' preciso, viene dai soldi davvero incassati. E
funziona, finche' il pacchetto non ha dentro una seduta regalata. Allora
quella divisione spalma il regalo su tutte le sedute e riporta un prezzo a
seduta che chi lavora non pratica con nessuno — nel caso che ha fatto scoprire
la cosa, 120 franchi al posto di 150.

Il prezzo di listino e' un dato che chi usa l'app DICHIARA, nella pagina
Crediti. Dedurlo a posteriori dai movimenti di cassa introduce un errore
silenzioso ogni volta che c'e' uno sconto, un omaggio o un pacchetto pagato in
due fatture. Meglio leggere quello che e' stato scritto apposta.

Per questo il numero si chiama «guadagno teorico»: e' il valore a listino del
tempo lavorato, non un totale di cassa, e non deve quadrare al centesimo con
le fatture. Una seduta regalata, qui, vale come le altre.

Non scrive niente: ne' nel registro, ne' nel database.
"""
import re


def _campo(riga, nome):
    """Un campo, che arrivi da un dizionario o da una riga di database.

    Le righe di sqlite non hanno «get», i dizionari si'. Senza questo, un
    modulo gira nelle prove — dove i dati sono dizionari scritti a mano — e si
    rompe sui dati veri, che arrivano dal database. E' gia' successo una volta
    in quest'app, agli abbonamenti, e si e' rotto in silenzio.
    """
    try:
        return riga[nome]
    except (KeyError, IndexError, TypeError):
        return None


def prezzo_a_seduta(cfg):
    """Quanto vale una seduta di quel cliente, in centesimi.

    Il prezzo del pacchetto diviso i crediti del pacchetto, come li ha scritti
    chi usa l'app nella pagina Crediti. Senza uno dei due non si inventa uno
    zero: si dice None, e chi disegna il grafico sa di non sapere.
    """
    if cfg is None:
        return None
    prezzi = _campo(cfg, 'prezzi') or []
    if isinstance(prezzi, str):                      # riga di database grezza
        prezzi = [int(x) for x in re.findall(r'\d+', prezzi)]
    crediti = int(_campo(cfg, 'crediti') or 0)
    if not prezzi or crediti <= 0:
        return None
    return int(prezzi[0]) // crediti


def prezzo_del_pacchetto(pacchetto, config):
    """Il prezzo a seduta del pacchetto, dal listino di chi lo ha comprato.

    Il pacchetto porta scritto un nome che puo' essere di due persone
    («Nina + Pierre»), quindi il cliente si cerca dentro quel nome — ma a
    parola intera, se no «Ivan» finisce dentro «Ivana» e il conto va a chi
    non c'entra.

    Se due clienti nominati nello stesso pacchetto hanno prezzi DIVERSI non si
    sceglie: si dice None. Sbagliare a meta' e' peggio che non rispondere,
    perche' un numero sbagliato nessuno lo va a controllare.
    """
    nome = _campo(pacchetto, 'cliente') or ''
    prezzi = set()
    for cfg in config or []:
        chi = (_campo(cfg, 'nome') or '').strip()
        if not chi:
            continue
        if re.search(rf'\b{re.escape(chi.lower())}\b', nome.lower()):
            p = prezzo_a_seduta(cfg)
            if p:
                prezzi.add(p)
    return prezzi.pop() if len(prezzi) == 1 else None


def _indice_mese(data, anno):
    """Da «2026-07-14» all'indice 6, ma solo se l'anno e' quello chiesto.

    Una data storta non fa saltare la pagina: non e' di quest'anno e basta.
    """
    try:
        a, m = int(str(data)[:4]), int(str(data)[5:7])
    except (TypeError, ValueError):
        return None
    return m - 1 if a == anno and 1 <= m <= 12 else None


def per_mese(reg, config, anno):
    """Dodici mesi, dal primo all'ultimo, anche quelli in cui non e' successo
    niente: chi disegna il grafico non deve chiedersi se l'indice esiste.

    Per ogni mese:
      sedute     — gli allenamenti FATTI (a credito, cancellate escluse)
      cancellate — chi non si e' presentato: il credito se n'e' andato lo stesso
      esclusi    — eventi del calendario che non hanno scalato niente
      cents      — il valore a listino, cancellate COMPRESE (il credito e' stato
                   consumato), esclusi ESCLUSI (nessuno li ha pagati)
    """
    mesi = [{'sedute': 0, 'cancellate': 0, 'esclusi': 0, 'cents': 0}
            for _ in range(12)]
    for p in (reg or {}).get('pacchetti') or []:
        unitario = prezzo_del_pacchetto(p, config)
        for s in p.get('sessioni') or []:
            i = _indice_mese(s.get('data'), anno)
            if i is None:
                continue
            if s.get('cancellata'):
                mesi[i]['cancellate'] += 1
            else:
                mesi[i]['sedute'] += 1
            if unitario:
                mesi[i]['cents'] += unitario
    for e in (reg or {}).get('esclusi') or []:
        i = _indice_mese(e.get('data'), anno)
        if i is not None:
            mesi[i]['esclusi'] += 1
    return mesi


def totali(mesi):
    """La somma dell'anno, piu' la media a seduta.

    La media si fa sulle sedute che hanno consumato un credito — quelle che
    hanno prodotto il guadagno — cancellate comprese. Senza nessuna seduta la
    media e' None: dividere per zero non da' «zero franchi a seduta», non da'
    niente, e un grosso 0.00 in pagina sarebbe una bugia.
    """
    mesi = mesi or []
    fuori = {k: sum(m.get(k, 0) for m in mesi)
             for k in ('sedute', 'cancellate', 'esclusi', 'cents')}
    a_credito = fuori['sedute'] + fuori['cancellate']
    fuori['a_credito'] = a_credito
    fuori['media_cents'] = fuori['cents'] // a_credito if a_credito else None
    return fuori


def primo_anno(reg):
    """L'anno della seduta piu' vecchia che il registro conosce, o None.

    Serve alla pagina per dire da quando i conti valgono. Un grafico che parte
    da zero senza spiegare perche' e' un grafico che mente: prima di quella
    data non e' che non si lavorasse, e' che il registro non c'era.
    """
    date = [s.get('data') for p in (reg or {}).get('pacchetti') or []
            for s in p.get('sessioni') or [] if s.get('data')]
    date += [e.get('data') for e in (reg or {}).get('esclusi') or [] if e.get('data')]
    if not date:
        return None
    try:
        return int(min(date)[:4])
    except (ValueError, TypeError):
        return None
