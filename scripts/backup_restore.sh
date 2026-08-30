#!/usr/bin/env bash
set -euo pipefail

# E.Y.T ERP PostgreSQL backup/restore helper.
# Usage:
#   ./scripts/backup_restore.sh backup /path/to/backup.dump
#   ./scripts/backup_restore.sh restore /path/to/backup.dump

ACTION="${1:-}"
FILE="${2:-}"

: "${DATABASE_URL:?DATABASE_URL must be set in the runtime environment}"

case "$ACTION" in
  backup)
    test -n "$FILE" || { echo "backup file path required" >&2; exit 2; }
    pg_dump "$DATABASE_URL" --format=custom --file="$FILE"
    echo "Backup created: $FILE"
    ;;
  restore)
    test -n "$FILE" || { echo "backup file path required" >&2; exit 2; }
    test -f "$FILE" || { echo "backup file not found: $FILE" >&2; exit 2; }
    pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$FILE"
    echo "Restore completed from: $FILE"
    ;;
  *)
    echo "Usage: $0 {backup|restore} /path/to/backup.dump" >&2
    exit 2
    ;;
esac
