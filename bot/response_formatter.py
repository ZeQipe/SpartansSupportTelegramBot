import re

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
    
    def format_response(self, response: str, user_query: str, user_language: str) -> str:
        """
        EXACT COPY: Current formatting logic from main.py
        1. Escalation detection and removal
        2. Markdown cleanup (### removal, **** to bold)
        3. Email removal logic  
        4. Source removal logic (when user didn't ask for sources)
        5. Support redirection phrase removal
        """
        # 1. Escalation detection and removal
        if '[ESCALATE]' in response:
            # Сразу показываем полный текст без дублирующего системного сообщения
            response = response.replace('[ESCALATE]', '').lstrip()
        
        # 2. Markdown cleanup (### removal, **** to bold)
        # Преобразуем **** в жирный Markdown и убираем ### заголовки
        response = re.sub(r'^#{1,6}\s*', '', response, flags=re.MULTILINE)
        response = re.sub(r'^\*{4}\s*(.+)', r'**\1**', response, flags=re.MULTILINE)

        # 3. Source removal logic (when user didn't ask for sources)
        # Дополнительная зачистка: если пользователь не запросил источники, удаляем упоминания "источник"/"sources"
        user_asked_sources = bool(re.search(r'(источник|sources?)', user_query, re.IGNORECASE))
        
        if not user_asked_sources:
            response = self._remove_sources(response)

        # 4. Email removal logic
        # Удаляем email
        # response = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '', response)  # 🔧 Убрали автоматическое удаление email

        # 5. Support redirection phrase removal
        # Удаляем фразы, которые перенаправляют обратно в поддержку (бот сам поддержка)
        response = re.sub(r'(?i)обратитесь\s+(в|к)?\s*служб[аe]?\s*поддержк[аe]?[^.]*\.?', '', response)
        response = re.sub(r'(?i)contact\s+support[^.]*\.?', '', response)

        return response
        
    def _detect_escalation(self, response: str) -> bool:
        """Detect if response contains escalation marker"""
        return '[ESCALATE]' in response
        
    def _remove_escalation_marker(self, response: str) -> str:
        """Remove escalation marker from response"""
        return response.replace('[ESCALATE]', '').lstrip()
        
    def _cleanup_markdown(self, response: str) -> str:
        """EXACT COPY: Current regex patterns"""
        # Преобразуем **** в жирный Markdown и убираем ### заголовки
        response = re.sub(r'^#{1,6}\s*', '', response, flags=re.MULTILINE)
        response = re.sub(r'^\*{4}\s*(.+)', r'**\1**', response, flags=re.MULTILINE)
        return response
        
    def _remove_sources_if_not_requested(self, response: str, user_asked_sources: bool) -> str:
        """EXACT COPY: Current source removal logic"""
        if not user_asked_sources:
            return self._remove_sources(response)
        return response
        
    def _remove_sources(self, text: str) -> str:
        """EXACT COPY: Current remove_sources function"""
        # Удаляем шаблоны вида (источник 1, 2) или (sources 3,4)
        text = re.sub(r'\(\s*(источник\w*|sources?)\s*[^)]*\)', '', text, flags=re.IGNORECASE)
        return text
        
    def _remove_support_redirections(self, response: str) -> str:
        """EXACT COPY: Current support phrase removal"""
        # Удаляем фразы, которые перенаправляют обратно в поддержку (бот сам поддержка)
        response = re.sub(r'(?i)обратитесь\s+(в|к)?\s*служб[аe]?\s*поддержк[аe]?[^.]*\.?', '', response)
        response = re.sub(r'(?i)contact\s+support[^.]*\.?', '', response)
        return response 