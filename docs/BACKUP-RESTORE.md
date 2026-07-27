# Backup and Restore

`scripts/backup.sh` creates a timestamped PostgreSQL custom-format dump and
snapshot-volume archive below the configured backup directory. It records
checksums and never includes `.env`.

`scripts/restore-smoke.sh` restores into isolated temporary database/volume
targets, runs integrity and PostGIS checks, compares checksums, and removes only
the verified temporary targets.

Production schedule should write to the existing protected GMKtec backup
destination with retention and off-host replication. Before upgrade or rollback:

1. Run a fresh backup.
2. Verify manifest and checksums.
3. Run the isolated restore smoke test.
4. Record release SHA and schema revision.

Never validate restore by overwriting the live database. Production restore
requires stopping worker/API writes (the dashboard is read-only but ingestion
writes normalized data), preserving the failed volume, restoring to a new volume,
running Alembic/integrity checks, then switching Compose explicitly.
