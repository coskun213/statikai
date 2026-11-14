@echo off
setlocal
chcp 65001 >nul
title StatikAI - 3B Cerceve Uygulamasi
cd /d "%~dp0"
set "STATIKAI_PY="
if exist ".statikai-python.txt" set /p STATIKAI_PY=<".statikai-python.txt"
if defined STATIKAI_PY if exist "%STATIKAI_PY%" goto check
set "STATIKAI_PY=%~dp0.venv\Scripts\python.exe"
if exist "%STATIKAI_PY%" goto check
where python >nul 2>nul
if errorlevel 1 goto missing_python
echo Ilk kurulum: Python ortami hazirlaniyor...
python -m venv .venv
if errorlevel 1 goto failed
:check
"%STATIKAI_PY%" -c "import tkinter, matplotlib; from Pynite import FEModel3D" >nul 2>nul
if not errorlevel 1 goto run
echo Masaustu uygulamasi icin paketler kuruluyor...
"%STATIKAI_PY%" -m pip install -r requirements-desktop.txt
if errorlevel 1 goto failed
:run
for %%I in ("%STATIKAI_PY%") do set "STATIKAI_PYW=%%~dpIpythonw.exe"
if exist "%STATIKAI_PYW%" (
    start "" "%STATIKAI_PYW%" "%~dp0statikai_desktop.py"
    exit /b 0
)
"%STATIKAI_PY%" -X utf8 statikai_desktop.py
if errorlevel 1 goto failed
exit /b 0
:missing_python
echo Python bulunamadi. Python 3.12 veya 3.13 kurun. Kurulumda Tcl/Tk ve PATH secili olmali.
:failed
echo Baslatma tamamlanamadi. Yukaridaki hata metnini kontrol edin.
pause
exit /b 1
