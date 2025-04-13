import os
import openai
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class OpenAIRouter:
    """Класс для взаимодействия с OpenRouter API через библиотеку OpenAI"""
    
    def __init__(self):
        # Получение API ключа из переменных окружения
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
        
        # Настройка клиента OpenAI для работы с OpenRouter
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
                "X-Title": "Personal Companion Bot"
            }
        )
    
    async def chat_completion(self, 
                             messages: List[Dict[str, str]], 
                             model: str = "openai/gpt-3.5-turbo", 
                             max_tokens: int = 1000, 
                             temperature: float = 0.7) -> Dict[str, Any]:
        """Отправка запроса на генерацию ответа"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Преобразование ответа в формат, совместимый с текущей реализацией
            return {
                "choices": [
                    {
                        "message": {
                            "content": response.choices[0].message.content
                        }
                    }
                ],
                "model": response.model
            }
        except Exception as e:
            raise Exception(f"Error calling OpenRouter API via OpenAI client: {str(e)}")
    
    async def list_models(self) -> Dict[str, Any]:
        """Получение списка доступных моделей"""
        try:
            response = self.client.models.list()
            
            # Преобразование ответа в формат, совместимый с текущей реализацией
            return {
                "data": [model.model_dump() for model in response.data]
            }
        except Exception as e:
            raise Exception(f"Error fetching models via OpenAI client: {str(e)}")