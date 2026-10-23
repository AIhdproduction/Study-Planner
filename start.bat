@echo off
chcp 65001 >nul
set PYTHONUTF8=1
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
  echo Claude Code was not found. Install it from https://docs.anthropic.com/en/docs/claude-code and try again.
  pause
  exit /b 2
)
uv sync
if errorlevel 1 pause & exit /b 1
uv run studyplan doctor
if errorlevel 1 pause & exit /b 1
claude
