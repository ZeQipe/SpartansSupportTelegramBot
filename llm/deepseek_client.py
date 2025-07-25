import os
import json
import time
import requests
from typing import List, Dict, Any

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
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        # EXACT COPY: Current initialization
        self.api_key = api_key
        self.base_url = base_url
        self.headers = self._build_headers()
        
    def make_request(self, messages: List[Dict[str, str]], 
                    model: str = "deepseek-chat",
                    max_tokens: int = 1000,
                    temperature: float = 0.7) -> Dict[str, Any]:
        """
        EXACT COPY: Current generate_response logic
        Pure HTTP client - no business logic
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = self._build_payload(messages, model, max_tokens, temperature)

        # Выполняем запрос к DeepSeek
        usage: Dict[str, Any] = {}
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            response_json: Dict[str, Any] = response.json()
            usage = response_json.get('usage', {}) or {}
        except requests.exceptions.RequestException as e:
            # При ошибке формируем ответ с ошибкой
            response_json = {"error": str(e)}
        
        # --- Расширенное логирование запроса ---------------------------------
        self._log_request(messages, model, usage)

        return response_json
        
    def _build_headers(self) -> Dict[str, str]:
        """Extract header building"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def _build_payload(self, messages: List[Dict[str, str]], model: str, 
                      max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Extract payload building"""
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Extract response handling and error parsing"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
            
    def _log_request(self, messages: List[Dict[str, str]], model: str, usage: Dict[str, Any]):
        """EXACT COPY: Current logging logic"""
        try:
            os.makedirs('logs', exist_ok=True)
            with open('logs/deepseek_prompts.log', 'a', encoding='utf-8') as log_file:
                log_file.write('---------------------\n')
                log_file.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"Model: {model}\n")

                # Логируем сообщения - каждый dict на своей строке
                log_file.write('Messages:\n')
                for msg in messages:
                    log_file.write(json.dumps(msg, ensure_ascii=False) + '\n')

                # Логируем usage, если есть
                if usage:
                    log_file.write(
                        f"Tokens — prompt: {usage.get('prompt_tokens', 'N/A')}, "
                        f"completion: {usage.get('completion_tokens', 'N/A')}, "
                        f"total: {usage.get('total_tokens', 'N/A')}\n"
                    )
                log_file.write('\n')  # Пустая строка в конце записи
        except Exception:
            # Не прерываем основной поток при ошибке логирования
            pass 