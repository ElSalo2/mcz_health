"""Локализация пользовательских сообщений (русский язык)."""

from app.locales import messages as alert_messages


class Messages:
    """Все пользовательские тексты системы."""

    # --- Авторизация ---
    AUTH_IDENTITY_FAILED = (
        "❌ Не удалось подтвердить личность.\n\n"
        'Пожалуйста, отправьте свой собственный номер телефона через кнопку «Авторизоваться».'
    )
    AUTH_ACCESS_DENIED = (
        "⛔ Доступ к системе ограничен.\n\n"
        "Для получения доступа обратитесь к администратору Telegram:\n"
        "@el_salo\n\n"
        "После добавления вашего номера телефона повторно откройте бот и подтвердите номер телефона."
    )
    AUTH_USER_BLOCKED = (
        "⛔ Ваш доступ к системе заблокирован.\n\n"
        "Для восстановления доступа обратитесь к администратору Telegram:\n"
        "@el_salo"
    )
    AUTH_SUCCESS = "✅ Авторизация выполнена успешно."
    WELCOME = (
        "👋 Добро пожаловать!\n\n"
        "Система работает в фоновом режиме и непрерывно контролирует качество "
        "каталога интернет-магазина.\n\n"
        "Что делает система автоматически:\n\n"
        "• Скачивает фиды товаров и магазинов.\n"
        "• Проверяет все товары и магазины из фида.\n"
        "• Контролирует доступность страниц и изображений.\n"
        "• Проверяет полноту и корректность обязательных данных.\n"
        "• Отслеживает изменения и аномалии в каталоге.\n"
        "• Отправляет алерты в Telegram при критичных проблемах.\n\n"
        "Алерты приходят, если:\n"
        "• страница, фото или XML-фид отвечает HTTP 4xx или 5xx;\n"
        "• в фиде отсутствует фото товара или магазина;\n"
        "• у товара отсутствует categoryId (категория каталога).\n\n"
        "Прочие замечания (пустые поля, устаревшие данные и т.д.) "
        "видны в отчётах бота, но без push-уведомлений.\n\n"
        "Запускать проверку вручную не требуется — мониторинг выполняется "
        "системой круглосуточно.\n\n"
        "В меню доступен просмотр результатов последних автоматических проверок."
    )
    AUTH_REQUEST_CONTACT = (
        "Для доступа к системе подтвердите номер телефона.\n"
        'Нажмите кнопку «Авторизоваться» ниже.'
    )
    ACCESS_REQUEST_ADMIN = (
        "🔔 Новый запрос на доступ\n\n"
        "Имя:\n{first_name}\n\n"
        "Фамилия:\n{last_name}\n\n"
        "Username:\n@{username}\n\n"
        "Telegram ID:\n{id}\n\n"
        "Телефон:\n{phone}\n\n"
        "Дата:\n{date}\n\n"
        "Время:\n{time}"
    )

    # --- Кнопки меню ---
    BTN_LAST_CHECK = "📊 Последняя проверка"
    BTN_HISTORY = "📋 История проверок"
    BTN_ABOUT = "ℹ️ О системе"
    BTN_USERS = "👥 Пользователи"
    BTN_SHARE_CONTACT = "🔐 Авторизоваться"

    # --- Общие ---
    ABOUT_SYSTEM = (
        "ℹ️ О системе\n\n"
        "Система мониторинга качества каталога интернет-магазина.\n\n"
        "Режим работы:\n"
        "• Непрерывный фоновый мониторинг без участия пользователя.\n"
        "• Скачивание фидов каждые 3 часа.\n"
        "• Проверка всех товаров и магазинов из каждого фида.\n"
        "• Максимальная длительность одной проверки — 2 ч 59 мин.\n"
        "• HTTP-проверки URL идут последовательно с рассчитанным интервалом,\n"
        "  чтобы не перегружать сайт.\n"
        "• После завершения проверки система скачивает новый фид.\n"
        "• Сначала проверяется фид магазинов, затем — товаров.\n\n"
        "Алерты в Telegram (всем авторизованным пользователям):\n"
        "• HTTP 4xx или 5xx — страница товара/магазина, изображение, XML-фид;\n"
        "• отсутствует фото в фиде — нет &lt;picture&gt; у товара или &lt;photo&gt; у магазина;\n"
        "• отсутствует категория — нет &lt;categoryId&gt; у товара;\n"
        "• некорректный parentId — родитель категории отсутствует или ссылается на себя.\n\n"
        "Без алертов (только в отчётах «Последняя проверка» / «История»):\n"
        "• прочие пустые поля, устаревшие данные, резкое изменение количества;\n"
        "• уведомления об устранении ранее найденных проблем.\n\n"
        "Telegram-бот используется для уведомлений и просмотра результатов проверок."
    )
    INTERNAL_ERROR = "⚠️ Произошла внутренняя ошибка. Попробуйте позже."
    NO_DATA = "Данные отсутствуют. Автоматическая проверка ещё не выполнялась."
    FEED_DATE_UNKNOWN = "не указана в фиде"
    FINISHED_AT_UNKNOWN = "ещё не завершена"
    DURATION_UNKNOWN = "ещё выполняется"
    ITEM_COUNT_UNKNOWN = "ещё не подсчитано"

    # --- Отчёты о проверках ---
    LAST_CHECK_HEADER = (
        "📊 Последняя автоматическая проверка\n\n"
        "Система периодически скачивает фиды и проверяет все товары и магазины. "
        "Ниже — результат последнего цикла."
    )
    CHECK_SUMMARY_RUNNING = (
        "🗂 {feed_name}\n"
        "⏳ Проверка ещё выполняется\n"
        "Запущена: {started_at}\n"
        "Прошло: {elapsed}"
    )
    CHECK_PREVIOUS_HEADER = "📎 Предыдущая проверка:"
    CHECK_STATS_HEADER = "Что проверяем:"
    CHECK_STATS_ITEMS = "• товаров в фиде: {count}"
    CHECK_STATS_STORES = "• магазинов в фиде: {count}"
    CHECK_STATS_CATEGORIES = "• категорий в дереве: {count}"
    CHECK_STATS_PRODUCT_PAGES = "• URL страниц товаров: {progress}, HTTP 200: {ok}"
    CHECK_STATS_PRODUCT_IMAGES = "• URL изображений товаров: {progress}, HTTP 200: {ok}"
    CHECK_STATS_STORE_PAGES = "• URL страниц магазинов: {progress}, HTTP 200: {ok}"
    CHECK_STATS_STORE_IMAGES = "• URL фото магазинов: {progress}, HTTP 200: {ok}"
    CHECK_STATS_HTTP_TOTAL = "• всего HTTP-запросов: {progress}, HTTP 200: {ok}"
    CHECK_STATS_HTTP_SKIPPED = "• HTTP-проверки пропущены (фид не изменился)"
    CHECK_STATS_PRICES = "• цен товаров: {count}"
    CHECK_STATS_STOCKS = "• остатков товаров: {count}"
    CHECK_STATS_NAMES = "• названий товаров: {count}"
    CHECK_STATS_FEED_DATE = "• фид сформирован: {feed_date}"
    CHECK_STATS_STARTED_AT = "• начало проверки: {started_at}"
    CHECK_STATS_PLANNED_FINISH = "• плановое окончание: {planned_finish}"
    CHECK_SUMMARY_ITEM = (
        "🗂 {feed_name}\n"
        "Статус: {status}\n"
        "Проверено: {item_count}\n"
        "Результат: {problems}\n"
        "Фид сформирован: {feed_date}\n"
        "Скачан и проверен с: {started_at}\n"
        "Завершено: {finished_at}\n"
        "Длилась: {duration}"
    )
    HISTORY_HEADER = (
        "📋 История автоматических проверок\n\n"
        "Здесь показаны последние фоновые проверки каталога."
    )
    HISTORY_ITEM_RUNNING = (
        "{index}. {feed_name}\n"
        "   ⏳ Сейчас выполняется\n"
        "   Запущена: {started_at}"
    )
    HISTORY_ITEM = (
        "{index}. {feed_name}\n"
        "   {status}\n"
        "   Проверено: {item_count}\n"
        "   Результат: {problems}\n"
        "   {started_at} → {finished_at} ({duration})"
    )
    PROBLEMS_NONE = "проблем не обнаружено"
    PROBLEMS_INTERRUPTED = "проверка прервана до завершения (перезапуск сервиса)"
    PROBLEMS_IN_PROGRESS = "результат будет после завершения проверки"
    PROBLEMS_FOUND = "критических — {critical}, предупреждений — {warnings}"

    # --- Администрирование ---
    ADMIN_ACCESS_DENIED = "⛔ Эта функция доступна только администратору."
    ADMIN_USERS_HEADER = "👥 Пользователи"
    ADMIN_NO_USERS = "👥 Пользователи\n\nСписок пуст."
    ADMIN_USER_ITEM = "{index}. {phone}\n   Статус: {status}\n   Telegram: {telegram}"
    ADMIN_ENTER_PHONE = (
        "Введите номер телефона нового пользователя.\n\n"
        "Формат: +79001234567 или 79001234567"
    )
    ADMIN_USER_ADDED = "✅ Пользователь {phone} добавлен."
    ADMIN_USER_DELETED = "✅ Пользователь {phone} удалён."
    ADMIN_USER_BLOCKED = "✅ Пользователь {phone} заблокирован."
    ADMIN_USER_UNBLOCKED = "✅ Пользователь {phone} разблокирован."
    ADMIN_ACTION_DONE = "✅ Действие выполнено."
    ADMIN_INVALID_PHONE = "❌ Некорректный номер телефона. Попробуйте снова."
    ADMIN_USER_NOT_FOUND = "❌ Пользователь не найден."

    BTN_ADMIN_ADD = "➕ Добавить"
    BTN_ADMIN_REFRESH = "🔄 Обновить"
    BTN_ADMIN_BACK = "◀️ Назад"
    BTN_CANCEL = "❌ Отмена"

    # --- Уведомления (автоматический мониторинг) ---
    CHECK_CYCLE_COMPLETED = (
        "✅ Автоматическая проверка завершена.\n\n"
        "Проверено:\n"
        "• Товаров: {products}\n"
        "• Магазинов: {stores}\n\n"
        "Критических ошибок: {critical}\n"
        "Предупреждений: {warnings}\n\n"
        "Время выполнения: {duration}"
    )
    XML_UNAVAILABLE = alert_messages.XML_UNAVAILABLE
    XML_ERROR = alert_messages.XML_ERROR
    PRODUCT_PAGE_UNAVAILABLE = alert_messages.PRODUCT_PAGE_UNAVAILABLE
    PRODUCT_IMAGE_UNAVAILABLE = alert_messages.PRODUCT_IMAGE_UNAVAILABLE
    STORE_IMAGE_UNAVAILABLE = alert_messages.STORE_IMAGE_UNAVAILABLE
    MISSING_REQUIRED_FIELD = alert_messages.MISSING_REQUIRED_FIELD
    PRODUCT_MISSING_PICTURE = alert_messages.PRODUCT_MISSING_PICTURE
    PRODUCT_MISSING_CATEGORY = alert_messages.PRODUCT_MISSING_CATEGORY
    PRODUCT_MISSING_NAME = alert_messages.PRODUCT_MISSING_NAME
    PRODUCT_INVALID_NAME = alert_messages.PRODUCT_INVALID_NAME
    PRODUCT_MISSING_PRICE = alert_messages.PRODUCT_MISSING_PRICE
    PRODUCT_INVALID_PRICE = alert_messages.PRODUCT_INVALID_PRICE
    PRODUCT_LOW_PRICE = alert_messages.PRODUCT_LOW_PRICE
    PRODUCT_INVALID_OLDPRICE = alert_messages.PRODUCT_INVALID_OLDPRICE
    PRODUCT_PRICE_CHANGE = alert_messages.PRODUCT_PRICE_CHANGE
    PRODUCT_INVALID_CATEGORY = alert_messages.PRODUCT_INVALID_CATEGORY
    PRODUCT_MISSING_URL = alert_messages.PRODUCT_MISSING_URL
    DUPLICATE_URLS = alert_messages.DUPLICATE_URLS
    PRODUCT_NEGATIVE_STOCK = alert_messages.PRODUCT_NEGATIVE_STOCK
    PRODUCT_AVAILABLE_AT_ZERO_STOCK = alert_messages.PRODUCT_AVAILABLE_AT_ZERO_STOCK
    PRODUCT_IMAGE_INVALID_CONTENT_TYPE = alert_messages.PRODUCT_IMAGE_INVALID_CONTENT_TYPE
    PRODUCT_IMAGE_EMPTY = alert_messages.PRODUCT_IMAGE_EMPTY
    STORE_IMAGE_INVALID_CONTENT_TYPE = alert_messages.STORE_IMAGE_INVALID_CONTENT_TYPE
    FEED_SIZE_CHANGE = alert_messages.FEED_SIZE_CHANGE
    CATEGORY_INVALID_PARENT = alert_messages.CATEGORY_INVALID_PARENT
    CATEGORY_EMPTY = alert_messages.CATEGORY_EMPTY
    STORE_MISSING_PHOTO = alert_messages.STORE_MISSING_PHOTO
    DUPLICATE_IDS = alert_messages.DUPLICATE_IDS
    COUNT_CHANGE = alert_messages.COUNT_CHANGE
    STALE_DATA = alert_messages.STALE_DATA
    ISSUE_RESOLVED = alert_messages.ISSUE_RESOLVED
