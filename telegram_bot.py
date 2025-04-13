import os
import logging
import asyncio
import json
import aiohttp
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена бота из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
# Получение модели по умолчанию из переменных окружения
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")

# Хранение контекста беседы для каждого пользователя
user_contexts = {}

# Функция для отправки запроса к API
async def send_to_api(messages: List[Dict[str, str]], model: str = None) -> Dict[str, Any]:
    # Если модель не указана, используем модель по умолчанию
    if model is None:
        model = DEFAULT_MODEL
        
    async with aiohttp.ClientSession() as session:
        payload = {
            "messages": messages,
            "model": model,
            "max_tokens": 1000,
            "temperature": 0.7,
            # Добавляем дополнительные заголовки, которые требует OpenRouter
            "extra_headers": {
                "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
                "X-Title": "Personal AI Companion"
            }
        }
        
        try:
            async with session.post(f"{API_URL}/api/chat", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"API error: {error_text}")
                    return {"response": f"Ошибка API: {error_text}", "model": model}
        except Exception as e:
            logger.error(f"Error sending request to API: {str(e)}")
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
                    logger.error(f"Error fetching models: {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"Error connecting to API for models: {str(e)}")
            return []

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_contexts[user_id] = []
    
    await update.message.reply_text(
        "👋 Привет! Я ваш персональный бот-компаньон, работающий с OpenRouter API. "
        "Вы можете общаться со мной на любые темы, и я постараюсь помочь."
        "\n\nИспользуйте /model для выбора модели ИИ."
        "\n\nИспользуйте /clear для очистки истории беседы."
    )

# Обработчик команды /clear
async def clear_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_contexts[user_id] = []
    await update.message.reply_text("История беседы очищена.")

# Обработчик команды /model
async def select_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    models = await get_available_models()
    
    if not models:
        await update.message.reply_text("Не удалось получить список моделей. Используется модель по умолчанию.")
        return
    
    keyboard = []
    row = []
    
    for i, model in enumerate(models):
        model_id = model.get("id", "")
        model_name = model.get("name", model_id)
        
        if i > 0 and i % 2 == 0:
            keyboard.append(row)
            row = []
            
        row.append(InlineKeyboardButton(model_name, callback_data=f"model:{model_id}"))
    
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите модель:", reply_markup=reply_markup)

# Обработчик выбора модели
async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    model_id = query.data.split(":")[1]
    user_id = update.effective_user.id
    
    if user_id not in context.bot_data:
        context.bot_data[user_id] = {}
    
    context.bot_data[user_id]["model"] = model_id
    
    await query.edit_message_text(f"Выбрана модель: {model_id}")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Инициализация контекста пользователя, если его нет
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    
    # Получение выбранной модели или использование модели по умолчанию
    model = context.bot_data.get(user_id, {}).get("model", DEFAULT_MODEL)
    
    # Добавление сообщения пользователя в контекст
    user_contexts[user_id].append({"role": "user", "content": user_message})
    
    # Отправка индикатора набора текста
    await update.message.chat.send_action(action="typing")
    
    # Отправка запроса к API
    response_data = await send_to_api(user_contexts[user_id], model)
    assistant_response = response_data.get("response", "Извините, произошла ошибка.")
    model_used = response_data.get("model", model)
    
    # Добавление ответа ассистента в контекст
    user_contexts[user_id].append({"role": "assistant", "content": assistant_response})
    
    # Ограничение длины контекста (сохраняем последние 20 сообщений)
    if len(user_contexts[user_id]) > 20:
        user_contexts[user_id] = user_contexts[user_id][-20:]
    
    # Отправка ответа пользователю
    await update.message.reply_text(f"{assistant_response}\n\n_Модель: {model_used}_", parse_mode="Markdown")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("Произошла ошибка при обработке запроса.")

# Основная функция
def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        return
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_context))
    application.add_handler(CommandHandler("model", select_model))
    application.add_handler(CallbackQueryHandler(model_callback, pattern=r"^model:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()