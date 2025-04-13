FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование файлов проекта
COPY . .

# Переменные окружения
ENV OPENROUTER_API_KEY=""
ENV APP_URL="http://localhost:8000"
ENV TELEGRAM_TOKEN=""
ENV API_URL="http://localhost:8000"

# Открытие порта
EXPOSE 8000

# Запуск API сервера
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]