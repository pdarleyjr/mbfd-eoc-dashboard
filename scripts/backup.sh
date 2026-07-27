#!/usr/bin/env sh
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
project_dir="$(dirname "$script_dir")"
if [ -f "${project_dir}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${project_dir}/.env"
  set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

backup_root="${EOC_BACKUP_ROOT:-/opt/mbfd/backups/eoc-dashboard}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="${backup_root}/${stamp}"
mkdir -p "$target"

docker exec mbfd-eoc-postgres pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --format=custom \
  --file=/tmp/eoc.dump
docker cp mbfd-eoc-postgres:/tmp/eoc.dump "${target}/eoc.dump"
docker exec mbfd-eoc-postgres rm -f /tmp/eoc.dump
docker run --rm \
  --volume mbfd-eoc_eoc-snapshots:/source:ro \
  --volume "${target}:/backup" \
  alpine:3.21 tar -czf /backup/raw-snapshots.tar.gz -C /source .
sha256sum "${target}/eoc.dump" "${target}/raw-snapshots.tar.gz" > "${target}/SHA256SUMS"
printf '%s\n' "$target"
