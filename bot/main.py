"""Telegram-бот АВЛИ: выдаёт цифровую квитанцию по лицевому счёту."""

import asyncio
from html import escape
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_URL = os.getenv(
    "ACCOUNT_API_URL",
    "http://django:8000/api/v1/account/lookup/",
).strip()
API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "").strip()

router = Router()


def money(value):
    return f"{float(value or 0):,.2f}".replace(",", " ").replace(".", ",")


def number(value):
    return f"{float(value or 0):.2f}".rstrip("0").rstrip(".").replace(".", ",")


def account_message(account):
    if account["balance_status"] == "prepayment":
        balance_line = f"Предоплата: <b>{money(account['closing_prepayment'])} сом</b>"
    elif account["balance_status"] == "settled":
        balance_line = "<b>Задолженности нет</b>"
    else:
        balance_line = f"Итого к оплате: <b>{money(account['total_due'])} сом</b>"

    return (
        f"<b>АВЛИ · электронная квитанция</b>\n"
        f"Период: <b>{escape(account['period'])}</b>\n\n"
        f"Лицевой счёт: <code>{escape(account['account_number'])}</code>\n"
        f"Плательщик: {escape(account['full_name'])}\n"
        f"Адрес: {escape(account['address'])}\n"
        f"Площадь: {number(account['area'])} м²\n"
        f"Тариф: {number(account['rate'])} сом/м²\n\n"
        f"<b>Расчёт за период</b>\n"
        f"Долг на начало: {money(account['opening_debt'])} сом\n"
        f"Предоплата на начало: {money(account['opening_prepayment'])} сом\n"
        f"Начислено: {money(account['charged'])} сом\n"
        f"Оплачено: {money(account['paid'])} сом\n"
        f"Долг на конец: {money(account['closing_debt'])} сом\n"
        f"Предоплата на конец: {money(account['closing_prepayment'])} сом\n\n"
        f"{balance_line}\n\n"
        f"<i>Данные сформированы {escape(account['generated_at'])}</i>"
    )


async def fetch_account(account_number):
    headers = {"X-AVLI-API-Key": API_TOKEN} if API_TOKEN else {}
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            API_URL,
            json={"account_number": account_number},
            headers=headers,
        ) as response:
            try:
                payload = await response.json()
            except (aiohttp.ContentTypeError, ValueError):
                payload = {"ok": False, "error": "bad_response"}
            return response.status, payload


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "<b>Здравствуйте! Это бот АВЛИ.</b>\n\n"
        "Отправьте лицевой счёт одним сообщением — я покажу начисления, оплату и текущий баланс.\n\n"
        "Пример: <code>1517227-4</code>"
    )


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Введите номер с квитанции. Дефис можно не ставить.\n"
        "Если счёт не находится, проверьте все цифры и отправьте его повторно."
    )


@router.message(F.text)
async def lookup(message: Message, bot: Bot):
    text = (message.text or "").strip()
    if text.startswith("/"):
        await message.answer("Неизвестная команда. Отправьте лицевой счёт или используйте /help.")
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        status, payload = await fetch_account(text)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        await message.answer("Сервис временно не отвечает. Попробуйте ещё раз через несколько минут.")
        return

    if status == 200 and payload.get("ok"):
        await message.answer(account_message(payload["account"]))
    elif status == 404:
        await message.answer("Лицевой счёт не найден. Проверьте номер и отправьте его ещё раз.")
    elif status == 400 and payload.get("error") == "bad_response":
        # Ответ не разобрался как JSON — значит отвечал не наш обработчик
        # (например, страница DisallowedHost). Винить ввод пользователя нельзя.
        await message.answer("Сервис отвечает некорректно. Сообщите администратору.")
    elif status == 400:
        await message.answer(escape(payload.get("message") or "Проверьте формат лицевого счёта."))
    elif status == 429:
        await message.answer("Слишком много запросов. Подождите минуту и попробуйте снова.")
    else:
        await message.answer("Не удалось получить данные. Попробуйте позже.")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Переменная BOT_TOKEN не задана")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Как найти лицевой счёт"),
    ])
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
