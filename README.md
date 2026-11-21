# Rent in Armenia

Django dashboard and scrapers for Armenian real-estate listings from [list.am](https://www.list.am/).

The app collects prices, stores them in SQLite, and shows charts for:

| Market | What it tracks |
|--------|----------------|
| **Yerevan** | Long-term flat rent |
| **Tavush** | House sales |
| **Dilijan** | Long-term rent (apartments and houses) |

Live site (when deployed): [itsfreerealestate.am](https://itsfreerealestate.am)

---

## What you need

- **Python 3.10+** (3.10 is known to work)
- Internet access for the first scrape (list.am)
- Windows, macOS, or Linux

---

## Quick start

### 1. Clone and enter the project

```bash
git clone <this-repo-url>
cd rent_in_armenia_git2
```

### 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in the terminal prompt.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Prepare the databases

Django uses `db.sqlite3` for sessions/admin. Listing data lives in `real_estate.db`.

```bash
python manage.py migrate
python manage.py setup_db
```

`setup_db` creates the listings schema and seeds regions. Safe to re-run; it will not wipe existing listing data unless you pass `--force`.

### 5. Start the web app

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

The first visit may ask you to solve a simple CAPTCHA (bot gate). For local use without it:

```powershell
# Windows PowerShell
$env:BOT_GATE_ENABLED="0"
python manage.py runserver
```

```bash
# macOS / Linux
BOT_GATE_ENABLED=0 python manage.py runserver
```

---

## Load listing data (optional, but useful)

Without a scrape, charts will be empty or outdated. A full scrape can take **several minutes** and should not be run too often — be polite to list.am.

**Everything (Yerevan rent + Tavush houses + Dilijan rent):**

```bash
python manage.py scrape_listings
```

**Only one market:**

```bash
python manage.py scrape_listings --flats-only
python manage.py scrape_listings --houses-only
python manage.py scrape_listings --dilijan-rent-only
```

In local `runserver` (DEBUG on), a weekly scrape scheduler may also run in-process. On a VPS, prefer the systemd timer under `deploy/` and keep `ENABLE_SCRAPE_SCHEDULER=0`.

---

## Useful commands

| Command | Purpose |
|---------|---------|
| `python manage.py runserver` | Start local web UI |
| `python manage.py migrate` | Apply Django DB migrations |
| `python manage.py setup_db` | Create / repair listings DB schema |
| `python manage.py scrape_listings` | Scrape all markets into `real_estate.db` |
| `python manage.py test dashboard.tests` | Run dashboard tests |

On Windows, if the venv is not activated, call the interpreter explicitly:

```powershell
.\venv\Scripts\python.exe manage.py runserver
```

---

## Configuration (optional)

For local development, defaults in `rentweb/settings.py` are enough. Environment variables you may care about:

| Variable | Default (local) | Meaning |
|----------|-----------------|---------|
| `DJANGO_DEBUG` | `1` | Debug mode |
| `DJANGO_SECRET_KEY` | insecure default | Change for any shared/deployed host |
| `BOT_GATE_ENABLED` | `1` | CAPTCHA gate on public pages |
| `ENABLE_SCRAPE_SCHEDULER` | `1` when DEBUG | In-process weekly scrape |

Production example: `deploy/env.example`. Deploy scripts and nginx/systemd units live in `deploy/`.

---

## Project layout (short)

- `dashboard/` — Django views, templates, management commands
- `scraper.py`, `house_scraper.py`, `dilijan_rent_scraper.py` — list.am scrapers
- `real_estate.db` — listings SQLite DB (created locally; not committed)
- `schema.sql` — listings schema
- `rentweb/` — Django project settings

---

## License

[MIT](LICENSE) © 2023–2026 Dmitrii Borisov
