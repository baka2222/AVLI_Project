from django.db import models
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File
import barcode
from django.db import transaction
from datetime import datetime
import os
import re

from .addresses import format_address
from .receipts import MONTHS, barcode_payload, digits


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


# Вид коммунальной услуги в отчётности: компания обслуживает жилые дома,
# услуга одна — техническое обслуживание.
DEFAULT_SERVICE_TYPE = "ТО"


class House(models.Model):
    """Дом — справочник.

    Раньше дом жил внутри строки адреса абонента, и одна улица разъезжалась на
    несколько написаний («ул Байтик-Батыра 6» и «ул Байтик-Баатыра дом 9»).
    Свод по домам из такого адреса собрать было нельзя. Теперь дом — отдельная
    запись: фильтр в админке становится выпадающим списком, а группировка
    отчёта — точной.
    """

    street = models.CharField(max_length=120, verbose_name='Улица / микрорайон')
    number = models.CharField(max_length=20, verbose_name='Номер дома')
    # Сортировка по строке ставит «дом 10» перед «дом 9». Отдельное числовое
    # поле держит дома в том порядке, в котором их читает человек.
    number_order = models.PositiveIntegerField(default=0, editable=False)
    service_type = models.CharField(
        max_length=20, default=DEFAULT_SERVICE_TYPE, verbose_name='Вид ком. услуг',
        help_text='Печатается в последней графе свода.',
    )

    @property
    def title(self):
        if self.street and self.number:
            return f'{self.street} дом {self.number}'
        return self.street or self.number

    def save(self, *args, **kwargs):
        self.street = (self.street or '').strip()
        self.number = (self.number or '').strip()
        leading = re.match(r'\d+', self.number)
        self.number_order = int(leading.group()) if leading else 0
        super().save(*args, **kwargs)
        # Адрес абонента — производное поле, и переименование дома в справочнике
        # обязано доехать до квитанций. bulk_update, а не save(): полное
        # сохранение абонента перерисовывает штрихкод, а он тут ни при чём.
        self.refresh_subscriber_addresses()

    def refresh_subscriber_addresses(self):
        subscribers = list(self.subscribers.all())
        for subscriber in subscribers:
            subscriber.address = format_address(self, subscriber.apartment)
        if subscribers:
            UserModel.objects.bulk_update(subscribers, ['address'])
        return len(subscribers)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Дом'
        verbose_name_plural = 'Дома'
        ordering = ('street', 'number_order', 'number')
        constraints = [
            models.UniqueConstraint(fields=('street', 'number'), name='unique_house'),
        ]


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
    house = models.ForeignKey(
        House, on_delete=models.PROTECT, related_name='subscribers',
        null=True, blank=True, verbose_name='Дом',
    )
    apartment = models.CharField(max_length=20, blank=True, default='', verbose_name='Квартира')
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

        # Когда дом выбран, адрес собирается из справочника: две записи одного
        # дома с разным написанием улицы сломали бы свод по домам.
        self.apartment = (self.apartment or '').strip()
        if self.house_id:
            self.address = format_address(self.house, self.apartment)

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


# Графа «3%» в отчётности бухгалтерии. На сальдо абонента не влияет: это
# отдельная колонка свода, которую бухгалтер при необходимости правит руками.
FEE_RATE = 0.03

MONTH_CHOICES = tuple(sorted(MONTHS.items()))


class PeriodSnapshot(models.Model):
    """Архив: расчёты одного абонента за один закрытый месяц.

    Запись создаётся в момент закрытия периода — до того, как
    `UserModel.start_new_period()` перезапишет графы. Поэтому здесь лежит ровно
    то, что было напечатано в квитанции за этот месяц.

    ФИО, адрес, площадь и тариф хранятся копией, а не только ссылкой на
    абонента: через год жилец может переехать, тариф — измениться, а архив
    обязан показывать прошлое, а не сегодняшнее состояние. По той же причине
    `subscriber` удаляется в NULL, а не каскадом — удаление абонента не должно
    стирать историю, по которой бухгалтерия отчитывалась.

    Своды по домам и общий итог считаются из этих строк агрегацией (см.
    `reports.py`). Отдельной таблицы с итогами по домам нет намеренно: тогда
    итог и расшифровка по жильцам не могут разойтись между собой.

    Тождество, которое обязано соблюдаться в каждой строке:
        (кредит - дебет) на конец = (кредит - дебет) на начало
                                    - начислено КУ + оплачено КУ + возврат
    Графы «3%», «Перевод» и «Пеня» в него не входят: они справочные и сальдо
    абонента не двигают.
    """

    year = models.PositiveSmallIntegerField(verbose_name='Год')
    month = models.PositiveSmallIntegerField(verbose_name='Месяц', choices=MONTH_CHOICES)

    subscriber = models.ForeignKey(
        UserModel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='snapshots', verbose_name='Абонент',
    )
    house = models.ForeignKey(
        House, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='snapshots', verbose_name='Дом',
    )

    ls = models.CharField(max_length=50, verbose_name='Лицевой счет')
    fio = models.CharField(max_length=100, verbose_name='ФИО')
    address = models.CharField(max_length=200, verbose_name='Адрес')
    apartment = models.CharField(max_length=20, blank=True, default='', verbose_name='Квартира')
    area = models.FloatField(default=0, verbose_name='Площадь (м2)')
    rate = models.FloatField(default=0, verbose_name='Тариф (сом / м2)')

    opening_debit = models.FloatField(default=0, verbose_name='Сальдо нач. месяца, дебет')
    opening_credit = models.FloatField(default=0, verbose_name='Сальдо нач. месяца, кредит')

    charged_ku = models.FloatField(default=0, verbose_name='Начислено, КУ')
    charged_fee = models.FloatField(default=0, verbose_name='Начислено, 3%')

    paid_ku = models.FloatField(default=0, verbose_name='Оплачено, КУ')
    paid_fee = models.FloatField(default=0, verbose_name='Оплачено, 3%')

    transfer = models.FloatField(default=0, verbose_name='Перевод')
    penalty = models.FloatField(default=0, verbose_name='Пеня')
    refund = models.FloatField(default=0, verbose_name='Возврат')

    closing_debit = models.FloatField(default=0, verbose_name='Сальдо кон. месяца, дебет')
    closing_credit = models.FloatField(default=0, verbose_name='Сальдо кон. месяца, кредит')
    overdue = models.FloatField(default=0, verbose_name='Просроченная задолженность')

    service_type = models.CharField(
        max_length=20, default=DEFAULT_SERVICE_TYPE, verbose_name='Вид ком. услуг')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Записано в архив')

    @staticmethod
    def overdue_for(closing_debit, charged_ku):
        """Просроченная задолженность = долг сверх начисления закрытого месяца.

        Считается по каждому абоненту, а не вычитанием из общего итога: у тех,
        кто заплатил больше начисленного, просрочки нет, и минус по ним не
        должен уменьшать общую сумму долга по компании.
        """
        return round(max(0.0, (closing_debit or 0.0) - (charged_ku or 0.0)), 2)

    @classmethod
    def capture(cls, user, year, month):
        """Снимок по текущему — ещё не закрытому — состоянию абонента.

        Вызывать строго до `start_new_period()`: после него графы уже описывают
        новый месяц.
        """
        charged_ku = round(user.period_charge or 0.0, 2)
        paid_ku = round(user.last_payment or 0.0, 2)
        closing_debit = round(user.current_dept or 0.0, 2)

        return cls(
            year=year,
            month=month,
            subscriber=user,
            house=user.house,
            ls=user.ls,
            fio=user.fio,
            address=user.address,
            apartment=user.apartment,
            area=user.area or 0.0,
            rate=user.rate or 0.0,
            opening_debit=round(user.last_dept or 0.0, 2),
            opening_credit=round(user.last_prepayment or 0.0, 2),
            charged_ku=charged_ku,
            # «3%» — по умолчанию доля от КУ; бухгалтер правит руками в архиве.
            charged_fee=round(charged_ku * FEE_RATE, 2),
            paid_ku=paid_ku,
            paid_fee=round(paid_ku * FEE_RATE, 2),
            closing_debit=closing_debit,
            closing_credit=round(user.current_prepayment or 0.0, 2),
            overdue=cls.overdue_for(closing_debit, charged_ku),
            service_type=user.house.service_type if user.house_id else DEFAULT_SERVICE_TYPE,
        )

    def save(self, *args, **kwargs):
        # Просрочка выводится из уже записанных граф, а не хранится сама по
        # себе: иначе правка архива оставила бы её от прежних цифр.
        self.overdue = self.overdue_for(self.closing_debit, self.charged_ku)
        super().save(*args, **kwargs)

    @property
    def period_label(self):
        return f'{MONTHS.get(self.month, self.month)} {self.year} г.'

    def __str__(self):
        return f'{self.ls} — {self.period_label}'

    class Meta:
        verbose_name = 'Архив начислений'
        verbose_name_plural = 'Архив начислений'
        ordering = ('-year', '-month', 'address', 'ls')
        indexes = [
            models.Index(fields=('year', 'month')),
            models.Index(fields=('year', 'month', 'house')),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('subscriber', 'year', 'month'), name='unique_snapshot_per_period',
            ),
        ]


# ----------------------------- контент публичного сайта -----------------------------


class SiteSettings(models.Model):
    """Единая карточка компании и SEO-настройки публичного сайта."""

    company_name = models.CharField(max_length=120, default='ОсОО «АВЛИ»', verbose_name='Название компании')
    short_name = models.CharField(max_length=40, default='АВЛИ', verbose_name='Короткое название')
    tagline = models.CharField(
        max_length=180,
        default='Надёжное управление многоквартирными домами в Бишкеке',
        verbose_name='Слоган',
    )
    about_title = models.CharField(
        max_length=180, default='Надёжный партнёр вашего дома', verbose_name='Заголовок блока «О нас»')
    about_text = models.TextField(verbose_name='Текст о компании')
    about_text_secondary = models.TextField(blank=True, verbose_name='Дополнительный текст о компании')
    mission = models.TextField(blank=True, verbose_name='Миссия')
    footer_text = models.TextField(blank=True, verbose_name='Текст в подвале')

    address = models.CharField(max_length=240, verbose_name='Адрес')
    phone_primary = models.CharField(max_length=40, verbose_name='Основной телефон')
    phone_secondary = models.CharField(max_length=40, blank=True, verbose_name='Дополнительный телефон')
    email = models.EmailField(verbose_name='Электронная почта')
    whatsapp_number = models.CharField(
        max_length=30, blank=True, verbose_name='WhatsApp',
        help_text='Только цифры с кодом страны, например 996225215740.',
    )
    telegram_url = models.URLField(blank=True, verbose_name='Ссылка на Telegram')
    map_embed_url = models.URLField(blank=True, max_length=1000, verbose_name='Ссылка на карту (embed)')

    seo_title = models.CharField(max_length=180, verbose_name='SEO-заголовок')
    seo_description = models.CharField(max_length=320, verbose_name='SEO-описание')
    og_image = models.ImageField(upload_to='site/', blank=True, verbose_name='Изображение для соцсетей')
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Карточка настроек должна быть одна. Фиксированный PK упрощает чтение
        # из API и не даёт случайно завести противоречащие друг другу контакты.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return None

    def __str__(self):
        return self.company_name

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'


class OrderedPublishedModel(models.Model):
    """Общие служебные поля для сортируемого контента сайта."""

    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Опубликовано')

    class Meta:
        abstract = True


class HeroSlide(OrderedPublishedModel):
    eyebrow = models.CharField(max_length=80, default='Приветствуем!', verbose_name='Надзаголовок')
    title = models.CharField(max_length=180, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')
    button_text = models.CharField(max_length=80, default='Заказать звонок', verbose_name='Текст кнопки')
    image = models.ImageField(upload_to='site/hero/', blank=True, verbose_name='Изображение')
    image_path = models.CharField(
        max_length=500, blank=True, verbose_name='Резервный путь изображения',
        help_text='Используется, если файл не загружен. Допустим путь вида /images/hero/slide.jpg.',
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Слайд первого экрана'
        verbose_name_plural = 'Слайды первого экрана'
        ordering = ('sort_order', 'pk')


class SiteFeature(OrderedPublishedModel):
    ICON_CHOICES = (
        ('shield-check', 'Щит'),
        ('file-chart', 'Отчётность'),
        ('house-heart', 'Дом и комфорт'),
        ('hard-hat', 'Подрядчики'),
    )

    title = models.CharField(max_length=140, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')
    icon = models.CharField(max_length=32, choices=ICON_CHOICES, default='shield-check', verbose_name='Иконка')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Преимущество'
        verbose_name_plural = 'Преимущества'
        ordering = ('sort_order', 'pk')


class SiteMetric(OrderedPublishedModel):
    ICON_CHOICES = (
        ('building', 'Дом'),
        ('users', 'Жители'),
        ('headphones', 'Поддержка'),
        ('smile', 'Улыбка'),
    )

    value = models.CharField(max_length=30, verbose_name='Значение')
    label = models.CharField(max_length=120, verbose_name='Подпись')
    icon = models.CharField(max_length=32, choices=ICON_CHOICES, default='building', verbose_name='Иконка')

    def __str__(self):
        return f'{self.value} — {self.label}'

    class Meta:
        verbose_name = 'Показатель компании'
        verbose_name_plural = 'Показатели компании'
        ordering = ('sort_order', 'pk')


class Service(OrderedPublishedModel):
    CATEGORY_CHOICES = (
        ('paid', 'Платная услуга'),
        ('included', 'Входит в обслуживание'),
    )

    slug = models.SlugField(max_length=180, unique=True, verbose_name='URL-имя')
    title = models.CharField(max_length=220, verbose_name='Название')
    short_description = models.TextField(verbose_name='Краткое описание')
    description = models.TextField(verbose_name='Полное описание')
    price_label = models.CharField(max_length=80, default='По запросу', verbose_name='Цена')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='paid', verbose_name='Категория')
    image = models.ImageField(upload_to='services/', blank=True, verbose_name='Изображение')
    image_path = models.CharField(
        max_length=500, blank=True, verbose_name='Резервный путь изображения',
        help_text='Используется, если файл не загружен.',
    )
    is_featured = models.BooleanField(default=False, verbose_name='Показывать на главной')
    legacy_path = models.CharField(
        max_length=320, blank=True, verbose_name='Старый URL',
        help_text='Нужен для постоянного редиректа со старой версии сайта.',
    )
    meta_title = models.CharField(max_length=180, blank=True, verbose_name='SEO-заголовок')
    meta_description = models.CharField(max_length=320, blank=True, verbose_name='SEO-описание')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Услуга сайта'
        verbose_name_plural = 'Услуги сайта'
        ordering = ('sort_order', 'title')


class Testimonial(OrderedPublishedModel):
    name = models.CharField(max_length=140, verbose_name='Имя')
    role = models.CharField(max_length=80, default='Житель', verbose_name='Подпись')
    text = models.TextField(verbose_name='Отзыв')
    initials = models.CharField(max_length=8, blank=True, verbose_name='Инициалы')

    def save(self, *args, **kwargs):
        if not self.initials:
            self.initials = ''.join(part[0] for part in self.name.split()[:2]).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('sort_order', 'pk')


class FrequentlyAskedQuestion(OrderedPublishedModel):
    question = models.CharField(max_length=260, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = 'Вопрос и ответ'
        verbose_name_plural = 'Вопросы и ответы'
        ordering = ('sort_order', 'pk')


class CallbackRequest(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('done', 'Обработана'),
        ('spam', 'Спам'),
    )

    name = models.CharField(max_length=120, blank=True, verbose_name='Имя')
    phone = models.CharField(max_length=40, verbose_name='Телефон')
    message = models.TextField(blank=True, verbose_name='Комментарий')
    page = models.CharField(max_length=320, blank=True, verbose_name='Страница заявки')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Получена')

    def __str__(self):
        return f'{self.phone} — {self.created_at:%d.%m.%Y %H:%M}'

    class Meta:
        verbose_name = 'Заявка с сайта'
        verbose_name_plural = 'Заявки с сайта'
        ordering = ('-created_at',)
        indexes = [models.Index(fields=('status', '-created_at'))]
