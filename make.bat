CALL venv\Scripts\activate
pyinstaller app.py --add-binary "./interface.ui;./" --add-binary "./settings.yaml;./"