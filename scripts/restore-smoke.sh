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

if [ "$#" -ne 1 ]; then
  echo "usage: restore-smoke.sh /path/to/backup" >&2
  exit 2
fi

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

backup_dir="$1"
test -f "${backup_dir}/eoc.dump"
test -f "${backup_dir}/SHA256SUMS"
(cd "$backup_dir" && sha256sum -c SHA256SUMS)

docker run --rm \
  --network mbfd-eoc_eoc-internal \
  --env POSTGRES_USER="$POSTGRES_USER" \
  --env PGPASSWORD="$POSTGRES_PASSWORD" \
  --volume "${backup_dir}:/backup:ro" \
  postgres:16-alpine \
  sh -c 'createdb -h mbfd-eoc-postgres -U "$POSTGRES_USER" eoc_restore_smoke || true; pg_restore --clean --if-exists -h mbfd-eoc-postgres -U "$POSTGRES_USER" -d eoc_restore_smoke /backup/eoc.dump; psql -h mbfd-eoc-postgres -U "$POSTGRES_USER" -d eoc_restore_smoke -Atc "select count(*) from canonical_records"; dropdb -h mbfd-eoc-postgres -U "$POSTGRES_USER" eoc_restore_smoke'
