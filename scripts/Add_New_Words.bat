@echo off
echo ===========================================
echo   Add New Words to Dataset...
echo ===========================================
cd /d "%~dp0.."
.\.venv\Scripts\python.exe training\add_lstm_word.py
pause
