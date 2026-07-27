# MBFD EOC API

FastAPI, PostgreSQL/PostGIS, Redis, and APScheduler implementation for the
read-only Miami Beach Emergency Management Dashboard. The API process serves
only normalized records. A separate worker performs all upstream acquisition.
