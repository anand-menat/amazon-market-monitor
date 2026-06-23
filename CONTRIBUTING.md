# Contributing to Amazon Competitor Automation

We welcome contributions to this project! Whether you want to fix a bug, add a new feature, or improve the documentation, your help is appreciated.

## Getting Started

1. Fork the repository and clone it to your local machine.
2. Follow the "Run Locally" instructions in the `README.md` to set up your Python and Node.js environments.
3. Ensure you copy `.env.example` to `backend/.env` and add your `SCRAPERAPI_KEY`.

## Development Guidelines

### Backend (Python/FastAPI)

- The backend is written in Python 3.11+.
- We use `pytest` for all backend testing. 
- Please run tests and check code coverage before submitting a pull request:
  ```bash
  cd backend
  pip install -r requirements.txt
  pytest --cov=src --cov-report=term-missing
  ```
- Ensure any new endpoints are protected by the `X-API-Key` dependency when `APP_API_KEY` is set.

### Frontend (Vue 3/Vite)

- The frontend uses Vue 3 Composition API with `<script setup>`.
- We use standard CSS (no Tailwind) to maintain full control over the aesthetic.
- Run the dev server to preview changes:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
- If adding new API endpoints, add the corresponding method to `frontend/src/services/api.js`.

## Submitting a Pull Request

1. Create a new branch for your feature (`git checkout -b feature/your-feature-name`).
2. Make your changes and commit them with a clear, descriptive message.
3. Push to your fork and submit a Pull Request against the `main` branch.
4. Ensure the CI pipeline passes (backend tests and frontend build).

Thank you for contributing!
