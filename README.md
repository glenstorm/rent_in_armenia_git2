Setup (use the project venv)
```
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py setup_db
.\venv\Scripts\python.exe manage.py runserver
```
Open http://127.0.0.1:8000/

Optional first scrape (several minutes):
```
.\venv\Scripts\python.exe manage.py scrape_listings
```
