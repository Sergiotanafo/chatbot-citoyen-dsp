@echo off
chcp 65001 >nul
echo ========================================================
echo   CHATBOT CITOYEN MALIEN - EVALUATION DSP NLU
echo ========================================================

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
)

set PYTHONPATH=%CD%;%PYTHONPATH%

echo Evaluation sur le jeu de donnees de test isole...
rasa test nlu --nlu tests/test_nlu.yml --config configs/rasa_config.yml --out results/

echo.
echo Evaluation terminee. Consultez les resultats dans results/
pause
