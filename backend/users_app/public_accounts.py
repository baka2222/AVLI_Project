"""Общий слой данных публичного сайта и Telegram-бота.

Никаких отдельных формул здесь нет: значения строятся через тот же
``receipts.build_receipts``, что и бумажные квитанции.
"""

import re

from django.db.models import F, Value
from django.db.models.functions import Replace

from .models import UserModel
from .receipts import COMPANY_NAME, build_receipts, digits


class InvalidAccountNumber(ValueError):
    pass


class AccountNotFound(LookupError):
    pass


def normalize_account_number(value):
    raw = str(value or "").strip()
    if len(raw) > 50:
        raise InvalidAccountNumber("Лицевой счёт слишком длинный.")
    if raw and not re.fullmatch(r"[\d\s\-–—−]+", raw):
        raise InvalidAccountNumber("Используйте только цифры и дефис.")

    normalized = digits(raw)
    if not 5 <= len(normalized) <= 20:
        raise InvalidAccountNumber("Введите от 5 до 20 цифр лицевого счёта.")
    return normalized


def find_account(value):
    """Найти абонента по ЛС, не требуя от пользователя вводить дефис."""
    normalized = normalize_account_number(value)
    normalized_column = F("ls")
    for separator in ("-", " ", "–", "—", "−"):
        normalized_column = Replace(normalized_column, Value(separator), Value(""))

    user = (
        UserModel.objects
        .annotate(normalized_ls=normalized_column)
        .filter(normalized_ls=normalized)
        .order_by("pk")
        .first()
    )
    if user is None:
        raise AccountNotFound(normalized)
    return user


def build_public_account(user, date=None):
    """JSON-совместимое представление всех полей бумажной квитанции."""
    receipt = build_receipts([user], date=date)[0]
    debt = receipt["total"]
    prepayment = receipt["current_prepayment"]
    if debt > 0:
        balance_status = "debt"
        balance_label = "Есть сумма к оплате"
    elif prepayment > 0:
        balance_status = "prepayment"
        balance_label = "Есть предоплата"
    else:
        balance_status = "settled"
        balance_label = "Задолженности нет"

    return {
        "company": COMPANY_NAME,
        "account_number": receipt["ls"],
        "full_name": receipt["fio"],
        "address": receipt["address"],
        "area": receipt["area"],
        "rate": receipt["rate"],
        "period": receipt["period"],
        "previous_date": receipt["previous_date"],
        "current_date": receipt["current_date"],
        "opening_debt": receipt["last_dept"],
        "opening_prepayment": receipt["last_prepayment"],
        "charged": receipt["charged"],
        "paid": receipt["last_payment"],
        "closing_debt": debt,
        "closing_prepayment": prepayment,
        "benefit": 0.0,
        "tax": 0.0,
        "penalty": 0.0,
        "total_due": debt,
        "balance_status": balance_status,
        "balance_label": balance_label,
        "generated_at": receipt["printed_at"],
    }
