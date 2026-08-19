"""Тесты расчётов, попадающих на печатную квитанцию.

Главный критерий — тождество квитанции:
    остаток на конец = остаток на начало - начислено + оплачено
где остаток = предоплата - долг. Если оно нарушено, жильцу уходит документ,
в котором цифры не сходятся между собой.
"""

from django.test import TestCase

from users_app.models import UserModel, PaymentModel, normalize_payment_date


def balance(dept, prepayment):
    """Остаток в виде одного числа: минус — долг, плюс — переплата."""
    return round(prepayment - dept, 2)


class ReceiptIdentityMixin:
    def assertReceiptBalances(self, user, msg=""):
        """Проверить тождество на текущем состоянии абонента."""
        opening = balance(user.last_dept, user.last_prepayment)
        closing = balance(user.current_dept, user.current_prepayment)
        expected = round(opening - user.period_charge + user.last_payment, 2)
        self.assertAlmostEqual(
            closing, expected, places=2,
            msg=(f"{msg}: тождество квитанции нарушено. "
                 f"на начало={opening}, начислено={user.period_charge}, "
                 f"оплачено={user.last_payment}, на конец={closing}, ожидалось={expected}")
        )


class BalanceDerivationTest(TestCase):
    """current_dept / current_prepayment должны выводиться из сальдо всегда."""

    def test_negative_saldo_becomes_debt_on_create(self):
        # Так грузятся абоненты из DBF (scripts/read_db.py): saldo=-BALANCE.
        user = UserModel.objects.create(
            ls="1510000-0", fio="Долг при загрузке", area=0, rate=0,
            address="—", saldo=-4076.6,
        )
        self.assertEqual(user.current_dept, 4076.6)
        self.assertEqual(user.current_prepayment, 0.0)

    def test_positive_saldo_becomes_prepayment(self):
        user = UserModel.objects.create(
            ls="1510001-8", fio="Переплата", area=0, rate=0, address="—", saldo=1500.0,
        )
        self.assertEqual(user.current_dept, 0.0)
        self.assertEqual(user.current_prepayment, 1500.0)

    def test_zero_saldo(self):
        user = UserModel.objects.create(
            ls="1510002-6", fio="Ноль", area=0, rate=0, address="—", saldo=0,
        )
        self.assertEqual(user.current_dept, 0.0)
        self.assertEqual(user.current_prepayment, 0.0)

    def test_editing_saldo_resyncs(self):
        user = UserModel.objects.create(
            ls="1510003-4", fio="Правка", area=0, rate=0, address="—", saldo=-100.0,
        )
        user.saldo = 250.0
        user.save()
        self.assertEqual(user.current_dept, 0.0)
        self.assertEqual(user.current_prepayment, 250.0)


class PaymentAccountingTest(ReceiptIdentityMixin, TestCase):

    def setUp(self):
        self.user = UserModel.objects.create(
            ls="1520000-1", fio="Иванов Иван", area=24.0, rate=24.0,
            address="Токтогула 1-1", saldo=0,
        )
        self.assertEqual(self.user.rate_sum, 576.0)
        self.user.start_new_period()          # начисление за расчётный месяц

    def pay(self, amount):
        PaymentModel.objects.create(date="2026-08-05", payment=amount,
                                    user=self.user, ls=self.user.ls)
        self.user.refresh_from_db()

    def test_single_payment(self):
        self.pay(300.0)
        self.assertEqual(self.user.last_payment, 300.0)
        self.assertEqual(self.user.current_dept, 276.0)
        self.assertReceiptBalances(self.user, "один платёж")

    def test_two_payments_in_same_period_sum_up(self):
        """Главный дефект прежней версии: второй платёж ломал графу «Оплачено»."""
        self.pay(300.0)
        self.pay(200.0)
        self.assertEqual(self.user.last_payment, 500.0)     # 300 + 200, а не формула
        self.assertEqual(self.user.last_dept, 0.0)          # снимок не переписан платежом
        self.assertEqual(self.user.current_dept, 76.0)      # 576 - 500
        self.assertReceiptBalances(self.user, "два платежа")

    def test_many_small_payments(self):
        for _ in range(12):
            self.pay(48.0)
        self.assertEqual(self.user.last_payment, 576.0)
        self.assertEqual(self.user.current_dept, 0.0)
        self.assertEqual(self.user.current_prepayment, 0.0)
        self.assertReceiptBalances(self.user, "12 платежей")

    def test_overpayment_becomes_prepayment(self):
        self.pay(1000.0)
        self.assertEqual(self.user.current_dept, 0.0)
        self.assertEqual(self.user.current_prepayment, 424.0)
        self.assertReceiptBalances(self.user, "переплата")

    def test_payment_without_prior_accrual(self):
        """Платёж на чистое сальдо: «Оплачено» = внесённая сумма, не тариф."""
        fresh = UserModel.objects.create(
            ls="1520001-9", fio="Без начисления", area=24.0, rate=24.0,
            address="—", saldo=0,
        )
        PaymentModel.objects.create(date="2026-08-05", payment=500.0, user=fresh, ls=fresh.ls)
        fresh.refresh_from_db()
        self.assertEqual(fresh.last_payment, 500.0)
        self.assertEqual(fresh.current_prepayment, 500.0)

    def test_resaving_payment_does_not_double_count(self):
        self.pay(300.0)
        payment = PaymentModel.objects.get(user=self.user)
        payment.save()                       # повторное сохранение
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_payment, 300.0)
        self.assertEqual(self.user.saldo, -276.0)

    def test_deleting_payment_rolls_back(self):
        self.pay(300.0)
        PaymentModel.objects.get(user=self.user).delete()
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_payment, 0.0)
        self.assertEqual(self.user.saldo, -576.0)
        self.assertEqual(self.user.current_dept, 576.0)

    def test_payment_date_is_normalized(self):
        PaymentModel.objects.create(date="27.12.2024 10:26:18", payment=100.0,
                                    user=self.user, ls=self.user.ls)
        self.assertEqual(PaymentModel.objects.latest("id").date, "2024-12-27 10:26:18")

    def test_ls_filled_from_user(self):
        PaymentModel.objects.create(date="2026-08-05", payment=100.0, user=self.user)
        self.assertEqual(PaymentModel.objects.latest("id").ls, self.user.ls)


class PeriodRolloverTest(ReceiptIdentityMixin, TestCase):

    def setUp(self):
        self.user = UserModel.objects.create(
            ls="1530000-2", fio="Петров Пётр", area=50.0, rate=24.0,
            address="Киевская 5-9", saldo=0,
        )   # rate_sum = 1200.0

    def test_three_months_running(self):
        """Три месяца подряд: тождество должно держаться в каждом."""
        # --- месяц 1: начислили 1200, оплатили 1200 ---
        self.user.start_new_period()
        self.assertEqual(self.user.last_dept, 0.0)
        self.assertEqual(self.user.current_dept, 1200.0)
        PaymentModel.objects.create(date="2026-06-10", payment=1200.0,
                                    user=self.user, ls=self.user.ls)
        self.user.refresh_from_db()
        self.assertReceiptBalances(self.user, "месяц 1")
        self.assertEqual(self.user.current_dept, 0.0)

        # --- месяц 2: начислили 1200, оплатили 700 двумя платежами ---
        self.user.start_new_period()
        self.assertEqual(self.user.last_payment, 0.0)   # счётчик обнулён
        for amount in (400.0, 300.0):
            PaymentModel.objects.create(date="2026-07-10", payment=amount,
                                        user=self.user, ls=self.user.ls)
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_payment, 700.0)
        self.assertEqual(self.user.current_dept, 500.0)
        self.assertReceiptBalances(self.user, "месяц 2")

        # --- месяц 3: долг 500 переносится на начало периода ---
        self.user.start_new_period()
        self.assertEqual(self.user.last_dept, 500.0)    # долг прошлого месяца
        self.assertEqual(self.user.last_payment, 0.0)
        self.assertEqual(self.user.current_dept, 1700.0)  # 500 + 1200
        self.assertReceiptBalances(self.user, "месяц 3 (без оплат)")

        PaymentModel.objects.create(date="2026-08-10", payment=2000.0,
                                    user=self.user, ls=self.user.ls)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_prepayment, 300.0)
        self.assertReceiptBalances(self.user, "месяц 3 (переплата)")

    def test_prepayment_carries_into_next_period(self):
        self.user.saldo = 500.0
        self.user.save()
        self.user.start_new_period()
        self.assertEqual(self.user.last_prepayment, 500.0)   # снимок предоплаты
        self.assertEqual(self.user.last_dept, 0.0)
        self.assertEqual(self.user.current_dept, 700.0)      # 1200 - 500
        self.assertReceiptBalances(self.user, "предоплата перешла")


class PaymentValidationTest(TestCase):

    def test_payment_without_user(self):
        with self.assertRaises(ValueError) as ctx:
            PaymentModel(date="20.12.2024", payment=200.0, user=None).save()
        self.assertIn("должно быть заполнено", str(ctx.exception))

    def test_payment_with_unsaved_user(self):
        with self.assertRaises(ValueError) as ctx:
            PaymentModel(date="20.12.2024", payment=200.0,
                         user=UserModel(ls="99999999")).save()
        self.assertIn("не найден", str(ctx.exception))


class DateNormalizationTest(TestCase):
    """Четыре банка присылают даты в трёх разных форматах."""

    def test_all_bank_formats(self):
        cases = {
            "2024-12-27 11:58:15": "2024-12-27 11:58:15",   # Optima, QuickPay
            "27.12.2024 10:26:18": "2024-12-27 10:26:18",   # Pay24
            "20.12.2024": "2024-12-20 00:00:00",            # Umai
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_payment_date(raw), expected, msg=raw)

    def test_unknown_format_is_kept(self):
        self.assertEqual(normalize_payment_date("не дата"), "не дата")

    def test_none(self):
        self.assertEqual(normalize_payment_date(None), "")


class BankImportTest(TestCase):
    """Загрузка реальных реестров четырёх банков через админку."""

    FILES = {
        "optima":   ("files/optima.xls",   ["1517227-4"]),
        "pay24":    ("files/pay24.xls",    ["1506226-6", "1502540-9", "1515205-2",
                                            "1512448-2", "1512418-0", "1516011-0"]),
        "quickpay": ("files/quickpay.csv", ["1515212-5"]),
        "umai":     ("files/umai.xlsx",    ["1517355-6"]),
    }

    def setUp(self):
        from django.contrib.auth.models import User
        self.admin_user = User.objects.create_superuser("imp", "a@b.c", "x")

    def _upload(self, bank, accounts_exist=True):
        import os
        from django.conf import settings
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.backends.db import SessionStore
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import RequestFactory
        from users_app.admin import PaymentAdmin, PaymentUploadForm

        path, accounts = self.FILES[bank]
        if accounts_exist:
            for ls in accounts:
                UserModel.objects.get_or_create(
                    ls=ls, defaults=dict(fio=f"А {ls}", area=24.0, rate=24.0,
                                         address="—", saldo=0))

        request = RequestFactory().post("/x")
        request.user = self.admin_user
        request.session = SessionStore()
        request.session.create()
        request._messages = FallbackStorage(request)

        full_path = os.path.join(settings.BASE_DIR, path)
        with open(full_path, "rb") as fh:
            upload = SimpleUploadedFile(os.path.basename(path), fh.read())

        form = PaymentUploadForm(data={"bank": bank}, files={"file": upload})
        self.assertTrue(form.is_valid(), form.errors)
        PaymentAdmin(PaymentModel, AdminSite()).save_model(
            request, PaymentModel(), form, change=False)
        return [str(m) for m in request._messages]

    def test_every_bank_file_imports(self):
        for bank, (_, accounts) in self.FILES.items():
            with self.subTest(bank=bank):
                messages = self._upload(bank)
                self.assertTrue(any("загружено" in m for m in messages), messages)
                for ls in accounts:
                    user = UserModel.objects.get(ls=ls)
                    self.assertGreater(user.last_payment, 0,
                                       f"{bank}/{ls}: платёж не учтён")
                    self.assertEqual(user.saldo, user.last_payment)

    def test_missing_account_rolls_back_whole_file(self):
        """Один неизвестный ЛС — реестр не применяется целиком."""
        _, accounts = self.FILES["pay24"]
        for ls in accounts[:-1]:                     # заводим всех, кроме последнего
            UserModel.objects.create(ls=ls, fio="А", area=24.0, rate=24.0,
                                     address="—", saldo=0)
        messages = self._upload("pay24", accounts_exist=False)

        self.assertTrue(any("не загружен" in m for m in messages), messages)
        self.assertTrue(any(accounts[-1] in m for m in messages), messages)
        self.assertEqual(PaymentModel.objects.count(), 0)
        self.assertEqual(set(UserModel.objects.values_list("saldo", flat=True)), {0.0})

    def test_second_upload_of_same_file_is_rejected(self):
        """Повторная загрузка того же реестра не должна задваивать платежи."""
        self._upload("pay24")
        snapshot = dict(UserModel.objects.values_list("ls", "saldo"))
        count = PaymentModel.objects.count()

        messages = self._upload("pay24")
        self.assertTrue(any("уже был загружен" in m for m in messages), messages)
        self.assertEqual(PaymentModel.objects.count(), count)
        self.assertEqual(dict(UserModel.objects.values_list("ls", "saldo")), snapshot)

    def test_import_keeps_receipt_identity(self):
        _, accounts = self.FILES["pay24"]
        for ls in accounts:
            user = UserModel.objects.create(ls=ls, fio="А", area=24.0, rate=24.0,
                                            address="—", saldo=0)
            user.start_new_period()
        self._upload("pay24", accounts_exist=False)

        for user in UserModel.objects.all():
            opening = balance(user.last_dept, user.last_prepayment)
            closing = balance(user.current_dept, user.current_prepayment)
            self.assertAlmostEqual(
                closing, round(opening - user.period_charge + user.last_payment, 2), places=2,
                msg=f"ЛС {user.ls}: тождество нарушено после импорта")


class MidPeriodEditTest(ReceiptIdentityMixin, TestCase):
    """Правка площади/тарифа в середине периода не должна ломать квитанцию."""

    def setUp(self):
        self.user = UserModel.objects.create(
            ls="1540000-3", fio="Смена тарифа", area=50.0, rate=24.0,
            address="—", saldo=0,
        )
        self.user.start_new_period()          # начислено 1200.00

    def test_rate_change_does_not_alter_printed_charge(self):
        self.assertEqual(self.user.period_charge, 1200.0)
        self.assertEqual(self.user.saldo, -1200.0)

        PaymentModel.objects.create(date="2026-08-05", payment=1200.0,
                                    user=self.user, ls=self.user.ls)
        self.user.refresh_from_db()

        # Админ поправил тариф в середине месяца
        self.user.rate = 32.0
        self.user.save()
        self.user.refresh_from_db()

        self.assertEqual(self.user.rate_sum, 1600.0)       # текущая сумма обновилась
        self.assertEqual(self.user.period_charge, 1200.0)  # но списано было 1200
        self.assertReceiptBalances(self.user, "тариф изменён в середине периода")

    def test_area_change_does_not_alter_printed_charge(self):
        self.user.area = 80.0
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.rate_sum, 1920.0)
        self.assertEqual(self.user.period_charge, 1200.0)
        self.assertReceiptBalances(self.user, "площадь изменена в середине периода")

    def test_new_rate_applies_from_next_period(self):
        self.user.rate = 32.0
        self.user.save()
        self.user.start_new_period()
        self.assertEqual(self.user.period_charge, 1600.0)   # новый тариф — новый период
        self.assertReceiptBalances(self.user, "новый период по новому тарифу")


class ReceiptRenderTest(TestCase):
    """Числа, реально попадающие в шаблон квитанции, должны сходиться."""

    def test_rendered_receipt_columns_add_up(self):
        from users_app import receipts as receipts_lib

        user = UserModel.objects.create(
            ls="1550000-4", fio="Печать", area=24.0, rate=24.0,
            address="Токтогула 7", saldo=-300.0,
        )
        user.start_new_period()
        for amount in (200.0, 150.0):
            PaymentModel.objects.create(date="2026-08-05", payment=amount,
                                        user=user, ls=user.ls)
        user.refresh_from_db()

        receipt = receipts_lib.build_receipts([user])[0]
        opening = round(receipt["last_prepayment"] - receipt["last_dept"], 2)
        closing = round(receipt["current_prepayment"] - receipt["total"], 2)
        self.assertAlmostEqual(
            closing, round(opening - receipt["charged"] + receipt["last_payment"], 2),
            places=2,
            msg=f"колонки квитанции не сходятся: {receipt}")
        self.assertEqual(receipt["last_payment"], 350.0)
        self.assertEqual(receipt["charged"], 576.0)
