#!/bin/zsh
# Avvia l'app Fatture.
# Doppio click e via: apre il browser da solo.
cd "$(dirname "$0")"
PORT=8471
URL="http://127.0.0.1:$PORT"
# l'app legge la porta da qui: cosi' cambiarla in un posto solo basta davvero
# (se la 8471 fosse occupata da qualcos'altro, si cambia questa riga e via)
export FATTURE_PORT="$PORT"

# --- 1. ambiente Python: verifica che sia sano, altrimenti lo (ri)creo ---
venv_ok() {
  [ -x "venv/bin/python" ] || return 1
  ./venv/bin/python -c "import flask, docx, openpyxl, dateutil, reportlab, pypdf, PIL" >/dev/null 2>&1
}
if ! venv_ok; then
  echo "Preparo l'ambiente (serve internet, 1-2 minuti)..."
  rm -rf venv
  python3 -m venv venv
  ./venv/bin/pip install --quiet --upgrade pip
  ./venv/bin/pip install --quiet flask python-docx openpyxl python-dateutil reportlab pypdf pillow
fi

# --- 1bis. c'è una versione nuova del programma? ---
# Funziona solo se questa copia arriva da un repository: chi ha ricevuto la
# cartella zippata non ha .git e qui non succede niente, l'app parte e basta.
# Non aggiorna mai di nascosto: mostra cos'è cambiato e chiede il permesso.
# I DATI non c'entrano: database, fatture, estratti, backup e logo sono fuori
# dal repository (vedi .gitignore), quindi l'aggiornamento non li vede nemmeno.
SEGNA_CONTROLLO="data/.ultimo-controllo-aggiornamenti"
ORE_FRA_CONTROLLI=6

# macOS non ha «timeout»: se la rete è lenta o assente, non si resta appesi
con_scadenza() {
  local secondi=$1; shift
  "$@" &
  local pid=$!
  local i=0
  while [ $i -lt $((secondi * 10)) ]; do
    kill -0 $pid 2>/dev/null || { wait $pid; return $?; }
    sleep 0.1
    i=$((i + 1))
  done
  kill -9 $pid 2>/dev/null
  return 124
}

troppo_presto() {
  [ -f "$SEGNA_CONTROLLO" ] || return 1
  [ -z "$(find "$SEGNA_CONTROLLO" -mmin +$((ORE_FRA_CONTROLLI * 60)) 2>/dev/null)" ]
}

cerca_aggiornamenti() {
  [ -d .git ] || return
  command -v git >/dev/null 2>&1 || return
  git remote get-url origin >/dev/null 2>&1 || return
  troppo_presto && return

  # GIT_TERMINAL_PROMPT=0: se il repository chiedesse una password, git
  # fallisce subito invece di bloccare l'avvio aspettando che qualcuno scriva
  GIT_TERMINAL_PROMPT=0 con_scadenza 15 git fetch --quiet origin 2>/dev/null || return
  mkdir -p data && touch "$SEGNA_CONTROLLO"

  local qui la_fuori
  qui=$(git rev-parse HEAD 2>/dev/null)
  la_fuori=$(git rev-parse origin/HEAD 2>/dev/null || git rev-parse origin/main 2>/dev/null)
  [ -n "$la_fuori" ] || return
  [ "$qui" = "$la_fuori" ] && return
  # solo in avanti: se questa copia è più avanti del repository, non si tocca
  git merge-base --is-ancestor "$qui" "$la_fuori" 2>/dev/null || return

  echo ""
  echo "  ┌─ C'è una versione nuova dell'app ─────────────────────────"
  git log --format='  │  · %s' "$qui..$la_fuori" 2>/dev/null | head -8
  echo "  └───────────────────────────────────────────────────────────"

  if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "  ATTENZIONE: hai modificato dei file del programma. Aggiornando,"
    echo "  quelle modifiche vengono perse. (I tuoi dati non c'entrano.)"
  fi

  echo -n "  La installo? [Invio = sì, n = non adesso] "
  local risposta
  if ! read -t 120 -r risposta; then
    echo ""; echo "  Nessuna risposta: avvio la versione che hai già."
    return
  fi
  case "$risposta" in
    [nN]*) echo "  Va bene, la propongo la prossima volta."; return ;;
  esac

  # copia di sicurezza dei dati PRIMA di toccare il programma
  if [ -x "venv/bin/python" ]; then
    ./venv/bin/python -c "from core import backup; backup.make_backup('prima-aggiornamento')" \
      >/dev/null 2>&1 && echo "  Copia di sicurezza dei dati: fatta."
  fi
  echo "$qui" > data/.versione-precedente     # per tornare indietro, se serve

  if git reset --hard --quiet "$la_fuori" 2>/dev/null; then
    echo "  Aggiornata."
    # se sono cambiate le librerie, l'ambiente si rifà da solo qui sotto
    if ! venv_ok; then
      echo "  Servono librerie nuove: le installo (1-2 minuti)..."
      rm -rf venv
      python3 -m venv venv
      ./venv/bin/pip install --quiet --upgrade pip
      ./venv/bin/pip install --quiet -r requirements.txt
    fi
  else
    echo "  L'aggiornamento non è riuscito: avvio la versione che hai già."
  fi
}
cerca_aggiornamenti

# --- 2. c'è già un'app SANA sulla porta? ---
# Sì, ma solo se è anche AGGIORNATA. Le pagine restano in memoria da quando
# l'app è partita: se il programma è stato modificato dopo, quella accesa è la
# versione vecchia e riaprendo il browser non si vedrebbe niente di nuovo.
# data/.avviata-$PORT lo scrive l'app quando parte; se un file del programma è più
# recente, si riparte invece di aprire e basta.
aggiornata() {
  [ -f "data/.avviata-$PORT" ] || return 1
  local piu_recente
  piu_recente=$(find app.py core templates static -type f \
                     \( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.js' \) \
                     -newer "data/.avviata-$PORT" -print -quit 2>/dev/null)
  [ -z "$piu_recente" ]
}
if [ "$(curl -s --max-time 2 $URL/health 2>/dev/null)" = "ok" ]; then
  if aggiornata; then
    open "$URL"
    exit 0
  fi
  echo "  Il programma è stato aggiornato: riavvio l'app..."
  lsof -ti:$PORT 2>/dev/null | xargs kill 2>/dev/null
  sleep 1
fi

# --- 3. c'è qualcosa di rotto attaccato alla porta? lo chiudo e riparto pulito ---
ZOMBIE=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$ZOMBIE" ]; then
  echo "Trovata un'istanza bloccata: la chiudo e riavvio pulito..."
  echo "$ZOMBIE" | xargs kill -9 2>/dev/null
  sleep 1
fi

# --- 4. avvio l'app e apro il browser appena è pronta ---
echo ""
echo "  Fatture — app locale"
echo "  Avvio su $URL ..."
./venv/bin/python app.py &
APP_PID=$!

# aspetta che /health risponda 'ok' (max ~15s), poi apri il browser
for i in $(seq 1 30); do
  if [ "$(curl -s --max-time 1 $URL/health 2>/dev/null)" = "ok" ]; then
    open "$URL"
    break
  fi
  # se il processo è morto durante l'avvio, mostra l'errore e fermati
  if ! kill -0 $APP_PID 2>/dev/null; then
    echo ""
    echo "  ⚠️  L'app non è partita. Dettagli in: data/error.log"
    echo "  Premi un tasto per chiudere."
    read -k1
    exit 1
  fi
  sleep 0.5
done

echo "  App pronta. Lascia aperta questa finestra."
echo "  Per chiudere l'app: Ctrl+C o chiudi la finestra."
echo ""
wait $APP_PID
