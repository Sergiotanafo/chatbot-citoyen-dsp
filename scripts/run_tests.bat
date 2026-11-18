@echo off
chcp 65001 >nul
echo ========================================================
echo   CHATBOT CITOYEN DSP - SUITE DE TESTS AUTOMATISES
echo ========================================================

:: Priorite a l'installation Python reelle sur les alias WindowsApps
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
)

set PYTHONPATH=%CD%;%PYTHONPATH%
python -m unittest discover -s tests -p "test_*.py" -v

echo.
if %ERRORLEVEL% EQU 0 (
    echo [SUCCES] Tous les tests unitaires et d'integration sont valides !
) else (
    echo [ERREUR] Certains tests ont echoue.
)
pause
