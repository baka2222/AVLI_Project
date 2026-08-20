"""Тесты архива начислений и сводов для бухгалтерии.

Главное, что здесь проверяется:
  * снимок снимается за *закрываемый* месяц, а не за новый — иначе в архиве
    окажутся цифры, которых не было ни в одной квитанции;
  * тождество квитанции соблюдается и внутри строки архива, и в итоге свода;
  * повторное закрытие месяца упирается в уже записанный архив, а не списывает
    тариф второй раз;
  * своды закрыты от посторонних: это финансовые данные всех жильцов сразу.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from users_app import reports as reports_lib
from users_app.addresses import parse_address
from users_app.models import House, PeriodSnapshot, UserModel


def net(debit, credit):
    """Остаток одним числом: минус — долг, плюс — переплата."""
    return round((credit or 0) - (debit or 0), 2)


class AddressParsingTest(TestCase):
    """Разбор адресов старой базы: одна улица не должна давать несколько домов."""

    def test_variants_of_one_street_collapse(self):
        variants = [
            "ул Байтик-Баатыра  дом 6 кв.1",
            "ул Байтик-Батыра 6 кв.2",
            "ул. Байтик-Батыра дом 6 кв.3",
        ]
        parsed = {parse_address(value)[:2] for value in variants}
        self.assertEqual(parsed, {("ул. Байтик-Баатыра", "6")})

    def test_house_number_with_separated_letter(self):
        self.assertEqual(parse_address("ул Байтик-Баатыра дом 3 а кв.12"),
                         ("ул. Байтик-Баатыра", "3а", "12"))

    def test_number_glued_to_street(self):
        self.assertEqual(parse_address("ул. Саманчина3а кв.7"),
                         ("ул. Саманчина", "3а", "7"))

    def test_microdistrict_formats(self):
        self.assertEqual(parse_address("10 мкр дом 4 кв.59")[:2], ("10 мкр-н", "4"))
        self.assertEqual(parse_address("Мкр 10 дом 20 кв.1")[:2], ("10 мкр-н", "20"))

    def test_garbage_address_does_not_crash(self):
        self.assertEqual(parse_address("кв."), ("", "", ""))
        self.assertEqual(parse_address(None), ("", "", ""))


class HouseTest(TestCase):

    def test_address_is_built_from_house_and_apartment(self):
        house = House.objects.create(street="ул. Саманчина", number="5а")
        user = UserModel.objects.create(
            ls="1", fio="Тест", area=50, rate=10, address="что угодно",
            house=house, apartment="12", saldo=0,
        )
        self.assertEqual(user.address, "ул. Саманчина дом 5а кв.12")

    def test_renaming_house_updates_subscriber_addresses(self):
        """Переименование дома обязано доехать до адреса в квитанции."""
        house = House.objects.create(street="ул. Политехническ", number="4")
        user = UserModel.objects.create(
            ls="2", fio="Тест", area=50, rate=10, address="",
            house=house, apartment="7", saldo=0,
        )
        house.street = "ул. Политехническая"
        house.save()
        user.refresh_from_db()
        self.assertEqual(user.address, "ул. Политехническая дом 4 кв.7")

    def test_houses_sort_by_number_not_by_string(self):
        House.objects.create(street="ул. Тестовая", number="10")
        House.objects.create(street="ул. Тестовая", number="9")
        self.assertEqual([h.number for h in House.objects.all()], ["9", "10"])


class ArchiveBase(TestCase):

    def setUp(self):
        self.house = House.objects.create(street="ул. Саманчина", number="5")
        self.other = House.objects.create(street="ул. Малдыбаева", number="36б")
        self.staff = User.objects.create_superuser("buh", "buh@avli.kg", "pass12345")
        self.client.force_login(self.staff)

    def make_user(self, ls, house, apartment, area=50.0, rate=10.0, saldo=0.0):
        return UserModel.objects.create(
            ls=ls, fio=f"Абонент {ls}", area=area, rate=rate, address="",
            house=house, apartment=apartment, saldo=saldo,
        )

    def close_period(self, users, year, month, extra=None):
        """Прогнать действие админки «Начислить за новый месяц»."""
        data = {
            "action": "update_saldo_action",
            "_selected_action": [str(user.pk) for user in users],
            "confirm_period": "yes",
            "period_year": str(year),
            "period_month": str(month),
        }
        data.update(extra or {})
        return self.client.post(
            reverse("admin:users_app_usermodel_changelist"), data, follow=True)


class SnapshotCaptureTest(ArchiveBase):

    def test_snapshot_describes_the_closed_month_not_the_new_one(self):
        user = self.make_user("100", self.house, "1")
        user.start_new_period()                       # начислено 500 за июль
        user.register_payment(300.0)                  # оплачено в июле

        self.close_period([user], 2026, 7)

        snapshot = PeriodSnapshot.objects.get(subscriber=user)
        self.assertEqual((snapshot.year, snapshot.month), (2026, 7))
        self.assertEqual(snapshot.charged_ku, 500.0)
        self.assertEqual(snapshot.paid_ku, 300.0)
        self.assertEqual(snapshot.closing_debit, 200.0)

        # А сам абонент уже живёт в августе: начислено заново, оплачено обнулено.
        user.refresh_from_db()
        self.assertEqual(user.last_payment, 0.0)
        self.assertEqual(user.last_dept, 200.0)

    def test_snapshot_keeps_receipt_identity(self):
        user = self.make_user("101", self.house, "2", saldo=-1200.0)
        user.start_new_period()
        user.register_payment(700.0)
        self.close_period([user], 2026, 7)

        snapshot = PeriodSnapshot.objects.get(subscriber=user)
        expected = round(net(snapshot.opening_debit, snapshot.opening_credit)
                         - snapshot.charged_ku + snapshot.paid_ku, 2)
        self.assertAlmostEqual(
            net(snapshot.closing_debit, snapshot.closing_credit), expected, places=2)

    def test_overdue_excludes_the_current_month_charge(self):
        """Просрочка — только то, что висит с прошлых месяцев."""
        user = self.make_user("102", self.house, "3", saldo=-800.0)
        user.start_new_period()                       # долг 800 + начислено 500
        self.close_period([user], 2026, 7)

        snapshot = PeriodSnapshot.objects.get(subscriber=user)
        self.assertEqual(snapshot.closing_debit, 1300.0)
        self.assertEqual(snapshot.overdue, 800.0)

    def test_no_overdue_when_paid_in_full(self):
        user = self.make_user("103", self.house, "4")
        user.start_new_period()
        user.register_payment(500.0)
        self.close_period([user], 2026, 7)
        self.assertEqual(PeriodSnapshot.objects.get(subscriber=user).overdue, 0.0)

    def test_fee_column_defaults_to_three_percent(self):
        user = self.make_user("104", self.house, "5")
        user.start_new_period()
        user.register_payment(200.0)
        self.close_period([user], 2026, 7)

        snapshot = PeriodSnapshot.objects.get(subscriber=user)
        self.assertEqual(snapshot.charged_fee, 15.0)   # 3% от 500
        self.assertEqual(snapshot.paid_fee, 6.0)       # 3% от 200

    def test_manual_columns_do_not_touch_subscriber_balance(self):
        user = self.make_user("105", self.house, "6")
        user.start_new_period()
        self.close_period([user], 2026, 7)

        snapshot = PeriodSnapshot.objects.get(subscriber=user)
        snapshot.penalty = 120.0
        snapshot.transfer = 50.0
        snapshot.save()

        user.refresh_from_db()
        self.assertEqual(user.saldo, -1000.0)          # два начисления по 500

    def test_snapshot_survives_deletion_of_subscriber(self):
        user = self.make_user("106", self.house, "7")
        user.start_new_period()
        self.close_period([user], 2026, 7)

        user.delete()
        snapshot = PeriodSnapshot.objects.get(ls="106")
        self.assertIsNone(snapshot.subscriber)
        self.assertEqual(snapshot.fio, "Абонент 106")


class DoubleClosingTest(ArchiveBase):

    def test_second_closing_of_same_month_is_blocked(self):
        user = self.make_user("200", self.house, "1")
        user.start_new_period()
        self.close_period([user], 2026, 7)
        user.refresh_from_db()
        saldo_after_first = user.saldo

        response = self.close_period([user], 2026, 7)

        self.assertContains(response, "архив уже записан")
        user.refresh_from_db()
        self.assertEqual(user.saldo, saldo_after_first)     # тариф не списан второй раз
        self.assertEqual(PeriodSnapshot.objects.filter(ls="200").count(), 1)

    def test_closing_can_be_forced_with_overwrite(self):
        user = self.make_user("201", self.house, "2")
        user.start_new_period()
        self.close_period([user], 2026, 7)
        self.close_period([user], 2026, 7, extra={"overwrite": "1"})

        self.assertEqual(PeriodSnapshot.objects.filter(ls="201").count(), 1)

    def test_archive_only_action_does_not_charge(self):
        user = self.make_user("202", self.house, "3")
        user.start_new_period()
        before = UserModel.objects.get(pk=user.pk).saldo

        self.client.post(reverse("admin:users_app_usermodel_changelist"), {
            "action": "archive_period_action",
            "_selected_action": [str(user.pk)],
            "confirm_period": "yes",
            "period_year": "2026",
            "period_month": "7",
        }, follow=True)

        user.refresh_from_db()
        self.assertEqual(user.saldo, before)
        self.assertTrue(PeriodSnapshot.objects.filter(ls="202", year=2026, month=7).exists())


class ReportTest(ArchiveBase):

    def setUp(self):
        super().setUp()
        self.users = [
            self.make_user("300", self.house, "1", saldo=-700.0),
            self.make_user("301", self.house, "2"),
            self.make_user("302", self.other, "1", saldo=-2000.0),
        ]
        for user in self.users:
            user.start_new_period()
        self.users[0].register_payment(400.0)
        self.users[1].register_payment(500.0)
        self.close_period(self.users, 2026, 7)

    def test_house_rows_sum_up_to_totals(self):
        report = reports_lib.build_report(2026, 7)
        rows = report["rows"]
        self.assertEqual(len(rows), 2)                       # два дома
        for field in reports_lib.MONEY_FIELDS:
            self.assertAlmostEqual(
                round(sum(row[field] for row in rows), 2),
                report["totals"][field], places=2,
                msg=f"строки свода не сходятся с итогом по графе {field}",
            )

    def test_totals_keep_receipt_identity(self):
        """Итог по компании обязан сходиться так же, как отдельная квитанция."""
        totals = reports_lib.build_report(2026, 7)["totals"]
        expected = round(net(totals["opening_debit"], totals["opening_credit"])
                         - totals["charged_ku"] + totals["paid_ku"], 2)
        self.assertAlmostEqual(
            net(totals["closing_debit"], totals["closing_credit"]), expected, places=2)

    def test_filter_by_house(self):
        report = reports_lib.build_report(2026, 7, house=self.house)
        self.assertEqual(report["totals"]["accounts"], 2)
        self.assertEqual(len(report["rows"]), 1)

    def test_subscriber_mode_lists_every_account(self):
        report = reports_lib.build_report(
            2026, 7, house=self.house, mode=reports_lib.MODE_SUBSCRIBERS)
        self.assertEqual([row["ls"] for row in report["rows"]], ["300", "301"])

    def test_debtors_only(self):
        report = reports_lib.build_report(
            2026, 7, mode=reports_lib.MODE_SUBSCRIBERS, only_debtors=True)
        self.assertEqual({row["ls"] for row in report["rows"]}, {"300", "302"})

    def test_empty_period_renders_without_error(self):
        report = reports_lib.build_report(2020, 1)
        self.assertTrue(report["is_empty"])
        self.assertEqual(report["totals"]["accounts"], 0)

    def test_apartments_sorted_naturally(self):
        for number in ("10", "2", "12а"):
            user = self.make_user(f"4{number}", self.other, number)
            user.start_new_period()
        self.close_period(UserModel.objects.filter(house=self.other), 2026, 8)

        report = reports_lib.build_report(
            2026, 8, house=self.other, mode=reports_lib.MODE_SUBSCRIBERS)
        self.assertEqual([row["apartment"] for row in report["rows"]],
                         ["1", "2", "10", "12а"])


class ReportViewTest(ArchiveBase):

    def setUp(self):
        super().setUp()
        user = self.make_user("500", self.house, "1", saldo=-300.0)
        user.start_new_period()
        self.close_period([user], 2026, 7)

    def test_report_page_renders(self):
        response = self.client.get(reverse("monthly_report"), {"period": "2026-7"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Свод по домам")
        self.assertContains(response, "ул. Саманчина дом 5")
        self.assertContains(response, "ИТОГО:")

    def test_subscriber_mode_page(self):
        response = self.client.get(reverse("monthly_report"), {
            "period": "2026-7", "house": self.house.pk, "mode": "subscribers"})
        self.assertContains(response, "Расшифровка по абонентам")
        self.assertContains(response, "500")

    def test_excel_export(self):
        response = self.client.get(reverse("monthly_report_excel"), {"period": "2026-7"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])
        self.assertIn(".xlsx", response["Content-Disposition"])

    def test_report_requires_staff(self):
        """Свод — финансовые данные всех жильцов, посторонним он недоступен."""
        self.client.logout()
        response = self.client.get(reverse("monthly_report"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response["Location"])

    def test_period_without_archive_shows_empty_report(self):
        response = self.client.get(reverse("monthly_report"), {"period": "2019-3"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "архив не найден")


class SubscriberCardTest(ArchiveBase):
    """История начислений должна открываться из карточки самого абонента."""

    def test_archive_shown_on_subscriber_page(self):
        user = self.make_user("600", self.house, "9", saldo=-450.0)
        user.start_new_period()
        self.close_period([user], 2026, 7)

        response = self.client.get(
            reverse("admin:users_app_usermodel_change", args=[user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Архив по месяцам")
        self.assertContains(response, "Июль 2026")
