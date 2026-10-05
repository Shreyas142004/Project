@echo off
echo ===========================================
echo   PHASE 1: Robust Dataset Download
echo ===========================================
cd /d "%~dp0.."
.\.venv\Scripts\python.exe training\download_include.py

echo ===========================================
echo   PHASE 2: LSTM Model Training
echo ===========================================
.\.venv\Scripts\python.exe training\train_include_lstm.py

echo ===========================================
echo   ALL TASKS COMPLETED SUCCESSFULLY!
echo ===========================================
pause
