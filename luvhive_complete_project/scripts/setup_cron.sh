#!/bin/bash
# Setup automated backup cron job - ChatGPT Phase-4 recommendation

set -e

echo "🔧 Setting up automated backup cron job..."

# Create log directory
mkdir -p /tmp/logs

# Add backup cron job (runs at 2 AM daily)
CRON_JOB="0 2 * * * cd $(pwd) && /usr/bin/python3 scripts/automated_backup.py >> /tmp/logs/backup_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "automated_backup.py"; then
    echo "⚠️  Backup cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Added backup cron job: runs daily at 2 AM"
fi

# Make backup script executable
chmod +x scripts/automated_backup.py

echo "🎉 Automated backup system configured!"
echo "   - Daily backups at 2 AM"
echo "   - Weekly restore tests on Sundays"
echo "   - Logs: /tmp/luvhive_backup.log"
echo "   - Cron logs: /tmp/logs/backup_cron.log"