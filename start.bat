@echo off
chcp 65001 >nul
set PYTHONUTF8=1
rem Set default language (change to en if preferred)
if not defined STUDYPLAN_LANG set "STUDYPLAN_LANG=de"
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv was not found. Install it from https://docs.astral.sh/uv/ and try again.
  pause
  exit /b 2
)
where claude >nul 2>nul
if errorlevel 1 (
  echo Claude Code was not found. Install it from https://code.claude.com/docs and try again.
  pause
  exit /b 2
)
uv sync
if errorlevel 1 pause & exit /b 1
uv run studyplan doctor
if errorlevel 1 pause & exit /b 1

:menu
echo.
echo ======================================================================
echo   Study Planner - Hauptmenue (Main Menu)
echo ======================================================================
echo   [1] Inbox-Ordner oeffnen (Open inbox folder to copy files)
echo   [2] Ablauf anzeigen und in Notepad oeffnen (Show workflow in Notepad)
echo   [3] Claude Code hier starten (Start Claude Code in this folder)
echo   [4] Output-Ordner mit Excel oeffnen (Open output folder)
echo   [5] Excel-Arbeitsmappe jetzt erstellen (Create Excel file now)
echo   [Q] Beenden (Quit)
echo ======================================================================
echo Ihre Wahl (Your choice) [1-5, Q]:
choice /c 12345Q /n
if errorlevel 6 goto opt_quit
if errorlevel 5 goto opt_excel
if errorlevel 4 goto opt_output
if errorlevel 3 goto opt_claude
if errorlevel 2 goto opt_guide
if errorlevel 1 goto opt_inbox
goto menu

:opt_inbox
if not exist "%~dp0my_study\inbox" mkdir "%~dp0my_study\inbox"
explorer "%~dp0my_study\inbox"
goto menu

:opt_guide
if not exist "%~dp0my_study" mkdir "%~dp0my_study"
uv run studyplan guide --output "%~dp0my_study\ABLAUF.txt"
start "" notepad "%~dp0my_study\ABLAUF.txt"
goto menu

:opt_claude
claude
goto menu

:opt_output
if not exist "%~dp0my_study\output" mkdir "%~dp0my_study\output"
explorer "%~dp0my_study\output"
goto menu

:opt_excel
if not exist "%~dp0my_study\profile.yaml" goto opt_excel_missing_profile
uv run studyplan excel
pause
goto menu

:opt_excel_missing_profile
echo Bitte zuerst /setup in Claude Code ausfuehren ^(my_study\profile.yaml fehlt^).
echo Please run /setup in Claude Code first ^(my_study\profile.yaml missing^).
pause
goto menu

:opt_quit
exit /b 0
