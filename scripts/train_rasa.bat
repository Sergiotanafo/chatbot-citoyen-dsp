@echo off
chcp 65001 >nul
echo ========================================================
echo   CHATBOT CITOYEN MALIEN - ENTRAINEMENT DSP RASA NLU
echo ========================================================

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
)

set PYTHONPATH=%CD%;%PYTHONPATH%

echo [1/2] Validation des donnees Rasa...
rasa data validate --data data/ --domain intelligence/domain.yml

if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Validation echouee. Verifiez la syntaxe des fichiers.
    pause
    exit /b %ERRORLEVEL%
)

echo [2/2] Entrainement du modele...
rasa train --config configs/rasa_config.yml --domain intelligence/domain.yml --data data/ --out models/

echo.
echo Entrainement termine avec succes ! Modele genere dans le dossier models/
pause
