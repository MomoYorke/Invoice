# ---------------------------------------------------------------------------
# Gli aggiornamenti, da dentro l'app.
#
# Prima si aggiornava solo dall'avviatore: guardava su GitHub al massimo ogni
# 6 ore, chiedeva nella finestra nera (che dall'icona non si vede) e, senza
# risposta entro due minuti, rimandava di altre 6 ore. Il 17.11.2026 ci sono
# voluti un'ora e una dozzina di foto per aggiornare un solo Mac.
#
# Qui le stesse quattro risposte dell'avviatore (none, forward, ahead,
# diverged), ma chieste quando le chiede chi usa l'app, con un pulsante.
# Le regole restano quelle dell'avviatore:
#   - prima di toccare il programma si fa la copia del database e si scrive
#     da dove si partiva (data/.previous-version), per poter tornare indietro;
#   - si cambiano SOLO i file del programma: i dati stanno fuori dal
#     repository (.gitignore) e git reset non li vede nemmeno;
#   - una copia con lavoro suo («ahead») non si tocca mai.
#
# Solo libreria standard: si importa anche quando git non c'e'.
# ---------------------------------------------------------------------------
import os

from . import desktop
from . import launcher

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARCATORE = os.path.join('data', '.last-update-check')
PRIMA = os.path.join('data', '.previous-version')
SECONDI_RETE = 15


def _git(base, *argomenti, secondi=10):
    """(esito, uscita) di un comando git. Non solleva mai."""
    ambiente = dict(os.environ, GIT_TERMINAL_PROMPT='0',
                    GIT_HTTP_LOW_SPEED_LIMIT='1000', GIT_HTTP_LOW_SPEED_TIME='10')
    return desktop.esegui(('git',) + argomenti, base, ambiente, secondi)


def tipo(base, qui, la):
    """Cosa separa questa copia da quella pubblicata (come l'avviatore)."""
    if qui == la:
        return 'none'
    if _git(base, 'merge-base', '--is-ancestor', qui, la)[0]:
        return 'forward'
    if _git(base, 'merge-base', '--is-ancestor', la, qui)[0]:
        return 'ahead'
    return 'diverged'


def _tocca(base):
    perc = os.path.join(base, MARCATORE)
    try:
        os.makedirs(os.path.dirname(perc), exist_ok=True)
        with open(perc, 'w') as f:
            f.write('')
    except OSError:                                     # pragma: no cover
        pass


def stato(base=None, rete=True):
    """Com'e' messa questa copia rispetto a quella pubblicata.

    «stato» e' una parola sola fra: senza_git (copia arrivata senza il
    collegamento a GitHub), git_mancante (sul computer manca git),
    non_raggiungibile, aggiornata, nuova, riallinea (storia riscritta),
    avanti (copia con lavoro suo: non si tocca).
    Con rete=False non chiede niente a GitHub: usa quello che sa gia'.
    """
    base = base or BASE
    fuori = {'stato': '', 'cartella': base, 'novita': [], 'modifiche_locali': False,
             'qui': '', 'la': ''}
    if not os.path.isdir(os.path.join(base, '.git')):
        fuori['stato'] = 'senza_git'
        return fuori
    ok, _ = _git(base, '--version')
    if not ok:
        fuori['stato'] = 'git_mancante'
        return fuori
    if rete:
        ok, _ = _git(base, 'fetch', '--quiet', 'origin', secondi=SECONDI_RETE)
        if not ok:
            fuori['stato'] = 'non_raggiungibile'
            return fuori
        _tocca(base)
    _, qui = _git(base, 'rev-parse', 'HEAD')
    ok, la = _git(base, 'rev-parse', 'origin/HEAD')
    if not ok or not la:
        ok, la = _git(base, 'rev-parse', 'origin/main')
    if not qui or not la:
        fuori['stato'] = 'non_raggiungibile'
        return fuori
    fuori['qui'], fuori['la'] = qui, la
    k = tipo(base, qui, la)
    fuori['stato'] = {'none': 'aggiornata', 'forward': 'nuova',
                      'diverged': 'riallinea', 'ahead': 'avanti'}[k]
    if k == 'forward':
        _, righe = _git(base, 'log', '--format=%s', '-12', '%s..%s' % (qui, la))
        fuori['novita'] = [r for r in righe.splitlines() if r.strip()]
    if k in ('forward', 'diverged'):
        _, cambi = _git(base, 'status', '--porcelain', '--untracked-files=no')
        fuori['modifiche_locali'] = bool(cambi)
    return fuori


def installa(base=None, la='', fai_copia=None):
    """Porta i file del programma alla versione «la». Ritorna un dizionario.

    «la» e' il commit che si e' fatto vedere a chi ha premuto il pulsante:
    se nel frattempo GitHub ne ha uno ancora piu' nuovo, si installa quello
    visto e non uno a sorpresa. «fai_copia» fa la copia del database (nei
    collaudi, un sostituto). Ritorna ok, motivo, e se servono librerie nuove
    (allora l'app va chiusa e riaperta, e l'avviatore le installa da solo).
    """
    base = base or BASE
    st = stato(base, rete=False)
    if st['stato'] not in ('nuova', 'riallinea') or not la or st['la'] != la:
        return {'ok': False, 'motivo': 'cambiato', 'librerie': False}
    if fai_copia is not None:
        try:
            fai_copia()
        except Exception:
            return {'ok': False, 'motivo': 'copia', 'librerie': False}
    try:
        os.makedirs(os.path.join(base, 'data'), exist_ok=True)
        with open(os.path.join(base, PRIMA), 'w') as f:
            f.write(st['qui'] + '\n')
    except OSError:
        return {'ok': False, 'motivo': 'scrittura', 'librerie': False}
    ok, _ = _git(base, 'reset', '--hard', '--quiet', la, secondi=60)
    if not ok:
        return {'ok': False, 'motivo': 'git', 'librerie': False}
    librerie = os.path.isdir(os.path.join(base, 'venv')) and not launcher.requisiti_a_posto(base)
    return {'ok': True, 'motivo': '', 'librerie': librerie}
