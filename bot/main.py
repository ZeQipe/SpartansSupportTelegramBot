import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
from langdetect import detect, DetectorFactory
from bot.history_manager import HistoryManager
# from embeddings.chunker import DocumentChunker  # legacy
from embeddings.line_chunker import LineChunker  # Новая версия чанкинга
from embeddings.embedder import Embedder
from embeddings.vector_store import VectorStore
from embeddings.search import DocumentSearch
from llm.deepseek_api import DeepSeekAPI
from config.settings import BOT_SETTINGS, LLM_SETTINGS

DetectorFactory.seed = 0  # For consistent langdetect
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Additional logger for user requests -----------------------------------
os.makedirs('logs', exist_ok=True)
user_logger = logging.getLogger('user_requests')
user_logger.setLevel(logging.INFO)
if not user_logger.handlers:
    req_handler = logging.FileHandler('logs/user_requests.log', encoding='utf-8')
    req_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    user_logger.addHandler(req_handler)

class TelSuppBot:
    def __init__(self, telegram_token: str, deepseek_api_key: str):
        self.application = Application.builder().token(telegram_token).build()
        self.history_manager = HistoryManager()
        self.chunker = LineChunker()  # используем новый алгоритм
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.search = DocumentSearch(self.vector_store, self.embedder)
        self.llm = DeepSeekAPI(deepseek_api_key)
        self.user_languages = {}  # {user_id: 'en' or 'ru'}
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

        # Callback & message handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user is None or update.message is None or update.message.text is None:
            logger.error('Invalid message text')
            return

        # Сырое сообщение
        message_text: str = update.message.text.strip()

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

        user_id = update.effective_user.id
        # Auto-detect language and store preference
        query_language = 'en'
        try:
            query_language_detected = detect(message_text)
            if query_language_detected in ['en', 'ru']:
                query_language = query_language_detected
                self.user_languages[user_id] = query_language
        except Exception as e:
            logger.warning(f'Language detection failed: {e}')

        user_language = self.user_languages.get(user_id, query_language)
        await update.message.reply_chat_action('typing')
        try:
            processed_query = self.search.preprocess_query(message_text, query_language)
            contexts = self.search.get_multilingual_context(processed_query, top_k=25)
            def sanitize_emails(text: str):
                return re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[email removed]', text)

            doc_context_raw = contexts.get(query_language, '') or next(iter(contexts.values()), '')
            doc_context = sanitize_emails(doc_context_raw)
            history = self.history_manager.get_history(user_id)
            response = self.llm.generate_support_response(message_text, doc_context, history, language=user_language)
            if '[ESCALATE]' in response:
                # Сразу показываем полный текст без дублирующего системного сообщения
                response = response.replace('[ESCALATE]', '').lstrip()
            # Преобразуем **** в жирный Markdown и убираем ### заголовки
            response = re.sub(r'^#{1,6}\s*', '', response, flags=re.MULTILINE)
            response = re.sub(r'^\*{4}\s*(.+)', r'**\1**', response, flags=re.MULTILINE)

            # Дополнительная зачистка: если пользователь не запросил источники, удаляем упоминания "источник"/"sources"
            user_asked_sources = bool(re.search(r'(источник|sources?)', message_text, re.IGNORECASE))

            def remove_sources(text: str):
                # Удаляем шаблоны вида (источник 1, 2) или (sources 3,4)
                text = re.sub(r'\(\s*(источник\w*|sources?)\s*[^)]*\)', '', text, flags=re.IGNORECASE)
                return text

            # Удаляем email
            response = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '', response)

            # Удаляем фразы, которые перенаправляют обратно в поддержку (бот сам поддержка)
            response = re.sub(r'(?i)обратитесь\s+(в|к)?\s*служб[аe]?\s*поддержк[аe]?[^.]*\.?', '', response)
            response = re.sub(r'(?i)contact\s+support[^.]*\.?', '', response)

            if not user_asked_sources:
                response = remove_sources(response)

            self.history_manager.add_message(user_id, 'user', message_text)
            self.history_manager.add_message(user_id, 'bot', response)
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
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
