@echo off
chcp 65001 >nul
echo ========================================================
echo   DEMARRAGE DU MODELE MISTRAL VIA OLLAMA POUR LE DSP
echo ========================================================

where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
    )
)

echo Verification d'Ollama...
ollama --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ATTENTION] Ollama n'est pas installe ou pas dans le PATH.
    echo Telechargez Ollama depuis https://ollama.com si vous souhaitez l'inference locale Mistral.
    echo Note : Le DSP fonctionne deja parfaitement en mode RAG extractif sans Ollama.
    pause
    exit /b 1
)

echo Lancement du modele Mistral (Port 11434)...
echo Appuyez sur Ctrl+C pour arreter.
ollama run mistral
pause
