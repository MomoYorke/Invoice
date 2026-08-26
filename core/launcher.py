# ---------------------------------------------------------------------------
# I conti che l'avviatore non sa fare da se'.
#
# Accendere l'app vuol dire rispondere a quattro domande: l'ambiente Python e'
# ancora quello giusto? Ho gia' guardato se c'e' una versione nuova? C'e'
# un'app viva su quella porta? E se c'e', e' aggiornata o e' rimasta indietro?
#
# Sul Mac l'avviatore se le sbriga con shasum, find e curl. Su Windows quegli
# attrezzi non ci sono, e i giri di parole per rifarli nel linguaggio dei .bat
# sono righe che nessuno rilegge e che nessun controllo puo' verificare.
# Allora i conti stanno qui, in un posto solo: i due avviatori li CHIEDONO
# invece di riscriverseli ognuno a modo suo, e i controlli dell'app possono
# verificarli davvero.
#
# Da riga di comando:  python -m core.launcher <domanda> [argomenti]
# Non stampa niente: risponde con l'esito, 0 per si' e 1 per no, che e' come
# si parla con un avviatore.
#
# Qui dentro entra SOLO roba della libreria standard: queste domande si fanno
# anche quando l'ambiente non e' ancora stato costruito e Flask non esiste.
# ---------------------------------------------------------------------------
import hashlib
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dove guarda per capire se il programma e' cambiato dopo l'accensione.
SORGENTI = ('app.py', 'core', 'templates', 'static')
ESTENSIONI = ('.py', '.html', '.css', '.js')


def impronta_requisiti(base=None):
    """L'impronta di requirements.txt: cambia lei, si rifa' l'ambiente.

    E' lo stesso identico numero che sul Mac scrive «shasum»: cosi' una
    cartella che passa da un sistema all'altro non si rifa' l'ambiente per
    niente, e soprattutto i due avviatori parlano della stessa cosa.
    """
    base = base or BASE
    with open(os.path.join(base, 'requirements.txt'), 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def _segnaposto_requisiti(base):
    # «.requisiti» e' il nome che aveva prima questo file: accettarlo evita a
    # tutti un rifacimento inutile dell'ambiente al primo aggiornamento.
    for nome in ('.requirements', '.requisiti'):
        perc = os.path.join(base, 'venv', nome)
        if os.path.isfile(perc):
            return perc
    return None


def requisiti_a_posto(base=None):
    """L'ambiente e' stato costruito con QUESTA lista di librerie?"""
    base = base or BASE
    perc = _segnaposto_requisiti(base)
    if not perc:
        return False
    try:
        with open(perc) as f:
            scritto = f.read().strip()
    except OSError:                                     # pragma: no cover
        return False
    return scritto == impronta_requisiti(base)


def scrivi_impronta(base=None):
    """Segna l'impronta dopo aver costruito l'ambiente."""
    base = base or BASE
    with open(os.path.join(base, 'venv', '.requirements'), 'w') as f:
        f.write(impronta_requisiti(base))


def controllato_da_poco(marcatore, ore=6, adesso=None):
    """Ho gia' guardato se c'e' una versione nuova, di recente?

    Non e' pigrizia: chiedere a GitHub a ogni accensione vuol dire aspettare
    la rete anche solo per riaprire la finestra dell'app dieci volte al
    giorno.
    """
    try:
        quando = os.path.getmtime(marcatore)
    except OSError:
        return False
    return (adesso or time.time()) - quando < ore * 3600


def aggiornato(porta, base=None, adesso=None):
    """L'app che sta girando e' quella di adesso, o e' rimasta indietro?

    Le pagine restano in memoria da quando l'app e' partita: se il programma
    e' stato cambiato dopo, quella accesa e' ancora la versione vecchia e
    riaprire il browser non farebbe vedere niente di nuovo. Il file
    «data/.started-PORTA» dice da quando sta girando; se un file del
    programma e' piu' recente, va riavviata.
    """
    base = base or BASE
    try:
        acceso = os.path.getmtime(os.path.join(base, 'data', '.started-%s' % porta))
    except OSError:
        return False
    for radice in SORGENTI:
        perc = os.path.join(base, radice)
        if os.path.isfile(perc):
            if os.path.getmtime(perc) > acceso:
                return False
            continue
        for cartella, _sotto, file in os.walk(perc):
            for nome in file:
                if not nome.endswith(ESTENSIONI):
                    continue
                if os.path.getmtime(os.path.join(cartella, nome)) > acceso:
                    return False
    return True


def in_salute(url, secondi=2):
    """C'e' un'app viva su quell'indirizzo, e risponde di star bene?"""
    import urllib.request
    try:
        with urllib.request.urlopen(url + '/health', timeout=secondi) as r:
            return r.read().strip() == b'ok'
    except Exception:
        return False


# --- la parte da riga di comando -------------------------------------------
def main(argv):
    domanda = argv[1] if len(argv) > 1 else ''
    if domanda == 'requisiti-a-posto':
        return 0 if requisiti_a_posto() else 1
    if domanda == 'scrivi-impronta':
        scrivi_impronta()
        return 0
    if domanda == 'controllato-da-poco':
        return 0 if controllato_da_poco(argv[2], float(argv[3])) else 1
    if domanda == 'aggiornato':
        return 0 if aggiornato(argv[2]) else 1
    if domanda == 'in-salute':
        return 0 if in_salute(argv[2]) else 1
    if domanda == 'tocca':                      # crea o rinfresca un marcatore
        cartella = os.path.dirname(argv[2])
        if cartella:
            os.makedirs(cartella, exist_ok=True)
        with open(argv[2], 'w') as f:
            f.write('')
        return 0
    return 2                                    # domanda che non conosco


if __name__ == '__main__':                              # pragma: no cover
    sys.exit(main(sys.argv))
