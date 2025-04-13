import os
import sys
import json
import asyncio
import aiohttp
import argparse
from typing import List, Dict, Any
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")
# Получение модели по умолчанию из переменных окружения
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")

# Хранение истории сообщений
message_history = []

# Функция для отправки запроса к API
async def send_to_api(messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        payload = {
            "messages": messages,
            "model": model,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            async with session.post(f"{API_URL}/api/chat", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    print(f"\nОшибка API: {error_text}")
                    return {"response": f"Ошибка API: {error_text}", "model": model}
        except Exception as e:
            print(f"\nОшибка соединения с API: {str(e)}")
            return {"response": f"Ошибка соединения с API: {str(e)}", "model": model}

# Получение списка доступных моделей
async def get_available_models() -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/api/models") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    print(f"\nОшибка при получении моделей: {await response.text()}")
                    return []
        except Exception as e:
            print(f"\nОшибка соединения с API для получения моделей: {str(e)}")
            return []

# Функция для вывода списка моделей
async def list_models():
    print("\nПолучение списка доступных моделей...")
    models = await get_available_models()
    
    if not models:
        print("Не удалось получить список моделей.")
        return
    
    print("\nДоступные модели:")
    for i, model in enumerate(models, 1):
        model_id = model.get("id", "")
        model_name = model.get("name", model_id)
        context_length = model.get("context_length", "N/A")
        print(f"{i}. {model_name} (ID: {model_id}, Макс. контекст: {context_length})")    

# Функция для очистки экрана
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Функция для отображения приветствия
def show_welcome():
    clear_screen()
    print("="*50)
    print("Персональный бот-компаньон (Терминальный клиент)")
    print("="*50)
    api_method = os.getenv("OPENROUTER_API_METHOD", "direct")
    print(f"Метод API: {api_method} (настраивается в .env файле)")
    print("="*50)
    print("Команды:")
    print("/help - показать справку")
    print("/clear - очистить историю беседы")
    print("/models - показать доступные модели")
    print("/model <id> - выбрать модель")
    print("/exit - выйти из программы")
    print("-"*50)

# Функция для отображения справки
def show_help():
    print("\nДоступные команды:")
    print("/help - показать эту справку")
    print("/clear - очистить историю беседы")
    print("/models - показать доступные модели")
    print("/model <id> - выбрать модель (например, /model openai/gpt-3.5-turbo)")
    print("/exit - выйти из программы")
    
    api_method = os.getenv("OPENROUTER_API_METHOD", "direct")
    print(f"\nТекущий метод API: {api_method}")
    print("Для изменения метода API отредактируйте переменную OPENROUTER_API_METHOD в файле .env:")
    print("- direct: прямые запросы к OpenRouter API")
    print("- openai: использование библиотеки OpenAI для запросов к OpenRouter API")

# Основная функция для запуска терминального клиента
async def main():
    global message_history
    
    parser = argparse.ArgumentParser(description="Терминальный клиент для персонального бота-компаньона")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="ID модели для использования")
    args = parser.parse_args()
    
    current_model = args.model
    
    show_welcome()
    print(f"Используемая модель: {current_model}\n")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            # Обработка команд
            if user_input.lower() == "/exit":
                print("\nДо свидания!")
                break
            elif user_input.lower() == "/help":
                show_help()
                continue
            elif user_input.lower() == "/clear":
                message_history.clear()
                print("\nИстория беседы очищена.")
                continue
            elif user_input.lower() == "/models":
                await list_models()
                continue
            elif user_input.lower().startswith("/model "):
                new_model = user_input[7:].strip()
                if new_model:
                    current_model = new_model
                    print(f"\nМодель изменена на: {current_model}")
                else:
                    print("\nУкажите ID модели. Например: /model openai/gpt-3.5-turbo")
                continue
            
            # Добавление сообщения пользователя в историю
            message_history.append({"role": "user", "content": user_input})
            
            print("\nОжидание ответа...")
            
            # Отправка запроса к API
            response_data = await send_to_api(message_history, current_model)
            assistant_response = response_data.get("response", "Извините, произошла ошибка.")
            model_used = response_data.get("model", current_model)
            
            # Добавление ответа ассистента в историю
            message_history.append({"role": "assistant", "content": assistant_response})
            
            # Ограничение длины истории (сохраняем последние 20 сообщений)
            if len(message_history) > 20:
                message_history = message_history[-20:]
            
            # Вывод ответа
            print(f"\n[{model_used}]:\n{assistant_response}")
            
        except KeyboardInterrupt:
            print("\n\nПрерывание работы. Для выхода введите /exit")
        except Exception as e:
            print(f"\nПроизошла ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())