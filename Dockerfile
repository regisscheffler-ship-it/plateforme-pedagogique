# Default Dockerfile — simplified WeasyPrint variant (lighter, easier to deploy)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install OS packages required by WeasyPrint (cairo, pango, gdk-pixbuf, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libcairo2 libcairo2-dev libpango-1.0-0 libpango1.0-dev libgdk-pixbuf2.0-0 libffi-dev libssl-dev \
       shared-mime-info fonts-dejavu-core build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

ENV PORT=8000
ENV GUNICORN_WORKERS=1
EXPOSE 8000

# Use shell form so env vars are expanded; default to 1 worker to limit memory usage on Render
# --timeout 120 prevents workers from being killed during slow WeasyPrint PDF operations
CMD sh -lc "gunicorn plateforme.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-1} --timeout 120"
