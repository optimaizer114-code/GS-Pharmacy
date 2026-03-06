#!/bin/sh
# ══════════════════════════════════════════
#  نسخ احتياطي تلقائي لقاعدة البيانات
#  يعمل يومياً عند منتصف الليل
# ══════════════════════════════════════════

BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d_%H-%M)
FILENAME="pharmacy_backup_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Create backup
pg_dump -h db -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/$FILENAME"

if [ $? -eq 0 ]; then
    echo "✅ Backup created: $FILENAME"
else
    echo "❌ Backup FAILED at $DATE"
fi

# Keep only last 30 backups
ls -tp "$BACKUP_DIR"/*.sql.gz 2>/dev/null | grep -v '/$' | tail -n +31 | xargs -I {} rm -- {}

echo "📦 Current backups:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5

# Add cron job (daily at midnight)
echo "0 0 * * * /backup.sh >> /var/log/backup.log 2>&1" | crontab -
