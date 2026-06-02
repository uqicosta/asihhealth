@echo off
cd /d "D:\github-uqicosta\asihhealth"

echo ============================================
echo   ASIHHEALTH - Daily Video Generator
echo ============================================

call .venv\Scripts\activate.bat 2>nul || echo Virtual environment not found, using system Python

python scheduler\daily.py --use-stock

echo.
echo Selesai. Tekan tombol apapun untuk keluar...
pause >nul
