from django.db import models
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File
import barcode
from django.db import transaction
from datetime import datetime
import os

from .receipts import barcode_payload, digits


# Даты платежей приходят от четырёх банков в трёх разных форматах
# (см. scripts/read_file.py). Приводим к одному виду при сохранении, иначе
# список платежей невозможно нормально читать и сортировать.
PAYMENT_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y",
    "%Y-%m-%d",
)
PAYMENT_DATE_OUTPUT = "%Y-%m-%d %H:%M:%S"


def normalize_payment_date(value):
    """Привести дату платежа к единому виду. Неизвестный формат — оставить как есть."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):          # datetime / pandas.Timestamp
        return value.strftime(PAYMENT_DATE_OUTPUT)

    text = str(value).strip()
    for fmt in PAYMENT_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime(PAYMENT_DATE_OUTPUT)
        except ValueError:
            continue
    return text


class UserModel(models.Model):
    """Абонент.

    Единственный источник правды по деньгам — `saldo`: это личный остаток
    абонента, а не общий баланс компании. Отрицательный — должен, положительный —
    переплата. Поля `current_dept` / `current_prepayment` из него выводятся
    (см. `_sync_balance`), поэтому руками их менять не нужно и нельзя рассинхронить.

    Расчётный период закрывается методом `start_new_period()`.
    """

    ls = models.CharField(max_length=50, verbose_name='Лицевой счет', blank=False, null=False)
    fio = models.CharField(max_length=100, verbose_name='ФИО', blank=False, null=False)
    area = models.FloatField(verbose_name='Площадь (м2)')
    rate = models.FloatField(verbose_name='Тариф (сом / м2)')
    rate_sum = models.FloatField(verbose_name='Сумма по тарифу (текущая)', editable=False)
    period_charge = models.FloatField(
        verbose_name='Начислено за период',
        default=0,
        help_text='Снимок суммы, реально списанной при последнем начислении. '
                  'Именно она печатается в графе «Начислено».',
    )
    address = models.TextField(verbose_name='Адрес', max_length=200, blank=False, null=False)
    saldo = models.FloatField(
        verbose_name='Сальдо',
        default=0,
        help_text='Личный остаток абонента: минус — долг, плюс — переплата.',
    )
    phone = models.CharField(max_length=50, verbose_name='Телефон', null=True, blank=True)
    last_payment = models.FloatField(verbose_name='Оплачено за период', default=0)
    last_dept = models.FloatField(verbose_name='Долг на начало периода', default=0)
    last_prepayment = models.FloatField(verbose_name='Предоплата на начало периода', default=0)
    current_dept = models.FloatField(verbose_name='Долг на конец периода', default=0)
    current_prepayment = models.FloatField(verbose_name='Предоплата на конец периода', default=0)
    barcode = models.ImageField(upload_to='images/', blank=True, null=True)
    calculated_payment = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        if self.barcode:
            barcode_path = self.barcode.path
            if os.path.isfile(barcode_path):
                os.remove(barcode_path)
        super().delete(*args, **kwargs)

    def _sync_balance(self):
        """Вывести долг/предоплату из сальдо.

        Раньше это дублировалось в трёх местах (save платежа, действие админки),
        а при обычном создании абонента не выполнялось вовсе — из-за чего
        загруженный из DBF долг висел в `saldo`, но на квитанцию не попадал.
        """
        self.saldo = round(self.saldo or 0.0, 2)
        if self.saldo < 0:
            self.current_dept = abs(self.saldo)
            self.current_prepayment = 0.0
        else:
            self.current_dept = 0.0
            self.current_prepayment = self.saldo

    def save(self, *args, **kwargs):
        # Рассчитать сумму по тарифу
        self.rate_sum = round((self.area or 0.0) * (self.rate or 0.0), 2)

        self._sync_balance()

        # Генерация штрихкода
        if self.barcode:
            old_barcode_path = self.barcode.path  # Путь к старому файлу
            if os.path.exists(old_barcode_path):  # Проверяем, существует ли файл
                os.remove(old_barcode_path)

        # Значение штрихкода считает receipts.barcode_payload — общая точка
        # с печатью, чтобы код в базе и код на бумаге не разъехались.
        ls_numeric = digits(self.ls)
        barcode_value = barcode_payload(self.ls, self.current_dept)
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(barcode_value, writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)
        self.barcode.save(f'barcode_{ls_numeric}.png', File(buffer), save=False)

        super().save(*args, **kwargs)

    def register_payment(self, amount):
        """Учесть поступивший платёж.

        `last_payment` именно накапливается, а не выводится формулой: за месяц
        от четырёх банков платежей может прийти несколько, и в графе «Оплачено»
        обязана стоять их фактическая сумма.
        """
        self.saldo = round(self.saldo + amount, 2)
        self.last_payment = round(self.last_payment + amount, 2)
        self.save()

    def cancel_payment(self, amount):
        """Откатить платёж (удаление ошибочно загруженной строки)."""
        self.saldo = round(self.saldo - amount, 2)
        self.last_payment = round(self.last_payment - amount, 2)
        self.save()

    def start_new_period(self):
        """Закрыть текущий расчётный период и начислить за новый.

        Порядок важен: сначала снимок остатка на начало нового периода
        (`last_*`), затем обнуление счётчика оплат, и только потом начисление.
        Соблюдается тождество квитанции:
            остаток на конец = остаток на начало - начислено + оплачено
        """
        self.last_dept = self.current_dept
        self.last_prepayment = self.current_prepayment
        self.last_payment = 0.0
        # Фиксируем начисленное отдельным полем: `rate_sum` пересчитывается при
        # каждом сохранении, и правка площади/тарифа в середине месяца иначе
        # поменяла бы графу «Начислено» на квитанции, не тронув сальдо.
        self.period_charge = self.rate_sum
        self.saldo = round(self.saldo - self.period_charge, 2)
        self.save()

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

    def _require_user(self):
        try:
            user = self.user
        except UserModel.DoesNotExist:
            user = None
        if user is None:
            raise ValueError("Поле 'user' должно быть заполнено.")
        if user.pk is None:
            raise ValueError(f"Абонент с лицевым счётом {user.ls} не найден.")
        return user

    def save(self, *args, **kwargs):
        user = self._require_user()
        # Сальдо двигаем только при создании: повторное сохранение той же
        # записи не должно начислять сумму второй раз.
        creating = self._state.adding

        with transaction.atomic():
            self.payment = round(self.payment, 2)
            self.date = normalize_payment_date(self.date)
            if not self.ls:
                self.ls = user.ls
            if creating:
                user.register_payment(self.payment)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            try:
                self.user.cancel_payment(self.payment)
            except UserModel.DoesNotExist:
                pass
            super().delete(*args, **kwargs)

    def __str__(self):
        return f'LS: {self.ls} | {self.date} | {self.payment} сом'

    class Meta:
        verbose_name = 'Платежи'
        verbose_name_plural = 'Платежи'
