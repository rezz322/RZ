FROM python:3.11-slim

# Встановлюємо таймзону Київ для коректного часу нагадувань про пари
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Kyiv

# Встановлюємо tzdata та оновлюємо сертифікати
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Спочатку копіюємо requirements для кешування шарів Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всі файли проєкту
COPY . .

# Створюємо директорію для даних, якщо вона ще не створена
RUN mkdir -p /app/data

# Запуск бота
CMD ["python", "main.py"]
