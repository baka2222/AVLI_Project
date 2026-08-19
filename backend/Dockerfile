# Используем официальный Python-образ
FROM python:3.11

# Устанавливаем рабочую директорию
WORKDIR /app

# Системные библиотеки для WeasyPrint (генерация PDF квитанций) и шрифты.
# Liberation Serif метрически совместим с Times New Roman и покрывает кириллицу,
# поэтому PDF выглядит так же, как предпросмотр в браузере.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-liberation \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Ожидаем миграции, статику, запуск
CMD python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000
