# Low Level Design: SpartansSupportTelegramBot Refactoring

## 1. Overview

**Objective**: Refactor SpartansSupportTelegramBot to be modular and production-ready while maintaining 100% identical business logic, system prompt behavior, and user experience.

**Scope**: Complete architectural restructuring without changing any business flows, parameters, or behaviors.

## 2. Current Architecture Analysis

### 2.1 Current Issues
- **Monolithic main.py**: 263 lines handling multiple responsibilities
- **Monolithic llm/deepseek_api.py**: 328 lines with mixed concerns
- **Tight coupling**: Business logic embedded in presentation layer
- **No clear separation**: Message processing, formatting, and API calls mixed
- **Hard to test**: Dependencies tightly coupled
- **Hard to maintain**: Changes require touching multiple unrelated concerns

### 2.2 Current Flows to Preserve
1. **Bot Initialization Flow**:
   - Environment variable loading → Document indexing → Vector store initialization → Service setup → Handler registration → Bot startup
2. **Document Loading Flow**:
   - Directory scanning → File processing → Chunking → Embedding generation → Vector store indexing → Statistics logging
3. **Message Processing Flow**:
   - Language detection → User language storage → Query preprocessing → Context search → LLM generation → Response cleanup → History update
4. **Admin Flow**:
   - Password verification → Prompt update → File atomic write → Backup creation
5. **Group Message Flow**:
   - Bot username caching → Mention detection → Message text cleanup → Normal processing
6. **History Management**:
   - 1-hour sliding window + 20 message limit + automatic cleanup + Database connection management
7. **Context Search**:
   - Query preprocessing → Multilingual search → Top 25 results → Context building → Statistics aggregation
8. **Response Processing**:
   - Escalation detection → Email removal → Source removal → Markdown cleanup → Support phrase removal
9. **Error Handling Flow**:
   - Exception capture → Error logging → User-friendly message → History preservation
10. **User Request Logging Flow**:
    - User ID extraction → Username capture → Message logging → Timestamp recording
11. **Language Detection Flow**:
    - Text analysis → Language detection → Fallback to previous preference → Storage update
12. **Vector Store Operations**:
    - Document processing → Embedding generation → Storage → Statistics calculation

## 3. New Modular Architecture

### 3.1 Directory Structure
```
SpartansSupportTelegramBot/
├── bot/
│   ├── __init__.py
│   ├── telegram_handler.py          # Telegram-specific logic + message processing
│   ├── response_formatter.py        # Response formatting and cleanup
│   └── admin_handler.py             # Admin system prompt management
├── core/
│   ├── __init__.py
│   ├── conversation_manager.py      # History + language management
│   ├── context_builder.py           # Context search and building
│   └── prompt_manager.py            # System prompt construction
├── llm/
│   ├── __init__.py
│   ├── deepseek_client.py          # Pure API client
│   └── llm_service.py              # Business logic wrapper
├── embeddings/                      # Keep existing structure
├── config/                          # Keep existing structure
├── data/                           # Keep existing structure
└── prompts/                        # Keep existing structure
```

### 3.2 Class Responsibilities

#### 3.2.1 bot/telegram_handler.py
```python
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
```

#### 3.2.2 bot/response_formatter.py
```python
class ResponseFormatter:
    """
    SINGLE RESPONSIBILITY: Response formatting and cleanup
    
    Responsibilities:
    - Escalation detection and removal
    - Email address removal (regex-based)
    - Source reference removal (when user didn't ask for sources)
    - Markdown cleanup (### headers, **** to bold)
    - Support redirection phrase removal
    - Telegram message length validation
    
    PRESERVE EXACT: All current regex patterns and logic
    """
```

#### 3.2.3 bot/admin_handler.py
```python
class AdminHandler:
    """
    SINGLE RESPONSIBILITY: Admin system prompt management
    
    Responsibilities:
    - Password verification
    - System prompt atomic file operations
    - Backup creation with timestamps
    - Admin state management per user
    
    PRESERVE EXACT: Current 3-state flow (idle → await_pwd → await_prompt)
    """
```

#### 3.2.4 core/conversation_manager.py
```python
class ConversationManager:
    """
    SINGLE RESPONSIBILITY: Conversation history and user preferences
    
    Responsibilities:
    - User language preference storage and retrieval
    - History management with 1-hour sliding window
    - 20 message limit enforcement
    - SQLite database operations
    - History cleanup and expiration
    
    PRESERVE EXACT: Current HistoryManager behavior and database schema
    """
```

#### 3.2.5 core/context_builder.py
```python
class ContextBuilder:
    """
    SINGLE RESPONSIBILITY: Context search and building
    
    Responsibilities:
    - Query preprocessing delegation
    - Multilingual context search (top_k=25)
    - Context text building and concatenation
    - Search statistics aggregation
    
    PRESERVE EXACT: Current search parameters and multilingual logic
    """
```

#### 3.2.6 core/prompt_manager.py
```python
class PromptManager:
    """
    SINGLE RESPONSIBILITY: System prompt construction
    
    Responsibilities:
    - System prompt file loading
    - Template variable substitution ({context}, {promotions})
    - Promotions text loading from data files
    - Prompt caching and invalidation
    
    PRESERVE EXACT: Current template structure and variable injection
    """
```



#### 3.2.7 llm/deepseek_client.py
```python
class DeepSeekClient:
    """
    SINGLE RESPONSIBILITY: Pure DeepSeek API client
    
    Responsibilities:
    - HTTP request construction and execution
    - Authentication header management
    - Response parsing and error handling
    - Retry logic and timeout handling
    - Token usage logging
    
    NO business logic - pure API client
    """
```

#### 3.2.8 llm/llm_service.py
```python
class LLMService:
    """
    SINGLE RESPONSIBILITY: LLM business logic wrapper
    
    Responsibilities:
    - Message structure construction for DeepSeek
    - Parameter management (max_tokens, temperature)
    - Model selection logic
    - Response validation and error handling
    
    PRESERVE EXACT: Current message structure and parameters
    """
```

## 4. Critical Implementation Details to Preserve

### 4.1 Exact Regex Patterns (from main.py)
```python
# Markdown cleanup - EXACT PRESERVATION REQUIRED
response = re.sub(r'^#{1,6}\s*', '', response, flags=re.MULTILINE)  # Remove ### headers
response = re.sub(r'^\*{4}\s*(.+)', r'**\1**', response, flags=re.MULTILINE)  # **** to bold

# Source removal - EXACT PRESERVATION REQUIRED  
user_asked_sources = bool(re.search(r'(источник|sources?)', message_text, re.IGNORECASE))
response = re.sub(r'\(\s*(источник\w*|sources?)\s*[^)]*\)', '', response, flags=re.IGNORECASE)

# Support redirection removal - EXACT PRESERVATION REQUIRED
response = re.sub(r'(?i)обратитесь\s+(в|к)?\s*служб[аe]?\s*поддержк[аe]?[^.]*\.?', '', response)
response = re.sub(r'(?i)contact\s+support[^.]*\.?', '', response)
```

### 4.2 Exact Error Messages (must be preserved)
```python
# Language-specific error messages for users
error_msg_ru = 'Ситуация кажется серьёзной, я уже зову оператора - он подойдёт через минуту.'
error_msg_en = 'The situation seems serious, I\'m calling an operator - they\'ll join in a minute.'

# LLM API error handling
"Ошибка при генерации ответа: {response['error']}"
"Ошибка при обработке ответа от API"
```

### 4.3 Exact User Request Logging Format
```python
# EXACT FORMAT - MUST BE PRESERVED
user_logger.info(f"user_id={update.effective_user.id} username={update.effective_user.username or ''} text={message_text}")
```

### 4.4 Exact Document Loading Statistics Format
```python
# EXACT LOGGING FORMAT - MUST BE PRESERVED
logger.info(f"Document indexing stats: added {stats['added']}, updated {stats['updated']}, skipped {stats['skipped']} | total vectors in DB: {total}")
logger.info(f"  {info['status'].upper():7} {info['path']} | chunks: {info.get('chunks', 0)}")
```

### 4.5 Exact Admin State Flow
```python
# THREE STATES - EXACT PRESERVATION REQUIRED
admin_states = {
    'idle': 'No admin operation in progress',
    'await_pwd': 'Waiting for password verification', 
    'await_prompt': 'Waiting for new system prompt'
}

# State transitions
'idle' → '/sys command' → 'await_pwd' → 'correct password' → 'await_prompt' → 'prompt text' → 'idle'
```

### 4.6 Exact Group Message Handling
```python
# EXACT LOGIC - MUST BE PRESERVED
mention_prefix = f'@{self.bot_username}' if self.bot_username else ''
if mention_prefix:
    if not message_text.lower().startswith(mention_prefix):
        return  # Bot not mentioned first - EXACT BEHAVIOR
    message_text = message_text[len(mention_prefix):].lstrip()
    if not message_text:
        return  # Empty message after mention - EXACT BEHAVIOR
```

### 4.7 Exact Language Detection Fallback
```python
# EXACT FALLBACK LOGIC - MUST BE PRESERVED
query_language = 'en'  # Default
try:
    query_language_detected = detect(message_text)
    if query_language_detected in ['en', 'ru']:  # Only these two languages
        query_language = query_language_detected
        self.user_languages[user_id] = query_language  # Store preference
except Exception as e:
    logger.warning(f'Language detection failed: {e}')  # Continue with default

user_language = self.user_languages.get(user_id, query_language)  # Use stored preference
```

### 4.8 Exact History Database Schema
```sql
-- EXACT SCHEMA - MUST BE PRESERVED
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    role TEXT,
    content TEXT
)
CREATE INDEX IF NOT EXISTS idx_user_id ON messages (user_id)
```

### 4.9 Exact Context Search Parameters
```python
# EXACT PARAMETERS - MUST BE PRESERVED
processed_query = self.search.preprocess_query(message_text, query_language)
contexts = self.search.get_multilingual_context(processed_query, top_k=25)  # Exact value
doc_context_raw = contexts.get(query_language, '') or next(iter(contexts.values()), '')
```

### 4.10 Exact LLM Parameters
```python
# EXACT PARAMETERS - MUST BE PRESERVED
response = self.llm.generate_response(messages, max_tokens=800, temperature=0.5)  # answer_with_context
response = self.llm.generate_support_response(
    user_query, doc_context, history, language=user_language,
    model="deepseek-chat", max_tokens=1000, temperature=0.7  # generate_support_response
)
```

### 4.11 Exact File Atomic Operations
```python
# EXACT ATOMIC WRITE SEQUENCE - MUST BE PRESERVED
def _save_new_system_prompt(self, prompt_text: str):
    prompt_dir = Path('prompts')
    prompt_dir.mkdir(exist_ok=True)
    target = prompt_dir / 'system_prompt.txt'
    if target.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target.rename(prompt_dir / f'system_prompt_{timestamp}.txt')  # Backup
    tmp_file = prompt_dir / f'.tmp_{os.getpid()}'
    tmp_file.write_text(prompt_text, encoding='utf-8')
    tmp_file.replace(target)  # Atomic replace
```

## 5. Detailed Implementation Plan

### 5.1 Phase 1: Extract Core Services

#### 5.1.1 Create core/conversation_manager.py
```python
# EXACT MIGRATION from existing HistoryManager + user language storage
class ConversationManager:
    def __init__(self, db_path: str = 'conversation_history.db'):
        # EXACT COPY: Current HistoryManager.__init__
        
    def set_user_language(self, user_id: int, language: str):
        # NEW: Extract from main.py self.user_languages management
        
    def get_user_language(self, user_id: int, default: str = 'en') -> str:
        # NEW: Extract from main.py self.user_languages management
        
    def add_message(self, user_id: int, role: str, content: str):
        # EXACT COPY: Current HistoryManager.add_message
        
    def get_history(self, user_id: int) -> List[Dict[str, str]]:
        # EXACT COPY: Current HistoryManager.get_history (1-hour window + 20 limit)
        
    def reset_history(self, user_id: int):
        # EXACT COPY: Current HistoryManager.reset_history
```

#### 5.1.2 Create core/context_builder.py
```python
class ContextBuilder:
    def __init__(self, search: DocumentSearch):
        self.search = search
        
    def get_context_for_query(self, query: str, language: str) -> str:
        # EXACT COPY: Current logic from main.py handle_message
        # processed_query = self.search.preprocess_query(message_text, query_language)
        # contexts = self.search.get_multilingual_context(processed_query, top_k=25)
        # doc_context_raw = contexts.get(query_language, '') or next(iter(contexts.values()), '')
        # return doc_context_raw  # No email removal at this stage
```

#### 5.1.3 Create core/prompt_manager.py
```python
class PromptManager:
    def __init__(self):
        self._cached_prompt = None
        self._prompt_file_mtime = None
        
    def get_system_prompt(self, context: str) -> str:
        # Load from prompts/system_prompt.txt with caching
        # EXACT COPY: Current _load_system_prompt logic
        # Template substitution with {context} and {promotions}
        
    def _load_promotions(self) -> str:
        # EXACT COPY: Load promotions from data files
        
    def _check_prompt_file_changed(self) -> bool:
        # File modification time checking for cache invalidation
```



### 5.2 Phase 2: Extract Formatting and Admin

#### 5.2.1 Create bot/response_formatter.py
```python
class ResponseFormatter:
    def format_response(self, response: str, user_query: str, user_language: str) -> str:
        # EXACT COPY: Current formatting logic from main.py
        # 1. Escalation detection and removal
        # 2. Markdown cleanup (### removal, **** to bold)
        # 3. Email removal logic
        # 4. Source removal logic (when user didn't ask for sources)
        # 5. Support redirection phrase removal
        
    def _detect_escalation(self, response: str) -> bool:
        return '[ESCALATE]' in response
        
    def _remove_escalation_marker(self, response: str) -> str:
        return response.replace('[ESCALATE]', '').lstrip()
        
    def _cleanup_markdown(self, response: str) -> str:
        # EXACT COPY: Current regex patterns
        
    def _remove_sources_if_not_requested(self, response: str, user_asked_sources: bool) -> str:
        # EXACT COPY: Current source removal logic
        
    def _remove_support_redirections(self, response: str) -> str:
        # EXACT COPY: Current support phrase removal
```

#### 5.2.2 Create bot/admin_handler.py
```python
class AdminHandler:
    def __init__(self, sys_password: str):
        self.sys_password = sys_password
        self.admin_states: dict[int, str] = {}  # EXACT COPY: Current state management
        
    def handle_sys_command(self, user_id: int) -> str:
        # EXACT COPY: Current /sys command logic
        
    def handle_admin_message(self, user_id: int, message: str) -> tuple[bool, str]:
        # EXACT COPY: Current admin flow interception logic
        # Returns (is_admin_message, response)
        
    def _save_new_system_prompt(self, prompt_text: str):
        # EXACT COPY: Current atomic file operations with backup
```



### 5.3 Phase 3: Extract LLM Services

#### 5.3.1 Create llm/deepseek_client.py
```python
class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        # EXACT COPY: Current initialization
        
    def make_request(self, messages: List[Dict[str, str]], 
                    model: str = "deepseek-chat",
                    max_tokens: int = 1000,
                    temperature: float = 0.7) -> Dict[str, Any]:
        # EXACT COPY: Current generate_response logic
        # Pure HTTP client - no business logic
        
    def _build_headers(self) -> Dict[str, str]:
        # Extract header building
        
    def _build_payload(self, messages, model, max_tokens, temperature) -> Dict[str, Any]:
        # Extract payload building
        
    def _handle_response(self, response) -> Dict[str, Any]:
        # Extract response handling and error parsing
```

#### 5.3.2 Create llm/llm_service.py
```python
class LLMService:
    def __init__(self, client: DeepSeekClient, prompt_manager: PromptManager):
        self.client = client
        self.prompt_manager = prompt_manager
        
    def generate_support_response(self, user_query: str, context: str, 
                                 history: List[Dict[str, str]], 
                                 language: str = "en") -> str:
        # EXACT COPY: Current generate_support_response business logic
        # Message construction, parameter selection, response extraction
```

### 5.4 Phase 4: Update Main Handler

#### 5.4.1 Update bot/telegram_handler.py
```python
class TelegramHandler:
    def __init__(self, telegram_token: str, deepseek_api_key: str):
        # Initialize with new modular services but keep message processing in same class
        self.conversation_manager = ConversationManager()
        self.context_builder = ContextBuilder(...)
        self.llm_service = LLMService(...)
        self.response_formatter = ResponseFormatter()
        self.admin_handler = AdminHandler(...)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # EXACT COPY: Current handle_message logic but delegating to new services
        # Keep all logic in this method but use injected services
        
    # Keep all other handlers (start, help, stats, etc.) unchanged
```

## 6. Migration Strategy

### 6.1 Step-by-Step Migration
1. **Create new modules** with EXACT copied logic
2. **Add unit tests** for each module to verify identical behavior
3. **Update main.py** to use new modules progressively
4. **Run integration tests** after each step
5. **Remove old code** only after verification

### 6.2 Testing Strategy
```python
# Create identical behavior tests
def test_message_processing_identical():
    # Test old vs new implementation with same inputs
    assert old_result == new_result
    
def test_history_management_identical():
    # Test database operations produce identical results
    
def test_response_formatting_identical():
    # Test all regex patterns and formatting rules
```

### 6.3 Rollback Plan
- **Keep old implementation** in separate branch
- **Feature flags** for gradual rollout
- **Monitoring** for behavior differences
- **Quick rollback** capability

## 7. Production Readiness Features

### 7.1 Error Handling
- Keep existing error handling patterns from current implementation
- Maintain current exception handling and logging without adding new abstractions

### 7.2 Logging
- Preserve existing logging configuration and format
- Keep current user request logging and document indexing stats format

## 8. Backwards Compatibility

### 8.1 Database Schema
- **No changes** to existing database schema
- **Maintain** all existing indexes and constraints
- **Preserve** all data migration paths

### 8.2 Configuration
- **Maintain** all existing configuration parameters
- **No new configuration required**

### 8.3 API Compatibility
- **Preserve** all existing command handlers
- **Maintain** all callback query handlers
- **Keep** all existing message processing flows

## 9. Verification Checklist

### 9.1 Functional Verification
- [ ] Language detection works identically (en/ru detection + fallback)
- [ ] Admin flow works identically (password → prompt update → backup)
- [ ] Group mention detection works identically (@bot_username prefix)
- [ ] History management preserves 1-hour + 20 message limits
- [ ] Context search returns identical results (top_k=25, multilingual)
- [ ] Response formatting applies all current rules
- [ ] Email removal works identically (regex patterns)
- [ ] Source removal logic preserved (user query analysis)
- [ ] Escalation detection preserved ([ESCALATE] marker)
- [ ] Document loading statistics format preserved
- [ ] User request logging format preserved
- [ ] Bot initialization sequence preserved
- [ ] File atomic operations preserved (system prompt updates)
- [ ] Database schema and operations preserved
- [ ] Vector store operations preserved
- [ ] LLM parameter preservation (max_tokens, temperature)
- [ ] Error message preservation (language-specific)

### 9.2 Performance Verification
- [ ] Response times remain similar
- [ ] Memory usage doesn't increase significantly
- [ ] Database operations perform identically
- [ ] Token usage remains the same

### 9.3 Integration Verification
- [ ] All Telegram commands work
- [ ] All callback queries work
- [ ] Error handling works correctly
- [ ] Logging produces expected output
- [ ] Configuration loading works

## 10. Success Criteria

### 10.1 Modularity Goals
- [ ] Each class has single responsibility
- [ ] Dependencies are injected, not hardcoded
- [ ] Business logic separated from infrastructure
- [ ] Easy to unit test each component
- [ ] Clear interfaces between modules

### 10.2 Production Readiness Goals
- [ ] Existing error handling patterns maintained
- [ ] Current logging format preserved
- [ ] Easy deployment and rollback

### 10.3 Behavioral Preservation Goals
- [ ] 100% identical user experience
- [ ] 100% identical business logic
- [ ] 100% identical response formatting
- [ ] 100% identical admin functionality
- [ ] 100% identical performance characteristics

---

**Note**: This refactoring maintains 100% behavioral compatibility while improving code organization, testability, and production readiness. Every business rule, parameter, and user-facing behavior is preserved exactly as-is.
