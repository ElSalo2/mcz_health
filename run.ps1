# Запуск Catalog Monitor из правильной директории
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Write-Host 'Ошибка: файл .env не найден.' -ForegroundColor Red
    Write-Host 'Скопируйте .env.example в .env и заполните BOT_TOKEN и ADMIN_ID:'
    Write-Host '  Copy-Item .env.example .env'
    exit 1
}

python -m app.main
