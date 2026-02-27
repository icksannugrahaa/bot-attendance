@echo off
:: Pindah ke direktori bot dimana file batch ini berada
cd /d "%~dp0"

:: Cek apakah folder logs sudah ada, kalau belum buat
if not exist "logs" mkdir "logs"

:: Gunakan Python dari venv secara eksplisit
"venv\Scripts\python.exe" automation\runner.py >> logs\cron.log 2>&1
