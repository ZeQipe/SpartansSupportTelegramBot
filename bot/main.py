import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from langdetect import detect, DetectorFactory
from bot.history_manager import HistoryManager
from embeddings.chunker import DocumentChunker
from embeddings.embedder import Embedder
from embeddings.vector_store import VectorStore
from embeddings.search import DocumentSearch
from llm.deepseek_api import DeepSeekAPI
from config.settings import BOT_SETTINGS, LLM_SETTINGS

DetectorFactory.seed = 0  # For consistent langdetect
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelSuppBot:
    def __init__(self, telegram_token: str, deepseek_api_key: str):
        self.application = Application.builder().token(telegram_token).build()
        self.history_manager = HistoryManager()
        self.chunker = DocumentChunker()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.search = DocumentSearch(self.vector_store, self.embedder)
        self.llm = DeepSeekAPI(deepseek_api_key)
        self.user_languages = {}  # {user_id: 'en' or 'ru'}
        self.load_documents()
        self._setup_handlers()
    
    def load_documents(self):
        chunks = self.chunker.process_all_documents('data')
        embeddings_data = self.embedder.embed_chunks(chunks)
        self.vector_store.add_embeddings(embeddings_data)
    
    def _setup_handlers(self):
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user is None or update.message is None or update.message.text is None:
            logger.error('Invalid message text')
            return
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        if message_text.lower() == 'старт':
            await self.start_conversation(update, context)
            return
        user_language = self.user_languages.get(user_id, 'en')
        await update.message.reply_chat_action('typing')
        try:
            query_language = detect(message_text)
            if query_language not in ['en', 'ru']:
                query_language = 'en'
            processed_query = self.search.preprocess_query(message_text, query_language)
            contexts = self.search.get_multilingual_context(processed_query, top_k=15)
            doc_context = contexts.get(query_language, '') or next(iter(contexts.values()), '')
            history = self.history_manager.get_history(user_id)
            response = self.llm.generate_support_response(message_text, doc_context, history, language=user_language)
            self.history_manager.add_message(user_id, 'user', message_text)
            self.history_manager.add_message(user_id, 'bot', response)
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f'Error: {e}')
            error_msg = 'Ситуация кажется серьёзной, я уже зову оператора - он подойдёт через минуту.' if user_language == 'ru' else 'The situation seems serious, I\'m calling an operator - they\'ll join in a minute.'
            await update.message.reply_text(error_msg)
    
    async def start_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user is None or update.message is None:
            logger.error('Invalid update in start_conversation')
            return
        user_id = update.effective_user.id
        user_language = self.user_languages.get(user_id, 'en')
        greeting = 'Привет! Я помощник поддержки Spartans.com. Чем могу помочь?' if user_language == 'ru' else 'Hi! I\'m the Spartans.com support assistant. How can I help?'
        keyboard = [[InlineKeyboardButton('RU', callback_data='lang_ru'), InlineKeyboardButton('EN', callback_data='lang_en')],
                    [InlineKeyboardButton('Сбросить историю' if user_language == 'ru' else 'Reset history', callback_data='reset')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(greeting, reply_markup=reply_markup)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query is None or query.from_user is None or query.data is None:
            logger.error('Invalid callback data')
            return
        user_id = query.from_user.id
        data = query.data
        if data.startswith('lang_'):
            lang = data.split('_')[1]
            self.user_languages[user_id] = lang
            await query.answer('Language changed!')
            await self.start_conversation(update, context)
        elif data == 'reset':
            self.history_manager.reset_history(user_id)
            await query.answer('History reset!')
            await self.start_conversation(update, context)
    
    def run(self):
        self.application.run_polling()

def main():
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    if not telegram_token:
        raise ValueError('TELEGRAM_TOKEN is required')
    if not deepseek_api_key:
        raise ValueError('DEEPSEEK_API_KEY is required')
    bot = TelSuppBot(telegram_token, deepseek_api_key)
    bot.run()

if __name__ == '__main__':
    main()
