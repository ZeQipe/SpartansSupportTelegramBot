from llm.deepseek_api import DeepSeekAPI
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

def split_text(query: str, language: str) -> str:
    api_key = os.getenv('DEEPSEEK_API_KEY') or ''
    llm = DeepSeekAPI(api_key)
    prompt = [{'role': 'system', 'content': 'Extract the key problem, metadata (game, specific issue, situation) from the user query as a clean string for search. Do not invent info.'}, {'role': 'user', 'content': query}]
    response = llm.generate_response(prompt, temperature=0.3)
    if 'choices' in response:
        return response['choices'][0]['message']['content']
    return query  # Fallback 