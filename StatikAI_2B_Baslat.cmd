@echo off
setlocal
chcp 65001 >nul
title StatikAI - 2B Goruntuden Kiris Cozumu
cd /d "%~dp0"
set "STATIKAI_BEAM_PY="
if exist ".statikai-python.txt" set /p STATIKAI_BEAM_PY=<".statikai-python.txt"
if defined STATIKAI_BEAM_PY if exist "%STATIKAI_BEAM_PY%" goto check
set "STATIKAI_BEAM_PY=%~dp0.venv\Scripts\python.exe"
if exist "%STATIKAI_BEAM_PY%" goto check
where python >nul 2>nul
if errorlevel 1 goto failed
python -m venv .venv
if errorlevel 1 goto failed
:check
"%STATIKAI_BEAM_PY%" -c "import tkinter, torch, rapidocr, onnxruntime, cv2, PIL" >nul 2>nul
if not errorlevel 1 goto run
echo Arastirma ve OCR paketleri kuruluyor...
"%STATIKAI_BEAM_PY%" -m pip install -r requirements.txt -r requirements-ocr.txt
if errorlevel 1 goto failed
:run
"%STATIKAI_BEAM_PY%" -X utf8 statikai_beam_app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Uygulama baslatilamadi. Python 3.11 veya ustu ve Tcl/Tk gereklidir.
echo Yukaridaki hata metnini kontrol edin.
pause
exit /b 1
