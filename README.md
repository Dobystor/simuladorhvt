# Haulage Event Simulator

A standalone web application that generates and publishes SmartFlow integration
events (primarily `HaulageVehicleIntegrationEvent`) onto the SmartFlow RabbitMQ
event bus. It fills the gap left by external hardware (reader/WiFi edge gateways)
in test and staging environments, letting an operator drive a complete
`Load → WeighingMachine → Unload` haulage cycle without physical hardware.

The application runs as a single Python process on Linux. A permanent background
Monitor subscribes to the event bus 24/7 and captures every haulage event, so
operators get a post-login summary of everything that happened since their last
session.

## Architecture

- **Backend**: FastAPI + asyncio, `aio-pika` (RabbitMQ), `aiosqlite` (audit DB),
  `httpx` (SmartFlow APIs), `rethinkdb` (weight writes).
- **Frontend**: React + Vite + Zustand + Axios, served as static files from the
  same FastAPI process.
- **Storage**: SQLite for the audit tables (`event_log`, `event_feed`,
  `user_last_seen`). All session state is kept in memory.

See `design.md`, `requirements.md`, and `tasks.md` for the full specification.

## Project layout

```
haulage-event-simulator/
├── backend/            # FastAPI application and services
│   ├── app/            # Application package
│   ├── tests/          # Unit and property-based tests
│   └── requirements.txt
├── frontend/           # React SPA (Vite)
├── config.example.yaml # Template for config.yaml
└── config.yaml         # Operator-edited; not committed (contains secrets)
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and fill in the connection
parameters for each SmartFlow server you want to target. At least one profile is
required; the process refuses to start if the config is missing, malformed, or
empty.

The config path can be overridden with the `SIMULATOR_CONFIG` environment
variable (defaults to `config.yaml` in the working directory).

## Prerequisites

- Python 3.11+ (tested on 3.13)
- Node.js 18+ and pnpm

## Backend setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
cd backend
pytest
```

## Frontend setup

```bash
cd frontend
pnpm install
pnpm run build     # outputs to frontend/dist, served by the backend
# or for development with hot reload against a running backend:
pnpm run dev       # dev server on http://localhost:5173, proxies /api and /ws
```

## Running the application

Build the frontend first (so the SPA is served), then start the backend:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The app is available at http://localhost:8000. The config path can be
overridden with the `SIMULATOR_CONFIG` environment variable and the SQLite file
with `SIMULATOR_DB`.

## Production deployment (Linux, systemd)

The simulator runs as a native systemd service — no Docker required. Scripts
live in `deploy/`.

### First-time install

From the project root on the server (as a user with sudo):

```bash
chmod +x deploy/*.sh
sudo ./deploy/install.sh
```

This will:
1. Install pnpm if missing, create a `haulage` system user
2. Build the frontend
3. Copy the project to `/opt/haulage-event-simulator`
4. Create the Python virtualenv and install dependencies
5. Install and enable the `haulage-simulator` systemd unit

Then edit the config and start the service:

```bash
sudo nano /opt/haulage-event-simulator/config.yaml   # fill in real values
sudo systemctl restart haulage-simulator
sudo systemctl status haulage-simulator
journalctl -u haulage-simulator -f                    # follow logs
```

The app listens on port 8000. Put it behind a reverse proxy (nginx/Caddy) for
TLS if exposing it beyond the local network.

### Configuration overrides

- `APP_DIR` — deployment directory (default `/opt/haulage-event-simulator`)
- `APP_USER` — service user (default `haulage`)
- `SIMULATOR_CONFIG` / `SIMULATOR_DB` — set in the systemd unit

### Updating an existing install

```bash
sudo ./deploy/update.sh
```

This rebuilds the frontend, syncs the backend and SPA, updates dependencies, and
restarts the service. Your `config.yaml` and the SQLite database in `data/` are
preserved.

### Quick manual run (no systemd)

For a fast test without installing the service:

```bash
./deploy/run.sh
```

> **Warning:** publishing events to a real SmartFlow bus triggers business logic
> in Haulages.API (creates haulage records, writes weights to RethinkDB). Always
> point at a staging/test environment first.

## Development status

Full stack implemented per `tasks.md`: FastAPI backend (config, DB, session
store, event constructor, entity/identity/rethinkdb/wrapper services, publisher
and monitor background tasks, all REST routes, WebSocket) and a React SPA
(auth, layout, post-login summary, six simulation panels, event log and live
feed). 63 backend tests pass, including 18 Hypothesis property tests and 7
end-to-end integration tests. The frontend builds cleanly with Vite.
