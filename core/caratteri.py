# -*- coding: utf-8 -*-
"""
Il carattere dei PDF.

L'Helvetica che reportlab ha dentro conosce solo le lettere dell'Europa
occidentale: un nome come «Željko Ćosić» o «Łukasz» usciva con dei quadratini
neri, sulla fattura e sul bollettino QR. Arial ha le stesse misure
dell'Helvetica (il foglio non si sposta di un millimetro) e le lettere
dell'Europa centrale e orientale. C'e' su ogni Mac e su ogni Windows: si usa
quello che c'e' gia', senza portarsi dietro un file da ridistribuire.

Se nessun carattere adatto si trova, si resta sull'Helvetica e le lettere che
non ha si scrivono nella forma piu' vicina (ć diventa c): meglio un nome
leggibile che un quadratino.
"""
import os
import unicodedata

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

REG, BOLD = 'Helvetica', 'Helvetica-Bold'
UNICODE = False


def _candidati():
    win = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    mac = '/System/Library/Fonts/Supplemental'
    lib = '/usr/share/fonts/truetype'
    return [
        (os.path.join(mac, 'Arial.ttf'), os.path.join(mac, 'Arial Bold.ttf')),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
        (os.path.join(win, 'arial.ttf'), os.path.join(win, 'arialbd.ttf')),
        (lib + '/liberation/LiberationSans-Regular.ttf', lib + '/liberation/LiberationSans-Bold.ttf'),
        (lib + '/liberation2/LiberationSans-Regular.ttf', lib + '/liberation2/LiberationSans-Bold.ttf'),
        (lib + '/dejavu/DejaVuSans.ttf', lib + '/dejavu/DejaVuSans-Bold.ttf'),
    ]


def _registra():
    global REG, BOLD, UNICODE
    for regolare, grassetto in _candidati():
        if os.path.exists(regolare) and os.path.exists(grassetto):
            try:
                pdfmetrics.registerFont(TTFont('FattureReg', regolare))
                pdfmetrics.registerFont(TTFont('FattureBold', grassetto))
            except Exception:
                continue
            REG, BOLD, UNICODE = 'FattureReg', 'FattureBold', True
            return


_registra()

# lettere senza una forma «lettera + accento»: la scomposizione non le riduce
_A_MANO = {'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D', 'ħ': 'h', 'ı': 'i', 'ŧ': 't'}


def stampabile(testo):
    """Il testo com'e', con un carattere vero; sull'Helvetica, nella forma che
    quel carattere sa scrivere."""
    if UNICODE or not testo:
        return testo
    fuori = []
    for ch in str(testo):
        try:
            ch.encode('cp1252')
            fuori.append(ch)
            continue
        except UnicodeEncodeError:
            pass
        ch = _A_MANO.get(ch, ch)
        base = ''.join(x for x in unicodedata.normalize('NFKD', ch)
                       if not unicodedata.combining(x))
        fuori.append(base if base.isascii() and base else '?')
    return ''.join(fuori)


class Canvas(canvas.Canvas):
    """Il foglio, che scrive col carattere giusto anche quando non e' unicode."""

    def drawString(self, x, y, text, *a, **k):
        return super().drawString(x, y, stampabile(text), *a, **k)

    def drawRightString(self, x, y, text, *a, **k):
        return super().drawRightString(x, y, stampabile(text), *a, **k)

    def drawCentredString(self, x, y, text, *a, **k):
        return super().drawCentredString(x, y, stampabile(text), *a, **k)
