# Portfolio / CV description

## One line

Full-stack e-commerce platform built with Angular and Django REST Framework on PostgreSQL,
Redis and Celery, with transactional checkout and a Docker Compose deployment.

## Three lines

MiniCommerce is a full-stack e-commerce application: an Angular 22 storefront and a Django REST
API covering authentication, catalog, cart, checkout and orders. Checkout is a single PostgreSQL
transaction with row-level locking and price snapshots; Redis provides shared caching and rate
limiting, and Celery handles post-commit background jobs. It runs as five Docker Compose
services and is covered by 232 backend and 63 frontend tests in CI.

## Resume bullet points

- Built a full-stack e-commerce platform with Angular 22 and Django REST Framework, covering
  JWT authentication, catalog search and filtering, cart management, checkout and order history.
- Implemented an atomic checkout workflow in PostgreSQL using `transaction.atomic()` and
  `select_for_update()` row-level locking, preventing overselling under concurrent checkouts;
  verified with a multi-threaded integration test.
- Preserved historical order pricing and enforced data integrity with database check
  constraints, unique constraints and protected foreign keys.
- Added a Redis-backed cache and distributed rate limiting shared across Gunicorn workers, with
  cache invalidation on transaction commit.
- Processed order confirmations asynchronously with Celery, enqueued via
  `transaction.on_commit()` and designed to be idempotent and resilient to broker outages.
- Developed the Angular frontend with standalone components, signals, lazy-loaded feature routes,
  feature services and an HTTP interceptor with transparent JWT refresh.
- Containerized the full stack (Angular/Nginx, Django/Gunicorn, Celery, PostgreSQL, Redis) with
  Docker Compose, health checks and persistent storage.
- Wrote 232 Django tests and 63 Angular tests, set up GitHub Actions CI, and documented the API
  with OpenAPI (Swagger UI, ReDoc).
