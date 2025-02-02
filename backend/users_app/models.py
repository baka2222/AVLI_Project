from django.db import models
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File
import barcode
from django.db import transaction
import os


class UserModel(models.Model):
    ls = models.CharField(max_length=50, verbose_name='Лицевой счет', blank=False, null=False)
    fio = models.CharField(max_length=100, verbose_name='ФИО', blank=False, null=False)
    area = models.FloatField(verbose_name='Площадь (м2)')
    rate = models.FloatField(verbose_name='Тариф (сом / м2)')
    rate_sum = models.FloatField(verbose_name='Сумма по тарифу', editable=False)
    address = models.TextField(verbose_name='Адрес', max_length=200, blank=False, null=False)
    saldo = models.FloatField(verbose_name='Сальдо', default=0)
    phone = models.CharField(max_length=50, verbose_name='Телефон', null=True, blank=True)
    last_payment = models.FloatField(verbose_name='Последняя оплата', default=0)
    last_dept = models.FloatField(verbose_name='Долг за предыдущий месяц', default=0)
    last_prepayment = models.FloatField(verbose_name='Предоплата за предыдущий месяц', default=0)
    current_dept = models.FloatField(verbose_name='Долг за текущий месяц', default=0)
    current_prepayment = models.FloatField(verbose_name='Предоплата за текущий месяц', default=0)
    barcode = models.ImageField(upload_to='images/', blank=True, null=True) 
    calculated_payment = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        if self.barcode: 
            barcode_path = self.barcode.path
            if os.path.isfile(barcode_path): 
                os.remove(barcode_path)  
        super().delete(*args, **kwargs) 

    def save(self, *args, **kwargs):
        # Рассчитать сумму по тарифу
        self.rate_sum = round(self.area * self.rate, 1)

        if self.current_prepayment or (not self.current_dept and not self.current_prepayment):
            self.last_payment = self.rate_sum + self.last_dept
        elif self.current_dept:
            self.last_payment = self.rate_sum + self.last_dept - self.current_dept
        else:
            self.last_payment = 0.0

        # Генерация штрихкода
        if self.barcode:
            old_barcode_path = self.barcode.path  # Путь к старому файлу
            if os.path.exists(old_barcode_path):  # Проверяем, существует ли файл
                os.remove(old_barcode_path)

        ls_numeric = ''.join(filter(str.isdigit, self.ls))
        barcode_value = f"12{ls_numeric}{int(abs(self.current_dept) * 10):06}00"
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(barcode_value, writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)
        self.barcode.save(f'barcode_{ls_numeric}.png', File(buffer), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f'Лицевой счет: {self.ls}'
    
    class Meta:
        verbose_name = 'Абоненты'
        verbose_name_plural = 'Абоненты'


class PaymentModel(models.Model):
    date = models.CharField(max_length=50, verbose_name='Дата платежа')
    payment = models.FloatField(verbose_name='Сумма платежа')
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='payments')
    ls = models.CharField(max_length=50, verbose_name='Лицевой счет', default='')

    def save(self, *args, **kwargs):
        with transaction.atomic():
            obj = self.user
            self.payment = round(self.payment, 1)
            obj.saldo += self.payment
            obj.last_dept = obj.current_dept
            if obj.saldo < 0:
                obj.current_dept = abs(obj.saldo)
                obj.current_prepayment = 0.0
            elif obj.saldo > 0:
                obj.current_dept = 0.0
                obj.current_prepayment = obj.saldo
            else:
                obj.current_dept = 0.0
                obj.current_prepayment = 0.0
        
            obj.save()
            super().save(*args, **kwargs)

    def __str__(self):
        return f'LS: {self.ls} | {self.date} | {self.payment} сом'
    
    class Meta:
        verbose_name = 'Платежи'
        verbose_name_plural = 'Платежи'
    