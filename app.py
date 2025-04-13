import os
import json
import logging
import requests
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from openai_router import OpenAIRouter

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(title="Персональный бот-компаньон с OpenRouter API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = Field(default="openai/gpt-3.5-turbo")
    max_tokens: Optional[int] = Field(default=1000)
    temperature: Optional[float] = Field(default=0.7)

class ChatResponse(BaseModel):
    response: str
    model: str

# Функция для взаимодействия с OpenRouter API
async def chat_with_openrouter(request_data: ChatRequest) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    # Определение метода API для OpenRouter
    api_method = os.getenv("OPENROUTER_API_METHOD", "direct")
    
    if api_method == "openai":
        # Использование OpenAI API для работы с OpenRouter
        try:
            from openai_router import OpenAIRouter
            openai_router = OpenAIRouter()
            messages = [msg.dict() for msg in request_data.messages]
            return await openai_router.chat_completion(
                messages=messages,
                model=request_data.model,
                max_tokens=request_data.max_tokens,
                temperature=request_data.temperature
            )
        except Exception as e:
            logger.error(f"Error calling OpenRouter API via OpenAI client: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error calling OpenRouter API via OpenAI client: {str(e)}")
    else:
        # Прямое использование OpenRouter API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
            "X-Title": "Personal Companion Bot"
        }
        
        payload = {
            "messages": [msg.dict() for msg in request_data.messages],
            "model": request_data.model,
            "max_tokens": request_data.max_tokens,
            "temperature": request_data.temperature
        }
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error calling OpenRouter API: {str(e)}")

# Маршруты API
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request_data: ChatRequest, background_tasks: BackgroundTasks):
    try:
        response = await chat_with_openrouter(request_data)
        
        # Извлечение ответа из результата API
        assistant_message = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        model_used = response.get("model", request_data.model)
        
        return ChatResponse(response=assistant_message, model=model_used)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def list_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    # Определение метода API для OpenRouter
    api_method = os.getenv("OPENROUTER_API_METHOD", "direct")
    
    if api_method == "openai":
        # Использование OpenAI API для работы с OpenRouter
        try:
            openai_router = OpenAIRouter()
            return await openai_router.list_models()
        except Exception as e:
            logger.error(f"Error fetching models via OpenAI client: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching models via OpenAI client: {str(e)}")
    else:
        # Прямое использование OpenRouter API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000")
        }
        
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching models: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Персональный бот-компаньон API работает. Используйте /docs для документации."}

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)