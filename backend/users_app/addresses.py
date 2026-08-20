"""Разбор адреса абонента на дом и квартиру.

Адреса достались от старой DBF-базы одной строкой и написаны как попало:
«8 микр-он дом 11 кв.19», «ул. Саманчина3а кв.7», «Малдыбаева 32 кв. 5»,
«ул Байтик-Батыра 6» и «ул Байтик-Баатыра дом 9» — это одна улица.

Пока адрес был текстом, отчёт по дому собрать было нельзя: одна и та же улица
разъезжалась на несколько написаний. Здесь единственное место, где строка
разбирается на части, — им пользуются и миграция, и любой будущий импорт,
поэтому справочник домов не зарастает вариантами написания заново.

Таблицы соответствий ниже — про конкретные данные АВЛИ, их можно дополнять.
Справочник домов редактируется в админке, так что ошибка разбора не фатальна:
дом можно переименовать руками.
"""

import re


# Тип улицы: как пишут в базе -> как печатаем.
STREET_TYPE_PATTERNS = (
    (re.compile(r"^ул(?:\.|ица)?\s+", re.IGNORECASE), "ул. "),
    (re.compile(r"^пер(?:\.|еулок)?\s+", re.IGNORECASE), "пер. "),
    (re.compile(r"^(?:пр\.?|проспект)\s+", re.IGNORECASE), "пр. "),
)

# Написания одной и той же улицы. Ключ — приведённое к нижнему регистру
# название уже после нормализации типа улицы.
STREET_ALIASES = {
    "ул. байтик-батыра": "ул. Байтик-Баатыра",
    "ул. байтик баатыра": "ул. Байтик-Баатыра",
    "ул. байтик батыра": "ул. Байтик-Баатыра",
    # В DBF названия обрезаны по ширине поля старой программы.
    "ул. политехническ": "ул. Политехническая",
    "ул. днепропетровск": "ул. Днепропетровская",
    # Улица записана без типа.
    "малдыбаева": "ул. Малдыбаева",
    "суеркулова": "ул. Суеркулова",
    "ул. ж.пудовкина": "ул. Ж. Пудовкина",
    "ул. м.горького": "ул. М. Горького",
    "ул. л.толстого": "ул. Л. Толстого",
    # Микрорайоны: «10 мкр», «Мкр 10» и «8 микр-он» — три разных формата.
    "10 мкр": "10 мкр-н",
    "мкр 10": "10 мкр-н",
    "8 микр-он": "8 мкр-н",
    "8 мкр": "8 мкр-н",
    "аламедин 1": "Аламедин-1",
}

# «… кв.19», «… кв. 19», «…, кв 19» — квартира всегда в хвосте строки.
APARTMENT_RE = re.compile(r"^(?P<house>.*?)[\s,]*кв\.?\s*(?P<apartment>[^\s].*)?$", re.IGNORECASE)

# Номер дома — последнее «слово» с цифрой: «11», «3 а», «36б», «8/1», «1\4».
NUMBER_RE = re.compile(
    r"^(?P<street>.*?)[\s,]*(?:дом|д\.)?\s*(?P<number>\d+[^\s]*(?:\s[а-яёa-z])?)\s*$",
    re.IGNORECASE,
)


def normalize_street(street):
    """Привести название улицы к единому виду."""
    text = re.sub(r"\s+", " ", str(street or "")).strip(" ,.")
    if not text:
        return ""

    for pattern, replacement in STREET_TYPE_PATTERNS:
        if pattern.match(text):
            text = pattern.sub(replacement, text, count=1)
            break

    return STREET_ALIASES.get(text.lower(), text)


def normalize_number(number):
    """Номер дома: «3 а» -> «3а», «1\4» -> «1/4»."""
    text = re.sub(r"\s+", "", str(number or "")).strip(" ,.")
    return text.replace("\\", "/").lower()


def normalize_apartment(apartment):
    return re.sub(r"\s+", "", str(apartment or "")).strip(" ,.").lower()


def parse_address(address):
    """Разобрать строку адреса.

    Возвращает (улица, номер дома, квартира). Любая часть может оказаться
    пустой — на «мусорных» адресах вида «кв.» разбор не должен падать.
    """
    text = re.sub(r"\s+", " ", str(address or "")).strip()
    if not text:
        return "", "", ""

    match = APARTMENT_RE.match(text)
    if match:
        house_part = match.group("house") or ""
        apartment = normalize_apartment(match.group("apartment"))
    else:
        house_part, apartment = text, ""

    match = NUMBER_RE.match(house_part)
    if match:
        street = normalize_street(match.group("street"))
        number = normalize_number(match.group("number"))
    else:
        # Номер дома не распознан — считаем домом всю строку, чтобы абонент
        # хотя бы попал в справочник и его можно было поправить руками.
        street, number = normalize_street(house_part), ""

    return street, number, apartment


def house_title(street, number):
    """Наименование дома для печати: «ул. Малдыбаева дом 36б»."""
    street = (street or "").strip()
    number = (number or "").strip()
    if street and number:
        return f"{street} дом {number}"
    return street or number


def format_address(house, apartment):
    """Собрать адрес абонента обратно в строку — так, как её печатает квитанция."""
    title = str(house) if house else ""
    apartment = (apartment or "").strip()
    if title and apartment:
        return f"{title} кв.{apartment}"
    return title or apartment
