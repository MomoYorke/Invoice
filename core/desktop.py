# ---------------------------------------------------------------------------
# Le poche cose che cambiano da un computer all'altro.
#
# Il resto del programma non sa su che sistema sta girando, e non deve
# saperlo: chiede «fammi vedere questa cartella» oppure «dove metto le copie
# di sicurezza», e la risposta si decide qui. Tenerle in un posto solo vuol
# dire che il giorno in cui si aggiunge un sistema si tocca questo file e
# nessun altro, invece di andare a caccia di righe sparse per il programma.
#
# Ogni funzione accetta «sistema» come argomento invece di guardare da se' su
# cosa sta girando. Serve ai controlli: da un Mac si puo' chiedere «e su
# Windows cosa faresti?» e verificare la risposta senza avere un Windows.
# ---------------------------------------------------------------------------
import os
import re
import subprocess
import sys

# Il nome della cartella delle copie di sicurezza, per chi installa l'app da
# oggi in poi. Chi ce l'ha gia' se la tiene com'e': il percorso e' scritto
# nelle impostazioni, e quello che c'e' scritto vince sempre su questo.
NOME_BACKUP = 'Invoice - Backup'


def _windows(sistema):
    return sistema.startswith('win')


def comando_apri(percorso, sistema=None, cartella=None):
    """Il comando che fa vedere un file o una cartella, sistema per sistema.

    Un file non si apre: si MOSTRA nella sua cartella, gia' selezionato.
    Aprirlo vorrebbe dire lanciare il programma che se lo prende, e non e'
    quello che si aspetta chi clicca «mostra dov'e'».

    «cartella» si passa solo per provare la funzione su percorsi che non
    esistono; normalmente lo guarda da se' sul disco.
    """
    sistema = sistema or sys.platform
    if cartella is None:
        cartella = os.path.isdir(percorso)
    if sistema == 'darwin':
        # «-a Finder», non «open» liscio: per il Mac una cartella che finisce
        # per .app e' un programma, e «open» la LANCEREBBE invece di aprirla.
        # Cosi' invece si apre e basta, qualunque cosa sia dentro.
        return ['open', '-a', 'Finder', percorso] if cartella else ['open', '-R', percorso]
    if _windows(sistema):
        # explorer non esegue mai niente: apre la cartella, oppure la apre con
        # dentro il file gia' evidenziato. Due trappole, tutt'e due vere:
        # «/select,» va attaccato al percorso (con uno spazio in mezzo
        # Explorer apre Documenti e buonanotte), e il percorso lo vuole con le
        # barre rovesce, anche quando arriva scritto all'americana.
        percorso = percorso.replace('/', '\\')
        return ['explorer', percorso] if cartella else ['explorer', '/select,' + percorso]
    # Linux e tutto il resto. Evidenziare un file dentro la sua cartella si
    # fa in un modo diverso per ogni scrivania, quindi si apre la cartella che
    # lo contiene: si vede un po' meno, ma funziona ovunque e non lancia
    # niente.
    return ['xdg-open', percorso if cartella else (os.path.dirname(percorso) or '.')]


def apri(percorso):
    """Fa vedere il file o la cartella. Torna False se non c'e' stato verso.

    Non riuscire ad aprire una finestra non e' un buon motivo per far fallire
    la pagina che l'ha chiesto: il lavoro vero (lo zip, la fattura) e' gia'
    fatto e salvato, questa e' solo la comodita' di vederselo comparire.
    """
    try:
        subprocess.Popen(comando_apri(percorso))
        return True
    except OSError:                                     # pragma: no cover
        return False


def cartella_backup(sistema=None, casa=None, ambiente=None, esiste=None):
    """Dove finiscono le copie di sicurezza, quando nessuno ha detto altrove.

    Il criterio e' lo stesso su ogni sistema: una cartella che si sincronizza
    da sola fuori dal computer. Una copia sullo stesso disco non salva da un
    disco che muore, ed e' esattamente da quello che deve salvare.
    """
    sistema = sistema or sys.platform
    casa = casa or os.path.expanduser('~')
    ambiente = os.environ if ambiente is None else ambiente
    esiste = esiste or os.path.isdir

    if sistema == 'darwin':
        return os.path.join(casa, 'Library', 'Mobile Documents',
                            'com~apple~CloudDocs', NOME_BACKUP)
    if _windows(sistema):
        # OneDrive e' acceso su quasi ogni Windows di oggi ed e' la cosa piu'
        # vicina a quello che iCloud fa sul Mac. Dov'e' finito lo scrive
        # Windows stesso in una variabile d'ambiente: meglio chiederlo a lui
        # che indovinare, perche' con un account aziendale sta in un altro
        # posto e con un nome diverso.
        nube = (ambiente.get('OneDrive') or ambiente.get('OneDriveConsumer')
                or ambiente.get('OneDriveCommercial'))
        if nube and esiste(nube):
            return os.path.join(nube, NOME_BACKUP)
        # Niente OneDrive: Documenti. Non si sincronizza, ma almeno e' una
        # cartella che la gente apre e vede, e che finisce nei backup di
        # sistema di Windows.
        return os.path.join(casa, 'Documents', NOME_BACKUP)
    # Linux e il resto: nessuna nube di sistema su cui contare.
    documenti = os.path.join(casa, 'Documents')
    return os.path.join(documenti if esiste(documenti) else casa, NOME_BACKUP)


# I caratteri che Windows non ammette dentro il nome di un file. Il Mac ne
# vieta uno solo, la barra, quindi un nome che qui si scrive benissimo puo'
# essere impossibile la'. Meglio ripulirlo appena nasce: un file che non si
# riesce a salvare non e' un dettaglio estetico, e' una fattura che non esce.
VIETATI_NEI_NOMI = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def nome_file_sicuro(nome):
    """Un nome di file che va bene su tutti e due i sistemi.

    Tocca solo i caratteri vietati e nient'altro: i punti restano dove sono,
    perche' un nome come «J. R.» non e' un problema — nel file finito ha
    sempre qualcosa dietro (il numero, l'estensione) e Windows si mangia i
    punti solo quando stanno proprio in fondo.
    """
    return VIETATI_NEI_NOMI.sub('-', nome or '')
