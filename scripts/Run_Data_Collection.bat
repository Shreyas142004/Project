@echo off
echo ===========================================
echo   Starting Custom Word Data Collection...
echo ===========================================
cd /d "%~dp0.."
.\.venv\Scripts\python.exe training\collect_lstm_words.py
pause
