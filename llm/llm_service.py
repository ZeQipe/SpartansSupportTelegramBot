import os
from typing import List, Dict, Any
from .deepseek_client import DeepSeekClient
from core.prompt_manager import PromptManager

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
    
    def __init__(self, client: DeepSeekClient, prompt_manager: PromptManager):
        self.client = client
        self.prompt_manager = prompt_manager
        
    def generate_support_response(self, user_query: str, context: str, 
                                 history: List[Dict[str, str]], 
                                 language: str = "en",
                                 config_messages: str = "",
                                 model: str = "deepseek-chat",
                                 max_tokens: int = 1000,
                                 temperature: float = 0.7) -> str:
        """
        EXACT COPY: Current generate_support_response business logic
        Message construction, parameter selection, response extraction
        """
        # Load system prompt from external file so it can be modified without code changes
        system_prompt = self.prompt_manager.get_system_prompt(context)

        # Append config_messages to user_query if provided
        full_user_query = user_query
        if config_messages:
            full_user_query += "\n\n" + ("Дополнительные конфигурационные сообщения: " if language == "ru" else "Additional configuration messages: ") + config_messages

        # Build messages
        # DeepSeek (OpenAI-style) API допускает роли 'system', 'user', 'assistant'.
        # В истории мы храним 'bot' для ответа, поэтому приведём к 'assistant'.
        normalized_history = [
            {**msg, 'role': ('assistant' if msg.get('role') == 'bot' else msg.get('role'))}
            for msg in history
            if msg.get('role') in ['user', 'bot', 'assistant']
        ]

        # Формируем список сообщений для DeepSeek
        # Стартуем с системного промпта
        messages = [
            {"role": "system", "content": system_prompt}
        ] + normalized_history

        # --- Изменение: дублируем системные инструкции ---
        # Если в истории более 5 сообщений, добавляем копию системного промпта
        if len(normalized_history) > 5:
            messages.append({"role": "system", "content": system_prompt})

        # В конце добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": full_user_query})
        
        # Generate response
        response = self.client.make_request(messages, model, max_tokens, temperature)
        
        if "error" in response:
            return f"Ошибка при генерации ответа: {response['error']}"
        
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return "Ошибка при обработке ответа от API"
            
    def answer_with_context(self, user_query: str, context: str, 
                           language: str = "en") -> str:
        """
        EXACT COPY: Current answer_with_context logic for backward compatibility
        """
        system_prompt = self.prompt_manager.get_system_prompt(context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        # EXACT PARAMETERS: Current answer_with_context parameters
        response = self.client.make_request(messages, max_tokens=800, temperature=0.5)
        
        if "error" in response:
            return f"Error generating response: {response['error']}"
        
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return "Error processing API response" 