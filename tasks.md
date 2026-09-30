# Implementation Plan: Haulage Event Simulator

## Overview

Build a standalone Python + React web application that publishes SmartFlow
integration events to RabbitMQ, runs a permanent background Monitor consumer,
and serves the compiled SPA from a single FastAPI process. The backend uses
FastAPI with asyncio, aio-pika, aiosqlite, and httpx; the frontend uses React,
Vite, Zustand, and Axios. All session state is kept in-memory; only the three
audit tables (event_log, event_feed, user_last_seen) touch SQLite.

---

## Tasks

- [x] 1. Project scaffolding
  - [x] 1.1 Create project directory structure and backend package setup
    - Create the full `haulage-event-simulator/` tree: `backend/app/{api,services,background,models,websocket}`, `backend/tests/`, and `frontend/`
    - Write `backend/requirements.txt` pinning: fastapi, uvicorn[standard], aio-pika, aiosqlite, httpx, pydantic, pyyaml, rethinkdb, hypothesis, pytest, pytest-asyncio
    - _Requirements: 17.1, 17.2_

  - [x] 1.2 Implement YAML config loading and ServerProfile validation
    - In `backend/app/config.py`, define a `ServerProfile` Pydantic model and a `SimulatorConfig` root model with a `server_profiles: list[ServerProfile]` field
    - Validate at startup: file exists, parses as valid YAML, at least one profile, all profile names unique, required fields present (`name`, `api_base_url`, `rabbitmq.host/username/password`, `rethinkdb.host`)
    - On any failure, print the file path and reason to stderr and `sys.exit(1)` before any FastAPI app is created
    - _Requirements: 1.1, 1.2, 17.4, 17.7_

  - [x]* 1.3 Write unit tests for config validation
    - Test missing file → startup error; malformed YAML → startup error; zero profiles → startup error; duplicate profile names → startup error; all required fields present → success
    - _Requirements: 1.2, 17.7_

- [x] 2. Database layer
  - [x] 2.1 Implement SQLite schema and migration system
    - In `backend/app/database.py`, implement `init_db()` (called from `lifespan`) using `aiosqlite`
    - Create `schema_version` table; on first run, execute DDL for `event_log`, `event_feed`, `user_last_seen`, and all their indexes exactly as specified in the design
    - Expose async helpers: `insert_event_log(record)`, `insert_event_feed(record)`, `upsert_user_last_seen(username, profile, ts)`, `get_user_last_seen(username, profile) -> datetime | None`
    - _Requirements: 13.4, 15.1, 15.2, 14.1_

  - [x]* 2.2 Write integration tests for database initialization
    - Test that `init_db()` on a fresh `:memory:` DB creates all three tables and all indexes; test that running `init_db()` twice is idempotent (no error, no duplicate tables)
    - _Requirements: 13.4_

- [x] 3. Data models
  - [x] 3.1 Define event payload models
    - In `backend/app/models/event_models.py`, write `HaulageVehicleIntegrationEvent` and `CatalogVehicleOperatorAssignmentEvent` as Python `dataclasses`; include `LocationVehicle` dict schema as a typed dict or dataclass
    - Document each field with its source (session, user input, or system-generated)
    - _Requirements: 7.1, 7.5, 10.1, 10.2, 12.1_

  - [x] 3.2 Define Pydantic API request and response models
    - In `backend/app/models/api_models.py`, write request bodies and response shapes for: `LoginRequest`, `LoginResponse`, `SimulateHaulageRequest`, `SimulateHaulageResponse`, `SimulateLocationUnloadRequest`, `SimulateOperatorAssignRequest`, `EntitiesResponse`, `HistoryLogsResponse`, `HistoryFeedResponse`, `SummaryResponse`, `ProfileInfo`
    - _Requirements: 2.1, 3.1, 7.1, 8.1, 9.1, 10.1, 11.1, 12.1, 13.1, 14.1, 15.1_

  - [x] 3.3 Define DB row models
    - In `backend/app/models/db_models.py`, write `TypedDict` or `dataclass` for `EventLogRow`, `EventFeedRow`, `UserLastSeenRow` matching the SQLite schema column names exactly
    - _Requirements: 13.2, 15.1_

- [x] 4. Session management
  - [x] 4.1 Implement in-memory SessionStore
    - In `backend/app/session_store.py`, define `SessionData` as a `dataclass` with fields: `session_token`, `username`, `profile_name`, `bearer_token`, `event_id_counter: int = 1`, `published_combos: set`, `created_at`; generate tokens with `secrets.token_urlsafe(32)`
    - Implement module-level `_sessions` dict and helper functions: `create_session(...)`, `get_session(token) -> SessionData | None`, `delete_session(token)`
    - Implement a FastAPI dependency `get_current_session(request) -> SessionData` that reads `Authorization: Bearer <token>`, looks up the session, and raises HTTP 401 if missing or invalid
    - _Requirements: 2.2, 2.3, 2.6, 18.5_

- [x] 5. Identity service and authentication routes
  - [x] 5.1 Implement IdentityService
    - In `backend/app/services/identity_service.py`, implement `async def authenticate(profile, username, password) -> str` using `httpx.AsyncClient` with a 10-second timeout
    - Post an OAuth2 password grant to `{profile.api_base_url}/connect/token` (or equivalent Identity.API endpoint)
    - On HTTP 4xx, extract and return `error_description` if present; otherwise return a generic failure string
    - On timeout (`httpx.TimeoutException`), raise a dedicated `AuthTimeoutError`; on connection failure, raise `AuthUnavailableError`
    - _Requirements: 2.1, 2.4, 2.8, 18.4_

  - [x] 5.2 Implement auth API routes and profiles route
    - In `backend/app/api/auth.py`, implement `POST /api/auth/login`: call `IdentityService.authenticate`, create a session, call `upsert_user_last_seen`, return `LoginResponse`; map `AuthTimeoutError` → 408, `AuthUnavailableError` → 503, auth failure → 401
    - Implement `POST /api/auth/logout` (requires `get_current_session`): clear `bearer_token` from `SessionData`, call `delete_session`; return 204
    - In `backend/app/api/profiles.py`, implement `GET /api/profiles`: return list of `ProfileInfo` from the loaded config (no auth required)
    - _Requirements: 1.3, 1.7, 2.1, 2.3, 2.6, 2.7, 2.8_

- [ ] 6. Entity service and entity routes
  - [x] 6.1 Implement EntityService with filter functions
    - In `backend/app/services/entity_service.py`, implement `async def fetch_all_entities(profile, bearer_token)` using `asyncio.gather` to call Catalog.API and Haulages.API concurrently; set a 30-second `httpx` timeout per request; collect per-type errors without aborting other requests
    - Implement the three pure filter functions exactly as defined in the design:
      - `filter_vehicles(vehicles, haulage_vehicle_ids)` — type ∈ {4, 5} AND id in haulage_vehicle_ids
      - `filter_employees(employees)` — at least one tag with non-null, non-empty swarm_id or bluetooth_address
      - `filter_beacons(beacons, haulage_site_ref_ids, weighing_machine_ref_ids)` — reference_point_id in union of both ref id sets
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x]* 6.2 Write property tests for entity filter functions
    - In `backend/tests/test_entity_filters.py`:
      - **Property 1: Vehicle filter correctness** — `filter_vehicles` returns exactly vehicles where type ∈ {4,5} AND id in haulage_vehicle_ids
        - **Validates: Requirements 3.2**
      - **Property 2: Employee filter correctness** — `filter_employees` returns exactly employees with at least one tag having a non-null, non-empty swarm_id or bluetooth_address
        - **Validates: Requirements 3.3**
      - **Property 3: Beacon filter correctness** — `filter_beacons` returns exactly beacons whose reference_point_id appears in the union of haulage_site_ref_ids and weighing_machine_ref_ids
        - **Validates: Requirements 3.4**
    - Use `@given` with `st.lists` of dicts with varied type ints, optional tag strings, and `st.frozensets` of reference ids
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ] 6.3 Implement entity API routes
    - In `backend/app/api/entities.py`, implement `GET /api/entities` (requires auth): call `EntityService.fetch_all_entities` with the session's bearer_token; return `EntitiesResponse` including the `errors` map for any failed entity type
    - Implement `POST /api/entities/reload` (requires auth): same as GET but forces a fresh fetch regardless of any cached state; return same shape
    - _Requirements: 3.1, 3.5, 3.6, 3.7, 3.8_

- [x] 7. Event constructor
  - [x] 7.1 Implement all pure functions in event_constructor.py
    - In `backend/app/services/event_constructor.py`, implement:
      - `resolve_mac(swarm_id, bluetooth_address) -> str | None` — return swarm_id.upper() if present, else bluetooth_address.upper() if present, else None
      - `next_event_id(session: SessionData) -> str` — return `str(session.event_id_counter)` then increment counter
      - `make_dedup_key(date_status, mac_vehicle, status) -> tuple` — `(date_status.strftime("%Y-%m-%d %H:%M:%S"), mac_vehicle.upper(), int(status))`
      - `is_duplicate(session, date_status, mac_vehicle, status) -> bool`
      - `record_published_combo(session, date_status, mac_vehicle, status)` — add key to `session.published_combos`
      - `classify_weighing_result(gross_weight, empty_weight) -> str` — `"net_load"` if `abs(gross - empty) > 2.5` else `"tare_update"`
      - `validate_gross_weight(weight) -> bool` — `0 < weight <= 999.99`
      - `compute_elapsed_time(load_ts, reference_ts) -> tuple[int, int]` — (hours, minutes) truncated
      - `check_18h_rule(load_ts, reference_ts) -> bool` — total seconds > 64800
      - `validate_offline_date_status(date_status, now) -> bool` — strictly before now
    - _Requirements: 4.2, 4.3, 5.1, 5.2, 6.2, 6.3, 6.4, 7.2, 7.3, 7.4, 7.8, 8.2, 8.3, 8.5, 9.3, 9.6_

  - [x]* 7.2 Write property tests for EventId sequencing and string format
    - In `backend/tests/test_event_constructor.py`:
      - **Property 4: EventId counter produces a strict sequence** — n calls to `next_event_id` return exactly `["1","2",...,str(n)]` in order; no skips, no repeats
        - **Validates: Requirements 4.2, 4.4**
      - **Property 5: EventId is serialised as a numeric string** — for any counter value k, return value is a string of digits whose numeric value equals k; when placed in a JSON payload, the field appears as a JSON string not a JSON number
        - **Validates: Requirements 4.3**
    - _Requirements: 4.2, 4.3, 4.4_

  - [x]* 7.3 Write property tests for MAC normalization and mode field correctness
    - In `backend/tests/test_event_constructor.py`:
      - **Property 7: MAC fields are normalised to uppercase** — `resolve_mac` returns uppercase swarm_id if non-empty, else uppercase bluetooth_address if non-empty, else None; MACOperator in constructed event is empty string (not None) when no employee
        - **Validates: Requirements 7.2, 7.3, 7.4, 7.8, 8.2**
      - **Property 8: Online mode sets RealTime and DateStatus correctly** — constructed event has `RealTime == True` and `DateStatus` within a 2-second window of call time
        - **Validates: Requirements 6.2**
      - **Property 9: Offline mode rejects non-past DateStatus** — `validate_offline_date_status(dt, now)` returns False for any dt >= now; returns True for dt < now; constructed event has `RealTime == False` and DateStatus equal to supplied value
        - **Validates: Requirements 6.3, 6.4**
    - _Requirements: 6.2, 6.3, 6.4, 7.2, 7.3, 7.4, 7.8, 8.2_

  - [x]* 7.4 Write property tests for dedup round-trip
    - In `backend/tests/test_dedup.py`:
      - **Property 6: Dedup round-trip prevents duplicate publication** — after `record_published_combo`, `is_duplicate` returns True for the same triple; second call to `record_published_combo` is idempotent; case-insensitive on mac_vehicle (both read and write normalise to uppercase)
        - **Validates: Requirements 5.1, 5.2, 5.4**
    - Use `@given(st.datetimes(), st.text(...), st.integers(0, 4))`
    - _Requirements: 5.1, 5.2, 5.4_

  - [x]* 7.5 Write property tests for weight classification and validation
    - In `backend/tests/test_weight_logic.py`:
      - **Property 10: Weight classification applies the 2.5-tonne threshold** — `classify_weighing_result(g, e)` returns `"net_load"` iff `abs(g - e) > 2.5`; consistent regardless of which operand is larger
        - **Validates: Requirements 9.6**
      - **Property 11: Standard weighing validates weight range** — `validate_gross_weight(w)` returns True iff `0 < w <= 999.99`; all values ≤ 0 and > 999.99 are rejected
        - **Validates: Requirements 9.3**
    - Use `@given(st.floats(min_value=0, max_value=2000, allow_nan=False))` pairs
    - _Requirements: 9.3, 9.6_

  - [x]* 7.6 Write property tests for elapsed time and 18-hour rule
    - In `backend/tests/test_elapsed_time.py`:
      - **Property 12: Elapsed time and 18-hour rule computation** — `compute_elapsed_time(load, ref)` returns `(hours, minutes)` where `hours * 60 + minutes == int((ref - load).total_seconds()) // 60`; `check_18h_rule` returns True iff total seconds > 64800
        - **Validates: Requirements 8.3, 8.5**
    - Use `@given` with datetime pairs where ref >= load
    - _Requirements: 8.3, 8.5_

- [x] 8. Publisher Manager
  - [x] 8.1 Implement PublisherManager with reconnection
    - In `backend/app/background/publisher_manager.py`, implement `PublisherManager` as an asyncio task class per Server_Profile
    - On startup: connect to the profile's RabbitMQ, declare exchange `smartflow_event_bus` (direct, durable)
    - `async def publish(payload: dict, routing_key: str)`: serialise to JSON, create a persistent `aio_pika.Message`, publish to the exchange; wrap in a 10-second asyncio timeout — raise `PublishError` on timeout or no connection
    - On connection drop: exponential backoff reconnection (start 2 s, double each attempt, cap at 60 s); broadcast `connection_status` WebSocket message on each state change
    - _Requirements: 7.1, 8.1, 10.2, 12.2, 16.1, 16.3, 16.5, 16.6_

- [x] 9. Monitor
  - [x] 9.1 Implement Monitor consumer with reconnection
    - In `backend/app/background/monitor.py`, implement `Monitor` as an asyncio task class per Server_Profile
    - Declare durable queue `smartflow_simulator_{sanitized_profile_name}`, bind to `smartflow_event_bus` exchange with routing key `HaulageVehicleIntegrationEvent`
    - For each message: parse JSON, check `is_simulated` by querying event_log for the message's `Id` within a 5-second window, INSERT into event_feed — `basic_ack` only after successful INSERT; on INSERT failure, `basic_nack(requeue=True)`
    - Broadcast `{ "type": "event_feed", "data": record }` to all connected WebSocket clients for this profile after successful persist
    - Exponential backoff reconnection (2 s → 60 s cap); log each attempt with timestamp and outcome; broadcast `connection_status` changes via WebSocket
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 16.1, 16.2, 16.3, 16.4_

- [x] 22. Checkpoint 1 — Core backend services complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. RethinkDB and Wrapper services
  - [ ] 10.1 Implement RethinkDBService
    - In `backend/app/services/rethinkdb_service.py`, implement `async def write_weighing_machine_weight(profile, rethinkdb_id, gross_weight_tonnes)` using the `rethinkdb` async driver
    - Connect per call using `profile.rethinkdb.host/port`; run `r.table("WeighingMachine").get(rethinkdb_id).update({"weight": gross_weight_tonnes})`; close connection after
    - Raise `RethinkDBWriteError` on any failure; the caller uses this to abort event publication
    - _Requirements: 9.4, 9.9_

  - [x] 10.2 Implement WrapperService
    - In `backend/app/services/wrapper_service.py`, implement `async def post_location_unload(profile, bearer_token, vehicle_id, reference_point_id)` using `httpx.AsyncClient`
    - POST to `{profile.api_base_url}/api/v1/Location/` with `Authorization: Bearer {bearer_token}` and body `{"VehicleId": vehicle_id, "ReferencePointId": reference_point_id, "IsUsedLocation": True}`
    - On non-2xx response, raise `WrapperAPIError` containing the response body; on timeout, raise `WrapperAPIError` with timeout message
    - _Requirements: 11.2, 11.3, 11.4_

- [x] 11. Simulate API routes
  - [x] 11.1 Implement POST /api/simulate/haulage
    - In `backend/app/api/simulate.py`, implement the haulage route covering all five event types: Load (Status=1), Unload (Status=2), WeighingMachine (Status=0), InTransit (Status=3), Stop (Status=4)
    - Validate request: required fields present; vehicle has a resolvable MAC; for Offline mode, DateStatus is strictly in the past; for Standard weighing, gross_weight is in range
    - Run dedup check via `is_duplicate`; return 409 if duplicate
    - For Standard weighing: call `RethinkDBService.write_weighing_machine_weight` first; on `RethinkDBWriteError` return 500 without publishing
    - Call `PublisherManager.publish`; on `PublishError` return 503 without writing event_log
    - On success: call `record_published_combo`, INSERT event_log row, return 200 with event_log_id, event_id, published_at
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 7.1–7.9, 8.1–8.7, 9.1–9.10, 10.1–10.5_

  - [x] 11.2 Implement POST /api/simulate/location-unload
    - In `backend/app/api/simulate.py`, implement the location-unload route
    - Call `WrapperService.post_location_unload`; on `WrapperAPIError` return 502 with detail, do NOT write event_log
    - On success: INSERT event_log row with event_type="LocationBasedUnload", vehicle_id, haulage_site_id, published_at; return 200
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 11.3 Implement POST /api/simulate/operator-assign
    - In `backend/app/api/simulate.py`, implement the operator-assign route
    - Validate that both mac_vehicle and mac_operator are non-empty; return 400 if either is absent
    - Call `PublisherManager.publish` with routing key `CatalogVehicleOperatorAssignmentEvent`; on `PublishError` return 503 without writing event_log
    - On success: INSERT event_log row with event_type="OperatorAssignment"; return 200
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 12. History and summary API routes
  - [x] 12.1 Implement history routes with filter and pagination
    - In `backend/app/api/history.py`, implement query helper functions: `filter_event_log(records, username, mac_vehicle, from_dt, to_dt, event_type)` and `filter_event_feed(records, profile_name, mac_vehicle, from_dt, to_dt)` as pure list-filtering functions
    - Implement default reverse-chronological sort helper
    - Implement `paginate(records, page, page_size=100) -> (page_records, total)`
    - Wire these into `GET /api/history/logs` and `GET /api/history/feed` (no auth required); apply filters from query params, sort, paginate, return `HistoryLogsResponse` / `HistoryFeedResponse`
    - _Requirements: 15.3, 15.4, 15.5, 15.6_

  - [x]* 12.2 Write property tests for event_log query functions
    - In `backend/tests/test_log_queries.py`:
      - **Property 13: Event_log records contain all required fields** — any event_log row produced by a successful publication has non-null, non-empty published_at, username, server_profile, event_type, payload; username equals the session username
        - **Validates: Requirements 2.7, 15.1**
      - **Property 14: Event_log filter returns only matching records** — `filter_event_log` with any combination of active filters returns exactly the subset satisfying all active (non-null) filters
        - **Validates: Requirements 15.3**
      - **Property 15: Event_log default order is reverse chronological** — default sort produces `records[i].published_at >= records[i+1].published_at` for all adjacent pairs
        - **Validates: Requirements 15.4**
      - **Property 16: Pagination invariant** — for N records and page_size 100: `ceil(N/100)` pages; each page ≤ 100 records; concatenation equals original; no record in more than one page; total field equals N
        - **Validates: Requirements 15.5**
    - _Requirements: 2.7, 15.1, 15.3, 15.4, 15.5_

  - [x] 12.3 Implement post-login summary route
    - In `backend/app/api/summary.py`, implement pure helper functions: `get_events_since(records, last_seen) -> list` (strictly greater than last_seen), `group_by_mac_vehicle(records) -> list[group]` (each group = mac_vehicle + its events, groups ordered by mac_vehicle ascending)
    - Wire into `GET /api/summary` (requires auth): look up `user_last_seen` for the session's username and profile; if no row, use 24-hour window; retrieve event_feed records in that window; call helpers; return `SummaryResponse`
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x]* 12.4 Write property tests for summary time window and grouping
    - In `backend/tests/test_log_queries.py`:
      - **Property 17: Login summary retrieves only events after last_seen** — `get_events_since(records, last_seen)` returns exactly records where received_at > last_seen; records with received_at == last_seen are excluded
        - **Validates: Requirements 14.2**
      - **Property 18: Login summary groups and orders by MACVehicle ascending** — `group_by_mac_vehicle(records)` places every record in exactly one group; each group key equals the mac_vehicle of its members; group keys are in ascending lexicographic order
        - **Validates: Requirements 14.3**
    - _Requirements: 14.2, 14.3_

- [x] 13. WebSocket layer
  - [x] 13.1 Implement WebSocket manager
    - In `backend/app/websocket/manager.py`, implement a module-level `_connections: dict[str, set[WebSocket]]` registry keyed by profile_name
    - Implement `async def broadcast(profile_name, message: dict)` — `send_json` to all connected sockets for that profile, catching and discarding stale connections
    - Implement `connect(ws, profile_name)`, `disconnect(ws, profile_name)` helpers
    - _Requirements: 13.2, 16.4_

  - [x] 13.2 Implement /ws WebSocket endpoint
    - In `backend/app/websocket/manager.py` or a dedicated route, implement the `/ws?token=<session_token>` endpoint
    - Validate the token using `get_session`; close with code 4001 if invalid
    - On connect: call `connect(ws, session.profile_name)`, then push the current connection status for all profiles as `connection_status` messages
    - Run a receive loop; on disconnect (any exception or normal close), call `disconnect(ws, session.profile_name)`
    - _Requirements: 1.4, 16.4_

- [x] 14. FastAPI application wiring
  - [x] 14.1 Implement FastAPI app factory with lifespan and static file serving
    - In `backend/app/main.py`, implement `lifespan`: call `load_config()` (exits on failure), `await init_db()`, then `asyncio.create_task(run_monitor(profile))` and `asyncio.create_task(run_publisher_manager(profile))` for every profile in the config; on shutdown, cancel all tasks and close connections
    - Register all routers with their prefixes: `/api/auth`, `/api` (profiles), `/api` (entities), `/api/simulate`, `/api/history`, `/api/summary`
    - Add the WebSocket route at `/ws`
    - Mount `StaticFiles(directory="frontend/dist", html=True)` at `/` — **after** all API routes so API routes take precedence
    - _Requirements: 1.1, 13.1, 17.1, 17.2, 17.3_

- [x] 23. Checkpoint 2 — Full backend wiring complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Frontend project setup
  - [x] 15.1 Initialize Vite + React project
    - Create `frontend/` with `package.json` specifying React 18, Vite, Zustand, Axios, React Router v6, and DevExtreme (confirm with user before adding DevExtreme; use plain HTML table as fallback)
    - Write `vite.config.js` with a dev proxy forwarding `/api` and `/ws` to `http://localhost:8000` so the dev server works without CORS issues
    - Create `frontend/src/main.jsx` and `frontend/src/App.jsx` as empty entry points
    - _Requirements: 17.1, 17.2_

  - [x] 15.2 Implement Zustand store
    - In `frontend/src/store/appStore.js`, implement the full store with slices as defined in the design: auth (session, profiles, selectedProfileName), connectionStatus per profile, entities (vehicles, employees, beacons, haulageSites, weighingMachines, loading, errors), simulationForm (selectedVehicle, selectedBeacon, selectedEmployee, simulationMode, dateStatusInput), eventFeed (capped at 500 entries)
    - Expose actions: setSession, clearSession, setProfiles, setConnectionStatus, setEntities, setEntitiesLoading, setEntitiesErrors, setSimulationFormField, appendFeedEvent
    - _Requirements: 1.3, 1.6, 3.5, 3.6_

  - [x] 15.3 Implement API client and WebSocket client
    - In `frontend/src/services/apiClient.js`, create an Axios instance with `baseURL="/api"` and a request interceptor attaching `Authorization: Bearer {token}` from the store; add a response interceptor that catches 401 responses, calls `clearSession()`, and redirects to `/login`
    - In `frontend/src/services/wsClient.js`, wrap native WebSocket with a 3-second reconnect loop; dispatch incoming messages to the store: `event_feed` → `appendFeedEvent`, `connection_status` → `setConnectionStatus`, `session_expired` → `clearSession` + redirect
    - _Requirements: 2.5, 13.2, 16.4_

- [x] 16. Auth and layout frontend components
  - [x] 16.1 Implement ProfileSelector, LoginForm, and LoginPage
    - `ProfileSelector` fetches `GET /api/profiles` on mount and renders the list as radio buttons or a select; stores the selected profile name in the Zustand store
    - `LoginForm` has username and password fields; on submit calls `POST /api/auth/login`, stores the returned session token, and redirects to `/summary`; displays API error messages inline
    - `LoginPage` composes both components
    - _Requirements: 1.3, 2.1, 2.4, 2.8_

  - [x] 16.2 Implement AppShell, ConnectionStatusBar, and SessionHeader layout components
    - `ConnectionStatusBar` reads `connectionStatus` from the store and renders one badge per profile showing connected/disconnected/reconnecting; shows the retry interval when reconnecting
    - `SessionHeader` shows the current username and a Logout button; logout calls `POST /api/auth/logout` then `clearSession()`
    - `AppShell` wraps both bars above a `<Outlet />` for nested routes
    - _Requirements: 1.4, 2.6, 16.4_

- [x] 17. Post-login summary page
  - [x] 17.1 Implement PostLoginSummary page
    - Fetch `GET /api/summary` on mount; display the `since` timestamp
    - Render one card per group in `groups`, keyed by mac_vehicle (ascending as returned by the API); each card lists its events with received_at, Status int, mac_beacon, and an is_simulated badge
    - Include a "Simulate" link per group that prefills the vehicle in the simulate form
    - Display an empty-state message when `groups` is empty
    - _Requirements: 14.2, 14.3, 14.4, 14.5_

- [x] 18. Simulate page components
  - [x] 18.1 Implement SimulatePage shell, ModeSelector, and EntitySelectors
    - `SimulatePage` hosts the tab container (Load, Unload, WeighingMachine, InTransit/Stop, LocationUnload, OperatorAssign) and dispatches the per-tab API call on Publish
    - `ModeSelector` renders Online/Offline toggle; when Offline is selected, show a DateStatus datetime-local input and keep it disabled in Online mode; validate that DateStatus is strictly in the past before enabling the Publish button
    - `EntitySelectors` renders three dropdowns (Vehicle, Beacon filtered by active tab type, Employee); fetches `GET /api/entities` if not already loaded; shows per-type error inline with a Reload button
    - Disable the Publish button until both a Mode and the required entities for the active tab are selected
    - _Requirements: 3.5, 3.6, 3.7, 6.1, 6.5_

  - [x] 18.2 Implement LoadPanel and UnloadPanel
    - `LoadPanel`: compose EntitySelectors (Beacon filtered to Load-type HaulageSites) and emit `POST /api/simulate/haulage` with `event_type="Load"`; display 409 duplicate warning inline
    - `UnloadPanel`: compose EntitySelectors (Beacon filtered to Unload-type HaulageSites); after vehicle selection, fetch most recent Load from event_log and display elapsed time chip (hh:mm); show 18-hour warning banner if elapsed > 18 h; show "no prior Load found" notice if no Load record; emit `POST /api/simulate/haulage` with `event_type="Unload"`
    - _Requirements: 7.1–7.9, 8.1–8.7_

  - [x] 18.3 Implement WeighingPanel
    - Render a Standard / SimulatedEnabled radio selector; in Standard mode, show a number input (0 < value ≤ 999.99) with client-side validation
    - When the vehicle has an EmptyWeight and a weight is entered, compute and display the net_load / tare_update classification badge (abs(entered - emptyWeight) > 2.5)
    - Suppress the classification badge and show "EmptyWeight unavailable" if the vehicle has no EmptyWeight
    - Emit `POST /api/simulate/haulage` with `event_type="WeighingMachine"`, `weighing_mode`, and `gross_weight`
    - _Requirements: 9.1–9.10_

  - [x] 18.4 Implement InTransitStopPanel, LocationUnloadPanel, and OperatorAssignPanel
    - `InTransitStopPanel`: two buttons (InTransit, Stop); emit the matching event_type; show vehicle-missing error if no vehicle selected
    - `LocationUnloadPanel`: vehicle (type 4/5) + Unload-type HaulageSite selects; emit `POST /api/simulate/location-unload`; show Wrapper.API error inline
    - `OperatorAssignPanel`: vehicle + employee selects; emit `POST /api/simulate/operator-assign`; show missing-MAC error if either MAC is absent
    - All panels show a success notification with event_log_id on 200 and an error notification on non-200
    - _Requirements: 10.1–10.5, 11.1–11.5, 12.1–12.5_

- [x] 19. History frontend pages
  - [x] 19.1 Implement EventLogPage
    - `FilterBar`: username text input, mac_vehicle text input, from/to datetime-local inputs, event_type select; call `GET /api/history/logs` with active filters on change (debounced 300 ms)
    - `LogTable`: paginated table showing all columns from `HistoryLogsResponse.records`; "Total: N records" + Previous/Next navigation; display empty-state message when no records match
    - _Requirements: 15.3, 15.4, 15.5, 15.6_

  - [x] 19.2 Implement EventFeedPage
    - `FeedTable`: reads `eventFeed` from the Zustand store (populated by `wsClient` via WebSocket pushes); renders rows in insertion order (newest at top); display mac_vehicle, status, received_at, server_profile, is_simulated badge, raw_payload expandable row
    - Show a "Disconnected — reconnecting…" banner when the profile's connection_status is not "connected"
    - _Requirements: 13.1, 13.2, 13.3, 16.4_

- [x] 20. Frontend routing and integration
  - [x] 20.1 Wire React Router and App integration
    - In `App.jsx`, set up React Router v6 routes: `/login` → LoginPage (public), all others wrapped in an auth-guard that redirects to `/login` if no session; `/summary`, `/simulate`, `/history/log`, `/history/feed` inside the AppShell layout
    - Initialize `wsClient` after login (connect with the session token) and disconnect on logout
    - Ensure the 401 redirect from `apiClient.js` integrates cleanly with the router (no double redirects)
    - _Requirements: 2.5, 1.7_

- [x] 24. Checkpoint 3 — Full stack integration complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 21. Configuration and deployment docs
  - [x] 21.1 Create config.example.yaml and README.md
    - Write `config.example.yaml` with two example profiles (Production, Staging), every supported field with inline comments explaining each, and a note that secrets should never be committed
    - Write `README.md` covering: prerequisites (Python 3.11+, Node 18+), installation steps (`pip install -r requirements.txt`, `npm install && npm run build`), configuration (`cp config.example.yaml config.yaml` and field guide), startup command (`uvicorn app.main:app --host 0.0.0.0 --port 8000`), and a note on running tests (`pytest backend/tests/`)
    - _Requirements: 17.1, 17.2, 17.4_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster initial delivery; they validate correctness properties and should be completed before any production deployment
- Each task references the specific requirements it satisfies for traceability
- The dedup key format (`date_status.strftime("%Y-%m-%d %H:%M:%S") + mac_vehicle.upper() + str(status)`) must match Haulages.API's SHA-256 input exactly — any deviation silently breaks dedup
- RethinkDB write MUST precede the RabbitMQ publish for Standard weighing mode; reverting this order will cause a race condition in Haulages.API
- Session state (bearer_token, event_id_counter, published_combos) must never be written to SQLite — it lives exclusively in the in-memory `_sessions` dict
- The Monitor must `basic_nack(requeue=True)` on DB persist failure; `basic_ack` only after a confirmed INSERT
- All three filter functions (filter_vehicles, filter_employees, filter_beacons) are pure; keep them free of any I/O so the property tests can exercise them without mocking

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "3.1", "3.3", "15.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "3.2", "15.2", "15.3"] },
    { "id": 2, "tasks": ["4.1", "5.1", "6.1", "8.1", "10.1", "10.2", "16.1", "16.2"] },
    { "id": 3, "tasks": ["5.2", "6.2", "6.3", "7.1", "13.1", "17.1"] },
    { "id": 4, "tasks": ["1.3", "2.2", "7.2", "7.4", "7.5", "7.6", "9.1", "13.2", "18.1", "19.1", "19.2"] },
    { "id": 5, "tasks": ["7.3", "11.1", "12.1", "12.3", "18.2", "18.3", "18.4"] },
    { "id": 6, "tasks": ["11.2", "12.2", "20.1"] },
    { "id": 7, "tasks": ["11.3", "12.4"] },
    { "id": 8, "tasks": ["14.1", "21.1"] }
  ]
}
```
