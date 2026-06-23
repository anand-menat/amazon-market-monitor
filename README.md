# Amazon Competitor Automation Platform

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D.svg)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)

A powerful platform for Amazon product monitoring, competitor discovery, scheduled scraping jobs, price history, and LLM-assisted market analysis.

## Why This Project Matters

This platform provides a complete workflow to connect messy external data sources, run repeatable workflows, expose internal APIs, and provide a simple dashboard to monitor results:

- Scrape Amazon product data through ScraperAPI.
- Normalize inconsistent marketplace responses into one product schema.
- Store products, competitors, price snapshots, jobs, and run history.
- Run scraping manually, from an API, from a CLI script, or on an interval schedule.
- Review products, competitors, automation status, and price history from a Vue dashboard.
- Generate optional LLM recommendations using a DeepSeek/OpenAI-compatible client.

## Architecture

```text
Vue dashboard
    |
    | /api
    v
FastAPI backend
    |
    |-- ScraperAPI client
    |-- APScheduler jobs
    |-- TinyDB local persistence
    |-- CLI automation runner
    |-- Optional LLM analysis
```

## What It Demonstrates

- Python automation with scheduled and on-demand jobs
- FastAPI API design with typed Pydantic request/response models
- Web scraping integration with retries and fallback parsing
- Persistent job history and price snapshots
- Vue 3 operational dashboard
- Logging for scraper requests, job runs, and failures
- Pytest coverage for scraper parsing, service logic, and API health
- Docker Compose setup for repeatable local deployment
- GitHub Actions CI for backend tests and frontend builds

## Project Structure

```text
backend/
  main.py
  requirements.txt
  pytest.ini
  src/
    automation.py
    db.py
    llm.py
    logging_config.py
    models.py
    scraper_client.py
    services.py
  scripts/
    run_scrape_job.py
  tests/
frontend/
  src/
    components/
    services/
  Dockerfile
  nginx.conf
.github/workflows/ci.yml
docker-compose.yml
```

## Configuration

Create `backend/.env` from the example:

```bash
copy .env.example backend\.env
```

Then set:

```env
SCRAPERAPI_KEY=your_scraperapi_key
DEEPSEEK_API_KEY=optional_deepseek_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
APP_API_KEY=your_secret_api_key_for_auth
LOG_LEVEL=INFO
```

`SCRAPERAPI_KEY` is required for live scraping. `DEEPSEEK_API_KEY` is only required for the analysis endpoint. 
`APP_API_KEY` is optional; if set, it enforces `X-API-Key` authentication on all endpoints.

## Run Locally

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

WSL or OneDrive folders may crash Uvicorn's reload file watcher. If that happens, use the no-reload helper:

```bash
cd backend
python scripts/run_server.py
```

If you still want auto-reload, try the polling dev helper:

```bash
cd backend
python scripts/run_dev_server.py
```

Or run Uvicorn with polling enabled:

```bash
cd backend
WATCHFILES_FORCE_POLLING=true uvicorn main:app --reload --reload-exclude ".pytest_cache/*" --reload-exclude "__pycache__/*"
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:5173`

## Run With Docker

```bash
docker compose up --build
```

Open the dashboard at `http://localhost:5173`.

The backend stores local data at `/app/data/data.json` inside the backend container volume.

## CLI Automation

Run a one-off scrape job:

```bash
cd backend
python scripts/run_scrape_job.py --asin B0CX23VSAS --domain com --country us --with-competitors
```

This script can be called from Windows Task Scheduler, cron, GitHub Actions, or another automation runner.

## Verification

Backend:

```bash
cd backend
pytest
python -m compileall .
```

Frontend:

```bash
cd frontend
npm run build
```

CI runs the same backend and frontend checks through GitHub Actions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to run tests, add features, and submit pull requests.

## Good Next Enhancements

- Move from TinyDB to SQLite or PostgreSQL with SQLAlchemy.
- Add Slack or email alerts when competitor prices drop.
- Add Playwright UI tests for the dashboard workflow.
- Add authentication for shared/team use.
- Add charts for price trend comparison across competitors.
