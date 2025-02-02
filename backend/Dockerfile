# Используем официальный Python-образ
FROM python:3.11

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Ожидаем миграции, статику, запуск
CMD python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000
