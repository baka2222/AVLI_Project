"""Наполнение базы тестовыми абонентами.

    python manage.py seed_subscribers            # 3600 записей
    python manage.py seed_subscribers 500        # другое количество
    python manage.py seed_subscribers --clear    # сначала удалить прежние тестовые

Данные детерминированы (фиксированный seed), поэтому повторный запуск даёт тот
же набор. Только для разработки и проверки печати.
"""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from users_app.models import UserModel


# Тестовые лицевые счета идут с этого номера — так их видно в списке и легко
# отличить от настоящих абонентов при удалении.
LS_START = 4_000_000

SURNAMES = [
    "Абдырахманов", "Оторбаев", "Джумагулов", "Кожомкулов", "Сатыбалдиев",
    "Мамбетов", "Асанов", "Токтогулов", "Бейшеналиев", "Иманалиев",
    "Иванов", "Петров", "Смирнов", "Кузнецов", "Соколов",
    "Ким", "Пак", "Цой", "Тен", "Хан",
    "Кожомкулова-Абдырахманова", "Оторбаева-Джумагулова",  # длинные, для проверки обрезки
]
NAMES_M = ["Нурбек", "Азамат", "Тилек", "Данияр", "Эркин", "Иван", "Пётр", "Сергей", "Алексей"]
NAMES_F = ["Гүлнара", "Айгүл", "Айнура", "Жылдыз", "Бегимай", "Татьяна", "Елена", "Ольга"]
PATRON_M = ["Асылбекович", "Кубанычбекович", "Мелисович", "Иванович", "Петрович", "Сергеевич"]
PATRON_F = ["Асылбековна", "Кубанычбековна", "Мелисовна", "Ивановна", "Петровна", "Сергеевна"]

STREETS = [
    "ул. Байтик Баатыра", "ул. Ахунбаева", "ул. Токтогула", "ул. Киевская",
    "ул. Абдрахманова", "пр. Чуй", "пр. Манаса", "ул. Медерова",
    "мкр. Джал-23", "мкр. Асанбай", "мкр. Восток-5", "мкр. Тунгуч",
]


def make_fio(rnd):
    surname = rnd.choice(SURNAMES)
    if rnd.random() < 0.5:
        return f"{surname}а {rnd.choice(NAMES_F)} {rnd.choice(PATRON_F)}"
    return f"{surname} {rnd.choice(NAMES_M)} {rnd.choice(PATRON_M)}"


def make_address(rnd):
    return (f"{rnd.choice(STREETS)}, дом {rnd.randint(1, 60)}"
            f"{rnd.choice(['', '', '', 'а', 'б', '/1', '/2'])}, кв. {rnd.randint(1, 220)}")


def close_period(last_dept, last_prepayment, rate_sum, paid):
    """Свести период так, чтобы соблюдалось тождество квитанции:

        остаток на конец = остаток на начало - начислено + оплачено

    Генерируем «правдоподобную историю» (что было на начало, сколько начислили,
    сколько заплатили) и выводим из неё сальдо — как это делает сама модель.
    bulk_create идёт в обход save(), поэтому производные поля считаем здесь.
    """
    opening = round(last_prepayment - last_dept, 2)
    saldo = round(opening - rate_sum + paid, 2)
    if saldo < 0:
        current_dept, current_prepayment = abs(saldo), 0.0
    else:
        current_dept, current_prepayment = 0.0, saldo
    return saldo, current_dept, current_prepayment


class Command(BaseCommand):
    help = "Создать тестовых абонентов для проверки печати квитанций"

    def add_arguments(self, parser):
        parser.add_argument("count", nargs="?", type=int, default=3600,
                            help="сколько записей создать (по умолчанию 3600)")
        parser.add_argument("--clear", action="store_true",
                            help=f"сначала удалить прежних тестовых (ЛС от {LS_START})")
        parser.add_argument("--seed", type=int, default=20260819,
                            help="seed генератора, для воспроизводимости")

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        rnd = random.Random(options["seed"])

        if options["clear"]:
            deleted, _ = UserModel.objects.filter(ls__gte=str(LS_START)).delete()
            self.stdout.write(f"Удалено прежних тестовых записей: {deleted}")

        existing = set(UserModel.objects.values_list("ls", flat=True))

        rows, ls_number = [], LS_START
        while len(rows) < count:
            ls = str(ls_number)
            ls_number += 1
            if ls in existing:
                continue

            area = round(rnd.uniform(18, 120), 1)
            rate = rnd.choice([24.0, 26.5, 28.0, 32.0])
            rate_sum = round(area * rate, 2)

            # Остаток на начало периода: чаще всего чисто, иногда долг или переплата.
            roll = rnd.random()
            if roll < 0.35:
                last_dept, last_prepayment = round(rnd.uniform(50, 4000), 2), 0.0
            elif roll < 0.45:
                last_dept, last_prepayment = 0.0, round(rnd.uniform(50, 1500), 2)
            else:
                last_dept, last_prepayment = 0.0, 0.0

            # Сколько заплатил за период: полностью, частично, ничего или с запасом.
            roll = rnd.random()
            due = max(0.0, round(last_dept + rate_sum - last_prepayment, 2))
            if roll < 0.45:
                paid = due                                   # рассчитался
            elif roll < 0.75:
                paid = round(due * rnd.uniform(0.1, 0.9), 2)  # частично
            elif roll < 0.90:
                paid = 0.0                                   # не платил
            else:
                paid = round(due + rnd.uniform(50, 2500), 2)  # с переплатой

            saldo, current_dept, current_prepayment = close_period(
                last_dept, last_prepayment, rate_sum, paid)

            rows.append(UserModel(
                ls=ls,
                fio=make_fio(rnd),
                area=area,
                rate=rate,
                rate_sum=rate_sum,
                period_charge=rate_sum,
                address=make_address(rnd),
                saldo=saldo,
                phone=f"+996{rnd.randint(500, 779)}{rnd.randint(100000, 999999)}",
                last_payment=paid,
                last_dept=last_dept,
                last_prepayment=last_prepayment,
                current_dept=current_dept,
                current_prepayment=current_prepayment,
            ))

        UserModel.objects.bulk_create(rows, batch_size=500)

        total = UserModel.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Создано {len(rows)} абонентов (ЛС {rows[0].ls}–{rows[-1].ls}). "
            f"Всего в базе: {total}."
        ))
