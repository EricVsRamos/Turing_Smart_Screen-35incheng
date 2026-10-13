@echo off
echo ==============================================
echo  Compilando TuringGallery.exe (PyInstaller)
echo ==============================================
echo Instalando dependencias caso necessario...
python -m pip install -r requirements.txt

echo.
echo Gerando o executavel...
pyinstaller --noconsole --onefile --name "TuringGallery" --add-data "library;library" --collect-all sv_ttk --collect-all pystray app.py

echo.
echo ==============================================
echo  Concluido! O executavel foi gerado em dist\TuringGallery.exe
echo ==============================================
pause
