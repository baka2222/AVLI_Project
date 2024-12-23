from django.contrib import admin
from .models import (UserModel)

class UserModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rate_sum',)
    search_fields = ['address', 'ls', 'fio']

admin.site.register(UserModel, UserModelAdmin)