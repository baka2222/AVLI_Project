from django.db import models


class UserModel(models.Model):
    ls = models.CharField(max_length=50,
                          verbose_name='Лицевой счет',
                          blank=False,
                          null=False)
    fio = models.CharField(max_length=100,
                           verbose_name='ФИО',
                           blank=False,
                           null=False)
    area = models.FloatField(verbose_name='Площадь (м2)')
    rate = models.FloatField(verbose_name='Тариф (сом / м2)')
    rate_sum = models.FloatField(verbose_name='Сумма по тарифу',
                                 editable=False)
    address = models.TextField(verbose_name='Адрес',
                               max_length=200,
                               blank=False,
                               null=False)
    saldo = models.FloatField(verbose_name='Сальдо')

    def save(self, *args, **kwargs):
        self.rate_sum = self.area * self.rate
        super().save(*args, **kwargs) 

    def __str__(self):
        return f'Лицевой счет: {self.ls}'
    
    class Meta:
        verbose_name = 'Абоненты'
        verbose_name_plural = 'Абоненты'
