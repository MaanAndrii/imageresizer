@echo off
title Compiling EXE

echo Starting the compilation of watermarker.py...
echo This may take a few moments.

pyinstaller --onefile --windowed watermarker.py

echo.
echo =======================================================
echo Compilation complete!
echo Your file 'watermarker.exe' is in the 'dist' folder.
echo =======================================================
echo.
pause