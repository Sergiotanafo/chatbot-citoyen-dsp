@echo off
chcp 65001 > nul
set "PYTHONIOENCODING=utf-8"
set "Path=C:\Users\HP\AppData\Local\Programs\Python\Python310;C:\Users\HP\AppData\Local\Programs\Python\Python310\Scripts;%Path%"

echo ====================================================================
echo   🇲🇱 CHATBOT CITOYEN MALIEN - SUITE DE RÉGRESSION AUTOMATISÉE 🇲🇱
echo ====================================================================
echo.
python scripts\run_conversation_tests.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCES] Tous les scenarios de conversation sont conformes a 100%% !
) else (
    echo.
    echo [ALERTE] Des regressions conversationnelles ont ete detectees.
)
pause
