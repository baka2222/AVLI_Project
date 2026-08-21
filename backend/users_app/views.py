from datetime import datetime
from io import BytesIO
import json
import re
import secrets

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import receipts as receipts_lib
from . import reports as reports_lib
from .models import (
    CallbackRequest,
    FrequentlyAskedQuestion,
    HeroSlide,
    House,
    Service,
    SiteFeature,
    SiteMetric,
    SiteSettings,
    Testimonial,
    UserModel,
)
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


# ----------------------------- API публичного сайта -----------------------------


def _published(queryset):
    return queryset.filter(is_active=True).order_by('sort_order', 'pk')


def _image_source(obj, field='image'):
    image = getattr(obj, field, None)
    if image:
        return image.url
    return getattr(obj, 'image_path', '') or ''


def _service_payload(service):
    return {
        'slug': service.slug,
        'title': service.title,
        'shortDescription': service.short_description,
        'description': service.description,
        'priceLabel': service.price_label,
        'category': service.category,
        'image': _image_source(service),
        'isFeatured': service.is_featured,
        'legacyPath': service.legacy_path,
        'metaTitle': service.meta_title or service.title,
        'metaDescription': service.meta_description or service.short_description,
        'updatedAt': service.updated_at.isoformat(),
    }


def _site_settings_payload(settings_obj):
    return {
        'companyName': settings_obj.company_name,
        'shortName': settings_obj.short_name,
        'tagline': settings_obj.tagline,
        'aboutTitle': settings_obj.about_title,
        'aboutText': settings_obj.about_text,
        'aboutTextSecondary': settings_obj.about_text_secondary,
        'mission': settings_obj.mission,
        'footerText': settings_obj.footer_text,
        'address': settings_obj.address,
        'phonePrimary': settings_obj.phone_primary,
        'phoneSecondary': settings_obj.phone_secondary,
        'email': settings_obj.email,
        'whatsappNumber': settings_obj.whatsapp_number,
        'telegramUrl': settings_obj.telegram_url,
        'mapEmbedUrl': settings_obj.map_embed_url,
        'seoTitle': settings_obj.seo_title,
        'seoDescription': settings_obj.seo_description,
        'ogImage': settings_obj.og_image.url if settings_obj.og_image else '/images/og-avli.jpg',
        'updatedAt': settings_obj.updated_at.isoformat(),
    }


@require_GET
def site_content_api(request):
    """Контент для Next.js. Только опубликованные записи, без персональных данных."""
    settings_obj = SiteSettings.objects.first()
    if settings_obj is None:
        return JsonResponse({'ok': False, 'error': 'site_not_configured'}, status=503)

    services = list(_published(Service.objects.all()))
    payload = {
        'ok': True,
        'settings': _site_settings_payload(settings_obj),
        'heroSlides': [
            {
                'eyebrow': item.eyebrow,
                'title': item.title,
                'description': item.description,
                'buttonText': item.button_text,
                'image': _image_source(item),
            }
            for item in _published(HeroSlide.objects.all())
        ],
        'features': [
            {'title': item.title, 'description': item.description, 'icon': item.icon}
            for item in _published(SiteFeature.objects.all())
        ],
        'metrics': [
            {'value': item.value, 'label': item.label, 'icon': item.icon}
            for item in _published(SiteMetric.objects.all())
        ],
        'services': [_service_payload(item) for item in services],
        'testimonials': [
            {'name': item.name, 'role': item.role, 'text': item.text, 'initials': item.initials}
            for item in _published(Testimonial.objects.all())
        ],
        'faq': [
            {'question': item.question, 'answer': item.answer}
            for item in _published(FrequentlyAskedQuestion.objects.all())
        ],
    }
    response = JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
    return response


@require_GET
def site_services_api(request):
    services = [_service_payload(item) for item in _published(Service.objects.all())]
    response = JsonResponse({'ok': True, 'services': services}, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
    return response


@require_GET
def site_service_detail_api(request, slug):
    service = Service.objects.filter(slug=slug, is_active=True).first()
    if service is None:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
    response = JsonResponse(
        {'ok': True, 'service': _service_payload(service)},
        json_dumps_params={'ensure_ascii': False},
    )
    response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
    return response


def _callback_rate_limited(request, limit=5, window=3600):
    address = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', 'unknown')
    bucket = int(datetime.now().timestamp() // window)
    key = f'callback:{address}:{bucket}'
    if cache.add(key, 1, timeout=window + 60):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, timeout=window + 60)
        return False


@csrf_exempt
@never_cache
@require_POST
def callback_request_api(request):
    """Принимает заявки с сайта и складывает их в привычную Django-админку."""
    if _callback_rate_limited(request):
        return JsonResponse(
            {'ok': False, 'error': 'rate_limited',
             'message': 'Слишком много заявок. Позвоните нам или попробуйте позднее.'},
            status=429,
        )

    try:
        content_length = int(request.META.get('CONTENT_LENGTH') or 0)
    except (TypeError, ValueError):
        content_length = 0
    if content_length > 8192:
        return JsonResponse({'ok': False, 'error': 'payload_too_large'}, status=413)

    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    # Невидимое для человека поле отсекает простейших спам-ботов без капчи.
    # Старое имя ``company`` оставлено для уже открытых в браузере страниц.
    # Важно не возвращать ложный 201: интерфейс может показывать успех только
    # после фактического создания CallbackRequest.
    honeypot = payload.get('contactTime') or payload.get('company')
    if str(honeypot or '').strip():
        response = JsonResponse(
            {
                'ok': False,
                'saved': False,
                'error': 'invalid_submission',
                'message': 'Не удалось отправить заявку. Обновите страницу и попробуйте ещё раз.',
            },
            status=400,
        )
        response['Cache-Control'] = 'no-store, private'
        return response

    name = str(payload.get('name') or '').strip()[:120]
    phone = str(payload.get('phone') or '').strip()
    message = str(payload.get('message') or '').strip()[:2000]
    page = str(payload.get('page') or '').strip()[:320]
    privacy_accepted = payload.get('privacyAccepted') is True

    if not privacy_accepted:
        return JsonResponse(
            {'ok': False, 'error': 'privacy_required',
             'message': 'Подтвердите согласие на обработку контактных данных.'},
            status=400,
        )
    if not re.fullmatch(r'[\d\s+()\-]{7,30}', phone):
        return JsonResponse(
            {'ok': False, 'error': 'invalid_phone',
             'message': 'Проверьте номер телефона и попробуйте ещё раз.'},
            status=400,
        )

    request_item = CallbackRequest.objects.create(
        name=name,
        phone=phone,
        message=message,
        page=page,
    )
    response = JsonResponse(
        {'ok': True, 'saved': True, 'id': request_item.pk},
        status=201,
    )
    response['Cache-Control'] = 'no-store, private'
    return response


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


# ----------------------------- своды для бухгалтерии -----------------------------
# Отчёты закрыты правами персонала: это финансовые данные всех жильцов сразу.

def _report_params(request):
    """Фильтры свода из адресной строки: период, дом, режим, только должники."""
    year, month = reports_lib.latest_period()
    if year is None:
        # Архива ещё нет — показываем прошлый месяц, он же будет первым закрытым.
        month, year = receipts_lib.previous_month(datetime.now())

    raw_period = (request.GET.get("period") or "").strip()
    if raw_period:
        try:
            raw_year, raw_month = raw_period.split("-")
            year, month = int(raw_year), int(raw_month)
        except (TypeError, ValueError):
            pass

    house = None
    raw_house = (request.GET.get("house") or "").strip()
    if raw_house.isdigit():
        house = House.objects.filter(pk=int(raw_house)).first()

    return {
        "year": year,
        "month": month,
        "house": house,
        "mode": request.GET.get("mode") or reports_lib.MODE_HOUSES,
        "only_debtors": request.GET.get("debtors") in ("1", "on", "true"),
    }


def _report_context(request, report):
    """Общий контекст шаблона свода: сам отчёт плюс наполнение фильтров."""
    periods = reports_lib.available_periods()
    selected = (report["year"], report["month"])
    if selected not in periods:
        periods = [selected] + periods

    query = request.GET.copy()
    query.pop("page", None)
    suffix = f"?{query.urlencode()}" if query else ""

    return {
        "report": report,
        "rows": reports_lib.table_rows(report),
        "period_choices": [
            (f"{year}-{month}", reports_lib.period_label(year, month))
            for year, month in periods
        ],
        "selected_period": f"{report['year']}-{report['month']}",
        "houses": reports_lib.available_houses(),
        "selected_house_id": report["house"].pk if report["house"] else None,
        "pdf_url": reverse("monthly_report_pdf") + suffix,
        "excel_url": reverse("monthly_report_excel") + suffix,
        "admin_url": reverse("admin:users_app_periodsnapshot_changelist"),
        "company_name": receipts_lib.COMPANY_NAME,
        "company_contacts": receipts_lib.COMPANY_CONTACTS,
        "printed_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }


@staff_member_required
def monthly_report(request):
    """Свод за месяц: по домам целиком либо по абонентам одного дома."""
    report = reports_lib.build_report(**_report_params(request))
    return render(request, "reports/monthly.html", _report_context(request, report))


@staff_member_required
def monthly_report_pdf(request):
    """Тот же свод в PDF — раскладка не зависит от браузера и принтера."""
    report = reports_lib.build_report(**_report_params(request))
    context = _report_context(request, report)
    context["pdf"] = True
    html = render_to_string("reports/monthly.html", context, request=request)

    try:
        pdf = receipts_lib.html_to_pdf(html, base_url=request.build_absolute_uri("/"))
    except receipts_lib.PdfBackendUnavailable as exc:
        return HttpResponse(
            "Генерация PDF недоступна: WeasyPrint не установлен или ему не хватает "
            f"системных библиотек ({exc}). Пересоберите образ командой "
            "`docker compose build web` — либо печатайте свод из браузера.",
            status=501,
            content_type="text/plain; charset=utf-8",
        )

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{reports_lib.report_filename(report, "pdf")}"'
    )
    return response


@staff_member_required
def monthly_report_excel(request):
    """Тот же свод в Excel — для дальнейшей работы бухгалтерии."""
    report = reports_lib.build_report(**_report_params(request))

    buffer = BytesIO()
    reports_lib.workbook_for(report).save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{reports_lib.report_filename(report, "xlsx")}"'
    )
    return response
