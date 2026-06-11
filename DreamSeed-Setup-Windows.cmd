@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "LOCAL_SCRIPT=%SCRIPT_DIR%DreamSeed-Setup-Windows.ps1"
set "TMP_SCRIPT=%TEMP%\DreamSeed-Setup-Windows.ps1"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL%" set "POWERSHELL=powershell.exe"

if exist "%LOCAL_SCRIPT%" (
  "%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%LOCAL_SCRIPT%" %*
  exit /b %ERRORLEVEL%
)

echo Downloading DreamSeed installer...
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/a2328275243/mempalace-evolve/master/DreamSeed-Setup-Windows.ps1' -OutFile '%TMP_SCRIPT%'"
if errorlevel 1 exit /b %ERRORLEVEL%

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%TMP_SCRIPT%" %*
exit /b %ERRORLEVEL%
