@echo off
setlocal
chcp 65001 >nul
title StatikAI - Sembol Tespit Demosu
cd /d "%~dp0"
set "STATIKAI_PY="
if exist ".statikai-python.txt" set /p STATIKAI_PY=<".statikai-python.txt"
if defined STATIKAI_PY if exist "%STATIKAI_PY%" goto run
set "STATIKAI_PY=%~dp0.venv\Scripts\python.exe"
if exist "%STATIKAI_PY%" goto run
echo Ilk kurulum yapiliyor. Bu islem birkac dakika surebilir.
where python >nul 2>nul
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed
"%STATIKAI_PY%" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
"%STATIKAI_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
if "%~1"=="" (
    "%STATIKAI_PY%" -X utf8 demo_baslat.py --output-dir "%~dp0.."
) else (
    "%STATIKAI_PY%" -X utf8 demo_baslat.py --image "%~1" --output-dir "%~dp0.."
)
if errorlevel 1 goto failed
echo.
echo Islem tamamlandi. Sonuc goruntusu acildi.
timeout /t 5 /nobreak >nul
exit /b 0
:missing_python
echo Python bulunamadi. Bu pencerenin ekranini veya hata metnini paylasin.
goto failed
:failed
echo.
echo Baslatma tamamlanamadi. Yukaridaki hata metnini paylasin.
pause
exit /b 1
