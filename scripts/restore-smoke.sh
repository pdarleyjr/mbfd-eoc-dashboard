#!/usr/bin/env sh
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
project_dir="$(dirname "$script_dir")"
env_file="${project_dir}/.env"
read_env() {
  sed -n "s/^${1}=//p" "$env_file" | tail -n 1
}
if [ -f "$env_file" ]; then
  POSTGRES_USER="${POSTGRES_USER:-$(read_env POSTGRES_USER)}"
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(read_env POSTGRES_PASSWORD)}"
fi

if [ "$#" -ne 1 ]; then
  echo "usage: restore-smoke.sh /path/to/backup" >&2
  exit 2
fi

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

backup_dir="$1"
test -f "${backup_dir}/eoc.dump"
test -f "${backup_dir}/raw-snapshots.tar.gz"
test -f "${backup_dir}/SHA256SUMS"
(cd "$backup_dir" && sha256sum -c SHA256SUMS)

suffix="$(date -u +%Y%m%d%H%M%S)-$$"
restore_db="eoc_restore_smoke_$(printf '%s' "$suffix" | tr -cd '0-9')"
snapshot_volume="mbfd-eoc-restore-smoke-${suffix}"

docker run --rm \
  --network mbfd-eoc_eoc-internal \
  --env POSTGRES_USER="$POSTGRES_USER" \
  --env PGPASSWORD="$POSTGRES_PASSWORD" \
  --env RESTORE_DB="$restore_db" \
  --volume "${backup_dir}:/backup:ro" \
  postgres:16-alpine \
  sh -eu -c '
    cleanup() {
      dropdb --if-exists -h mbfd-eoc-postgres -U "$POSTGRES_USER" "$RESTORE_DB"
    }
    trap cleanup EXIT INT TERM
    createdb -h mbfd-eoc-postgres -U "$POSTGRES_USER" "$RESTORE_DB"
    pg_restore -h mbfd-eoc-postgres -U "$POSTGRES_USER" -d "$RESTORE_DB" /backup/eoc.dump
    psql -h mbfd-eoc-postgres -U "$POSTGRES_USER" -d "$RESTORE_DB" -Atc "
      select json_build_object(
        '\''database'\'', current_database(),
        '\''records'\'', count(*),
        '\''geometry_rows'\'', count(geom),
        '\''invalid_geometry_rows'\'',
          count(geom) filter (where not st_isvalid(geom)),
        '\''postgis_version'\'', postgis_lib_version()
      )
      from canonical_records
    "
  '

docker volume create "$snapshot_volume" >/dev/null
cleanup_volume() {
  docker volume rm -f "$snapshot_volume" >/dev/null
}
trap cleanup_volume EXIT INT TERM
docker run --rm \
  --volume "${snapshot_volume}:/restore" \
  --volume "${backup_dir}:/backup:ro" \
  alpine:3.21 \
  sh -eu -c '
    tar -xzf /backup/raw-snapshots.tar.gz -C /restore
    files="$(find /restore -type f | wc -l | tr -d " ")"
    bytes="$(du -sb /restore | cut -f1)"
    test "$files" -gt 0
    printf "{\"snapshot_files\":%s,\"snapshot_bytes\":%s}\n" "$files" "$bytes"
  '
cleanup_volume
trap - EXIT INT TERM
