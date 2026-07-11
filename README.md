# Catalog Monitor

Система непрерывного фонового мониторинга качества каталога интернет-магазина с уведомлениями через Telegram.

## Принцип работы

Программа **автоматически и непрерывно**:

1. Скачивает XML-фиды товаров и магазинов.
2. Проверяет **все** товары и магазины из каждого фида.
3. Отправляет алерты пользователям бота при критичных проблемах (см. ниже).
4. После завершения проверки скачивает новый фид и повторяет цикл.

Пользователи **не запускают проверки вручную**. Telegram-бот служит для уведомлений и просмотра результатов.

## Алерты в Telegram

Уведомления получают все авторизованные пользователи бота. Полная матрица — в [docs/MONITORING.md](docs/MONITORING.md).

### CRITICAL

`XML_UNAVAILABLE`, `XML_ERROR`, `PRODUCT_PAGE_UNAVAILABLE`, `PRODUCT_IMAGE_UNAVAILABLE`, `STORE_IMAGE_UNAVAILABLE`, `PRODUCT_MISSING_PICTURE`, `STORE_MISSING_PHOTO`, `PRODUCT_MISSING_CATEGORY`, `PRODUCT_INVALID_CATEGORY`, `PRODUCT_MISSING_NAME`, `PRODUCT_MISSING_PRICE`, `PRODUCT_INVALID_PRICE`, `CATEGORY_INVALID_PARENT`, `DUPLICATE_IDS`

HTTP-алерты (`XML_UNAVAILABLE`, страницы, изображения) — только при ответе **4xx/5xx**.

### WARNING

`COUNT_CHANGE`, `FEED_SIZE_CHANGE`, `STALE_DATA`, `PRODUCT_LOW_PRICE`, `PRODUCT_INVALID_OLDPRICE`

### Без Telegram (только отчёты)

`PRODUCT_PRICE_CHANGE`, `PRODUCT_IMAGE_INVALID_CONTENT_TYPE`, `PRODUCT_IMAGE_EMPTY`, `STORE_IMAGE_INVALID_CONTENT_TYPE`, а также проверки остатков, дублей URL, отсутствия URL и прочие предупреждения.

Шаблоны: `app/locales/messages.py`. Логика: `app/services/monitoring/alert_policy.py`.

Подробнее: [docs/MONITORING.md](docs/MONITORING.md)

## Временные параметры

| Параметр | По умолчанию |
|----------|--------------|
| Интервал скачивания фида | сразу после завершения цикла | непрерывный цикл |
| Макс. длительность проверки | 5 часов (`MAX_CHECK_DURATION_SECONDS=18000`) |
| Резерв на локальные проверки | 10 мин (`LOCAL_CHECK_RESERVE_SECONDS=600`) |

HTTP-проверки URL выполняются **последовательно**: интервал между запросами =
`(MAX_CHECK_DURATION − LOCAL_CHECK_RESERVE) / количество URL` из обоих фидов.

## Telegram-бот (меню пользователя)

| Кнопка | Действие |
|--------|----------|
| 📊 Последняя проверка | Результат последнего автоматического цикла |
| 📋 История проверок | История автоматических проверок |
| ℹ️ О системе | Описание режима работы |
| 👥 Пользователи | Управление доступом (только администратор) |

## Установка

```bash
cd catalog_monitor
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
# Заполнить BOT_TOKEN и ADMIN_ID в .env
```

## Запуск

```bash
cd catalog_monitor
python -m app.main
```

**Windows (PowerShell):**

```powershell
cd catalog_monitor
.\run.ps1
```

Важно: запускать из папки `catalog_monitor`, не из родительской `Фид`.
Конфигурация читается из файла `catalog_monitor/.env` (не из `.env.example`).

Приложение запускает:

- фоновый мониторинг фидов (после инициализации модуля проверки);
- Telegram-бот (polling);
- HTTP API (`/health`, `/ready`) на порту 8000.

## Переменные окружения

См. [.env.example](.env.example).

Ключевые переменные:

- `BOT_TOKEN` — токен Telegram-бота
- `ADMIN_ID` — Telegram ID администратора
- `PRODUCT_FEED_URL` / `STORE_FEED_URL` — URL XML-фидов
- `FEED_DOWNLOAD_INTERVAL` — интервал скачивания (сек)
- `MAX_CHECK_DURATION_SECONDS` — лимит длительности проверки (сек)
- `LOCAL_CHECK_RESERVE_SECONDS` — резерв на парсинг и локальную валидацию (сек)
- `CHECK_MODE` — `FAST` или `FULL`

## Архитектура

```
app/
├── main.py                    # Точка входа
├── core/                      # Конфигурация, DI, логирование
├── domain/                    # Сущности, правила валидации
├── infrastructure/            # БД, HTTP, XML, планировщик
├── services/
│   ├── continuous_monitoring_service.py  # Фоновый цикл
│   ├── monitoring/            # 3-этапная проверка
│   └── notification_service.py
├── bot/                       # Telegram UI (только просмотр + алерты)
└── locales/ru.py              # Все тексты на русском
```

## База данных

SQLite. Таблицы: `users`, `authorization_log`, `feed_checks`, `active_errors`, `error_history`, `application_settings`.

Данные старше 3 дней автоматически удаляются (`DATA_RETENTION_DAYS`).

## Тесты

```bash
python -m pytest tests/ -v
```

## Python

Требуется Python 3.14+ (тестировано на 3.14.5).
