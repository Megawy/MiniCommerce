# LinkedIn post

I built MiniCommerce, a small but complete e-commerce application, to go deeper on Django and
Angular and to practise the parts of backend work that usually only show up in production code.

The stack: an Angular 22 frontend served by Nginx, a Django REST Framework API, PostgreSQL,
Redis, a Celery worker, all running together with Docker Compose.

The catalog and cart are the easy part. What I spent most of my time on:

1. Checkout as one database transaction. Creating the order, deducting stock, recording the
   payment and emptying the cart either all happen or none of them do.
2. Inventory locking. Cart and product rows are locked with select_for_update, in a fixed
   order, so two customers buying the last unit can't both succeed. There is a test that runs
   two checkouts in parallel threads, and it fails if the lock is removed.
3. Historical pricing. Each order line stores the price paid, so editing a product later
   doesn't rewrite past orders.
4. Redis caching for read-mostly data, with invalidation after commit.
5. Rate limiting on login/register with the counters in Redis, so the limit holds across all
   Gunicorn workers instead of being multiplied by them.
6. Celery for the order confirmation, queued with transaction.on_commit so the worker never
   sees an order that isn't committed yet, and made idempotent so a redelivered message
   doesn't notify twice.
7. JWT authentication, with the Angular interceptor refreshing an expired token once and
   retrying the request.
8. An Angular frontend organised by feature, with signals and small feature services rather
   than a global store — the app doesn't have enough shared state to justify one.
9. Docker Compose for the whole thing: five services, health checks, and a persistent
   database volume.

It has 232 Django tests (running against real PostgreSQL) and 63 Angular tests, an OpenAPI
schema with Swagger UI, Django Admin as the back-office, and a GitHub Actions pipeline.

It's a portfolio project, not a live shop, and the payment provider is a mock. But building it
end to end was a good way to work through transactions, locking, caching and background jobs
in a codebase small enough to read in an afternoon.

Code, screenshots and architecture notes: [GitHub link]

#SoftwareEngineering #Django #Angular #Python #PostgreSQL #Redis #Celery #Docker #BackendDevelopment
