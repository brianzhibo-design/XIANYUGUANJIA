# Xianyu Guanjia - Agent Deployment Guide

This document is specifically designed for AI Agents (like GitHub Copilot, Gemini Code Assist, or Claude) to understand how to deploy and run this project. All legacy one-click `.bat`/`.sh` scripts have been removed in favor of standard Node.js and Python deployment practices.

## 1. Prerequisites
- **Python:** `3.12` or higher.
- **Node.js:** `v18` or higher (for building the frontend).
- **npm:** or `yarn` / `pnpm`.

## 2. Frontend Build (Required)
The project uses a separated frontend built with React, Vite, and Tailwind. The backend serves the compiled static files from `client/dist`.

```bash
cd client
npm install
npm run build
```
*Note: If `client/dist` does not exist, the backend will return a 404 or an error page when accessing the dashboard.*

## 3. Backend Setup
The backend is a pure Python application using standard library HTTP servers and Asyncio.

```bash
# Return to project root
cd ..

# Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Playwright browsers if slider auto-solve is needed
playwright install chromium
```

## 4. Configuration
The system requires a `.env` file in the root directory. Copy the example file and fill in the necessary keys.

```bash
cp .env.example .env
```

**Key `.env` variables to check:**
- `PORT`: Dashboard port (default: 8080)
- `XIANYU_COOKIE_1`: Essential for connecting to Xianyu.
- `DEEPSEEK_API_KEY` (or other AI keys): For message auto-reply.
- `COOKIE_CLOUD_URL` / `COOKIE_CLOUD_UUID` / `COOKIE_CLOUD_PASSWORD`: For automatic cookie syncing.

## 5. Starting the Service
Start the main backend service. It will automatically load `.env` and serve the API routes and the compiled frontend dashboard.

```bash
python -m src.main
```

The dashboard will be available at `http://localhost:<PORT>` (default `http://localhost:8080`).

## 6. Architecture Note
- **Frontend:** `client/src/`
- **Backend Entry:** `src/main.py` -> `src/dashboard_server.py`
- **Routes:** `src/dashboard/routes/`
- **Legacy God Object:** `src/dashboard/mimic_ops.py` (Contains core business logic, decoupled from the HTTP server).
