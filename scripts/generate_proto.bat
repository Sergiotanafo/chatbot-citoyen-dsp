@echo off
chcp 65001 >nul
echo ========================================================
echo   GENERATION DES STUBS gRPC POUR LE DSP SERVICE
echo ========================================================

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
)

python -m grpc_tools.protoc -Iproto --python_out=service --grpc_python_out=service proto/dsp_service.proto

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCES] Stubs gRPC generes dans le dossier service/ :
    echo   - service/dsp_service_pb2.py
    echo   - service/dsp_service_pb2_grpc.py
) else (
    echo.
    echo [ERREUR] Echec de la generation. Verifiez que grpcio-tools est installe :
    echo   pip install grpcio grpcio-tools protobuf
)
pause
