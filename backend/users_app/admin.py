from django.contrib import admin
from .models import (UserModel, PaymentModel, normalize_payment_date)
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

from . import receipts as receipts_lib
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
               "Адрес", "Сальдо", "Телефон", "Начислено за период", "Оплачено за период",
               "Долг на конец периода"]
    sheet.append(headers)

    for user in queryset:
        sheet.append([
            user.ls,
            user.fio,
            user.area,
            user.rate,
            user.rate_sum,
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


@admin.action(description="Шаг 3. Начислить за новый месяц (закрыть предыдущий)")
def update_saldo_action(modeladmin, request, queryset):
    """Закрытие расчётного периода — самое опасное действие в системе.

    Повторный запуск начислит тариф второй раз всем выделенным, поэтому
    спрашиваем подтверждение на отдельной странице.
    """
    if request.POST.get("confirm_period"):
        with transaction.atomic():
            for user in queryset:
                user.start_new_period()
        modeladmin.message_user(
            request,
            f"Начислено за новый месяц: {queryset.count()} абонент(ов). "
            f"Графа «Оплачено» обнулена, остатки перенесены на начало периода.",
            messages.SUCCESS,
        )
        return None

    return render(request, "admin/confirm_new_period.html", {
        "title": "Подтверждение начисления",
        "users": queryset[:20],
        "total": queryset.count(),
        "extra_shown": max(0, queryset.count() - 20),
        "action_name": "update_saldo_action",
        "selected": queryset.values_list("pk", flat=True),
        "opts": modeladmin.model._meta,
    })


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


@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ('ls', 'fio', 'address', 'area', 'rate', 'saldo', 'current_dept', 'last_payment')
    list_filter = ('rate',)
    search_fields = ['address', 'ls', 'fio']
    readonly_fields = ('rate_sum', 'period_charge', 'last_dept', 'last_prepayment',
                       'last_payment', 'current_dept', 'current_prepayment')
    exclude = ('calculated_payment', 'barcode')
    inlines = [PaymentInlines]
    change_list_template = "admin/subscribers_changelist.html"
    list_per_page = 50

    fieldsets = (
        ("Абонент", {
            "fields": ("ls", "fio", "address", "phone"),
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
        save_to_excel_action,
    ]
