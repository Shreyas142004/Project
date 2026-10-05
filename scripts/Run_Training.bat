@echo off
echo ===========================================
echo   Training the Custom Word Model...
echo ===========================================
cd /d "%~dp0.."
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
.\.venv\Scripts\python.exe training\train_lstm_words.py
pause
