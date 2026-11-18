@echo off
chcp 65001 >nul
echo ========================================================
echo   DEMARRAGE DU SERVEUR DSP (gRPC PORT 50051)
echo ========================================================

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
)

set PYTHONPATH=%CD%;%PYTHONPATH%
python service/grpc_server.py

pause
