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
    ]),
    ('Fatturare', [
        ('nuova', 'Nuova fattura', 'nuova', ('nuova',)),
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
        ('controlli', 'Controlli', 'controlli', ('controlli',)),
        ('verifica', 'Verifica calcoli', 'verifica', ('verifica',)),
        ('cestino', 'Cestino', 'cestino', ('cestino',)),
        ('impostazioni', 'Impostazioni', 'impostazioni', ('impostazioni',)),
    ]),
]

# Sta sopra a tutto e sparisce da sola quando non resta piu' niente da fare:
# finche' c'e', e' l'unico modo per tornare ai primi passi dopo aver chiuso
# il promemoria della Dashboard.
PRIMI_PASSI = ('benvenuto', 'Primi passi', 'bussola', ('benvenuto',))


def voci():
    """Tutte le voci, gruppi sciolti: serve ai controlli."""
    return [v for _, elenco in GRUPPI for v in elenco] + [PRIMI_PASSI]
