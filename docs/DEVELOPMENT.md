# MiniCommerce — Developer Guide

Day-to-day details for running, testing and operating MiniCommerce. The project overview,
architecture and engineering decisions are in the [README](../README.md).


## Local setup (Windows / PowerShell)

Requires Python 3.12+ and PostgreSQL running locally.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt
copy .env.example .env          # then edit SECRET_KEY / DATABASE_URL
```

Create the database (psql as the postgres superuser):

```sql
CREATE USER minicommerce WITH PASSWORD 'minicommerce' CREATEDB;
CREATE DATABASE minicommerce OWNER minicommerce;
```

Check and run:

```powershell
python manage.py check --database default
python manage.py migrate
python manage.py createsuperuser      # email + password
python manage.py runserver
pytest                                # test DB is created automatically (needs CREATEDB)
```

Health check: <http://127.0.0.1:8000/api/health/>

## Docker

Prerequisites: Docker with Compose v2 (Docker Desktop on Windows/macOS).

```powershell
copy .env.example .env        # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build     # app on http://localhost:4200, API on http://localhost:8000
```

The whole stack (Angular included) is described in [Full Docker Stack](#full-docker-stack).

| Command | Purpose |
|---|---|
| `docker compose up -d` / `docker compose down` | start / stop (data is kept) |
| `docker compose logs -f web` | Gunicorn + Django logs |
| `docker compose ps` | status and health of all five services |
| `docker compose exec web python manage.py migrate` | run Django commands in the container |
| `docker compose exec web python manage.py seed_demo --password <dev-password>` | demo data (never automatic) |
| `docker compose exec web pytest` | test suite (uses `config.settings.test`, test DB in the `db` container) |
| `docker compose down -v` | **also deletes the database volume** |

URLs: [health](http://localhost:8000/api/health/) · [Swagger](http://localhost:8000/api/docs/) ·
[ReDoc](http://localhost:8000/api/redoc/) · [admin](http://localhost:8000/admin/)

- `web` runs the image built from `Dockerfile`: production settings (`DEBUG=False`), Gunicorn,
  static files served by WhiteNoise. On start it applies migrations, then starts Gunicorn.
- PostgreSQL runs in its own `db` container; Django reaches it at host `db` (inside a container
  `localhost` is the container itself). It is not published to the host.
- Database files live in the named volume `postgres_data`: they survive `down`/`up`, not `down -v`.
- `.env` is local configuration: it is git-ignored and excluded from the image (`.dockerignore`).

## Redis (cache)

Compose runs `redis:7-alpine` with no persistence, 128 MB and `volatile-lru` eviction, reachable only
inside the Compose network. DB 1 is the Django cache (`redis://redis:6379/1`); DB 0 is the Celery
broker (see [Background jobs](#background-jobs-celery)). Outside Docker, leave `REDIS_URL` unset to
use an in-process cache, or set it to a local Redis.

- Application code reaches the cache only through Django's cache framework (`django-redis`).
- **DRF throttling** (login/register, 10/min) keeps its counters in that cache, so all Gunicorn
  workers share one limit.
- **`GET /api/categories/`** is cached for 60 s (key `catalog:categories:v1`); any category write
  (API, admin, shell) clears it after commit.
- **PostgreSQL stays authoritative.** Products, stock, carts, orders and payments are never cached.
  Redis can be flushed or restarted at any time; if it is down, reads fall back to PostgreSQL
  and throttling is temporarily off.
- DB 1 = app cache, DB 2 = test suite (`pytest` never clears the app's cache).

```powershell
docker compose ps                     # all services healthy
docker compose logs -f redis
docker compose exec web python manage.py shell -c "from django.core.cache import cache; cache.set('ping','ok',10); print(cache.get('ping'))"
```

## Background jobs (Celery)

Work that shouldn't slow down or break an HTTP request runs in a separate **worker** process.
After a successful checkout, an order-confirmation job is queued; the worker picks it up and
"sends" the confirmation (simulated: a log line with a masked e-mail).

```
POST /api/orders/checkout/ → checkout transaction → COMMIT → transaction.on_commit()
    → send_order_confirmation.delay(order_id) → Redis DB 0 (broker) → worker → task
```

- **Broker**: Redis DB 0 holds queued jobs (DB 1 = cache, DB 2 = tests).
- **`transaction.on_commit()`**: the job is queued only after the order is committed; a
  rolled-back checkout queues nothing, and the worker never sees an order that doesn't exist yet.
- **Idempotent task**: it receives only `order_id`, re-reads the order, and marks
  `confirmation_sent_at` with a conditional UPDATE, so duplicates/retries never notify twice.
- Checkout and payment stay synchronous; only the follow-up notification is background work.
- Without `CELERY_BROKER_URL` (plain `runserver`), tasks run inline after commit — no worker needed.

```powershell
docker compose ps                     # db, redis, web, worker
docker compose logs -f worker         # "Connected to redis://redis:6379/0", task logs
docker compose restart worker
```

ASP.NET Core mapping: task ≈ Hangfire job / queued work item · worker ≈ `BackgroundService`
in a separate process · Redis broker ≈ the job store/queue · `.delay()` ≈ `BackgroundJob.Enqueue()`
· `transaction.on_commit()` ≈ enqueue after `SaveChanges`/commit (the outbox idea, minus the outbox).

## Frontend

Angular 22 app in [`frontend/`](../frontend/) (standalone components, signals, lazy routes,
Reactive Forms, `HttpClient` with one functional interceptor). Django stays at the repository root.

```
Browser
  ↓
Angular (frontend/, :4200 in development)
  ↓ HTTP + JWT  (Authorization: Bearer <access>)
Django REST API (:8000/api)
  ↓
PostgreSQL / Redis
  ↓
Celery worker
```

**Run it** (Node `^22.22.3` or `^24.15`; the API must be running on :8000, e.g. `docker compose up -d`):

```powershell
cd frontend
npm install
npm start        # http://localhost:4200
npm test         # unit tests (Vitest + jsdom)
npm run build    # production build -> dist/minicommerce/browser
```

- **API base URL**: `src/environments/environment.development.ts` → `http://localhost:8000/api`
  (production build: `http://localhost:8000/api` by default, set at build time with
  `--define "MC_API_BASE_URL='…'"` — the Docker build arg `API_BASE_URL`). Services read it through the
  `API_BASE_URL` injection token — no URLs scattered through the code.
- **CORS**: Django allows exactly `http://localhost:4200` / `http://127.0.0.1:4200` in development
  (dev settings and the Compose stack); production allows none (`CORS_ALLOWED_ORIGINS` is empty).
- **Structure**: `core/` (auth, HTTP, guards, theme), `shared/` (API models, UI primitives),
  `layout/` (shell, header), `features/` (auth, catalog, cart, orders — lazy-loaded).
- **Docker**: `frontend/Dockerfile` builds with Node, then serves the static files with
  Nginx (SPA fallback). It runs as the `frontend` service — see [Full Docker Stack](#full-docker-stack).

**Authentication flow**

1. `POST /api/auth/login/` → `{access, refresh}` stored by `TokenStorage`; then `GET /api/auth/me/`.
2. The interceptor adds `Authorization: Bearer <access>` to requests for the API only.
3. On a 401, it calls `POST /api/auth/refresh/` once (shared by concurrent requests) and retries
   the request once; if the refresh fails it logs out and redirects to `/login?returnUrl=…`.
4. `authGuard` protects `/cart` and `/orders`; logout clears the tokens and the cached cart.

**Token storage trade-off**: tokens are kept in `localStorage` so a reload keeps you signed in.
That is fine for a learning project but **not** XSS-proof: any script running on the page can read
them. Production-grade options: keep the access token in memory and put the refresh token in an
`HttpOnly`, `Secure`, `SameSite` cookie set by the backend (requires backend changes), plus a strict
Content-Security-Policy. The choice is isolated in `core/auth/token-storage.ts`.

**Angular ↔ ASP.NET Core**

| Angular | ASP.NET Core |
|---|---|
| Component | Razor/Blazor component, a page |
| Service (`@Injectable`, `inject()`) | Application/client service registered in DI |
| `HttpClient` | `HttpClient` |
| HTTP interceptor | `DelegatingHandler` (client-side pipeline) |
| Route guard (`CanActivateFn`) | `[Authorize]` / authorization on navigation |
| Reactive Form + validators | Model binding + DataAnnotations/FluentValidation |
| TypeScript interface | DTO contract |
| `environment.*.ts` | `appsettings.{Environment}.json` |
| `app.config.ts` providers | `Program.cs` service registration |

## Angular Application

The frontend is a working storefront: browse/filter the catalog, manage the cart, check out and
see order history — all against the real API. Django stays authoritative for prices, stock,
totals and permissions; Angular only displays what the API returns and re-reads after changes.

```
Angular ── HTTP + JWT ──▶ Django REST API ──▶ PostgreSQL

Angular ── POST /api/orders/checkout/ ──▶ Django
                                            └─ transaction.atomic()  (lock stock, snapshot prices, pay, clear cart)
                                                 └─ on_commit ──▶ Celery ──▶ Redis (broker) ──▶ Worker (confirmation email)
```

**Run locally** — API on :8000 (`docker compose up -d`, plus
`docker compose exec web python manage.py seed_demo --password <dev-password>` for demo data), then:

```powershell
cd frontend
npm install
npm start        # http://localhost:4200  (sign in as jane@example.com / your dev password, or register)
npm test         # 63 unit tests
```

**Pages**: `/products` (search, category, sort, pages — all in the URL, so filters survive reload
and links can be shared), `/products/:id`, `/cart`, `/orders`, `/orders/:id`, `/login`, `/register`.
`/cart` and `/orders/**` require sign-in; adding to the cart while anonymous goes to
`/login?returnUrl=/products/:id`.

**API routes consumed**

| Feature | Requests |
|---|---|
| Auth (`AuthService`) | `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/refresh/`, `GET /api/auth/me/` |
| Catalog (`ProductService`, `CategoryService`) | `GET /api/products/?search=&category=<slug>&ordering=&page=&page_size=12`, `GET /api/products/{id}/`, `GET /api/categories/?page_size=100` |
| Cart (`CartService`) | `GET /api/cart/`, `DELETE /api/cart/`, `POST /api/cart/items/`, `PATCH /api/cart/items/{id}/`, `DELETE /api/cart/items/{id}/` |
| Orders (`OrderService`) | `GET /api/orders/?page=`, `GET /api/orders/{id}/`, `POST /api/orders/checkout/` |

**Design choices**

- One service per feature, no generic `ApiService`/repository; pages use `rxResource` (signals) for
  reads and plain `subscribe` for commands.
- Cart state is one signal in `CartService` (header badge + cart page). Every cart change is
  followed by `GET /api/cart/` instead of recalculating totals in the browser. No NgRx.
- Checkout: the button is disabled and reads "Placing order…" while the request runs (no double
  submit); on success the cart is re-read (badge → 0) and the app opens `/orders/{id}?placed=1`.
  On failure the API's message is shown and the cart re-read (stock may have changed).
- Order lines show `OrderItem.price` — what was paid at checkout, even if the product price changes later.
- Errors go through one function, `core/http/api-error.ts`: 400 → the API's own message
  ("Only 3 in stock…"); 401 → "Your session has expired…" (login: "Incorrect email or password.");
  404 → a not-found page (also for another user's order); 409 / 429 / 5xx / network → fixed
  friendly sentences. Raw server output is never shown.

## Full Docker Stack

One command starts everything — no local Python, Node, PostgreSQL or Redis needed:

```powershell
copy .env.example .env        # set SECRET_KEY and POSTGRES_PASSWORD (and DEMO_PASSWORD for demo data)
docker compose up --build
docker compose exec web python manage.py seed_demo   # optional demo catalog + users
```

| URL | |
|---|---|
| http://localhost:4200 | Angular app |
| http://localhost:8000/api/ | Django REST API |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/admin/ | Django Admin |

| Service | Image | Host port | Role | Healthcheck |
|---|---|---|---|---|
| `frontend` | `frontend/Dockerfile` (Node build → `nginx:alpine`) | `127.0.0.1:4200` → 80 | serves the compiled Angular app | `wget` of `/` |
| `web` | `Dockerfile` | `127.0.0.1:8000` | Django + Gunicorn: REST API, admin, Swagger; runs migrations on start | `GET /api/health/` |
| `worker` | same image as `web` | — | Celery worker (order confirmation emails) | `celery inspect ping` |
| `redis` | `redis:7-alpine` | — | DB 0 Celery broker · DB 1 Django cache · DB 2 tests | `redis-cli ping` |
| `db` | `postgres:16-alpine` | — | PostgreSQL, data in volume `postgres_data` | `pg_isready` |

Start order: `db` + `redis` healthy → `web` and `worker` → `frontend` (after `web` has started).
Ports are bound to `127.0.0.1` only; PostgreSQL and Redis are not published at all.

```
Browser
  ↓  http://localhost:4200          (HTML/JS/CSS)
Angular / Nginx  (frontend)
  ↓  http://localhost:8000/api      (JSON + JWT, CORS: localhost:4200 only)
Django REST API  (web)
  ↓
PostgreSQL       (db)

Django (web, on checkout commit)
  ↓  task message
Redis            (redis, DB 0)
  ↓
Celery Worker    (worker) ── writes Order.confirmation_sent_at
```

Nginx only serves static files. The Angular code runs **in the browser**, on the host — so it
calls the API at `http://localhost:8000/api`, never at `http://web:8000` (Docker service names
resolve only inside the Compose network). The URL is compiled into the bundle from the build arg
`FRONTEND_API_BASE_URL` (default `http://localhost:8000/api`; change it in `.env`, then rebuild).
Deep links such as `/products/7`, `/cart` or `/orders` are answered with `index.html`, so a browser
refresh works; hashed JS/CSS files are cached for a year, `index.html` is always revalidated.

| Command | Purpose |
|---|---|
| `docker compose up --build` | build images and start everything (foreground) |
| `docker compose up -d --build` | rebuild after code changes, run in the background |
| `docker compose ps` | all five services should be `healthy` |
| `docker compose logs -f worker` | watch `send_order_confirmation` tasks |
| `docker compose exec web pytest` | Django test suite (Angular tests: `cd frontend; npm test`) |
| `docker compose down` | stop; the database is kept |
| `docker compose down -v` | stop **and delete the database** |

## Demo data (development only)

```powershell
python manage.py seed_demo              # idempotent: safe to run repeatedly
python manage.py seed_demo --reset      # restore demo records; other data untouched
python manage.py seed_demo --password "my-dev-pass"   # or set DEMO_PASSWORD
```

Creates `admin@example.com` (staff), `jane@example.com`, `bob@example.com`, 4 categories,
8 products, a cart for Bob and two paid orders for Jane. Default password: `demo-password-123`
(refused when `DEBUG=False` unless `--password`/`DEMO_PASSWORD` is given).

## API documentation

| URL | What |
|---|---|
| <http://127.0.0.1:8000/api/schema/> | OpenAPI 3 schema (JSON) |
| <http://127.0.0.1:8000/api/docs/> | Swagger UI (interactive) |
| <http://127.0.0.1:8000/api/redoc/> | ReDoc (reference) |

Generated by drf-spectacular from the views, serializers, filters and permissions.
Export to a file: `python manage.py spectacular --format openapi-json --file openapi.json --validate`.

**Authenticating in Swagger UI:** call `POST /api/auth/login/` → copy `access` → click
**Authorize** → paste the token *without* the `Bearer` prefix (Swagger adds it). Every request
then sends:

```
Authorization: Bearer <access_token>
```

The UI pages load Swagger UI / ReDoc assets from the jsDelivr CDN, so they need internet access.

## Admin (back-office)

<http://127.0.0.1:8000/admin/> — staff users only (`is_staff` + `is_active`; e.g. `createsuperuser`
or the seeded `admin@example.com`). Django Admin is the internal back-office for the team; the
REST API under `/api/` is the public application API.

- Products: search, filters (active, stock level, category), quick edit of price/active.
- Orders: status filter, search by order number or email, items inline with the checkout-time price.
- Orders, order items and payments are **history**: they cannot be added or deleted in the admin,
  totals/prices/payments are read-only. Only an order's `status` can be changed (no side effects).

## Auth endpoints

| Method | URL | Auth |
|---|---|---|
| POST | `/api/auth/register/` | public |
| POST | `/api/auth/login/` → `{access, refresh}` | public |
| POST | `/api/auth/refresh/` → `{access}` | public |
| GET | `/api/auth/me/` | `Authorization: Bearer <access>` |

## Settings

- `config.settings.dev` — used by `manage.py` (DEBUG, browsable API)
- `config.settings.prod` — used by `wsgi.py` / `asgi.py` and the Docker image (`DEBUG=False`)
- `config.settings.test` — used by `pytest` (selected in `pytest.ini`)

Override with the `DJANGO_SETTINGS_MODULE` environment variable.
