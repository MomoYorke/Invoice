# -*- coding: utf-8 -*-
"""
Il report del mese: per ogni cliente a pacchetto le sedute fatte nel mese,
i crediti che restano e l'ultima seduta. In cima chi va fatturato presto e le
cose che non tornano.

E' solo lettura: guarda il registro e il calendario, non scrive niente, non
corregge niente. Se una seduta non va contata la si toglie dal calendario,
come sempre: il report lo dice, non lo decide.
"""
import datetime

from . import sessions as S
from . import conferme
from . import mensili
from . import language as L


def mese_scorso(oggi):
    primo = oggi.replace(day=1) - datetime.timedelta(days=1)
    return primo.strftime('%Y-%m')


def nome_mese(mese, lingua=None):
    anno, m = mese.split('-')
    return '%s %s' % (L.MESI_DOC[L.normalizza(lingua)][int(m) - 1], anno)


def _nel_mese(data, mese):
    return (data or '')[:7] == mese


def costruisci(reg, mese, eventi=(), oggi=None):
    """Il report di `mese` ('2026-09'). `eventi` sono quelli del calendario
    (come li da' calendar_feed.leggi): servono solo a trovare i titoli in cui
    non si riconosce nessun cliente."""
    oggi = (oggi or datetime.date.today()).isoformat()
    righe = []
    for v in S.vista_crediti(reg, datetime.date.fromisoformat(oggi)):
        if not v['pacchetto']:
            continue              # solo abbonamento: non ha crediti che finiscono
        suoi = [p for p in reg['pacchetti'] if v['chiave'] in S._chiavi_di(p)]
        nel_mese = [s['data'] for p in suoi for s in S.contate(p) if _nel_mese(s['data'], mese)]
        righe.append({
            'cliente': v['cliente'],
            'pacchetto': v['pacchetto'],
            'sedute_mese': len(nel_mese),
            'rimasti': v['rimasti'],
            'ultima_seduta': v['ultima_sessione'],
            'stato': v['stato'],
            'da_fatturare': v['terminati'] or v['in_esaurimento'],
        })
    righe.sort(key=lambda x: x['cliente'].lower())

    anomalie = []
    for x in righe:
        if x['rimasti'] < 0:
            anomalie.append({'tipo': 'negativi', 'data': '', 'testo': x['cliente'],
                             'quanti': x['rimasti']})
    for d in conferme.in_attesa(reg):
        date_mese = [x for x in d['date'] if _nel_mese(x, mese)]
        if date_mese:
            anomalie.append({'tipo': 'sparita', 'data': date_mese[0], 'testo': d['cliente'],
                             'quanti': len(date_mese)})
    for e in reg.get('esclusi') or []:
        if _nel_mese(e.get('data'), mese) and e.get('motivo') == mensili.MOTIVO_NESSUN_ABBONAMENTO:
            anomalie.append({'tipo': 'non_scalata', 'data': e['data'],
                             'testo': e.get('titolo') or '', 'quanti': 1})
    for ev in eventi or ():
        if (not _nel_mese(ev.get('data'), mese) or ev['data'] > oggi
                or ev.get('stato_google') == 'cancelled'):
            continue
        _chiave, _canc, motivo = S.classifica(ev.get('titolo', ''))
        if motivo == 'nessun cliente riconosciuto':
            anomalie.append({'tipo': 'sconosciuto', 'data': ev['data'],
                             'testo': ev.get('titolo', ''), 'quanti': 1})
    anomalie.sort(key=lambda a: (a['data'], a['tipo']))
    return {'mese': mese, 'righe': righe,
            'da_fatturare': [x for x in righe if x['da_fatturare'] or x['rimasti'] < 0],
            'anomalie': anomalie}


def _data_breve(iso):
    return '%s.%s.%s' % (iso[8:10], iso[5:7], iso[:4]) if iso else '—'


def frase_anomalia(a, lingua=None):
    """L'anomalia in parole, nella lingua di chi legge."""
    frasi = {
        'negativi': '{testo}: crediti sotto zero ({quanti}). Controlla le sedute del pacchetto.',
        'sparita': '{testo}: {quanti} seduta/e sparite dal calendario, da confermare in Crediti.',
        'non_scalata': '«{testo}»: seduta senza pacchetto né abbonamento, non è stata scalata.',
        'sconosciuto': '«{testo}»: nessun cliente riconosciuto nel titolo. Correggi il nome nel calendario o nella scheda del cliente.',
    }
    return L.t(frasi[a['tipo']], lingua).format(testo=a['testo'], quanti=a['quanti'])


def componi(rep, destinatario, lingua=None):
    """L'email del report, in testo semplice: si legge bene anche dal telefono."""
    t = lambda f: L.t(f, lingua)
    righe = [t('Report crediti: {mese}').format(mese=nome_mese(rep['mese'], lingua)), '']
    righe.append(t('Da fatturare presto'))
    if rep['da_fatturare']:
        for x in rep['da_fatturare']:
            righe.append('- ' + t('{cliente}: {rimasti} crediti rimasti').format(
                cliente=x['cliente'], rimasti=x['rimasti']))
    else:
        righe.append('- ' + t('Nessuno: tutti hanno ancora più di 2 crediti.'))
    righe += ['', t('Anomalie')]
    if rep['anomalie']:
        for a in rep['anomalie']:
            righe.append('- ' + ('%s  ' % _data_breve(a['data']) if a['data'] else '')
                         + frase_anomalia(a, lingua))
    else:
        righe.append('- ' + t('Nessuna: tutto torna.'))
    righe += ['', t('Tutti i clienti')]
    for x in rep['righe']:
        righe.append('- ' + t('{cliente}: {sedute} sedute nel mese, {rimasti} crediti rimasti, '
                              'ultima seduta {ultima}').format(
            cliente=x['cliente'], sedute=x['sedute_mese'], rimasti=x['rimasti'],
            ultima=_data_breve(x['ultima_seduta'])))
    if not rep['righe']:
        righe.append('- ' + t('Nessun cliente con un pacchetto.'))
    righe += ['', t('Report fatto dall\'app: non ha cambiato niente, né nel calendario né nei crediti.')]
    return {'to': destinatario,
            'subject': t('Report crediti: {mese}').format(mese=nome_mese(rep['mese'], lingua)),
            'body': '\n'.join(righe) + '\n'}


def markdown(rep, lingua=None):
    """Lo stesso report come nota Markdown, per una cartella di appunti (per
    esempio un vault di Obsidian): titoli, elenchi e una tabella."""
    t = lambda f: L.t(f, lingua)
    titolo = t('Report crediti: {mese}').format(mese=nome_mese(rep['mese'], lingua))
    righe = ['# ' + titolo, '', '## ' + t('Da fatturare presto')]
    righe += ['- ' + t('{cliente}: {rimasti} crediti rimasti').format(
        cliente=x['cliente'], rimasti=x['rimasti']) for x in rep['da_fatturare']] or \
        ['- ' + t('Nessuno: tutti hanno ancora più di 2 crediti.')]
    righe += ['', '## ' + t('Anomalie')]
    righe += ['- ' + ('%s  ' % _data_breve(a['data']) if a['data'] else '') + frase_anomalia(a, lingua)
              for a in rep['anomalie']] or ['- ' + t('Nessuna: tutto torna.')]
    righe += ['', '## ' + t('Tutti i clienti'), '']
    if rep['righe']:
        righe.append('| %s | %s | %s | %s |' % (t('Cliente'), t('Sedute nel mese'),
                                               t('Crediti rimasti'), t('Ultima seduta')))
        righe.append('|---|---|---|---|')
        righe += ['| %s | %d | %d | %s |' % (x['cliente'], x['sedute_mese'], x['rimasti'],
                                              _data_breve(x['ultima_seduta'])) for x in rep['righe']]
    else:
        righe.append(t('Nessun cliente con un pacchetto.'))
    righe += ['', t('Report fatto dall\'app: non ha cambiato niente, né nel calendario né nei crediti.')]
    return '\n'.join(righe) + '\n'


def percorso_pulito(testo):
    """La cartella come la incolla il Mac: a volte fra apici, a volte con
    «\\ » al posto degli spazi (se viene dal Terminale). E' sempre la stessa
    cartella, e dirle «non esiste» farebbe pensare a un errore che non c'e'."""
    testo = (testo or '').strip()
    if len(testo) >= 2 and testo[0] == testo[-1] and testo[0] in '\'"':
        testo = testo[1:-1].strip()
    return testo.replace('\\ ', ' ')


def nome_file(mese):
    return 'Report crediti %s.md' % mese


def da_mandare(settings, oggi):
    """Il mese da mandare oggi, oppure None.

    Si manda il mese scorso, una volta sola. Non serve che l'app sia aperta
    proprio il primo: parte la prima volta che la si apre nel mese nuovo. Se
    l'invio fallisce si riprova il giorno dopo, non a ogni pagina: la posta
    che rifiuta la password tre volte di fila blocca l'indirizzo."""
    if settings.get('report_mese_auto') != '1':
        return None
    mese = mese_scorso(oggi)
    if (settings.get('report_mese_ultimo') or '') >= mese:
        return None
    if settings.get('report_mese_tentato') == oggi.isoformat():
        return None
    return mese
