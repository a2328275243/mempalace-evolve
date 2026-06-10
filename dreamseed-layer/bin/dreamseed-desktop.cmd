@echo off
setlocal EnableExtensions
set "APP_ROOT=%~dp0.."
set "LOCAL_ROOT=D:\DreamSeed-Local-Agent"
set "LOG_DIR=%LOCAL_ROOT%\logs"
set "LOG_FILE=%LOG_DIR%\dreamseed-desktop-launch.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul

set "NODE_EXE=D:\clcude\node\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=%APP_ROOT%\node\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=%APP_ROOT%\runtime\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=node"

echo [%date% %time%] launching DreamSeed Desktop>>"%LOG_FILE%"
echo APP_ROOT=%APP_ROOT%>>"%LOG_FILE%"
echo NODE_EXE=%NODE_EXE%>>"%LOG_FILE%"

"%NODE_EXE%" "%APP_ROOT%\scripts\dreamseed_desktop.mjs" %* >>"%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('DreamSeed Desktop failed to start. Log: %LOG_FILE%', 'DreamSeed Desktop') | Out-Null" >nul 2>nul
)
exit /b %EXIT_CODE%
