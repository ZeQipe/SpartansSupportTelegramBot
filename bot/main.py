import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import os
from typing import Dict, Any

from embeddings.chunker import DocumentChunker
from embeddings.embedder import Embedder
from embeddings.vector_store import VectorStore
from embeddings.search import DocumentSearch
from llm.deepseek_api import DeepSeekAPI

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelSuppBot:
    """Основной класс Telegram бота для поддержки клиентов"""
    
    def __init__(self, telegram_token: str, deepseek_api_key: str):
        self.telegram_token = telegram_token
        self.deepseek_api_key = deepseek_api_key
        
        # Инициализация компонентов
        self.chunker = DocumentChunker()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.search = DocumentSearch(self.vector_store, self.embedder)
        self.llm = DeepSeekAPI(deepseek_api_key)
        
        # История разговоров пользователей
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
        # Инициализация бота
        self.application = Application.builder().token(telegram_token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Обработка кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Инициализация сессии пользователя
        self.user_sessions[user.id] = {
            'language': 'en',
            'conversation_history': []
        }
        
        welcome_text = f"""Привет, {user.first_name}! 👋

Я - помощник службы поддержки Spartans.com. Я могу ответить на ваши вопросы о:
• Правилах букмекерской конторы
• Бонусах и акциях
• Условиях использования
• Политике конфиденциальности
• AML политике

Просто задайте мне любой вопрос!

/help - показать справку
/language - изменить язык
"""
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """📚 **Справка по командам:**

/start - Начать работу с ботом
/help - Показать эту справку
/language - Изменить язык (Русский/English)
/stats - Статистика документов

💡 **Как использовать:**
Просто напишите ваш вопрос, и я найду ответ в документах Spartans.com.

🔍 **Примеры вопросов:**
• "Какие минимальные ставки?"
• "Как вывести деньги?"
• "Какие бонусы доступны?"
• "Правила для спортивных ставок"

Я отвечу на основе официальных документов компании.
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /language"""
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите язык / Choose language:",
            reply_markup=reply_markup
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        stats = self.search.get_document_stats()
        
        stats_text = f"""📊 **Статистика документов:**

📄 Всего чанков: {stats['total_embeddings']}
🔤 Языки: {', '.join(stats['languages'])}
📋 Типы документов: {', '.join(stats['document_types'])}

📈 **По языкам:**
"""
        for lang, count in stats['language_counts'].items():
            stats_text += f"• {lang.upper()}: {count} чанков\n"
        
        stats_text += "\n📋 **По типам документов:**\n"
        for doc_type, count in stats['document_type_counts'].items():
            stats_text += f"• {doc_type}: {count} чанков\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("lang_"):
            language = query.data.split("_")[1]
            user_id = query.from_user.id
            
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {'language': language, 'conversation_history': []}
            else:
                self.user_sessions[user_id]['language'] = language
            
            if language == "ru":
                await query.edit_message_text("✅ Язык изменен на русский!")
            else:
                await query.edit_message_text("✅ Language changed to English!")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # Получаем язык пользователя
        user_language = self.user_sessions.get(user_id, {}).get('language', 'en')
        
        # Отправляем индикатор набора
        await update.message.reply_chat_action("typing")
        
        try:
            # Ищем релевантный контекст
            contexts = self.search.get_multilingual_context(user_message, top_k=2)
            
            if not contexts:
                if user_language == "ru":
                    response = "Извините, я не нашел релевантной информации в документах. Попробуйте переформулировать вопрос."
                else:
                    response = "Sorry, I couldn't find relevant information in the documents. Please try rephrasing your question."
            else:
                # Генерируем ответ на основе контекста
                if user_language in contexts:
                    # Используем контекст на языке пользователя
                    response = self.llm.answer_with_context(user_message, contexts[user_language], user_language)
                else:
                    # Используем контекст на другом языке
                    available_language = list(contexts.keys())[0]
                    response = self.llm.answer_with_context(user_message, contexts[available_language], user_language)
            
            # Сохраняем в историю
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {'language': user_language, 'conversation_history': []}
            
            self.user_sessions[user_id]['conversation_history'].append({
                'user': user_message,
                'bot': response,
                'timestamp': update.message.date.isoformat()
            })
            
            # Ограничиваем историю
            if len(self.user_sessions[user_id]['conversation_history']) > 10:
                self.user_sessions[user_id]['conversation_history'] = \
                    self.user_sessions[user_id]['conversation_history'][-10:]
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_message = "Произошла ошибка при обработке вашего запроса. Попробуйте позже." if user_language == "ru" else "An error occurred while processing your request. Please try again later."
            await update.message.reply_text(error_message)
    
    def load_documents(self, data_dir: str = "data"):
        """Загружает и индексирует документы"""
        logger.info("Loading and indexing documents...")
        
        # Разбиваем документы на чанки
        chunks = self.chunker.process_all_documents(data_dir)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Создаем эмбеддинги
        embeddings_data = self.embedder.embed_chunks(chunks)
        logger.info(f"Created embeddings for {len(embeddings_data)} chunks")
        
        # Добавляем в векторное хранилище
        self.vector_store.add_embeddings(embeddings_data)
        logger.info("Documents indexed successfully")
        
        # Сохраняем статистику
        stats = self.search.get_document_stats()
        logger.info(f"Index contains {stats['total_embeddings']} embeddings")
    
    def run(self):
        """Запускает бота"""
        logger.info("Starting TelSuppBot...")
        
        # Загружаем документы
        self.load_documents()
        
        # Запускаем бота
        self.application.run_polling()

def main():
    """Основная функция"""
    # Получаем токены из переменных окружения
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not telegram_token:
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    # Создаем и запускаем бота
    bot = TelSuppBot(telegram_token, deepseek_api_key)
    bot.run()

if __name__ == "__main__":
    main()
