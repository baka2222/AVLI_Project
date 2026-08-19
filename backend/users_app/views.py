from datetime import datetime
import json
import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import receipts as receipts_lib
from .models import UserModel
from .public_accounts import (
    AccountNotFound,
    InvalidAccountNumber,
    build_public_account,
    find_account,
)


# Листов A4 на одну страницу превью. 25 листов = 100 квитанций — страница
# открывается мгновенно даже при 4000 абонентов в базе.
SHEETS_PER_PAGE = 25

# Ключ сессии, через который админка передаёт сюда выделенных абонентов:
# в GET-параметры 4000 идентификаторов не помещаются.
SELECTION_KEY = "receipt_selection"


def _is_rate_limited(request, limit=20, window=60):
    """Простой лимит на подбор лицевых счетов в одном процессе Django.

    В production он работает вторым слоем после nginx. X-Forwarded-For здесь
    намеренно не читается: этот заголовок клиент может подделать.
    """
    # nginx полностью перезаписывает X-Real-IP, а сам Django наружу не опубликован.
    address = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "unknown")
    bucket = int(datetime.now().timestamp() // window)
    key = f"account-lookup:{address}:{bucket}"
    if cache.add(key, 1, timeout=window + 5):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, timeout=window + 5)
        return False


def _lookup_error_message(exc):
    if isinstance(exc, InvalidAccountNumber):
        return str(exc)
    return "Лицевой счёт не найден. Проверьте номер и попробуйте ещё раз."


@never_cache
@csrf_exempt
@require_http_methods(["GET", "POST"])
def home(request):
    """Публичная страница: точный поиск и цифровая версия квитанции."""
    account = None
    error = ""
    submitted_account = ""

    if request.method == "POST":
        submitted_account = (request.POST.get("account_number") or "").strip()
        if _is_rate_limited(request):
            error = "Слишком много запросов. Подождите минуту и повторите попытку."
        else:
            try:
                account = build_public_account(find_account(submitted_account))
            except (InvalidAccountNumber, AccountNotFound) as exc:
                error = _lookup_error_message(exc)

    bot_username = settings.TELEGRAM_BOT_USERNAME.lstrip("@")
    response = render(request, "public/home.html", {
        "account": account,
        "error": error,
        "submitted_account": submitted_account,
        "telegram_bot_url": f"https://t.me/{bot_username}" if bot_username else "",
    })
    response["Cache-Control"] = "no-store, private"
    return response


@csrf_exempt
@never_cache
@require_POST
def account_lookup_api(request):
    """Внутренний JSON API, которым пользуется Telegram-бот."""
    expected_token = settings.INTERNAL_API_TOKEN
    if not expected_token and not settings.DEBUG:
        return JsonResponse({"ok": False, "error": "api_not_configured"}, status=503)
    supplied_token = request.headers.get("X-AVLI-API-Key", "")
    authenticated = bool(
        expected_token and secrets.compare_digest(supplied_token, expected_token)
    )
    if expected_token and not authenticated:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    if not authenticated and _is_rate_limited(request, limit=60):
        return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)

    try:
        try:
            content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError):
            content_length = 0
        if content_length > 2048:
            raise InvalidAccountNumber("Слишком длинный запрос.")
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            raise InvalidAccountNumber("Ожидается объект с номером лицевого счёта.")
        user = find_account(payload.get("account_number"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
    except InvalidAccountNumber as exc:
        return JsonResponse({"ok": False, "error": "invalid_account", "message": str(exc)}, status=400)
    except AccountNotFound:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    response = JsonResponse({"ok": True, "account": build_public_account(user)})
    response["Cache-Control"] = "no-store, private"
    return response


@require_GET
def healthcheck(request):
    return JsonResponse({"status": "ok"})


def get_print_queryset(request):
    """Абоненты для печати с учётом выборки из админки и фильтра в адресе.

    Порядок фиксирован (адрес, затем лицевой счёт) — печатная пачка должна
    совпадать с маршрутом разноски и быть воспроизводимой между запусками.
    """
    queryset = UserModel.objects.order_by("address", "ls")

    if request.GET.get("src") == "selection":
        queryset = queryset.filter(pk__in=request.session.get(SELECTION_KEY) or [])

    search = (request.GET.get("q") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(address__icontains=search)
            | Q(ls__icontains=search)
            | Q(fio__icontains=search)
        )

    return queryset


def _page_query(request, page_number):
    params = request.GET.copy()
    params["page"] = page_number
    return params.urlencode()


def product_detail(request):
    """HTML-превью квитанций: постранично, по 4 штуки на лист A4."""
    queryset = get_print_queryset(request)
    paginator = Paginator(queryset, SHEETS_PER_PAGE * receipts_lib.PER_SHEET)
    page = paginator.get_page(request.GET.get("page"))

    pdf_params = request.GET.copy()
    pdf_params.pop("page", None)
    pdf_query = pdf_params.urlencode()

    html = receipts_lib.render_sheets_html(
        page.object_list,
        total_count=paginator.count,
        page_number=page.number,
        num_pages=paginator.num_pages,
        has_prev=page.has_previous(),
        has_next=page.has_next(),
        prev_query=_page_query(request, page.previous_page_number() if page.has_previous() else 1),
        next_query=_page_query(request, page.next_page_number() if page.has_next() else paginator.num_pages),
        pdf_url=reverse("receipts_pdf") + (f"?{pdf_query}" if pdf_query else ""),
    )
    return HttpResponse(html)


def receipts_pdf(request):
    """Готовый PDF: раскладка не зависит от настроек браузера и принтера."""
    queryset = get_print_queryset(request)
    date = datetime.now()

    try:
        pdf = receipts_lib.render_pdf(
            queryset, date=date, base_url=request.build_absolute_uri("/")
        )
    except receipts_lib.PdfBackendUnavailable as exc:
        return HttpResponse(
            "Генерация PDF недоступна: WeasyPrint не установлен или ему не хватает "
            f"системных библиотек ({exc}). Пересоберите образ командой "
            "`docker compose build web` — либо печатайте из HTML-превью.",
            status=501,
            content_type="text/plain; charset=utf-8",
        )

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{receipts_lib.pdf_filename(date)}"'
    )
    return response
