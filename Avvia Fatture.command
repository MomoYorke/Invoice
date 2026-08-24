#!/bin/zsh
# Avvia l'app Fatture.
# Doppio click e via: apre il browser da solo.
cd "$(dirname "$0")"
PORT=8471
URL="http://127.0.0.1:$PORT"

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
