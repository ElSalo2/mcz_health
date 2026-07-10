"""Шаблоны Telegram-алертов и сообщений мониторинга каталога."""

# --- CRITICAL ---

XML_UNAVAILABLE = (
    "🚨 Источник данных недоступен\n\n"
    "Тип ошибки:\n"
    "XML_UNAVAILABLE\n\n"
    "Фид:\n"
    "{feed_name}\n\n"
    "URL:\n"
    "{feed_url}\n\n"
    "Причина:\n"
    "{reason}\n\n"
    "HTTP:\n"
    "{status_code}\n\n"
    "Время проверки:\n"
    "{check_datetime}"
)

XML_ERROR = (
    "🚨 Ошибка структуры данных\n\n"
    "Тип ошибки:\n"
    "XML_ERROR\n\n"
    "Фид:\n"
    "{feed_name}\n\n"
    "Причина:\n"
    "{reason}\n\n"
    "Описание:\n"
    "XML не удалось обработать или структура данных не соответствует ожидаемой.\n\n"
    "Время проверки:\n"
    "{check_datetime}"
)

PRODUCT_PAGE_UNAVAILABLE = (
    "🚨 Недоступна страница товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_PAGE_UNAVAILABLE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "HTTP:\n"
    "{status_code}\n\n"
    "Причина:\n"
    "{reason}\n\n"
    "Время проверки:\n"
    "{check_datetime}"
)

PRODUCT_IMAGE_UNAVAILABLE = (
    "🚨 Недоступно изображение товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_IMAGE_UNAVAILABLE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка товара:\n"
    "{product_url}\n\n"
    "Изображение:\n"
    "{image_url}\n\n"
    "Номер изображения:\n"
    "{image_number}\n\n"
    "HTTP:\n"
    "{status_code}\n\n"
    "Причина:\n"
    "{reason}\n\n"
    "Время проверки:\n"
    "{check_datetime}"
)

STORE_IMAGE_UNAVAILABLE = (
    "🚨 Недоступна фотография магазина\n\n"
    "Тип ошибки:\n"
    "STORE_IMAGE_UNAVAILABLE\n\n"
    "Магазин:\n"
    "{name}\n\n"
    "ID магазина:\n"
    "{company_id}\n\n"
    "Адрес:\n"
    "{address}\n\n"
    "Изображение:\n"
    "{image_url}\n\n"
    "HTTP:\n"
    "{status_code}\n\n"
    "Причина:\n"
    "{reason}\n\n"
    "Время проверки:\n"
    "{check_datetime}"
)

PRODUCT_MISSING_PICTURE = (
    "🚨 У товара отсутствует изображение\n\n"
    "Тип ошибки:\n"
    "PRODUCT_MISSING_PICTURE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Причина:\n"
    "В карточке товара отсутствует обязательное поле picture."
)

STORE_MISSING_PHOTO = (
    "🚨 У магазина отсутствует фотография\n\n"
    "Тип ошибки:\n"
    "STORE_MISSING_PHOTO\n\n"
    "Магазин:\n"
    "{name}\n\n"
    "ID:\n"
    "{company_id}\n\n"
    "Адрес:\n"
    "{address}\n\n"
    "Причина:\n"
    "В данных магазина отсутствует обязательное поле photo."
)

PRODUCT_MISSING_CATEGORY = (
    "🚨 У товара отсутствует категория\n\n"
    "Тип ошибки:\n"
    "PRODUCT_MISSING_CATEGORY\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Причина:\n"
    "Не указана категория товара."
)

PRODUCT_INVALID_CATEGORY = (
    "🚨 У товара указана неизвестная категория\n\n"
    "Тип ошибки:\n"
    "PRODUCT_INVALID_CATEGORY\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Category ID:\n"
    "{category_id}\n\n"
    "Причина:\n"
    "Категория отсутствует в дереве категорий."
)

PRODUCT_MISSING_NAME = (
    "🚨 У товара отсутствует название\n\n"
    "Тип ошибки:\n"
    "PRODUCT_MISSING_NAME\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Причина:\n"
    "Поле name отсутствует или пустое."
)

PRODUCT_MISSING_PRICE = (
    "🚨 У товара отсутствует цена\n\n"
    "Тип ошибки:\n"
    "PRODUCT_MISSING_PRICE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Цена:\n"
    "{price}\n\n"
    "Причина:\n"
    "Поле price отсутствует или содержит некорректное значение."
)

PRODUCT_INVALID_PRICE = (
    "🚨 Некорректная цена товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_INVALID_PRICE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Цена:\n"
    "{price}\n\n"
    "Причина:\n"
    "Цена должна быть больше нуля."
)

CATEGORY_INVALID_PARENT = (
    "🚨 Ошибка структуры категорий\n\n"
    "Тип ошибки:\n"
    "CATEGORY_INVALID_PARENT\n\n"
    "Категория:\n"
    "{name}\n\n"
    "Category ID:\n"
    "{category_id}\n\n"
    "Родитель:\n"
    "{parent_id}\n\n"
    "Причина:\n"
    "{reason}"
)

DUPLICATE_IDS = (
    "🚨 Обнаружены дубли идентификаторов\n\n"
    "Тип ошибки:\n"
    "DUPLICATE_IDS\n\n"
    "Тип объекта:\n"
    "{object_type}\n\n"
    "Поле:\n"
    "{id_field}\n\n"
    "Количество:\n"
    "{count}\n\n"
    "Значения:\n"
    "{duplicates}"
)

# --- WARNING (Telegram) ---

COUNT_CHANGE = (
    "⚠️ Изменилось количество объектов\n\n"
    "Тип ошибки:\n"
    "COUNT_CHANGE\n\n"
    "Объект:\n"
    "{object_type}\n\n"
    "Предыдущее количество:\n"
    "{previous_count}\n\n"
    "Текущее количество:\n"
    "{current_count}\n\n"
    "Изменение:\n"
    "{percent}%"
)

FEED_SIZE_CHANGE = (
    "⚠️ Изменился размер фида\n\n"
    "Тип ошибки:\n"
    "FEED_SIZE_CHANGE\n\n"
    "Фид:\n"
    "{feed_name}\n\n"
    "Предыдущий размер:\n"
    "{previous_size}\n\n"
    "Текущий размер:\n"
    "{current_size}\n\n"
    "Изменение:\n"
    "{percent}%"
)

STALE_DATA = (
    "⚠️ Данные давно не обновлялись\n\n"
    "Тип ошибки:\n"
    "STALE_DATA\n\n"
    "Объект:\n"
    "{object_type}\n\n"
    "Дата формирования:\n"
    "{feed_date}\n\n"
    "Возраст данных:\n"
    "{age}"
)

PRODUCT_LOW_PRICE = (
    "⚠️ Подозрительно низкая цена\n\n"
    "Тип ошибки:\n"
    "PRODUCT_LOW_PRICE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Цена:\n"
    "{price}\n\n"
    "Минимальный порог:\n"
    "{threshold}"
)

PRODUCT_INVALID_OLDPRICE = (
    "⚠️ Некорректная старая цена\n\n"
    "Тип ошибки:\n"
    "PRODUCT_INVALID_OLDPRICE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Цена:\n"
    "{price}\n\n"
    "Старая цена:\n"
    "{oldprice}\n\n"
    "Причина:\n"
    "oldprice должна быть выше текущей цены."
)

# --- Без Telegram (отчёты) ---

PRODUCT_PRICE_CHANGE = (
    "⚠️ Резкое изменение цены товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_PRICE_CHANGE\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Ссылка:\n"
    "{product_url}\n\n"
    "Предыдущая цена:\n"
    "{old_price}\n\n"
    "Текущая цена:\n"
    "{price}\n\n"
    "Изменение:\n"
    "{percent}%"
)

PRODUCT_MISSING_URL = (
    "🚨 У товара отсутствует URL\n\n"
    "Тип ошибки:\n"
    "PRODUCT_MISSING_URL\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Причина:\n"
    "Отсутствует обязательное поле url."
)

DUPLICATE_URLS = (
    "🚨 Обнаружены повторяющиеся URL товаров\n\n"
    "Тип ошибки:\n"
    "DUPLICATE_URLS\n\n"
    "URL:\n"
    "{url}\n\n"
    "Количество повторений:\n"
    "{count}"
)

PRODUCT_NEGATIVE_STOCK = (
    "⚠️ Отрицательный остаток товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_NEGATIVE_STOCK\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Остаток:\n"
    "{stock}"
)

PRODUCT_AVAILABLE_AT_ZERO_STOCK = (
    "⚠️ Товар доступен при нулевом остатке\n\n"
    "Тип ошибки:\n"
    "PRODUCT_AVAILABLE_AT_ZERO_STOCK\n\n"
    "Товар:\n"
    "{name}\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Остаток:\n"
    "{stock}\n\n"
    "available:\n"
    "{available}"
)

PRODUCT_IMAGE_INVALID_CONTENT_TYPE = (
    "⚠️ Некорректный Content-Type изображения товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_IMAGE_INVALID_CONTENT_TYPE\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Название:\n"
    "{name}\n\n"
    "Изображение №{image_number}\n\n"
    "Content-Type:\n"
    "{status_code}\n\n"
    "URL:\n"
    "{image_url}"
)

PRODUCT_IMAGE_EMPTY = (
    "⚠️ Пустое изображение товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_IMAGE_EMPTY\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Название:\n"
    "{name}\n\n"
    "Изображение №{image_number}\n\n"
    "URL:\n"
    "{image_url}"
)

STORE_IMAGE_INVALID_CONTENT_TYPE = (
    "⚠️ Некорректный Content-Type фото магазина\n\n"
    "Тип ошибки:\n"
    "STORE_IMAGE_INVALID_CONTENT_TYPE\n\n"
    "Магазин:\n"
    "{name}\n\n"
    "Фото №{image_number}\n\n"
    "Content-Type:\n"
    "{status_code}\n\n"
    "URL:\n"
    "{image_url}"
)

PRODUCT_INVALID_NAME = (
    "⚠️ Некорректное название товара\n\n"
    "Тип ошибки:\n"
    "PRODUCT_INVALID_NAME\n\n"
    "Артикул:\n"
    "{offer_id}\n\n"
    "Текущее значение:\n"
    "{name}"
)

CATEGORY_EMPTY = (
    "⚠️ Категория не содержит товаров\n\n"
    "Тип ошибки:\n"
    "CATEGORY_EMPTY\n\n"
    "Категория:\n"
    "{name}\n\n"
    "ID:\n"
    "{category_id}\n\n"
    "Причина:\n"
    "{reason}"
)

MISSING_REQUIRED_FIELD = (
    "🚨 Обнаружены некорректные данные\n\n"
    "Тип ошибки:\n"
    "MISSING_REQUIRED_FIELD\n\n"
    "Объект:\n"
    "{name}\n\n"
    "Отсутствует поле:\n"
    "{field}"
)

# --- Устранение проблемы ---

ISSUE_RESOLVED = (
    "✅ Проблема устранена\n\n"
    "Тип ошибки:\n"
    "{error_code}\n\n"
    "Объект:\n"
    "{object}\n\n"
    "Описание:\n"
    "{description}\n\n"
    "Время устранения:\n"
    "{datetime}"
)

# Все ключи алертов для реестра Messages
ALERT_MESSAGE_KEYS = (
    "XML_UNAVAILABLE",
    "XML_ERROR",
    "PRODUCT_PAGE_UNAVAILABLE",
    "PRODUCT_IMAGE_UNAVAILABLE",
    "STORE_IMAGE_UNAVAILABLE",
    "PRODUCT_MISSING_PICTURE",
    "STORE_MISSING_PHOTO",
    "PRODUCT_MISSING_CATEGORY",
    "PRODUCT_INVALID_CATEGORY",
    "PRODUCT_MISSING_NAME",
    "PRODUCT_MISSING_PRICE",
    "PRODUCT_INVALID_PRICE",
    "CATEGORY_INVALID_PARENT",
    "DUPLICATE_IDS",
    "COUNT_CHANGE",
    "FEED_SIZE_CHANGE",
    "STALE_DATA",
    "PRODUCT_LOW_PRICE",
    "PRODUCT_INVALID_OLDPRICE",
    "PRODUCT_PRICE_CHANGE",
    "PRODUCT_MISSING_URL",
    "DUPLICATE_URLS",
    "PRODUCT_NEGATIVE_STOCK",
    "PRODUCT_AVAILABLE_AT_ZERO_STOCK",
    "PRODUCT_IMAGE_INVALID_CONTENT_TYPE",
    "PRODUCT_IMAGE_EMPTY",
    "STORE_IMAGE_INVALID_CONTENT_TYPE",
    "PRODUCT_INVALID_NAME",
    "CATEGORY_EMPTY",
    "MISSING_REQUIRED_FIELD",
    "ISSUE_RESOLVED",
)
