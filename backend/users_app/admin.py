from django.contrib import admin
from django.db import models
from .models import (House, PaymentModel, PeriodSnapshot, UserModel,
                     normalize_payment_date)
from django import forms
from scripts.read_file import (read_optima, read_pay24, read_quickpay, read_umai)
import io
from datetime import datetime
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from openpyxl import Workbook
from django.contrib import messages
from django.utils.safestring import mark_safe

from . import receipts as receipts_lib
from . import reports as reports_lib
from .views import SELECTION_KEY


class _PartialImport(Exception):
    """Внутренний сигнал: в реестре есть проблемные строки, откатываем всё."""


BANK_READERS = {
    'optima': ('Optima', read_optima),
    'pay24': ('Pay24', read_pay24),
    'quickpay': ('QuickPay', read_quickpay),
    'umai': ('Umai', read_umai),
}


@admin.action(description="Выгрузить выбранных в Excel")
def save_to_excel_action(modeladmin, request, queryset):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Пользователи"

    headers = ["Лицевой счет", "ФИО", "Площадь (м2)", "Тариф (сом/м2)", "Сумма по тарифу",
               "Дом", "Квартира", "Адрес", "Сальдо", "Телефон", "Начислено за период",
               "Оплачено за период", "Долг на конец периода"]
    sheet.append(headers)

    for user in queryset.select_related('house'):
        sheet.append([
            user.ls,
            user.fio,
            user.area,
            user.rate,
            user.rate_sum,
            str(user.house) if user.house_id else '',
            user.apartment,
            user.address,
            user.saldo,
            user.phone or '',
            user.period_charge,
            user.last_payment,
            user.current_dept,
        ])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=user_data.xlsx'

    return response


def _period_confirmation(modeladmin, request, queryset, action_name, title,
                         archive_only, conflicts=0):
    """Страница подтверждения с выбором закрываемого месяца.

    Месяц спрашивается явно, а не берётся из текущей даты: закрыть период могут
    и 30-го числа, и 5-го следующего, а архив обязан лечь в тот месяц, за
    который реально начисляли и принимали платежи.
    """
    default_month, default_year = receipts_lib.previous_month(datetime.now())
    # Значения из формы могут быть любыми: страница перерисовывается и после
    # ошибочного ввода, поэтому разбираем их без доверия.
    chosen_year, chosen_month = _requested_period(request)
    total = queryset.count()
    return render(request, "admin/confirm_new_period.html", {
        "title": title,
        "users": queryset[:20],
        "total": total,
        "extra_shown": max(0, total - 20),
        "action_name": action_name,
        "archive_only": archive_only,
        "selected": queryset.values_list("pk", flat=True),
        "opts": modeladmin.model._meta,
        "month_choices": sorted(receipts_lib.MONTHS.items()),
        "year_choices": range(default_year - 2, default_year + 2),
        "default_month": chosen_month or default_month,
        "default_year": chosen_year or default_year,
        "conflicts": conflicts,
    })


def _requested_period(request):
    try:
        return int(request.POST.get("period_year")), int(request.POST.get("period_month"))
    except (TypeError, ValueError):
        return None, None


def _write_archive(queryset, year, month, close_period):
    """Записать снимки за период; при `close_period` — ещё и начислить дальше.

    Снимок обязательно снимается до `start_new_period()`: после него графы
    абонента описывают уже новый месяц, и в архив легли бы чужие цифры.
    """
    snapshots = []
    # select_related: без него `capture` дёргает дом отдельным запросом
    # на каждого из нескольких тысяч абонентов.
    for user in queryset.select_related('house'):
        snapshots.append(PeriodSnapshot.capture(user, year, month))
        if close_period:
            user.start_new_period()
    PeriodSnapshot.objects.bulk_create(snapshots, batch_size=500)
    return len(snapshots)


def _archive_link(year, month):
    return (f'<a href="{reverse("monthly_report")}?period={year}-{month}">'
            f'открыть свод за {reports_lib.period_label(year, month)}</a>')


def _run_period_action(modeladmin, request, queryset, *, action_name, title,
                       archive_only):
    """Общий сценарий обоих действий: подтверждение -> проверка -> запись."""
    if not request.POST.get("confirm_period"):
        return _period_confirmation(modeladmin, request, queryset, action_name,
                                    title, archive_only)

    year, month = _requested_period(request)
    if year is None:
        modeladmin.message_user(request, "Не выбран закрываемый период.", messages.ERROR)
        return _period_confirmation(modeladmin, request, queryset, action_name,
                                    title, archive_only)

    existing = PeriodSnapshot.objects.filter(
        subscriber__in=queryset.values("pk"), year=year, month=month)
    conflicts = existing.count()
    if conflicts and not request.POST.get("overwrite"):
        # Архив за этот месяц уже есть — почти наверняка период закрывают
        # второй раз. Для начисления это означало бы двойное списание тарифа.
        modeladmin.message_user(
            request,
            f"За {reports_lib.period_label(year, month)} архив уже записан "
            f"по {conflicts} абонент(ам). Проверьте, не закрыт ли этот месяц. "
            f"Чтобы всё-таки продолжить, отметьте «перезаписать архив».",
            messages.ERROR,
        )
        return _period_confirmation(modeladmin, request, queryset, action_name,
                                    title, archive_only, conflicts=conflicts)

    with transaction.atomic():
        if conflicts:
            existing.delete()
        written = _write_archive(queryset, year, month, close_period=not archive_only)

    period = reports_lib.period_label(year, month)
    if archive_only:
        text = (f"В архив записано {written} абонент(ов) за {period}. "
                f"Начисление не выполнялось.")
    else:
        text = (f"Период {period} закрыт: {written} абонент(ов) записаны в архив, "
                f"начислено за новый месяц, графа «Оплачено» обнулена.")
    modeladmin.message_user(request, mark_safe(f"{text} {_archive_link(year, month)}"),
                            messages.SUCCESS)
    return None


@admin.action(description="Шаг 3. Начислить за новый месяц (закрыть предыдущий)")
def update_saldo_action(modeladmin, request, queryset):
    """Закрытие расчётного периода — самое опасное действие в системе.

    Повторный запуск начислит тариф второй раз всем выделенным, поэтому месяц
    выбирается явно, а уже записанный за него архив считается признаком того,
    что период закрывают повторно.
    """
    return _run_period_action(
        modeladmin, request, queryset,
        action_name="update_saldo_action",
        title="Подтверждение начисления",
        archive_only=False,
    )


@admin.action(description="Записать в архив за месяц (без начисления)")
def archive_period_action(modeladmin, request, queryset):
    """Снимок текущих расчётов в архив, не трогая сальдо.

    Нужен для первого месяца — когда архив заводят по уже посчитанным данным, —
    и чтобы переснять месяц после исправления платежей.
    """
    return _run_period_action(
        modeladmin, request, queryset,
        action_name="archive_period_action",
        title="Запись в архив",
        archive_only=True,
    )


@admin.action(description="Шаг 2. Квитанции: скачать PDF для печати")
def print_receipts_pdf_action(modeladmin, request, queryset):
    """PDF по выделенным абонентам — по 4 квитанции на лист A4."""
    date = datetime.now()
    # Пересобираем queryset по первичным ключам: сортировка админки может быть
    # любой (или queryset уже нарезан), а печатная пачка обязана идти в порядке
    # адрес -> лицевой счёт, тем же, что и в предпросмотре.
    users = UserModel.objects.filter(
        pk__in=list(queryset.values_list("pk", flat=True))
    ).order_by("address", "ls")

    try:
        pdf = receipts_lib.render_pdf(
            users, date=date, base_url=request.build_absolute_uri("/")
        )
    except receipts_lib.PdfBackendUnavailable as exc:
        messages.error(
            request,
            f"Генерация PDF недоступна ({exc}). Пересоберите образ командой "
            "`docker compose build web` или воспользуйтесь действием "
            "«Квитанции: открыть предпросмотр для печати».",
        )
        return None

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{receipts_lib.pdf_filename(date)}"'
    )
    return response


@admin.action(description="Шаг 2. Квитанции: открыть предпросмотр для печати")
def print_receipts_preview_action(modeladmin, request, queryset):
    """Предпросмотр выделенных абонентов.

    Идентификаторы кладём в сессию, а не в адрес: выделение может быть на
    тысячи строк, и такой URL просто не соберётся.
    """
    request.session[SELECTION_KEY] = list(queryset.values_list("pk", flat=True))
    return redirect(f"{reverse('product_detail')}?src=selection")


class PaymentUploadForm(forms.ModelForm):
    bank = forms.ChoiceField(
        choices=[(key, title) for key, (title, _) in BANK_READERS.items()],
        label="Банк",
        help_text="Формат файла определяется банком: Optima и Umai — .xls/.xlsx, "
                  "Pay24 — .xls, QuickPay — .csv",
    )
    file = forms.FileField(
        label="Файл реестра",
        help_text="Реестр платежей, выгруженный из личного кабинета банка, без правок.",
    )

    class Meta:
        model = PaymentModel
        fields = []


class PaymentInlines(admin.TabularInline):
    model = PaymentModel
    extra = 0
    readonly_fields = ('date', 'payment', 'ls')
    can_delete = True
    verbose_name = 'Платёж'
    verbose_name_plural = 'Платежи абонента'

    def has_add_permission(self, request, obj=None):
        # Платежи заводятся только загрузкой банковского реестра — так сальдо
        # и графа «Оплачено» гарантированно сходятся с первичным документом.
        return False


@admin.register(PaymentModel)
class PaymentAdmin(admin.ModelAdmin):
    form = PaymentUploadForm
    list_display = ('ls', 'date', 'payment')
    search_fields = ('ls',)
    readonly_fields = ['date', 'ls', 'payment']
    change_list_template = "admin/payments_changelist.html"

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        """Загрузка банковского реестра.

        Вся пачка идёт одной транзакцией: раньше цикл обрывался на первой
        неизвестной строке, часть платежей оставалась в базе, остальные молча
        терялись, и админ видел только «Произошла ошибка».
        """
        file = form.cleaned_data['file']
        bank = form.cleaned_data['bank']
        bank_title, reader = BANK_READERS[bank]

        try:
            rows = reader(file)
        except Exception as exc:
            messages.error(request, f"Не удалось прочитать файл {bank_title}: {exc}")
            return

        if not rows:
            messages.warning(request, f"В файле {bank_title} не найдено ни одной строки платежа.")
            return

        # Отпечатки уже загруженных платежей — защита от повторной загрузки того
        # же реестра. Ключ (лицевой счёт, дата, сумма): у Optima, Pay24 и QuickPay
        # в дате есть время до секунды, поэтому совпадение означает именно дубль.
        file_accounts = {str(r.get('Лицевой счет') or '').strip() for r in rows}
        seen = {
            (ls, date, round(amount, 2))
            for ls, date, amount in PaymentModel.objects
                .filter(ls__in=file_accounts)
                .values_list('ls', 'date', 'payment')
        }

        applied, total_sum, missing, bad, duplicates = 0, 0.0, [], [], 0
        try:
            with transaction.atomic():
                for index, row in enumerate(rows, start=1):
                    ls = str(row.get('Лицевой счет') or '').strip()
                    try:
                        amount = round(float(row.get('Сумма')), 2)
                    except (TypeError, ValueError):
                        bad.append(f"строка {index} (ЛС {ls or '—'}): некорректная сумма")
                        continue

                    user = UserModel.objects.filter(ls=ls).first()
                    if user is None:
                        missing.append(ls or f"строка {index}")
                        continue

                    fingerprint = (ls, normalize_payment_date(row.get('Дата')), amount)
                    if fingerprint in seen:
                        duplicates += 1
                        continue
                    seen.add(fingerprint)

                    PaymentModel.objects.create(
                        date=row.get('Дата'),
                        payment=amount,
                        user=user,
                        ls=ls,
                    )
                    applied += 1
                    total_sum += amount

                if missing or bad:
                    # Ничего не применяем, пока админ не разберётся с проблемными
                    # строками:наполовину загруженный реестр хуже, чем незагруженный.
                    raise _PartialImport()
        except _PartialImport:
            problems = []
            if missing:
                shown = ", ".join(missing[:10])
                more = f" и ещё {len(missing) - 10}" if len(missing) > 10 else ""
                problems.append(f"не найдены лицевые счета ({len(missing)}): {shown}{more}")
            if bad:
                problems.append("; ".join(bad[:10]))
            messages.error(
                request,
                f"Реестр {bank_title} не загружен — ни один платёж не применён. "
                + " | ".join(problems)
                + ". Заведите недостающих абонентов или поправьте файл и повторите."
            )
            return
        except Exception as exc:
            messages.error(request, f"Реестр {bank_title} не загружен: {exc}")
            return

        if duplicates and not applied:
            messages.warning(
                request,
                f"Реестр {bank_title} уже был загружен: все {duplicates} строк(и) "
                f"совпадают с ранее принятыми платежами. Ничего не изменено."
            )
            return

        note = (f" Пропущено дублей (уже были загружены): {duplicates}." if duplicates else "")
        messages.success(
            request,
            f"Реестр {bank_title}: загружено {applied} платеж(ей) на {round(total_sum, 2)} сом. "
            f"Сальдо и графа «Оплачено» обновлены." + note
        )

    def response_add(self, request, obj, post_url_continue=None):
        # save_model ничего не создаёт сам (создаются дочерние PaymentModel),
        # поэтому возвращаем админа к списку платежей.
        return redirect(reverse("admin:users_app_paymentmodel_changelist"))


class StreetFilter(admin.SimpleListFilter):
    """Фильтр по улице.

    Домов 96, улиц 23 — по улице список фильтра остаётся обозримым, а дальше
    можно уточнить конкретный дом соседним фильтром.
    """

    title = 'Улица'
    parameter_name = 'street'

    def lookups(self, request, model_admin):
        streets = (House.objects.order_by('street')
                   .values_list('street', flat=True).distinct())
        return [(street, street) for street in streets]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(house__street=self.value())
        return queryset


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    """Справочник домов: по нему группируются своды и работают фильтры."""

    list_display = ('__str__', 'street', 'number', 'subscriber_count', 'service_type')
    list_filter = ('street', 'service_type')
    search_fields = ('street', 'number')
    ordering = ('street', 'number_order', 'number')
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            subscriber_count=models.Count('subscribers'))

    @admin.display(description='Абонентов', ordering='subscriber_count')
    def subscriber_count(self, obj):
        return obj.subscriber_count


@admin.action(description="Выгрузить выбранные строки архива в Excel")
def export_snapshots_excel_action(modeladmin, request, queryset):
    output = io.BytesIO()
    reports_lib.workbook_for_snapshots(queryset).save(output)
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=archive.xlsx'
    return response


@admin.register(PeriodSnapshot)
class PeriodSnapshotAdmin(admin.ModelAdmin):
    """Архив по месяцам: сюда лезут, когда жилец спорит о прошлых начислениях.

    Расчётные графы только для чтения — это документ о том, что уже произошло.
    Руками правятся лишь справочные колонки отчётности («3%», перевод, пеня,
    возврат): они на сальдо абонента не влияют.
    """

    list_display = ('period_column', 'ls', 'fio', 'address', 'opening_debit',
                    'charged_ku', 'paid_ku', 'closing_debit', 'overdue')
    list_filter = ('year', 'month', StreetFilter,
                   ('house', admin.RelatedOnlyFieldListFilter))
    search_fields = ('ls', 'fio', 'address')
    list_select_related = ('house',)
    list_per_page = 50
    change_list_template = 'admin/snapshots_changelist.html'
    actions = [export_snapshots_excel_action]

    readonly_fields = ('year', 'month', 'subscriber', 'ls', 'fio', 'house', 'apartment',
                       'address', 'area', 'rate', 'opening_debit', 'opening_credit',
                       'charged_ku', 'paid_ku', 'closing_debit', 'closing_credit',
                       'overdue', 'created_at')

    fieldsets = (
        ("Период и абонент", {
            "fields": (("year", "month"), "subscriber", "ls", "fio",
                       "house", "apartment", "address", ("area", "rate")),
        }),
        ("Расчёты закрытого месяца", {
            "fields": (("opening_debit", "opening_credit"),
                       ("charged_ku", "paid_ku"),
                       ("closing_debit", "closing_credit"),
                       "overdue", "created_at"),
            "description": "Снимок на момент закрытия периода — то же, что было "
                           "напечатано в квитанции. Не редактируется.",
        }),
        ("Графы отчётности", {
            "fields": (("charged_fee", "paid_fee"),
                       ("transfer", "penalty", "refund"), "service_type"),
            "description": "Заполняются бухгалтером и печатаются в своде. "
                           "На сальдо абонента не влияют. «3%» при записи в архив "
                           "проставляется как доля от начисленного и оплаченного по КУ.",
        }),
    )

    @admin.display(description='Период', ordering='-year')
    def period_column(self, obj):
        return obj.period_label

    def has_add_permission(self, request):
        # Архив создаётся действием закрытия периода — руками строку не завести,
        # иначе в отчёте появятся цифры, которых не было ни в одной квитанции.
        return False


class PeriodSnapshotInline(admin.TabularInline):
    """История начислений прямо в карточке абонента.

    Ради этого архив и заводился: когда жилец приходит с вопросом по прошлым
    месяцам, историю видно сразу, без поиска по отдельному разделу.
    """

    model = PeriodSnapshot
    extra = 0
    can_delete = False
    verbose_name = 'Месяц'
    verbose_name_plural = 'Архив по месяцам'
    fields = ('period_column', 'opening_debit', 'charged_ku', 'paid_ku',
              'closing_debit', 'overdue')
    readonly_fields = fields
    ordering = ('-year', '-month')

    @admin.display(description='Период')
    def period_column(self, obj):
        return obj.period_label

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ('ls', 'fio', 'address', 'area', 'rate', 'saldo', 'current_dept', 'last_payment')
    list_filter = (StreetFilter, ('house', admin.RelatedOnlyFieldListFilter), 'rate')
    list_select_related = ('house',)
    autocomplete_fields = ('house',)
    search_fields = ['address', 'ls', 'fio', 'apartment']
    readonly_fields = ('rate_sum', 'period_charge', 'last_dept', 'last_prepayment',
                       'last_payment', 'current_dept', 'current_prepayment')
    exclude = ('calculated_payment', 'barcode')
    inlines = [PaymentInlines, PeriodSnapshotInline]
    change_list_template = "admin/subscribers_changelist.html"
    list_per_page = 50

    fieldsets = (
        ("Абонент", {
            "fields": ("ls", "fio", "house", "apartment", "address", "phone"),
            "description": "Адрес собирается из дома и квартиры автоматически — "
                           "по нему строятся своды и работают фильтры. "
                           "Заполнять его руками нужно, только если дом не выбран.",
        }),
        ("Начисление", {
            "fields": ("area", "rate", "rate_sum"),
            "description": "Сумма по тарифу считается автоматически: площадь × тариф.",
        }),
        ("Расчёты", {
            "fields": ("saldo", "period_charge", "last_dept", "last_prepayment",
                       "last_payment", "current_dept", "current_prepayment"),
            "description": "Редактируется только «Сальдо» — остальное выводится из него "
                           "и из загруженных платежей. Минус в сальдо — долг, плюс — переплата.",
        }),
    )

    actions = [
        print_receipts_preview_action,
        print_receipts_pdf_action,
        update_saldo_action,
        archive_period_action,
        save_to_excel_action,
    ]
