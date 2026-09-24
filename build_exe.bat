@echo off
rem Build the standalone FastBid.exe GUI application.
rem Requirements: Python 3.12+, pip install -r requirements.txt pyinstaller tzdata
setlocal
cd /d "%~dp0"
py -3 -c "import tkinter"
if errorlevel 1 (
  echo Python with Tcl/Tk is required. Install Python with the Tk option enabled.
  exit /b 1
)
py -3 -m PyInstaller fastbid.spec --noconfirm --distpath dist --workpath build
if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo Done: dist\FastBid.exe
echo Debug build with console:
echo   set FASTBID_CONSOLE=1
echo   py -3 -m PyInstaller fastbid.spec --noconfirm
endlocal
