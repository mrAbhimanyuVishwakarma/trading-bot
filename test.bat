@echo off
echo Running backtest demo...
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Setting up virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Run the backtest
python backtest.py

echo.
echo Backtest complete. Press any key to exit.
pause >nul