# Operations

Daily checks:

```bash
cd /opt/mbfd/eoc-dashboard
docker compose ps
curl --fail http://127.0.0.1:8220/health/ready
curl --fail http://127.0.0.1:8220/api/v1/sources/health
curl --fail http://127.0.0.1:8220/api/system/version
docker compose logs --since=30m eoc-api eoc-worker
```

Interpret source health by last attempt, last success, authoritative observation,
data age, failure count, LKG, circuit state and schema version. A healthy process
does not prove a healthy publisher. An empty valid source is different from an
unavailable source.

Prometheus metrics at `/metrics` include source polls/durations/records, cache
events, and scheduler locks. Structured logs contain request IDs and safe error
classes, never secrets or raw authorization headers.

Release identity is proven independently by Git commit, image label, running
container image ID, and `/api/system/version`.
