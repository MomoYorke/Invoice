# -*- coding: utf-8 -*-
"""
Il menu di sinistra.

Tredici voci una sotto l'altra sono un elenco, non un menu: chi arriva
dall'esterno le legge tutte ogni volta perche' niente gli dice quali servono
tutti i giorni e quali una volta l'anno. Qui sono divise in gruppi con un
titolo, nell'ordine in cui capitano davvero: prima si fa la fattura, poi si
guarda chi segui, poi si controllano gli incassi, e in fondo le cose
dell'app.

«attivo» elenca le pagine che devono accendere quella voce: la scheda di una
singola fattura accende «Fatture», la pagina di un pacchetto accende
«Crediti». Senza, aprendo un dettaglio il menu si spegne tutto e non si capisce
piu' dove si e'.
"""

GRUPPI = [
    (None, [
        ('dashboard', 'Dashboard', 'cruscotto', ('dashboard',)),
        ('performance', 'Performance', 'grafico', ('performance',)),
    ]),
    ('Fatturare', [
        ('nuova', 'Nuova fattura', 'nuova', ('nuova',)),
        ('abbonamenti', 'Abbonamenti', 'ricicla', ('abbonamenti',)),
        ('fatture', 'Fatture', 'fattura', ('fatture', 'fattura', 'fattura_email')),
        ('email_inviate', 'Email inviate', 'email', ('email_inviate', 'email_letta')),
    ]),
    ('Chi segui', [
        ('clienti', 'Clienti', 'clienti', ('clienti',)),
        ('crediti', 'Crediti', 'crediti', ('crediti', 'crediti_pacchetto', 'crediti_clienti')),
        ('agenda', 'Agenda', 'agenda', ('agenda',)),
    ]),
    ('Incassi e fisco', [
        ('banca_pagina', 'Banca', 'banca', ('banca_pagina',)),
        ('commercialista', 'Commercialista', 'pacco', ('commercialista',)),
    ]),
    ("L'app", [
        ('impostazioni', 'Impostazioni', 'impostazioni', ('impostazioni',)),
    ]),
]

# Fuori dal menu, ma vive lo stesso.
#
# Un posto fisso in barra e' la cosa piu' cara che l'app abbia: chi arriva lo
# legge ogni volta, e ogni voce che non serve rende meno visibili quelle che
# servono. Queste tre pagine non sono lavoro — sono la manutenzione dell'app —
# e stavano li' dentro tutti i giorni per farsi aprire tre volte l'anno.
#
# CONTROLLI torna in barra da solo quando ha qualcosa da dire, col numero
# addosso: e' il contrario di prima, dove occupava un posto per dire che
# andava tutto bene. VERIFICA e CESTINO si raggiungono da Impostazioni.
#
# Nessuna delle tre si cancella. La verifica dei calcoli, in un programma che
# uno si scarica invece di comprare da un'azienda, e' quasi l'unica prova che
# i conti tornino: va messa dove la trova chi la cerca, non tolta.
CONTROLLI = ('controlli', 'Controlli', 'controlli', ('controlli',))
VERIFICA = ('verifica', 'Verifica calcoli', 'verifica', ('verifica',))
CESTINO = ('cestino', 'Cestino', 'cestino', ('cestino',))
FUORI_MENU = (CONTROLLI, VERIFICA, CESTINO)


def gruppi(da_sistemare=0):
    """I gruppi da mostrare adesso.

    «da_sistemare» e' quante anomalie ha trovato l'app nei dati delle fatture.
    Se ce n'e' almeno una, «Controlli» compare in fondo col numero; se non ce
    n'e', non compare — che e' l'unico modo perche' comparire voglia dire
    qualcosa.
    """
    if not da_sistemare:
        return GRUPPI
    endpoint, etichetta, disegno, attivo = CONTROLLI
    voce = (endpoint, '%s (%d)' % (etichetta, da_sistemare), disegno, attivo)
    return [(titolo, ([voce] + list(voci)) if titolo == "L'app" else voci)
            for titolo, voci in GRUPPI]

# Sta sopra a tutto e sparisce da sola quando non resta piu' niente da fare:
# finche' c'e', e' l'unico modo per tornare ai primi passi dopo aver chiuso
# il promemoria della Dashboard.
PRIMI_PASSI = ('benvenuto', 'Primi passi', 'bussola', ('benvenuto',))


def voci():
    """Tutte le voci, anche quelle fuori menu: serve ai controlli.

    Fuori dal menu non vuol dire fuori dai controlli: quelle pagine hanno
    ancora bisogno di un'icona, di un nome tradotto e di una pagina che
    esista davvero.
    """
    return ([v for _, elenco in GRUPPI for v in elenco]
            + list(FUORI_MENU) + [PRIMI_PASSI])
