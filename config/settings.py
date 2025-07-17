"""
Конфигурационные настройки для TelSuppBot
"""

import os
from dotenv import load_dotenv, find_dotenv
from typing import Dict, Any

# Load environment variables from a .env file if present (helps when running tests)
load_dotenv(find_dotenv())

# Настройки чанкинга
CHUNK_SETTINGS = {
    'chunk_size': 300,  # Target chunk size in tokens
    'overlap': 50,      # Overlap in tokens
}

# Настройки OpenAI embeddings
EMBEDDING_SETTINGS = {
    # Preferred model; falls back automatically in Embedder if unavailable
    'model_name': 'text-embedding-3-small',
    'device': None,  # Устройство (None для автоопределения)
    'dimensions': 1536
}

# Настройки ChromaDB
CHROMADB_SETTINGS = {
    'persist_directory': 'chroma_db',  'collection_name': 'spartans_docs'
}

# Настройки поиска
SEARCH_SETTINGS = {
    'default_top_k': 15,  # Количество результатов по умолчанию
    'max_top_k': 30,     # Максимальное количество результатов
    'similarity_threshold': 0.3,  # Минимальный порог сходства
    'enable_fuzzy_search': True,
    'preprocess_type': 'simple'  # or 'deepseek'
}

# Настройки LLM
LLM_SETTINGS = {
    'model': 'deepseek-chat',
    'max_tokens': 800,
    'temperature': 0.5,
    'timeout': 30,  # Таймаут запроса в секундах
}

# Настройки бота
BOT_SETTINGS = {
    'max_history_length': 20,  # Максимальная длина истории разговора
    'typing_delay': 1.0,       # Задержка перед отправкой "печатает"
    'max_message_length': 4096,  # Максимальная длина сообщения Telegram
}

# Настройки персонализации пользователей
USER_PREFERENCES = {
    'auto_append_context': True,
    'preferences_expire_days': 30,
    'enable_structured_dialog': True,
}

# Настройки логирования
LOGGING_SETTINGS = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'telsuppbot.log',
}

# Поддерживаемые языки
SUPPORTED_LANGUAGES = ['en', 'ru']

# API ключи (из .env)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
