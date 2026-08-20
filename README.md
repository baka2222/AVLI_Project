# АВЛИ

Система учёта дополнена публичным сайтом и Telegram-ботом. Оба канала показывают те же расчётные поля, что и бумажная квитанция: долг и предоплату на начало периода, начисление, оплату, текущий баланс, площадь и тариф.

## Запуск через Docker

1. Скопируйте пример окружения:

   ```powershell
   Copy-Item backend/.env.example .env
   ```

2. Заполните в `.env` как минимум `SECRET_KEY`, `DATABASE_PASSWORD`, `BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` и `INTERNAL_API_TOKEN`.

3. Соберите и запустите сервисы:

   ```powershell
   docker compose up --build -d
   ```

   Для проверки конфигурации без локального `.env` можно использовать пример:

   ```powershell
   $env:AVLI_ENV_FILE='backend/.env.example'
   docker compose --env-file backend/.env.example config
   ```

4. Откройте `http://localhost`. Админка находится на `http://localhost/admin/`.

Первого администратора можно создать командой:

```powershell
docker compose exec django python manage.py createsuperuser
```

## Состав

- `django` — существующая админка, печать квитанций, публичный сайт и внутренний API;
- `bot` — Telegram polling-бот на aiogram;
- `db` — PostgreSQL 16;
- `nginx` — reverse proxy, статика, media и ограничение частоты запросов к API.

Публичный поиск принимает только точный лицевой счёт, ответы не кешируются. JSON API защищается заголовком `X-AVLI-API-Key`, когда задан `INTERNAL_API_TOKEN`.

## Локальные тесты без PostgreSQL

```powershell
$env:USE_SQLITE='True'
$env:DEBUG='True'
python backend/manage.py test users_app
```

Для production подключите HTTPS на внешнем reverse proxy или добавьте сертификат в nginx, затем выставьте `SECURE_SSL_REDIRECT=True`, `SECURE_COOKIES=True`, укажите HTTPS-домен в `CSRF_TRUSTED_ORIGINS` и только после проверки HTTPS настройте `SECURE_HSTS_SECONDS`.
