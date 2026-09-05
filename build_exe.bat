@echo off
setlocal EnableExtensions
cd /d "%~dp0"

py -3.13 -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo Python 3.13 is required for this pinned release build. Install it with the Windows Python Launcher enabled.
  exit /b 1
)

set "BOOTSTRAP_PYTHON=py -3.13"
if not exist ".build-venv-py313\Scripts\python.exe" %BOOTSTRAP_PYTHON% -m venv .build-venv-py313
if errorlevel 1 exit /b 1

set "PYTHON=.build-venv-py313\Scripts\python.exe"
%PYTHON% -m pip install --upgrade pip
if errorlevel 1 exit /b 1
%PYTHON% -m pip install -r requirements.txt -r requirements-build.txt -r requirements-dev.txt
if errorlevel 1 exit /b 1

%PYTHON% -m compileall -q .
if errorlevel 1 exit /b 1
%PYTHON% -m unittest discover -s tests -v
if errorlevel 1 exit /b 1

%PYTHON% -m ruff check core tests reset_admin_password.py
if errorlevel 1 exit /b 1

%PYTHON% -m PyInstaller --noconfirm --clean NetGuard_Professional.spec
if errorlevel 1 exit /b 1

%PYTHON% -m PyInstaller --noconfirm --clean --onefile --console --name NetGuard_Admin_Recovery reset_admin_password.py
if errorlevel 1 exit /b 1

for /f %%V in ('%PYTHON% -c "from core.version import APP_VERSION; print(APP_VERSION)"') do set "APP_VERSION=%%V"
echo Build succeeded: dist\NetGuard_Professional_%APP_VERSION:.=_%.exe
echo Recovery tool: dist\NetGuard_Admin_Recovery.exe
