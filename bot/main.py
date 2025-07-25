import os
from dotenv import load_dotenv
from bot.telegram_handler import TelegramHandler

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
