EDUSPHERE LMS - FINAL PROJECT

Open the ecms folder in VS Code, not the outer projectPy27 folder.

Correct folder:
projectPy27\ecms

Quick start on Windows:
1) Double-click start_windows.bat
OR run in VS Code Terminal:
   python -m venv venv
   venv\Scripts\activate
   python -m pip install -r requirements.txt
   python run.py

Open in browser:
http://127.0.0.1:5000/

Database files:
- instance\ecms.db (SQLite database used by the application)
- database.sql (SQL export for submission/documentation)

Do not delete the instance or uploads folders if you want to preserve data and uploaded files.
