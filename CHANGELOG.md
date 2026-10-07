# Changelog

All notable changes to this project are documented in this file.

## v1.0.0 — 2026-10-07

First public release.

### Authentication
- Custom user model with email login.
- JWT authentication (SimpleJWT): register, login, refresh, current user.
- Rate limiting on login and registration (shared Redis counters).

### Catalog
- Categories and products with search, category filter, price range, ordering and pagination.
- Inactive products hidden from customers; catalog writes restricted to staff.

### Cart
- One cart per user: add (merges duplicate lines), update quantity, remove item, clear.
- Server-side subtotals and totals; stock and availability validation.

### Checkout and orders
- Atomic checkout: cart → paid order in a single database transaction.
- Row-level locking (`select_for_update`) on cart and product rows to prevent overselling.
- Order items store the price paid at checkout.
- Order history and detail, scoped to the owner.
- Mock payment provider with a `Payment` record per order.

### Inventory
- Stock deducted at checkout; database check constraints on stock, prices, quantities and totals.
- Products and categories referenced by orders are protected from deletion.

### Redis
- Django cache backed by Redis (category list, throttle counters), invalidated after commit.
- Separate Redis databases for the Celery broker, the application cache and tests.

### Celery
- Order confirmation task queued with `transaction.on_commit()`; idempotent; tolerant of broker outages.

### Angular
- Angular 22 storefront: catalog with URL-driven filters, product detail, cart, checkout, order history.
- JWT interceptor with transparent token refresh, route guards, central API error handling.
- Light/dark theme, responsive layout.

### Admin and API documentation
- Django Admin back-office; orders, order items and payments are read-only history.
- OpenAPI 3 schema with Swagger UI and ReDoc.

### Docker
- Docker Compose stack: frontend (Nginx), web (Gunicorn), worker (Celery), Redis, PostgreSQL.
- Health checks, start ordering, persistent database volume, localhost-only ports.

### Tests and CI
- 232 Django tests (pytest, real PostgreSQL) and 63 Angular tests (Vitest).
- GitHub Actions: Django checks and tests, Angular tests and production build, Docker image builds.
