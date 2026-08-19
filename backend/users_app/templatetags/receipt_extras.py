"""Фильтры форматирования чисел для квитанций."""

from django import template

register = template.Library()


def _comma(text):
    return text.replace(".", ",")


@register.filter
def money(value):
    """Денежная сумма: всегда два знака после запятой (1234,50).

    В старом шаблоне часть сумм печаталась как «423,0», а часть — как
    захардкоженный «0.00»; в одном документе это выглядело как ошибка расчёта.
    """
    try:
        return _comma(f"{float(value or 0):.2f}")
    except (TypeError, ValueError):
        return value


@register.filter
def num(value):
    """Площадь и тариф: 1-2 знака после запятой без хвостовых нулей (24,0 / 24,55)."""
    try:
        text = f"{float(value or 0):.2f}"
    except (TypeError, ValueError):
        return value
    if text.endswith("0"):
        text = text[:-1]
    return _comma(text)
