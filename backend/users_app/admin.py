from django.contrib import admin
from .models import (UserModel, PaymentModel)


@admin.action(description="Обновить сальдо для выбранных объектов")
def update_saldo_action(modeladmin, request, queryset):
    for user in queryset:
        user.saldo -= user.rate_sum
        user.save()
    modeladmin.message_user(request, "Сальдо успешно обновлено для выбранных абонентов!")


class PaymentInlines(admin.TabularInline):
    model = PaymentModel
    extra = 0


class UserModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rate_sum',)
    search_fields = ['address', 'ls', 'fio']
    inlines = [PaymentInlines]
    actions = [update_saldo_action]


admin.site.register(UserModel, UserModelAdmin)
admin.site.register(PaymentModel)