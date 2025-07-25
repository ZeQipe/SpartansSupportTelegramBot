import os
import logging
import re
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
from langdetect import detect, DetectorFactory

# Import new modular services
from core.conversation_manager import ConversationManager
from core.context_builder import ContextBuilder
from core.prompt_manager import PromptManager
from llm.deepseek_client import DeepSeekClient
from llm.llm_service import LLMService
from bot.response_formatter import ResponseFormatter
from bot.admin_handler import AdminHandler

# Keep existing imports for embeddings
from embeddings.line_chunker import LineChunker
from embeddings.embedder import Embedder
from embeddings.vector_store import VectorStore
from embeddings.search import DocumentSearch
from config.settings import BOT_SETTINGS, LLM_SETTINGS

DetectorFactory.seed = 0  # For consistent langdetect
logging.basicConfig(level=logging.INFO)

# Suppress INFO logs from noisy libraries, keep ERROR and WARNING
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- Additional logger for user requests -----------------------------------
os.makedirs('logs', exist_ok=True)
user_logger = logging.getLogger('user_requests')
user_logger.setLevel(logging.INFO)
if not user_logger.handlers:
    req_handler = logging.FileHandler('logs/user_requests.log', encoding='utf-8')
    req_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    user_logger.addHandler(req_handler)

class TelegramHandler:
    """
    SINGLE RESPONSIBILITY: Telegram API interactions and message processing orchestration
    
    Responsibilities:
    - Bot initialization and setup
    - Command handlers (/start, /help, /stats, /language, /sys)
    - Callback handlers (language selection, history reset)
    - Message processing orchestration
    - Admin flow interception and routing
    - Group message mention detection and cleanup
    - Language detection and user preference storage
    - Error handling for Telegram-specific errors
    - Bot username caching for group mentions
    
    Delegates business logic to specialized services
    """
    
    def __init__(self, telegram_token: str, deepseek_api_key: str):
        # Initialize with new modular services but keep message processing in same class
        self.application = Application.builder().token(telegram_token).build()
        
        # Initialize embeddings infrastructure (keep existing)
        self.chunker = LineChunker()  # используем новый алгоритм
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.search = DocumentSearch(self.vector_store, self.embedder)
        
        # Initialize new modular services
        self.conversation_manager = ConversationManager()
        self.context_builder = ContextBuilder(self.search)
        self.prompt_manager = PromptManager()
        
        deepseek_client = DeepSeekClient(deepseek_api_key)
        self.llm_service = LLMService(deepseek_client, self.prompt_manager)
        
        self.response_formatter = ResponseFormatter()
        self.admin_handler = AdminHandler(os.getenv('BOT_SYS_PASSWORD', ''))

        self.bot_username: str = ""  # будет заполнено при первом обращении

        self.load_documents()
        self._setup_handlers()
    
    def load_documents(self):
        """(Re)index documents and provide detailed logging."""
        before_total = self.vector_store.get_stats().get('total_embeddings', 0)
        stats = self.vector_store.load_documents('data', self.chunker, self.embedder)
        total = self.vector_store.get_stats().get('total_embeddings', 0)
        logger.info(
            f"Document indexing stats: added {stats['added']}, updated {stats['updated']}, skipped {stats['skipped']} | total vectors in DB: {total}")

        for info in stats['files']:
            logger.info(
                f"  {info['status'].upper():7} {info['path']} | chunks: {info.get('chunks', 0)}"
            )
    
    def _setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_conversation))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("sys", self.sys_command))

        # Callback & message handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def sys_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate admin flow for updating system prompt."""
        if update.effective_user is None or update.message is None:
            return
        user_id = update.effective_user.id
        response = self.admin_handler.handle_sys_command(user_id)
        await update.message.reply_text(response)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        EXACT COPY: Current handle_message logic but delegating to new services
        Keep all logic in this method but use injected services
        """
        if update.effective_user is None or update.message is None or update.message.text is None:
            logger.error('Invalid message text')
            return

        # Сырое сообщение
        message_text: str = update.message.text.strip()

        # ---------- Admin flow interception -----------------------------------
        user_id = update.effective_user.id
        is_admin_message, admin_response = self.admin_handler.handle_admin_message(user_id, message_text)
        if is_admin_message:
            await update.message.reply_text(admin_response)
            return  # Do not continue normal processing

        # Log the incoming request details
        user_logger.info(f"user_id={update.effective_user.id} username={update.effective_user.username or ''} text={message_text}")

        # --- Ignore group messages unless bot is mentioned first -------------------------
        if update.effective_chat and update.effective_chat.type in ['group', 'supergroup']:
            if not self.bot_username:
                try:
                    me = await context.bot.get_me()
                    self.bot_username = (me.username or '').lower()
                except Exception as e:
                    logger.warning(f'Failed to fetch bot username: {e}')
            mention_prefix = f'@{self.bot_username}' if self.bot_username else ''
            if mention_prefix:
                if not message_text.lower().startswith(mention_prefix):
                    return  # бот не упомянут первым
                # убираем упоминание из начала текста
                message_text = message_text[len(mention_prefix):].lstrip()
                if not message_text:
                    return  # пустой запрос после упоминания

        # Auto-detect language and store preference
        query_language = 'en'
        try:
            query_language_detected = detect(message_text)
            if query_language_detected in ['en', 'ru']:
                query_language = query_language_detected
                self.conversation_manager.set_user_language(user_id, query_language)
        except Exception as e:
            logger.warning(f'Language detection failed: {e}')

        user_language = self.conversation_manager.get_user_language(user_id, query_language)
        await update.message.reply_chat_action('typing')
        try:
            # Use new modular services
            doc_context = self.context_builder.get_context_for_query(message_text, query_language)
            history = self.conversation_manager.get_history(user_id)
            response = self.llm_service.generate_support_response(message_text, doc_context, history, language=user_language)
            
            # Use response formatter
            formatted_response = self.response_formatter.format_response(response, message_text, user_language)

            self.conversation_manager.add_message(user_id, 'user', message_text)
            self.conversation_manager.add_message(user_id, 'bot', formatted_response)
            await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f'Error: {e}')
            error_msg = 'Ситуация кажется серьёзной, я уже зову оператора - он подойдёт через минуту.' if user_language == 'ru' else 'The situation seems serious, I\'m calling an operator - they\'ll join in a minute.'
            await update.message.reply_text(error_msg)
    
    async def start_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user is None or update.message is None:
            logger.error('Invalid update in start_conversation')
            return
        user_id = update.effective_user.id
        user_language = self.conversation_manager.get_user_language(user_id, 'en')
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
            self.conversation_manager.set_user_language(user_id, lang)
            await query.answer('Language changed!')
            await self.start_conversation(update, context)
        elif data == 'reset':
            self.conversation_manager.reset_history(user_id)
            await query.answer('History reset!')
            await self.start_conversation(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help text."""
        help_text = (
            "Ask me anything about deposits, withdrawals, bonuses or rules. "
            "Use /language to switch language, /stats for index stats, or simply type your question.")
        if update.message is not None:
            await update.message.reply_text(help_text)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show vector store stats."""
        stats = self.vector_store.get_stats()
        if update.message is not None:
            await update.message.reply_text(f"Indexed chunks: {stats.get('total_embeddings', 0)}")

    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show language selection keyboard."""
        await self.start_conversation(update, context)

    def run(self):
        self.application.run_polling()

def main():
    # Load .env file variables if present
    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    if not telegram_token:
        raise ValueError('TELEGRAM_TOKEN is required')
    if not deepseek_api_key:
        raise ValueError('DEEPSEEK_API_KEY is required')
    bot = TelegramHandler(telegram_token, deepseek_api_key)
    bot.run()

if __name__ == '__main__':
    main() 