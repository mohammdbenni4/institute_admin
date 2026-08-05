# Operations

## Database backups

`backup-db.sh` takes a compressed, **verified** `pg_dump` of the institute database,
keeps 30 days, and prunes older ones. It refuses to keep a dump that `pg_restore
--list` cannot read, so a silently corrupt backup never accumulates unnoticed.

Install on the VPS as root:

```bash
cp ops/backup-db.sh /usr/local/bin/quran-backup && chmod +x /usr/local/bin/quran-backup
cp ops/quran-backup.service ops/quran-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now quran-backup.timer
systemctl start quran-backup          # take one now
journalctl -u quran-backup -n 30      # confirm it succeeded
systemctl list-timers quran-backup    # confirm the schedule
```

Tunable with environment overrides in the unit file: `BACKUP_DIR`, `RETAIN_DAYS`,
`DB_NAME`, `DB_USER`, `DB_HOST`.

### Restoring

```bash
pg_restore -h localhost -U postgres -d institute_administration --clean --if-exists \
  /var/backups/quran/institute_administration-YYYYmmdd-HHMMSS.dump
```

**Two things worth doing that this script does not do for you:**

1. **Copy the dumps off the machine.** Everything here lives on the same VPS; if the
   disk or the provider fails, the backups go with the database. `rclone`/`scp` to
   another host or object storage on a second timer closes that gap.
2. **Rehearse a restore.** A backup nobody has ever restored is a hypothesis. Restore
   into a scratch database once and confirm the row counts look right.

## Before running migrations

```bash
/usr/local/bin/quran-backup            # never migrate without a fresh dump
psql -c "SELECT version();"            # confirm PostgreSQL 11+
cd backend && alembic upgrade head     # migrate BEFORE restarting the API
```
