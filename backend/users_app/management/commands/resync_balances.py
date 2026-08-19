"""Пересчёт долга/предоплаты из сальдо для уже существующих абонентов.

    python manage.py resync_balances --dry-run    # показать, что изменится
    python manage.py resync_balances              # применить
    python manage.py resync_balances --reset-period   # + починить строки, где графы не сходятся

Зачем: записи, заведённые прежней версией кода, могли получить одновременно
ненулевой долг И ненулевую предоплату — состояние, которого не бывает. Теперь
`current_dept` / `current_prepayment` выводятся из `saldo` в `UserModel.save()`,
но старые строки не пересчитаются сами, пока их кто-нибудь не сохранит.

Тождество квитанции (остаток на конец = остаток на начало - начислено + оплачено)
для старых строк восстановить по-настоящему нельзя: истории платежей за прошлый
период нет. `--reset-period` делает переходную квитанцию хотя бы внутренне
непротиворечивой: остаток на начало = остаток на конец, начислено 0, оплачено 0.
После первого начисления («Шаг 3» в админке) всё идёт обычным порядком.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from users_app.models import UserModel


BATCH = 500


class Command(BaseCommand):
    help = "Привести долг/предоплату абонентов в соответствие с сальдо"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="только показать расхождения, ничего не менять")
        parser.add_argument("--reset-period", action="store_true",
                            help="дополнительно свести графы периода у строк, "
                                 "где тождество квитанции нарушено")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reset_period = options["reset_period"]

        fields = ["current_dept", "current_prepayment"]
        if reset_period:
            fields += ["last_dept", "last_prepayment", "last_payment", "period_charge"]

        changed, examples, pending = 0, [], []

        # bulk_update в обход save(): нам нужны только два числовых поля, а save()
        # на каждой записи перерисовывает PNG-штрихкод — на 3600 абонентов это минуты.
        for user in UserModel.objects.all().iterator(chunk_size=BATCH):
            saldo = round(user.saldo or 0.0, 2)
            new_dept = abs(saldo) if saldo < 0 else 0.0
            new_prepayment = 0.0 if saldo < 0 else saldo

            differs = (abs(user.current_dept - new_dept) > 0.011
                       or abs(user.current_prepayment - new_prepayment) > 0.011)

            # Сброс периода применяем только там, где тождество квитанции
            # действительно нарушено: у строк с нормальной историей затирать
            # графы «на начало» и «оплачено» нельзя.
            broken_identity = False
            if reset_period:
                opening = round(user.last_prepayment - user.last_dept, 2)
                closing = round(new_prepayment - new_dept, 2)
                expected = round(opening - user.period_charge + user.last_payment, 2)
                broken_identity = abs(closing - expected) > 0.011

            if not differs and not broken_identity:
                continue

            if len(examples) < 10:
                note = " + сброс периода (графы не сходились)" if broken_identity else ""
                examples.append(
                    f"  ЛС {user.ls}: сальдо {saldo} | "
                    f"долг {user.current_dept} -> {new_dept}, "
                    f"предоплата {user.current_prepayment} -> {new_prepayment}{note}"
                )

            user.current_dept = new_dept
            user.current_prepayment = new_prepayment
            if broken_identity:
                # Зеркалим остаток, а не обнуляем: «ничего не начислено, ничего
                # не оплачено, остаток каким был — таким и остался». Тогда графы
                # переходной квитанции сходятся между собой.
                user.last_dept = new_dept
                user.last_prepayment = new_prepayment
                user.last_payment = 0.0
                user.period_charge = 0.0

            changed += 1
            pending.append(user)

            if not dry_run and len(pending) >= BATCH:
                UserModel.objects.bulk_update(pending, fields)
                pending.clear()

        if not dry_run and pending:
            with transaction.atomic():
                UserModel.objects.bulk_update(pending, fields)

        total = UserModel.objects.count()
        for line in examples:
            self.stdout.write(line)
        if changed > len(examples):
            self.stdout.write(f"  …и ещё {changed - len(examples)}")

        verb = "Требуют пересчёта" if dry_run else "Пересчитано"
        style = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(style(
            f"{verb}: {changed} из {total} абонентов."
            + (" Запустите без --dry-run, чтобы применить." if dry_run and changed else "")
        ))
