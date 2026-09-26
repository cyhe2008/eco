@echo off
REM Build single-file exe (install deps first: pip install -r requirements.txt pyinstaller)
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name EcoTank main.py
echo.
echo Done: dist\EcoTank.exe
pause
