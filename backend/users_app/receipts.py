"""Подготовка данных и рендеринг квитанций (HTML-превью и PDF).

Модуль намеренно не трогает модели: он строит plain-dict контекст, чтобы
случайное сохранение объекта во время печати было невозможно.
"""

from datetime import datetime
from io import BytesIO
from itertools import groupby

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

import barcode


MONTHS = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}

# Реквизиты организации в шапке квитанции.
COMPANY_NAME = 'ОсОО "АВЛИ"'
COMPANY_CONTACTS = "ул. Байтик баатыра 9а тел 54-45-72"
COMPANY_DISTRICT = "Участок 3"
COMPANY_LINE_NO = "1"

# Квитанций на листе A4: сетка 2x2, альбомная ориентация.
SHEET_COLS = 2
SHEET_ROWS = 2
PER_SHEET = SHEET_COLS * SHEET_ROWS

# Сколько квитанций рендерится за один проход WeasyPrint. Ограничивает пиковую
# память на больших выгрузках. Обязано делиться на PER_SHEET, иначе на стыке
# порций появятся полупустые листы.
PDF_CHUNK_SIZE = 200


class PdfBackendUnavailable(RuntimeError):
    """WeasyPrint недоступен: не установлен или нет системных библиотек."""


def _load_pdf_backend():
    """Импорт бэкендов PDF отложенный: HTML-превью работает и без них.

    Ловим и OSError: если weasyprint установлен, но нет системных библиотек
    (pango/cairo — типично при запуске вне Docker), он падает именно так,
    и без этого пользователь получал бы 500 вместо внятного сообщения.
    """
    try:
        from weasyprint import HTML
        from pypdf import PdfWriter
    except (ImportError, OSError) as exc:
        raise PdfBackendUnavailable(str(exc)) from exc
    return HTML, PdfWriter


def html_to_pdf(html, base_url=None):
    """HTML -> PDF. Общая точка для квитанций и сводов бухгалтерии."""
    HTML, _ = _load_pdf_backend()
    return HTML(string=html, base_url=base_url).write_pdf()


def previous_month(date):
    """(номер месяца, год) для месяца, предшествующего `date`."""
    if date.month > 1:
        return date.month - 1, date.year
    return 12, date.year - 1


def digits(value):
    """Только цифры из строки — лицевой счёт может содержать разделители."""
    return "".join(filter(str.isdigit, str(value or "")))


def barcode_payload(ls, current_dept):
    """Значение штрихкода: 12 + ЛС + сумма долга в копейках (6 знаков) + 00.

    Общая точка для models.UserModel.save() и печати — чтобы штрихкод на
    бумажной квитанции и штрихкод в базе не разъехались.
    """
    return f"12{digits(ls)}{int(abs(current_dept or 0) * 10):06}00"


def barcode_svg(value, quiet_zone=10, bar_height=100):
    """Инлайн-SVG штрихкода Code128.

    Векторный SVG вместо PNG по HTTP: нет 4000 запросов к серверу за
    картинками, нет обращений к диску, и в PDF штрихкод остаётся чётким при
    любом масштабе. viewBox + preserveAspectRatio="none" растягивают код точно
    по размеру блока, заданного в CSS.
    """
    modules = barcode.get_barcode_class("code128")(str(value)).build()[0]

    rects = []
    x = quiet_zone
    for bit, run in groupby(modules):
        width = len(list(run))
        if bit == "1":
            rects.append(f'<rect x="{x}" width="{width}" height="{bar_height}"/>')
        x += width
    total = x + quiet_zone

    return mark_safe(
        f'<svg class="bc" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total} {bar_height}" preserveAspectRatio="none" '
        f'shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{bar_height}" fill="#fff"/>'
        f'<g fill="#000">{"".join(rects)}</g></svg>'
    )


def build_receipts(users, date=None):
    """Список словарей-квитанций по queryset/списку абонентов."""
    date = date or datetime.now()
    prev_month, _ = previous_month(date)

    period = f"{MONTHS[date.month]} {date.year} г."
    current_date = f"на 1-е {MONTHS[date.month]}"
    previous_date = f"на 1-е {MONTHS[prev_month]}"
    printed_at = date.strftime("%d.%m.%Y %H:%M:%S")

    receipts = []
    for user in users:
        receipts.append({
            "ls": user.ls,
            "fio": user.fio,
            "address": user.address,
            "area": user.area,
            "rate": user.rate,
            # «Начислено» — снимок на момент начисления, а не текущее area*rate.
            "charged": round(user.period_charge or 0, 2),
            "last_dept": round(user.last_dept or 0, 2),
            "last_prepayment": round(user.last_prepayment or 0, 2),
            "last_payment": round(user.last_payment or 0, 2),
            "current_prepayment": round(user.current_prepayment or 0, 2),
            "total": round(user.current_dept or 0, 2),
            "period": period,
            "current_date": current_date,
            "previous_date": previous_date,
            "printed_at": printed_at,
            "barcode": barcode_svg(barcode_payload(user.ls, user.current_dept)),
        })
    return receipts


def chunked(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def sheet_context(receipts, **extra):
    """Контекст для receipt.html.

    Раскладываем квитанции по листам здесь, а не в шаблоне: явные листы дают
    детерминированную разбивку на страницы (по 4 на A4) и в PDF, и в браузере,
    вместо того чтобы полагаться на автоматические разрывы страниц.
    """
    sheets = []
    for chunk in chunked(list(receipts), PER_SHEET):
        cells = list(chunk) + [None] * (PER_SHEET - len(chunk))
        sheets.append(list(chunked(cells, SHEET_COLS)))

    context = {
        "sheets": sheets,
        "per_sheet": PER_SHEET,
        "company_name": COMPANY_NAME,
        "company_contacts": COMPANY_CONTACTS,
        "company_district": COMPANY_DISTRICT,
        "company_line_no": COMPANY_LINE_NO,
    }
    context.update(extra)
    return context


def render_sheets_html(users, date=None, **extra):
    """HTML одного «пакета» листов — для превью и печати из браузера."""
    receipts = build_receipts(users, date=date)
    return render_to_string("receipt.html", sheet_context(receipts, **extra))


def render_pdf(users, date=None, base_url=None):
    """Собрать PDF по списку абонентов.

    Каждая порция сразу дописывается в готовый PDF и выбрасывается из памяти.
    Копить объекты страниц WeasyPrint нельзя: они держат полное дерево вёрстки,
    и на 4000 квитанций (1000 страниц) процесс выносит по OOM. Готовые
    PDF-страницы весят на порядки меньше, поэтому склейка через pypdf проходит
    в постоянной по объёму памяти.
    """
    HTML, PdfWriter = _load_pdf_backend()

    date = date or datetime.now()
    chunks = list(chunked(list(users), PDF_CHUNK_SIZE)) or [[]]

    def render_chunk(chunk):
        html = render_sheets_html(chunk, date=date, pdf=True)
        return HTML(string=html, base_url=base_url).write_pdf()

    if len(chunks) == 1:
        return render_chunk(chunks[0])

    writer = PdfWriter()
    try:
        for chunk in chunks:
            writer.append(BytesIO(render_chunk(chunk)))
        buffer = BytesIO()
        writer.write(buffer)
    finally:
        writer.close()
    return buffer.getvalue()


def pdf_filename(date=None):
    date = date or datetime.now()
    return f"receipts_{date:%Y-%m-%d_%H%M}.pdf"
