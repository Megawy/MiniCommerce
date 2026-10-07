# LinkedIn — Projects section

**Project title**
MiniCommerce — Full-Stack E-Commerce Platform (Angular, Django REST Framework)

**Project link**
https://github.com/<your-github-username>/MiniCommerce

**Short description** (one line)
Full-stack e-commerce application with an Angular storefront and a Django REST API on
PostgreSQL, Redis and Celery, containerized with Docker Compose.

**Long description**
MiniCommerce is a portfolio project that implements a complete shopping flow — catalog, cart,
checkout and order history — with a focus on backend correctness. Checkout runs in a single
PostgreSQL transaction that locks cart and product rows (select_for_update), validates stock,
snapshots prices onto order lines, records a (mock) payment and clears the cart, so it either
fully succeeds or leaves nothing behind. Redis provides a shared cache and rate-limit counters
across Gunicorn workers; a Celery worker sends order confirmations queued with
transaction.on_commit and made idempotent. The Angular 22 frontend uses standalone components,
signals, lazy-loaded feature routes and a JWT interceptor with transparent token refresh. The
system runs as five Docker Compose services, is documented with OpenAPI/Swagger, and is covered
by 232 Django tests and 63 Angular tests in a GitHub Actions pipeline.

**Tech stack**
Angular 22 · TypeScript · Python 3.13 · Django 5.2 · Django REST Framework · PostgreSQL 16 ·
Redis 7 · Celery · JWT (SimpleJWT) · Gunicorn · Nginx · Docker Compose · pytest · Vitest ·
GitHub Actions · OpenAPI (drf-spectacular)

**Key engineering highlights**
- Atomic checkout with row-level locking; a concurrency test proves stock cannot be oversold.
- Historical order pricing and database constraints protecting stock, prices and totals.
- Redis-backed cache and distributed rate limiting shared by all application workers.
- Background jobs queued after commit, idempotent and tolerant of a broker outage.
- Angular feature architecture: feature services, signals, URL-driven filters, central error handling.
- Full stack in Docker Compose with health checks and a persistent database volume.
- OpenAPI schema with Swagger UI/ReDoc; Django Admin back-office with read-only financial history.

**Skills**
Django · Django REST Framework · Angular · PostgreSQL · Redis · Celery · Docker · REST APIs · Python · TypeScript
