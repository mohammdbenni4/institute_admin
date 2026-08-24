#!/usr/bin/env bash
# Nightly PostgreSQL backup for the institute database.
#
# Writes a compressed custom-format dump (restorable with pg_restore), keeps a
# rolling window, and verifies the dump is readable before trusting it — an
# unverified backup is only a belief that you have a backup.
#
# Install (as root on the VPS):
#   cp ops/backup-db.sh /usr/local/bin/quran-backup
#   chmod +x /usr/local/bin/quran-backup
#   cp ops/quran-backup.service ops/quran-backup.timer /etc/systemd/system/
#   systemctl daemon-reload && systemctl enable --now quran-backup.timer
#   systemctl start quran-backup      # take one immediately and check the output
set -Eeuo pipefail

DB_NAME="${DB_NAME:-institute_administration}"
DB_USER="${DB_USER:-postgres}"
# Empty by default *on purpose*: with no -h, pg_dump uses the local unix socket and
# peer authentication, so running as the `postgres` user needs no password and none
# has to be stored anywhere. Setting DB_HOST forces TCP, which then needs a password.
DB_HOST="${DB_HOST:-}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/quran}"
RETAIN_DAYS="${RETAIN_DAYS:-30}"

# Build the connection arguments once.
conn_args=(-U "$DB_USER")
[ -n "$DB_HOST" ] && conn_args+=(-h "$DB_HOST")

timestamp="$(date +%Y%m%d-%H%M%S)"
target="${BACKUP_DIR}/${DB_NAME}-${timestamp}.dump"

mkdir -p "$BACKUP_DIR"
# Only the owner may read it: these dumps contain students' names and guardians'
# phone numbers.
chmod 700 "$BACKUP_DIR"

log() { printf '%s  %s\n' "$(date -Is)" "$*"; }

# A failed dump must not leave a truncated file behind: a 0-byte file in the backup
# directory looks like a backup until the day you need it.
#
# `return 0` is load-bearing. Without it the final test fails on the happy path, the
# EXIT trap returns non-zero, and that becomes the script's exit status — systemd
# then reports a failure for a backup that actually succeeded.
cleanup_partial() {
    if [ -f "$target" ] && [ ! -s "$target" ]; then
        rm -f "$target"
    fi
    return 0
}
trap cleanup_partial EXIT

log "dumping ${DB_NAME} -> ${target}"
# -Fc = custom format: compressed, and restorable table-by-table.
pg_dump "${conn_args[@]}" -Fc "$DB_NAME" > "$target"
chmod 600 "$target"

# A dump that cannot be listed cannot be restored. Fail loudly now rather than
# during an emergency.
log "verifying"
if ! pg_restore --list "$target" > /dev/null; then
    log "ERROR: dump failed verification, removing it"
    rm -f "$target"
    exit 1
fi

size="$(du -h "$target" | cut -f1)"
log "ok (${size})"

log "pruning dumps older than ${RETAIN_DAYS} days"
find "$BACKUP_DIR" -name "${DB_NAME}-*.dump" -type f -mtime "+${RETAIN_DAYS}" -print -delete

log "done; ${BACKUP_DIR} now holds $(find "$BACKUP_DIR" -name '*.dump' | wc -l) dump(s)"
