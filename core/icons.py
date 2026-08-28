# -*- coding: utf-8 -*-
"""
Le icone dell'app: disegni, non faccine.

Le emoji sembrano comode ma sono un guaio: ogni sistema le disegna a modo suo,
hanno colori e dimensioni che non si possono cambiare, restano colorate anche
sopra uno sfondo scuro e su Windows o Linux alcune non esistono proprio.
Qui ognuna e' un disegno a tratto: prende il colore del testo che le sta
intorno, ha sempre la stessa dimensione e sta allineata alla riga.

Sono tutte costruite nello stesso quadrato di 24 unita' e con lo stesso
spessore di tratto, cosi' stanno insieme senza che una sembri piu' grassa
delle altre.
"""
from markupsafe import Markup, escape

RIQUADRO = 24

# Il corpo di ogni icona: solo le forme, il resto della cornice e' uguale
# per tutte e lo mette icona() qui sotto.
DISEGNI = {
    # --- le voci del menu ---
    'cruscotto': '<rect x="3.2" y="3.2" width="7" height="8.2" rx="1.6"/>'
                 '<rect x="13.8" y="3.2" width="7" height="5" rx="1.6"/>'
                 '<rect x="13.8" y="11" width="7" height="9.8" rx="1.6"/>'
                 '<rect x="3.2" y="14.2" width="7" height="6.6" rx="1.6"/>',
    'nuova':     '<path d="M14 3.2H7a2 2 0 0 0-2 2v13.6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.2z"/>'
                 '<path d="M14 3.2v5h5"/><path d="M12 12.2v5M9.5 14.7h5"/>',
    'fattura':   '<path d="M14 3.2H7a2 2 0 0 0-2 2v13.6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.2z"/>'
                 '<path d="M14 3.2v5h5"/><path d="M8.4 13h7.2M8.4 16.6h4.6"/>',
    'clienti':   '<circle cx="9.4" cy="8" r="3.3"/>'
                 '<path d="M15.4 20.4v-1.7a3.5 3.5 0 0 0-3.5-3.5H6.9a3.5 3.5 0 0 0-3.5 3.5v1.7"/>'
                 '<path d="M15.6 5.1a3.3 3.3 0 0 1 0 5.8"/>'
                 '<path d="M20.6 20.4v-1.7a3.5 3.5 0 0 0-2.6-3.4"/>',
    'crediti':   '<path d="M4.4 5.6h15.2a1.8 1.8 0 0 1 1.8 1.8v1.9a2.8 2.8 0 0 0 0 5.4v1.9a1.8 1.8 0 0'
                 ' 1-1.8 1.8H4.4a1.8 1.8 0 0 1-1.8-1.8v-1.9a2.8 2.8 0 0 0 0-5.4V7.4a1.8 1.8 0 0 1 1.8-1.8z"/>'
                 '<path d="M13 8.4v1.6M13 12.4v1.6M13 16v1.6"/>',
    'spegni':    '<path d="M12 3.4v7.6"/>'
                 '<path d="M17.1 6.5a7.3 7.3 0 1 1-10.2 0"/>',
    'agenda':    '<rect x="3.4" y="5" width="17.2" height="15.6" rx="2.6"/>'
                 '<path d="M3.4 10.1h17.2M8 3.2v3.8M16 3.2v3.8"/>',
    'email':     '<rect x="2.6" y="5" width="18.8" height="14" rx="2.6"/>'
                 '<path d="M3.6 7.2 10.8 12.3a2 2 0 0 0 2.4 0l7.2-5.1"/>',
    'banca':     '<path d="M3.4 9.6 12 4.2l8.6 5.4"/>'
                 '<path d="M5.8 9.8v7.9M9.9 9.8v7.9M14.1 9.8v7.9M18.2 9.8v7.9"/>'
                 '<path d="M3.2 20.4h17.6"/>',
    'pacco':     '<path d="M3.2 7.4 12 3.2l8.8 4.2v9.2L12 20.8l-8.8-4.2z"/>'
                 '<path d="m3.2 7.4 8.8 4.3 8.8-4.3M12 11.7v9.1"/>',
    'controlli': '<path d="M12 3.2 4.6 6v5.4c0 4.3 3 8 7.4 9.4 4.4-1.4 7.4-5.1 7.4-9.4V6z"/>'
                 '<path d="m8.9 11.9 2.3 2.3 4.2-4.6"/>',
    'cestino':   '<path d="M4.2 6.6h15.6M9.6 6.6V4.7a1.2 1.2 0 0 1 1.2-1.2h2.4a1.2 1.2 0 0 1 1.2 1.2v1.9"/>'
                 '<path d="m6.4 6.6.9 12.3a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9l.9-12.3"/>'
                 '<path d="M10.4 10.4v6.4M13.6 10.4v6.4"/>',
    'verifica':  '<rect x="4.6" y="2.9" width="14.8" height="18.2" rx="2.6"/>'
                 '<rect x="7.9" y="6" width="8.2" height="3.4" rx="1.1"/>'
                 '<path d="M8.4 13h.01M12 13h.01M15.6 13h.01'
                 'M8.4 17h.01M12 17h.01M15.6 17h.01"/>',
    'impostazioni': '<circle cx="12" cy="12" r="3.1"/>'
                 '<path d="M19.1 14.8a1.6 1.6 0 0 0 .3 1.8l.1.1a1.9 1.9 0 1 1-2.7 2.7l-.1-.1a1.6 1.6 0 0 0'
                 '-1.8-.3 1.6 1.6 0 0 0-1 1.4v.3a1.9 1.9 0 1 1-3.8 0v-.2a1.6 1.6 0 0 0-1-1.4 1.6 1.6 0 0 0'
                 '-1.8.3l-.1.1a1.9 1.9 0 1 1-2.7-2.7l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.4-1h-.3a1.9'
                 ' 1.9 0 1 1 0-3.8h.2a1.6 1.6 0 0 0 1.4-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a1.9 1.9 0 1 1 2.7-2.7'
                 'l.1.1a1.6 1.6 0 0 0 1.8.3h.1a1.6 1.6 0 0 0 1-1.4v-.3a1.9 1.9 0 1 1 3.8 0v.2a1.6 1.6 0 0 0'
                 ' 1 1.4 1.6 1.6 0 0 0 1.8-.3l.1-.1a1.9 1.9 0 1 1 2.7 2.7l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6'
                 ' 1.6 0 0 0 1.4 1h.3a1.9 1.9 0 1 1 0 3.8h-.2a1.6 1.6 0 0 0-1.4 1z"/>',
    'bussola':   '<circle cx="12" cy="12" r="8.8"/>'
                 '<path d="m15.9 8.1-2.1 5.7-5.7 2.1 2.1-5.7z"/>',

    # --- usate nelle pagine ---
    'matita':    '<path d="M16.8 3.6a2.2 2.2 0 0 1 3.1 3.1L7.6 19 3.4 20.6 5 16.4z"/>'
                 '<path d="m14.6 5.8 3.6 3.6"/>',
    'nota':      '<path d="M11.2 4.2H6a2 2 0 0 0-2 2v11.8a2 2 0 0 0 2 2h11.8a2 2 0 0 0 2-2v-5.2"/>'
                 '<path d="M17.2 3.4a2.1 2.1 0 0 1 3 3l-7.8 7.8-3.9 1 1-3.9z"/>',
    'spunta':    '<path d="m4.6 12.4 4.9 4.9L19.4 6.4"/>',
    'croce':     '<path d="M6.2 6.2 17.8 17.8M17.8 6.2 6.2 17.8"/>',
    'avviso':    '<path d="M10.3 4.3 2.7 17.4a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z"/>'
                 '<path d="M12 9.4v4.2M12 17.2h.01"/>',
    'graffetta': '<path d="M20.1 11.4 12.4 19a4.5 4.5 0 0 1-6.4-6.4l8-8a3 3 0 0 1 4.2 4.2l-8 8a1.5 1.5 0 0'
                 ' 1-2.1-2.1l7.3-7.3"/>',
    'giu':       '<path d="M12 3.6v10.8M7.7 10.4 12 14.6l4.3-4.2"/>'
                 '<path d="M4.2 16v2.6a2 2 0 0 0 2 2h11.6a2 2 0 0 0 2-2V16"/>',
    'ricicla':   '<path d="M3.6 12a8.4 8.4 0 0 1 14.1-6.2l2.7 2.5"/><path d="M20.4 3.6v5h-5"/>'
                 '<path d="M20.4 12a8.4 8.4 0 0 1-14.1 6.2l-2.7-2.5"/><path d="M3.6 20.4v-5h5"/>',
    'grafico':   '<path d="M4.5 19.5h15"/><path d="M7.5 19.5V13.5"/>'
                 '<path d="M12 19.5V6.5"/><path d="M16.5 19.5V10.5"/>',
    'soldi':     '<rect x="2.6" y="5.8" width="18.8" height="12.4" rx="2.6"/>'
                 '<circle cx="12" cy="12" r="2.7"/><path d="M6 12h.01M18 12h.01"/>',
}


def icona(nome, classe='ic'):
    """Il disegno pronto da mettere in pagina.

    Se il nome non esiste non si disegna niente: una pagina senza un'icona si
    legge lo stesso, una pagina con un errore no. I test pero' controllano che
    tutti i nomi usati nei modelli esistano davvero, cosi' la svista si vede
    prima di arrivare a schermo.
    """
    forme = DISEGNI.get(nome)
    if not forme:
        return Markup('')
    return Markup(
        f'<svg class="{classe}" viewBox="0 0 {RIQUADRO} {RIQUADRO}" width="{RIQUADRO}"'
        f' height="{RIQUADRO}" fill="none" stroke="currentColor" stroke-width="1.7"'
        f' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'
        f' focusable="false">{forme}</svg>')


def nomi():
    return sorted(DISEGNI)


COLORI = ('verde', 'giallo', 'arancio', 'rosso', 'blu', 'vuoto')


def pallino(colore, titolo=''):
    """Il pallino di stato accanto a una riga.

    Al posto delle emoji colorate: quelle cambiano dimensione da un sistema
    all'altro, non si possono ricolorare e chi legge con la voce sintetica si
    sente dire «cerchio verde grande» in mezzo a una frase. Questo e' un
    quadratino di CSS con scritto sopra cosa vuol dire.
    """
    if colore not in COLORI:                            # pragma: no cover
        colore = 'vuoto'
    t = f' title="{escape(titolo)}"' if titolo else ''
    return Markup(f'<span class="pallino {colore}"{t}></span>')
