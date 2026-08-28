@echo off
REM Starts the Invoice app.
REM Double-click and go: it opens the browser by itself.
REM
REM This is the Windows twin of "Start Invoice.command". The two do the same
REM job in two languages, so they can drift apart without anyone noticing:
REM that is why the hard parts (is the environment sound, has the program
REM changed since it started, is the app answering, did we already check for
REM updates today) are NOT written twice. They live in core\launcher.py and
REM both launchers ask it. A check inside the app compares the two files and
REM complains if one learns something the other does not know.
setlocal
cd /d "%~dp0"

set "PORT=8471"
set "URL=http://127.0.0.1:%PORT%"
REM the app reads the port from here, so changing it in one place really is
REM enough (if 8471 were taken by something else, change this line and go)
set "INVOICE_PORT=%PORT%"
set "VPY=venv\Scripts\python.exe"

REM --- 0. Python: the one thing Windows does not bring by itself ---
REM "py" is the launcher that python.org installs; "python" is what the
REM Microsoft Store gives you. If neither answers there is no point going on:
REM better to say where to get it than to fail five lines later with a
REM message nobody can read.
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo.
  echo   Python is not installed, and the app is written in Python.
  echo   Get it from https://www.python.org/downloads/ and tick
  echo   "Add python.exe to PATH" while installing. Then double-click
  echo   this file again.
  echo.
  pause
  exit /b 1
)

REM --- 1. Python environment: check it is sound, otherwise (re)build it ---
REM The list of libraries lives in requirements.txt and nowhere else: add one
REM and venv\.requirements no longer matches, so the environment rebuilds
REM itself.
call :venv_ok
if not errorlevel 1 goto :environment_ready
call :build_environment
if errorlevel 1 (
  echo.
  echo   The environment could not be built. Are you online?
  echo.
  pause
  exit /b 1
)
:environment_ready

REM --- 1b. is there a new version of the program? ---
REM This only works if this copy came from a repository: whoever received the
REM folder as a zip has no .git and nothing happens here, the app just starts.
REM It never updates behind your back: it shows what changed and asks
REM permission. Your DATA is not involved: database, invoices, statements,
REM backups and logo all live outside the repository (see .gitignore), so the
REM update does not even see them.
call :check_for_updates

REM --- 2. is a HEALTHY app already on the port? ---
REM Yes, but only if it is also UP TO DATE. The pages stay in memory from when
REM the app started: if the program was modified afterwards, the one running
REM is the old version, and reopening the browser would show nothing new.
"%VPY%" -m core.launcher in-salute "%URL%"
if errorlevel 1 goto :clear_the_port
"%VPY%" -m core.launcher aggiornato "%PORT%"
if errorlevel 1 goto :restart_it
start "" "%URL%"
exit /b 0

:restart_it
echo   The program has been updated: restarting the app...
call :kill_port
goto :launch

REM --- 3. is something broken stuck on the port? close it and start clean ---
:clear_the_port
netstat -ano -p tcp | findstr /c:"LISTENING" | findstr /c:":%PORT% " >nul 2>&1
if errorlevel 1 goto :launch
echo Found a stuck instance: closing it and restarting clean...
call :kill_port

REM --- 4. start the app, then get out of the way ---
:launch
echo.
echo   Invoice - local app
echo   Starting on %URL% ...
REM pythonw is the Python with no console. Started through "start" it gets a
REM life of its own, so this window can close and the app carries on. That is
REM the whole point: a window you must not close is a window somebody closes,
REM sooner or later, halfway through an invoice. If pythonw is missing - a few
REM installs do not ship it - the ordinary one still works; it just leaves a
REM window behind, which is what happened here every time until now.
set "VPYW=venv\Scripts\pythonw.exe"
if not exist "%VPYW%" set "VPYW=%VPY%"
REM The app opens the browser itself the moment it has taken the port, which
REM is the only place that knows for sure it is up.
set "INVOICE_OPEN_BROWSER=1"
start "" "%VPYW%" app.py

REM Wait for it to answer before letting this window go. Once it closes there
REM is nowhere left to complain: this is the last place able to say that the
REM app never came up at all.
for /l %%i in (1,1,40) do (
  "%VPY%" -m core.launcher in-salute "%URL%" >nul 2>&1
  if not errorlevel 1 goto :running
  REM ping and not timeout: timeout refuses to run when input has been
  REM redirected, and a refusal would send this loop through in an instant
  REM and report a failure that never happened. ping simply waits.
  ping -n 2 127.0.0.1 >nul
)
echo.
echo   The app did not start. What went wrong is written in: data\error.log
echo.
pause
exit /b 1

:running
echo.
echo   App ready. You can close this window now - the app stays open.
echo   To close the app: the power button at the foot of the menu, inside it.
ping -n 5 127.0.0.1 >nul
exit /b 0


REM ===========================================================================
REM   the parts called above
REM ===========================================================================

:venv_ok
if not exist "%VPY%" exit /b 1
"%VPY%" -m core.launcher requisiti-a-posto >nul 2>&1
if errorlevel 1 exit /b 1
"%VPY%" -c "import flask, docx, openpyxl, dateutil, reportlab, pypdf, PIL" >nul 2>&1
exit /b %errorlevel%

:build_environment
echo Setting up the environment (needs internet, 1-2 minutes)...
if exist venv rmdir /s /q venv
%PY% -m venv venv
if errorlevel 1 exit /b 1
"%VPY%" -m pip install --quiet --upgrade pip
"%VPY%" -m pip install --quiet -r requirements.txt
if errorlevel 1 exit /b 1
"%VPY%" -m core.launcher scrivi-impronta
exit /b 0

:check_for_updates
if not exist ".git" exit /b 0
where git >nul 2>&1
if errorlevel 1 exit /b 0
git remote get-url origin >nul 2>&1
if errorlevel 1 exit /b 0
"%VPY%" -m core.launcher controllato-da-poco "data\.last-update-check" 6
if not errorlevel 1 exit /b 0

REM GIT_TERMINAL_PROMPT=0: if the repository asked for a password, git fails
REM straight away instead of holding up the start waiting for someone to type.
REM The two LOW_SPEED lines are the timeout: Windows has no "timeout" for a
REM command, but git can give up by itself on a transfer that is going nowhere.
set "GIT_TERMINAL_PROMPT=0"
set "GIT_HTTP_LOW_SPEED_LIMIT=1000"
set "GIT_HTTP_LOW_SPEED_TIME=10"
<nul set /p "=  Checking for a new version... "
git fetch --quiet origin >nul 2>&1
if errorlevel 1 (
  echo not reachable, never mind.
  exit /b 0
)
echo.
"%VPY%" -m core.launcher tocca "data\.last-update-check"

set "HERE="
set "THERE="
for /f %%h in ('git rev-parse HEAD 2^>nul') do set "HERE=%%h"
for /f %%h in ('git rev-parse origin/HEAD 2^>nul') do set "THERE=%%h"
if not defined THERE for /f %%h in ('git rev-parse origin/main 2^>nul') do set "THERE=%%h"
if not defined HERE exit /b 0
if not defined THERE exit /b 0

call :update_kind "%HERE%" "%THERE%"
if "%KIND%"=="none" exit /b 0
if "%KIND%"=="ahead" exit /b 0
if "%KIND%"=="diverged" goto :say_diverged

echo.
echo   ------ There is a new version of the app -------------------
git log -8 --format="     . %%s" %HERE%..%THERE% 2>nul
echo   ------------------------------------------------------------
call :warn_local_changes
call :ask_and_apply "  Install it?" "%HERE%" "%THERE%"
exit /b 0

:say_diverged
REM The published history was rewritten (old commits replaced by new ones
REM holding the same work). This copy still has the old ones, so "only
REM forwards" would never be true again and the app would quietly stop
REM updating for good. Better to say so and offer to line back up.
echo.
echo   ------ This copy no longer lines up with the published one --
echo      The history was rewritten, so your version and the
echo      published one no longer share the same commits.
echo      Lining up replaces the program files with the published
echo      ones. YOUR DATA IS NOT TOUCHED: database, invoices,
echo      statements and backups live outside the repository.
echo   ------------------------------------------------------------
call :warn_local_changes
call :ask_and_apply "  Line up with the published version?" "%HERE%" "%THERE%"
exit /b 0

REM What separates this copy from the published one. Four answers, because the
REM wrong thing to do differs in each case:
REM   none      same commit: nothing to do
REM   forward   the usual case, a newer version exists
REM   ahead     this copy has work the repository does not: never touch it
REM   diverged  the published history was rewritten: neither contains the other
:update_kind
set "KIND=diverged"
if "%~1"=="%~2" (
  set "KIND=none"
  exit /b 0
)
git merge-base --is-ancestor %~1 %~2 >nul 2>&1
if not errorlevel 1 (
  set "KIND=forward"
  exit /b 0
)
git merge-base --is-ancestor %~2 %~1 >nul 2>&1
if not errorlevel 1 set "KIND=ahead"
exit /b 0

:warn_local_changes
git diff --quiet HEAD >nul 2>&1
if errorlevel 1 (
  echo   WARNING: you have modified some program files. Going ahead will
  echo   lose those changes. ^(Your data is not involved.^)
)
exit /b 0

REM Asks, and if the answer is yes replaces the program files. Backs the data
REM up first, and writes down where we were, so there is always a way back.
REM "choice" and not "set /p" because it can wait a limited time: a window
REM left open by mistake must not hold the app hostage for ever. No answer
REM means no, exactly as on the Mac.
:ask_and_apply
choice /c yn /n /t 120 /d n /m "%~1 [Y = yes, N = not now] "
if errorlevel 2 (
  echo   Not now. I will offer it again next time.
  exit /b 1
)
if exist "%VPY%" (
  "%VPY%" -c "from core import backup; backup.make_backup('prima-aggiornamento')" >nul 2>&1 && echo   Data backup: done.
)
if not exist data mkdir data
>"data\.previous-version" echo %~2
git reset --hard --quiet %~3 >nul 2>&1
if errorlevel 1 (
  echo   It did not go through: starting the version you have.
  exit /b 1
)
echo   Done.
REM if the libraries changed, the environment rebuilds itself here
call :venv_ok
if errorlevel 1 (
  echo   New libraries needed:
  call :build_environment
)
exit /b 0

:kill_port
REM the trailing space matters: without it ":8471" would also catch :84710.
REM And no regular expression on purpose - inside a for/f the ^ is an escape
REM character, so [^0-9] would quietly arrive at findstr as [0-9] and the
REM whole line would match nothing.
for /f "tokens=5" %%p in ('netstat -ano -p tcp ^| findstr /c:"LISTENING" ^| findstr /c:":%PORT% "') do taskkill /f /pid %%p >nul 2>&1
exit /b 0
