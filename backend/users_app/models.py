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
    phone = models.CharField(max_length=50,
                             verbose_name='Телефон',
                             null=True,
                             blank=True)

    def save(self, *args, **kwargs):
        self.rate_sum = self.area * self.rate
        super().save(*args, **kwargs) 

    def __str__(self):
        return f'Лицевой счет: {self.ls}'
    
    class Meta:
        verbose_name = 'Абоненты'
        verbose_name_plural = 'Абоненты'


class PaymentModel(models.Model):
    date = models.CharField(max_length=50,
                            verbose_name='Дата платежа')
    payment = models.FloatField(verbose_name='Сумма платежа')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             related_name='user')
    
    def __str__(self):
        return f'{self.user.ls}'
    
    def save(self, *args, **kwargs):
        obj = UserModel.objects.get(ls=f'{self.user.ls}')
        obj.saldo = float(obj.saldo) + float(self.payment)
        obj.save()
        super().save(*args, **kwargs) 

    class Meta:
        verbose_name = 'Платежи'
        verbose_name_plural = 'Платежи'