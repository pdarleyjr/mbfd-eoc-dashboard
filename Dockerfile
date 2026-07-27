FROM node:22.22.0-alpine AS web-build
WORKDIR /build
COPY package.json package-lock.json* ./
COPY web/package.json web/package.json
RUN npm install --ignore-scripts
COPY web web
ARG VITE_GOOGLE_MAPS_API_KEY=""
ARG VITE_GOOGLE_MAPS_MAP_ID=""
ARG EOC_RELEASE_SHA="development"
ARG EOC_BUILD_ID="local"
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY
ENV VITE_GOOGLE_MAPS_MAP_ID=$VITE_GOOGLE_MAPS_MAP_ID
ENV VITE_RELEASE_SHA=$EOC_RELEASE_SHA
ENV VITE_BUILD_ID=$EOC_BUILD_ID
RUN npm --workspace web run build

FROM python:3.12.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --gid 10001 eoc \
    && useradd --uid 10001 --gid eoc --create-home --shell /usr/sbin/nologin eoc \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY api/pyproject.toml api/README.md /app/
COPY api/app /app/app
RUN pip install .
COPY api/alembic.ini /app/alembic.ini
COPY api/alembic /app/alembic
COPY --from=web-build /build/web/dist /app/static
RUN mkdir -p /app/data/raw-snapshots && chown -R eoc:eoc /app/data
ARG EOC_RELEASE_SHA="development"
ARG EOC_BUILD_ID="local"
ENV EOC_RELEASE_SHA=$EOC_RELEASE_SHA \
    EOC_BUILD_ID=$EOC_BUILD_ID \
    EOC_STATIC_DIR=/app/static
LABEL org.opencontainers.image.title="MBFD EOC Dashboard" \
      org.opencontainers.image.revision=$EOC_RELEASE_SHA \
      org.opencontainers.image.version=$EOC_BUILD_ID
USER 10001:10001
EXPOSE 8220
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8220 --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
