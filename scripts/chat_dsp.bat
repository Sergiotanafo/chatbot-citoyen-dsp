@echo off
chcp 65001 >nul

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
)

set PYTHONPATH=%CD%;%PYTHONPATH%
python scripts\interactive_chat.py

pause
