# MiniCommerce API — production-style image: Gunicorn + WhiteNoise, non-root.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Unprivileged runtime user.
RUN useradd --create-home --uid 1000 app && chown app:app /app

# Dependencies before source code: this layer is reused until requirements change.
# REQUIREMENTS=dev adds pytest (docker-compose.yml builds with it so tests can run in the container).
ARG REQUIREMENTS=base
COPY requirements/ requirements/
RUN pip install -r requirements/${REQUIREMENTS}.txt

COPY --chown=app:app . .
USER app

# Bake admin/DRF static files into the image (served by WhiteNoise).
# The two variables exist only for this build step; nothing connects to a database here.
RUN SECRET_KEY=collectstatic-only DATABASE_URL=sqlite:///:memory: \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Apply migrations, then replace the shell with Gunicorn (PID 1 receives SIGTERM on `docker stop`).
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --access-logfile - --error-logfile -"]
