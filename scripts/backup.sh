#!/bin/bash
# PostgreSQL backup script
# Schedule via cron: 0 3 * * * /app/scripts/backup.sh

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
S3_BUCKET="${S3_BUCKET:-sns-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

echo "[$(date)] Starting database backup..."

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# PostgreSQL dump
DUMP_FILE="${BACKUP_DIR}/db_${DATE}.sql.gz"
pg_dump "${DATABASE_URL}" | gzip > "${DUMP_FILE}"
echo "[$(date)] PostgreSQL backup created: ${DUMP_FILE} ($(du -h "${DUMP_FILE}" | cut -f1))"

# Upload to S3 (if AWS CLI or MinIO client available)
if command -v aws &> /dev/null; then
    aws s3 cp "${DUMP_FILE}" "s3://${S3_BUCKET}/postgres/" --quiet
    echo "[$(date)] Uploaded to S3: s3://${S3_BUCKET}/postgres/"
elif command -v mc &> /dev/null; then
    mc cp "${DUMP_FILE}" "minio/${S3_BUCKET}/postgres/"
    echo "[$(date)] Uploaded to MinIO"
fi

# Redis snapshot
if command -v redis-cli &> /dev/null; then
    redis-cli BGSAVE
    echo "[$(date)] Redis BGSAVE triggered"
fi

# Cleanup old local backups
find "${BACKUP_DIR}" -name "db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Cleaned up backups older than ${RETENTION_DAYS} days"

echo "[$(date)] Backup completed successfully"
