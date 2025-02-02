from django.contrib import admin
from .models import (UserModel, PaymentModel)
from django import forms
from scripts.read_file import (read_optima, read_pay24, read_quickpay, read_umai)
import io
from django.http import HttpResponse
from openpyxl import Workbook
from django.contrib import messages


@admin.action(description="Сохранить данные в Excel-файл")
def save_to_excel_action(modeladmin, request, queryset):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Пользователи"

    headers = ["Лицевой счет", "ФИО", "Площадь (м2)", "Тариф (сом/м2)", "Сумма по тарифу", "Адрес", "Сальдо", "Телефон"]
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
            user.phone or ''
        ])
    
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=user_data.xlsx'

    return response


@admin.action(description="Обновить сальдо для выбранных объектов")
def update_saldo_action(modeladmin, request, queryset):
    for user in queryset:
        user.saldo -= user.rate_sum
        user.last_dept = user.current_dept

        if user.saldo < 0:
            user.current_dept = abs(user.saldo)
            user.current_prepayment = 0.0
        elif user.saldo > 0:
            user.current_dept = 0.0
            user.current_prepayment = user.saldo
        else:
            user.current_dept = 0.0
            user.current_prepayment = 0.0

        user.save()

    modeladmin.message_user(request, "Сальдо успешно обновлено для выбранных абонентов!")



class PaymentUploadForm(forms.ModelForm):
    bank = forms.ChoiceField(
        choices=[
            ('optima', 'Optima'),
            ('pay24', 'Pay24'),
            ('quickpay', 'QuickPay'),
            ('umai', 'Umai')
        ],
        label="Выберите банк"
    )
    file = forms.FileField(label="Выберите файл")

    class Meta:
        model = PaymentModel
        fields = []


class PaymentInlines(admin.TabularInline):
    model = PaymentModel
    extra = 0


class PaymentAdmin(admin.ModelAdmin):
    form = PaymentUploadForm
    readonly_fields = ['date', 'ls', 'payment']
    
    def has_change_permission(self, request, obj=None):
        if obj: 
            return False  
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        try:
            file = form.cleaned_data['file']
            bank = form.cleaned_data['bank']

            if bank == 'optima':
                data = read_optima(file)
            elif bank == 'pay24':
                data = read_pay24(file)
            elif bank == 'quickpay':
                data = read_quickpay(file)
            elif bank == 'umai':
                data = read_umai(file)

            if data: 
                for i in data:
                    user = UserModel.objects.get(ls=i['Лицевой счет'])

                    PaymentModel.objects.create(
                    date=i['Дата'],
                    payment=i['Сумма'],
                    user=user,
                    ls=i['Лицевой счет']
                    )
                
        except Exception as e:
            messages.error(request, f"Произошла ошибка при обработке файла: {str(e)}")
    

class UserModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rate_sum', 'last_dept')
    search_fields = ['address', 'ls', 'fio']
    exclude = ('calculated_payment', 'last_payment', 'last_prepayment')
    inlines = [PaymentInlines]
    actions = [update_saldo_action, save_to_excel_action]


admin.site.register(UserModel, UserModelAdmin)
admin.site.register(PaymentModel, PaymentAdmin)