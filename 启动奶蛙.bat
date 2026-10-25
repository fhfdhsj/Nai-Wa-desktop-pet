@echo off
cd /d "%~dp0"

python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Installation failed. Please make sure Python is installed.
        pause
        exit /b 1
    )
)

where pythonw >nul 2>&1
if errorlevel 1 (
    start "" python main.py
) else (
    start "" pythonw main.py
)