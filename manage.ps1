# =====================================================================
# اسکریپت مدیریت و اجرای سریع سامانه Iran Monitor در ویندوز (PowerShell)
# =====================================================================

param (
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "build", "status", "logs", "scheduler-on", "scheduler-off", "backup-db")]
    [string]$Action = "status"
)

switch ($Action) {
    "start" {
        Write-Host "🚀 در حال اجرای سرویس‌های اصلی Iran Monitor..." -ForegroundColor Cyan
        docker compose up -d
        docker compose ps
    }
    "stop" {
        Write-Host "🛑 در حال متوقف‌سازی تمامی سرویس‌ها..." -ForegroundColor Yellow
        docker compose down
    }
    "restart" {
        Write-Host "🔄 در حال راه‌اندازی مجدد سرویس‌ها..." -ForegroundColor Cyan
        docker compose restart
        docker compose ps
    }
    "build" {
        Write-Host "🔨 در حال بیلد مجدد و اجرای سرویس‌ها..." -ForegroundColor Cyan
        docker compose up -d --build
        docker compose ps
    }
    "status" {
        docker compose ps
    }
    "logs" {
        docker compose logs -f --tail=100
    }
    "scheduler-on" {
        Write-Host "📡 فعال‌سازی کانتینر جمع‌آوری اخبار (Collector Scheduler)..." -ForegroundColor Green
        docker compose --profile scheduler up -d collector
        docker compose ps
    }
    "scheduler-off" {
        Write-Host "⏹️ غیرفعال‌سازی کانتینر جمع‌آوری اخبار..." -ForegroundColor Yellow
        docker compose stop collector
    }
    "backup-db" {
        $date = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupDir = "./backups"
        if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }
        $file = "$backupDir/iran_monitor_backup_$date.sql"
        Write-Host "💾 در حال تهیه فایل پشتیبان از دیتابیس در $file..." -ForegroundColor Cyan
        docker compose exec -T postgres pg_dump -U iran_monitor_user iran_monitor | Out-File -FilePath $file -Encoding utf8
        Write-Host "✅ نسخه پشتیبان با موفقیت ذخیره شد." -ForegroundColor Green
    }
}
