# TelSuppBot - Telegram Support Bot

Telegram бот для автоматической поддержки клиентов Spartans.com на основе документов и правил компании.

## Возможности

- 🤖 Автоматические ответы на вопросы клиентов
- 🌍 Поддержка русского и английского языков
- 📚 Поиск по документам: правила букмекерской конторы, бонусы, условия использования
- 🔍 Семантический поиск с использованием векторных эмбеддингов
- 💬 История разговоров для каждого пользователя
- 📊 Статистика документов и использования

## Архитектура

```
TelSuppBot/
├── data/                 # Документы на разных языках
│   ├── en/              # Английские документы
│   └── ru/              # Русские документы
├── embeddings/          # Система эмбеддингов и поиска
│   ├── chunker.py       # Разбиение документов на чанки
│   ├── embedder.py      # Создание эмбеддингов
│   ├── vector_store.py  # Векторное хранилище
│   └── search.py        # Система поиска
├── llm/                 # Интеграция с LLM
│   └── deepseek_api.py  # DeepSeek API
├── bot/                 # Telegram бот
│   └── main.py          # Основной файл бота
└── config/              # Конфигурация
```

## Установка

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd TelSuppBot
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
Создайте файл `.env` в корне проекта:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 4. Получение токенов

#### Telegram Bot Token
1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

#### DeepSeek API Key
1. Зарегистрируйтесь на [DeepSeek](https://platform.deepseek.com/)
2. Получите API ключ в разделе API Keys
3. Скопируйте ключ в переменную окружения

## Запуск

### Запуск бота
```bash
python bot/main.py
```

### Первый запуск
При первом запуске бот автоматически:
1. Загрузит все документы из папки `data/`
2. Разобьет их на семантические чанки
3. Создаст векторные эмбеддинги
4. Индексирует документы для быстрого поиска

## Использование

### Команды бота
- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/language` - Изменить язык (Русский/English)
- `/stats` - Статистика документов

### Примеры вопросов
- "Какие минимальные ставки?"
- "Как вывести деньги?"
- "Какие бонусы доступны?"
- "Правила для спортивных ставок"
- "Какие документы нужны для верификации?"

## Конфигурация

### Настройка чанкинга
В файле `embeddings/chunker.py` можно настроить:
- Размер чанков (`chunk_size`)
- Перекрытие между чанками (`overlap`)

### Настройка поиска
В файле `embeddings/search.py` можно настроить:
- Количество результатов поиска (`top_k`)
- Фильтры по языку и типу документа

### Настройка LLM
В файле `llm/deepseek_api.py` можно настроить:
- Модель DeepSeek
- Параметры генерации (temperature, max_tokens)

## Структура документов

Бот поддерживает следующие типы документов:
- `sportsbook_rules.txt` - Правила букмекерской конторы
- `bonus_rules.txt` - Правила бонусов
- `terms.txt` - Условия использования
- `privacy_policy.txt` - Политика конфиденциальности
- `aml_policy.txt` - AML политика
- `promotions.txt` - Акции и промо

## Технологии

- **Python 3.8+**
- **python-telegram-bot** - Telegram Bot API
- **sentence-transformers** - Создание эмбеддингов
- **DeepSeek API** - Генерация ответов
- **NumPy** - Работа с векторами
- **Requests** - HTTP запросы

## Разработка

### Добавление новых документов
1. Поместите документ в соответствующую папку (`data/en/` или `data/ru/`)
2. Перезапустите бота для переиндексации

### Добавление новых языков
1. Создайте папку для нового языка в `data/`
2. Добавьте документы на новом языке
3. Обновите код в `bot/main.py` для поддержки нового языка

### Тестирование
```bash
# Тест подключения к API
python -c "from llm.deepseek_api import DeepSeekAPI; print(DeepSeekAPI('test').test_connection())"

# Тест чанкинга
python -c "from embeddings.chunker import DocumentChunker; chunker = DocumentChunker(); print('Chunker initialized')"
```

## Лицензия

MIT License

## Поддержка

Для вопросов и предложений создавайте Issues в репозитории.

## Admin prompt update

Set two environment variables for prompt update via `/sys` command:

- `BOT_ADMIN_IDS` – comma-separated Telegram user IDs allowed to update the prompt.
- `BOT_SYS_PASSWORD` – password requested after `/sys`.

Sequence: `/sys` → enter password → send new system prompt. Old prompt is archived with timestamp, new one applied immediately without bot restart.
