# PowerShell script to run Alembic migrations with Neon

# Set environment variables
$env:PYTHONUTF8 = "1"
$env:DATABASE_URL = "postgresql+psycopg://neondb_owner:npg_GOgCDu71okKS@ep-little-block-a23fv9os-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"

Write-Host "Running Alembic migrations..." -ForegroundColor Green
Write-Host "Database: Neon PostgreSQL" -ForegroundColor Cyan
Write-Host "Host: ep-little-block-a23fv9os-pooler.eu-central-1.aws.neon.tech" -ForegroundColor Cyan

# Run migrations
alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migrations completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Migration failed!" -ForegroundColor Red
    exit 1
}