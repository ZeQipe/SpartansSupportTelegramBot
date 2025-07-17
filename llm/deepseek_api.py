import requests
import json
from typing import List, Dict, Any, Optional
import time

class DeepSeekAPI:
    """Класс для работы с DeepSeek API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_response(self, messages: List[Dict[str, str]], 
                         model: str = "deepseek-chat", 
                         max_tokens: int = 1000,
                         temperature: float = 0.7) -> Dict[str, Any]:
        """
        Генерирует ответ с помощью DeepSeek API
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            model: Модель для использования
            max_tokens: Максимальное количество токенов
            temperature: Температура генерации
            
        Returns:
            Ответ от API
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def create_support_prompt(self, user_query: str, context: str, 
                            language: str = "en") -> List[Dict[str, str]]:
        """
        Создает промпт для поддержки клиентов
        
        Args:
            user_query: Запрос пользователя
            context: Контекст из документов
            language: Язык ответа
            
        Returns:
            Список сообщений для API
        """
        if language == "ru":
            system_prompt = """Ты - помощник службы поддержки Spartans.com. Твоя задача - отвечать на вопросы клиентов на основе предоставленных документов и правил.

Инструкции:
1. Отвечай ТОЛЬКО на основе предоставленного контекста
2. Если информации в контексте недостаточно, скажи об этом
3. Будь вежливым и профессиональным
4. Давай точные и конкретные ответы
5. Если нужно, цитируй соответствующие разделы документов
6. Отвечай на русском языке

Контекст из документов:
{context}

Вопрос клиента: {query}

Ответь на вопрос клиента, используя только информацию из предоставленного контекста."""
        else:
            system_prompt = """You are a Spartans.com customer support assistant. Your task is to answer customer questions based on the provided documents and rules.

Instructions:
1. Answer ONLY based on the provided context
2. If there's insufficient information in the context, say so
3. Be polite and professional
4. Give accurate and specific answers
5. If needed, quote relevant document sections
6. Respond in English

Document context:
{context}

Customer question: {query}

Answer the customer's question using only information from the provided context."""
        
        return [
            {"role": "system", "content": system_prompt.format(context=context, query=user_query)}
        ]
    
    def answer_with_context(self, user_query: str, context: str, 
                           language: str = "en") -> str:
        """
        Генерирует ответ на основе контекста
        
        Args:
            user_query: Запрос пользователя
            context: Контекст из документов
            language: Язык ответа
            
        Returns:
            Сгенерированный ответ
        """
        messages = self.create_support_prompt(user_query, context, language)
        
        response = self.generate_response(messages, max_tokens=800, temperature=0.5)
        
        if "error" in response:
            return f"Ошибка при генерации ответа: {response['error']}"
        
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return "Ошибка при обработке ответа от API"
    
    def answer_multilingual(self, user_query: str, contexts: Dict[str, str]) -> Dict[str, str]:
        """
        Генерирует ответы на нескольких языках
        
        Args:
            user_query: Запрос пользователя
            contexts: Словарь с контекстом по языкам
            
        Returns:
            Словарь с ответами по языкам
        """
        answers = {}
        
        for language, context in contexts.items():
            answer = self.answer_with_context(user_query, context, language)
            answers[language] = answer
        
        return answers
    
    def test_connection(self) -> bool:
        """Проверяет подключение к API"""
        try:
            response = self.generate_response([
                {"role": "user", "content": "Hello"}
            ], max_tokens=10)
            return "error" not in response
        except:
            return False

    def generate_support_response(self, user_query: str, context: str, 
                                  history: List[Dict[str, str]], 
                                  language: str = "en",
                                  config_messages: str = "",
                                  model: str = "deepseek-chat",
                                  max_tokens: int = 1000,
                                  temperature: float = 0.7) -> str:
        """
        Generates a support response using system prompt with context, history, and user query.
        
        Args:
            user_query: Current user question
            context: Formatted document context
            history: List of previous messages [{'role': 'user/assistant', 'content': '...'}]
            language: Response language
            model: Model to use
            max_tokens: Max tokens
            temperature: Temperature
            
        Returns:
            Generated response
        """
        # Create system prompt
        if language == "ru":
            system_prompt = """Ты - помощник службы поддержки Spartans.com. Твоя задача - отвечать на вопросы клиентов исключительно на основе предоставленного контекста из документов и истории разговора. Не придумывай информацию от себя и не используй внешние знания.

Подробные инструкции:
1. Отвечай ТОЛЬКО на основе предоставленного контекста документов и предыдущих сообщений в истории разговора. Если вопрос касается тем, не покрытых контекстом, вежливо задай уточняющий вопрос, который поможет лучше понять запрос пользователя и потенциально найти релевантную информацию в будущем, или предложи обратиться к специалисту поддержки. Вопрос должен быть конкретным и полезным.
2. Будь максимально вежливым, профессиональным и эмпатичным. Начинай ответ с приветствия или подтверждения понимания вопроса, заканчивай предложением дальнейшей помощи.
3. Обеспечивай безопасность: не разглашай конфиденциальную информацию, не давай финансовые или юридические советы без прямой опоры на контекст, не поощряй азартные игры или рискованное поведение.
4. Давай точные, конкретные и краткие ответы. Избегай ненужных деталей.
5. Если это уместно, цитируй точные разделы или фразы из предоставленного контекста, указывая источник (например, 'Согласно правилам букмекерской конторы, раздел X: ...').
6. Всегда отвечай на русском языке, независимо от языка вопроса, если не указано иное.
7. Учитывай контекст предыдущих сообщений в истории для coherentности разговора, но не выходи за рамки предоставленного контекста.
8. Если пользователь спрашивает о чем-то потенциально вредном или незаконном, перенаправь к официальным правилам или посоветуй обратиться в поддержку.
9. Если пользователь запрашивает связь с оператором: проверь историю разговора — если это первый такой запрос, вежливо предложи помочь самостоятельно на основе контекста; если повторный — подтверди вызов оператора и скажи 'Я передал ваш запрос оператору, он скоро подключится.'

Контекст из документов:
{context}

Используй ТОЛЬКО эту информацию для формирования ответа.""".format(context=context)
        else:
            system_prompt = """You are a customer support assistant for Spartans.com. Your task is to answer customer questions exclusively based on the provided document context and conversation history. Do not invent information or use external knowledge.

Detailed instructions:
1. Answer ONLY based on the provided document context and previous messages in the conversation history. If the question concerns topics not covered in the context, politely ask a clarifying question that will help better understand the user's query and potentially find relevant information in the future, or suggest contacting a support specialist. The question should be specific and helpful.
2. Be extremely polite, professional, and empathetic. Start the response with a greeting or acknowledgment of the question, end with an offer for further assistance.
3. Ensure safety: do not disclose confidential information, do not give financial or legal advice without direct support from the context, do not encourage gambling or risky behavior.
4. Provide accurate, specific, and concise answers. Avoid unnecessary details.
5. If appropriate, quote exact sections or phrases from the provided context, indicating the source (e.g., 'According to the sportsbook rules, section X: ...').
6. Always respond in English, unless otherwise specified.
7. Consider the context of previous messages in the history for conversation coherence, but do not go beyond the provided context.
8. If the user asks about something potentially harmful or illegal, redirect to official rules or advise contacting support.
9. If the user requests contact with an operator: check the conversation history — if this is the first such request, politely offer to help yourself based on the context; if repeated, confirm the call and say 'I have forwarded your request to an operator, they will join soon.'

Document context:
{context}

Use ONLY this information to form your response.""".format(context=context)
        
        # Append config_messages to user_query if provided
        full_user_query = user_query
        if config_messages:
            full_user_query += "\n\nДополнительные конфигурационные сообщения: " + config_messages if language == "ru" else user_query + "\n\nAdditional configuration messages: " + config_messages
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt}
        ] + history + [
            {"role": "user", "content": full_user_query}
        ]
        
        # Generate response
        response = self.generate_response(messages, model, max_tokens, temperature)
        
        if "error" in response:
            return f"Ошибка при генерации ответа: {response['error']}"
        
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return "Ошибка при обработке ответа от API"
