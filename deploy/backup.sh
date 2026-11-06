#!/usr/bin/env bash
# Copy the game database to ~/backups, safely while the bot is running. Keeps the last 14.
# Run nightly by chongabot-backup.timer; run it by hand any time.
set -euo pipefail
cd "$(dirname "$0")/.."

db=${DATABASE_PATH:-chonga.db}
dest=${BACKUP_DIR:-$HOME/backups}
mkdir -p "$dest"
out="$dest/chonga-$(date -u +%Y-%m-%dT%H%M).db"

sqlite3 "$db" ".backup '$out'"   # consistent snapshot, even mid-write
sqlite3 "$out" "PRAGMA integrity_check" | grep -qx ok
gzip -f "$out"
cp -f "$out.gz" "$dest/chonga-latest.db.gz"

find "$dest" -maxdepth 1 -name 'chonga-2*.db.gz' | sort -r | tail -n +15 | xargs -r rm --
echo "Backed up to $out.gz"
