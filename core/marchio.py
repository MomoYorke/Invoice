# -*- coding: utf-8 -*-
"""
Il marchio dell'attività: il logo e il modo in cui il nome viene scritto.

Il logo è UNO SOLO e vale ovunque — barra laterale, PDF, documento Word.
Chi usa l'app lo carica dalle Impostazioni e finisce in data/logo.png, che
resta sul suo computer e non entra mai nel programma condiviso. Finché non
l'ha caricato si usa il segnaposto in assets/logo-esempio.png: così le
fatture escono comunque complete, e si vede a colpo d'occhio che manca il
logo vero.
"""
import io
import os

from PIL import Image

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# si puo' deviare con FATTURE_LOGO: serve alle prove, per non toccare il vero
PERSONALE = os.environ.get('FATTURE_LOGO') or os.path.join(APP_DIR, 'data', 'logo.png')
SEGNAPOSTO = os.path.join(APP_DIR, 'assets', 'logo-esempio.png')

LATO_MAX = 600          # px: piu' che sufficiente per stampa e schermo
PESO_MAX = 5 * 1024 * 1024


def percorso():
    """Il logo da usare adesso: quello dell'utente se c'e', altrimenti il segnaposto."""
    return PERSONALE if os.path.exists(PERSONALE) else SEGNAPOSTO


def personalizzato():
    return os.path.exists(PERSONALE)


def versione():
    """Numero che cambia quando cambia il logo: serve al browser per non
    tenersi in cache quello vecchio dopo un caricamento."""
    try:
        return int(os.path.getmtime(percorso()))
    except OSError:
        return 0


def salva(dati):
    """Salva il logo caricato dall'utente. Restituisce None se e' andata,
    altrimenti una frase da mostrare a schermo.

    Qualunque formato entri (PNG, JPEG, ...) esce PNG: cosi' il resto
    dell'app non deve piu' preoccuparsi di che immagine sia."""
    if not dati:
        return ('Non hai scelto nessun file.', {})
    if len(dati) > PESO_MAX:
        return ('Immagine troppo pesante ({kb} KB): il massimo è 5 MB.',
                {'kb': len(dati) // 1024})
    try:
        img = Image.open(io.BytesIO(dati))
        img.load()
    except Exception:
        return ("Non riesco a leggere questo file: dev'essere un'immagine (PNG, JPG).",
                {})
    img = img.convert('RGBA')
    img.thumbnail((LATO_MAX, LATO_MAX), Image.LANCZOS)
    os.makedirs(os.path.dirname(PERSONALE), exist_ok=True)
    # prima in un file a parte, poi lo sposto: se qualcosa va storto a meta'
    # non resta un logo mezzo scritto
    tmp = PERSONALE + '.nuovo'
    img.save(tmp, 'PNG')
    os.replace(tmp, PERSONALE)
    return None


def rimuovi():
    """Torna al segnaposto. Il file dell'utente viene tolto, non nascosto."""
    try:
        os.remove(PERSONALE)
        return True
    except OSError:
        return False


def adattato(larghezza, altezza):
    """Il logo nella forma che serve al documento Word, senza deformarlo.

    Lo spazio del logo nel Word ha una forma fissa (largo e basso): un logo
    quadrato ci finirebbe schiacciato. Invece di rimpicciolire il logo lo
    lasciamo com'e' e gli allarghiamo intorno un bordo trasparente, finche'
    il tutto non ha la forma giusta. Cosi' l'immagine non viene ne' stirata
    ne' ricampionata: chi aveva un logo nitido se lo ritrova nitido.

    larghezza/altezza servono solo a dire che FORMA deve avere il risultato."""
    forma = (larghezza / altezza) if altezza else 1.0
    # niente logo caricato: sulla fattura lo spazio resta vuoto. Il segnaposto
    # va bene dentro l'app, ma non su un documento che finisce a un cliente
    if not personalizzato():
        return _png(Image.new('RGBA', (larghezza, altezza), (255, 255, 255, 0)))
    try:
        img = Image.open(percorso())
        img.load()
        img = img.convert('RGBA')
    except Exception:
        return _png(Image.new('RGBA', (larghezza, altezza), (255, 255, 255, 0)))
    if img.width / img.height > forma:
        cornice = (img.width, max(1, round(img.width / forma)))
    else:
        cornice = (max(1, round(img.height * forma)), img.height)
    tela = Image.new('RGBA', cornice, (255, 255, 255, 0))
    # copia secca, senza fondere niente: i bordi sfumati del logo restano
    # esattamente com'erano
    tela.paste(img, ((cornice[0] - img.width) // 2, (cornice[1] - img.height) // 2))
    return _png(tela)


def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def due_righe(nome):
    """Il nome dell'attività spezzato per la barra laterale: le prime due
    parole in grande, il resto sotto in piccolo.

    «Anna Rossi Personal Training» -> «Anna Rossi» / «Personal Training»
    «Studio Bianchi Fisioterapia»  -> «Studio Bianchi» / «Fisioterapia»
    «Centro Vitale»                -> «Centro Vitale» / «»
    Non e' furba, ma non sbaglia mai in modo brutto: al massimo mette una
    parola nella riga sbagliata."""
    parole = (nome or '').split()
    if not parole:
        return ('La tua attività', '')
    return (' '.join(parole[:2]), ' '.join(parole[2:]))
