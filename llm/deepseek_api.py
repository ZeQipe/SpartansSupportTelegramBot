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
