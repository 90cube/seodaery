@echo off
echo === 서대리 데스크톱 클라이언트 빌드 ===
pip install pyinstaller
pyinstaller --onefile --windowed --name "서대리" --icon=icon.ico main.py
echo 빌드 완료: dist\서대리.exe
pause
