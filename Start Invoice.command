#!/bin/zsh
# Starts the Invoice app.
# Double-click and go: it opens the browser by itself.
cd "$(dirname "$0")"
PORT=8471
URL="http://127.0.0.1:$PORT"
# the app reads the port from here, so changing it in one place really is
# enough (if 8471 were taken by something else, change this line and go)
export INVOICE_PORT="$PORT"

# --- 1. Python environment: check it is sound, otherwise (re)build it ---
# The list of libraries lives in requirements.txt and nowhere else: add one and
# venv/.requirements no longer matches, so the environment rebuilds itself. The
# list used to be written twice, and the copy in the check would have forgotten.
venv_ok() {
  [ -x "venv/bin/python" ] || return 1
  local stamp
  # .requisiti was the old name of this stamp file: accepting it too spares
  # everyone a needless rebuild the first time they update
  if [ -f "venv/.requirements" ]; then stamp="venv/.requirements"
  elif [ -f "venv/.requisiti" ]; then stamp="venv/.requisiti"
  else return 1; fi
  [ "$(shasum requirements.txt | cut -d' ' -f1)" = "$(cat $stamp)" ] || return 1
  ./venv/bin/python -c "import flask, docx, openpyxl, dateutil, reportlab, pypdf, PIL" >/dev/null 2>&1
}
build_environment() {
  echo "Setting up the environment (needs internet, 1-2 minutes)..."
  rm -rf venv
  python3 -m venv venv || return 1
  ./venv/bin/pip install --quiet --upgrade pip
  ./venv/bin/pip install --quiet -r requirements.txt || return 1
  shasum requirements.txt | cut -d' ' -f1 > venv/.requirements
}
venv_ok || build_environment

# --- 1b. is there a new version of the program? ---
# This only works if this copy came from a repository: whoever received the
# folder as a zip has no .git and nothing happens here, the app just starts.
# It never updates behind your back: it shows what changed and asks permission.
# Your DATA is not involved: database, invoices, statements, backups and logo
# all live outside the repository (see .gitignore), so the update does not even
# see them.
CHECK_MARKER="data/.last-update-check"
HOURS_BETWEEN_CHECKS=6

# macOS has no «timeout»: if the network is slow or missing, we do not hang
with_timeout() {
  local seconds=$1; shift
  "$@" &
  local pid=$!
  local i=0
  while [ $i -lt $((seconds * 10)) ]; do
    kill -0 $pid 2>/dev/null || { wait $pid; return $?; }
    sleep 0.1
    i=$((i + 1))
  done
  kill -9 $pid 2>/dev/null
  return 124
}

too_soon() {
  [ -f "$CHECK_MARKER" ] || return 1
  [ -z "$(find "$CHECK_MARKER" -mmin +$((HOURS_BETWEEN_CHECKS * 60)) 2>/dev/null)" ]
}

check_for_updates() {
  [ -d .git ] || return
  command -v git >/dev/null 2>&1 || return
  git remote get-url origin >/dev/null 2>&1 || return
  too_soon && return

  # GIT_TERMINAL_PROMPT=0: if the repository asked for a password, git fails
  # straight away instead of holding up the start waiting for someone to type
  echo -n "  Checking for a new version... "
  if ! GIT_TERMINAL_PROMPT=0 with_timeout 10 git fetch --quiet origin 2>/dev/null; then
    echo "not reachable, never mind."
    return
  fi
  echo
  mkdir -p data && touch "$CHECK_MARKER"

  local here out_there
  here=$(git rev-parse HEAD 2>/dev/null)
  out_there=$(git rev-parse origin/HEAD 2>/dev/null || git rev-parse origin/main 2>/dev/null)
  [ -n "$out_there" ] || return

  case "$(update_kind "$here" "$out_there")" in
    none|ahead) return ;;
    forward)
      echo ""
      echo "  ┌─ There is a new version of the app ───────────────────────"
      git log --format='  │  · %s' "$here..$out_there" 2>/dev/null | head -8
      echo "  └───────────────────────────────────────────────────────────"
      warn_local_changes
      ask_and_apply "  Install it?" "$here" "$out_there" || return
      ;;
    diverged)
      # The published history was rewritten (old commits replaced by new ones
      # holding the same work). This copy still has the old ones, so «only
      # forwards» would never be true again and the app would quietly stop
      # updating for good. Better to say so and offer to line back up.
      echo ""
      echo "  ┌─ This copy no longer lines up with the published one ─────"
      echo "  │  The history was rewritten, so your version and the"
      echo "  │  published one no longer share the same commits."
      echo "  │  Lining up replaces the program files with the published"
      echo "  │  ones. YOUR DATA IS NOT TOUCHED: database, invoices,"
      echo "  │  statements and backups live outside the repository."
      echo "  └───────────────────────────────────────────────────────────"
      warn_local_changes
      ask_and_apply "  Line up with the published version?" "$here" "$out_there" || return
      ;;
  esac
}

# What separates this copy from the published one. Four answers, because the
# wrong thing to do differs in each case:
#   none      same commit: nothing to do
#   forward   the usual case, a newer version exists
#   ahead     this copy has work the repository does not: never touch it
#   diverged  the published history was rewritten: neither contains the other
update_kind() {
  local here=$1 out_there=$2
  [ "$here" = "$out_there" ] && { echo none; return; }
  if git merge-base --is-ancestor "$here" "$out_there" 2>/dev/null; then
    echo forward
  elif git merge-base --is-ancestor "$out_there" "$here" 2>/dev/null; then
    echo ahead
  else
    echo diverged
  fi
}

warn_local_changes() {
  [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ] || return
  echo "  WARNING: you have modified some program files. Going ahead will"
  echo "  lose those changes. (Your data is not involved.)"
}

# Asks, and if the answer is yes replaces the program files. Backs the data up
# first, and writes down where we were, so there is always a way back.
ask_and_apply() {
  local question=$1 here=$2 target=$3 answer
  echo -n "$question [Enter = yes, n = not now] "
  if ! read -t 120 -r answer; then
    echo ""; echo "  No answer: starting the version you already have."
    return 1
  fi
  case "$answer" in
    [nN]*) echo "  All right, I will offer it again next time."; return 1 ;;
  esac

  if [ -x "venv/bin/python" ]; then
    ./venv/bin/python -c "from core import backup; backup.make_backup('prima-aggiornamento')" \
      >/dev/null 2>&1 && echo "  Data backup: done."
  fi
  mkdir -p data && echo "$here" > data/.previous-version

  if git reset --hard --quiet "$target" 2>/dev/null; then
    echo "  Done."
    # if the libraries changed, the environment rebuilds itself just below
    venv_ok || { echo "  New libraries needed:"; build_environment; }
  else
    echo "  It did not go through: starting the version you have."
  fi
}
check_for_updates

# --- 2. is a HEALTHY app already on the port? ---
# Yes, but only if it is also UP TO DATE. The pages stay in memory from when
# the app started: if the program was modified afterwards, the one running is
# the old version, and reopening the browser would show nothing new.
# data/.started-$PORT is written by the app when it starts; if a program file
# is more recent, we restart instead of just opening.
up_to_date() {
  [ -f "data/.started-$PORT" ] || return 1
  local newer
  newer=$(find app.py core templates static -type f \
               \( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.js' \) \
               -newer "data/.started-$PORT" -print -quit 2>/dev/null)
  [ -z "$newer" ]
}
if [ "$(curl -s --max-time 2 $URL/health 2>/dev/null)" = "ok" ]; then
  if up_to_date; then
    open "$URL"
    exit 0
  fi
  echo "  The program has been updated: restarting the app..."
  lsof -ti:$PORT 2>/dev/null | xargs kill 2>/dev/null
  sleep 1
fi

# --- 3. is something broken stuck on the port? close it and start clean ---
ZOMBIE=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$ZOMBIE" ]; then
  echo "Found a stuck instance: closing it and restarting clean..."
  echo "$ZOMBIE" | xargs kill -9 2>/dev/null
  sleep 1
fi

# --- 4. start the app and open the browser as soon as it is ready ---
echo ""
echo "  Invoice — local app"
echo "  Starting on $URL ..."
./venv/bin/python app.py &
APP_PID=$!

# wait for /health to answer 'ok' (max ~15s), then open the browser
for i in $(seq 1 30); do
  if [ "$(curl -s --max-time 1 $URL/health 2>/dev/null)" = "ok" ]; then
    open "$URL"
    break
  fi
  # if the process died while starting, show the error and stop
  if ! kill -0 $APP_PID 2>/dev/null; then
    echo ""
    echo "  ⚠️  The app did not start. Details in: data/error.log"
    echo "  Press a key to close."
    read -k1
    exit 1
  fi
  sleep 0.5
done

echo "  App ready. Leave this window open."
echo "  To stop the app: Ctrl+C, or close the window."
echo ""
wait $APP_PID
