import json

from django.test import TestCase, override_settings
from django.urls import reverse

from users_app.models import UserModel
from users_app.public_accounts import (
    AccountNotFound,
    InvalidAccountNumber,
    build_public_account,
    find_account,
)


class PublicAccountServiceTest(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(
            ls="1517227-4",
            fio="Иванова Мария",
            address="ул. Байтик Баатыра, 9а, кв. 12",
            area=50,
            rate=24,
            saldo=-900,
            period_charge=1200,
            last_payment=300,
        )

    def test_finds_account_without_hyphen(self):
        self.assertEqual(find_account("15172274").pk, self.user.pk)

    def test_rejects_invalid_input(self):
        with self.assertRaises(InvalidAccountNumber):
            find_account("1517<script>")
        with self.assertRaises(InvalidAccountNumber):
            find_account("12")

    def test_unknown_account(self):
        with self.assertRaises(AccountNotFound):
            find_account("99999999")

    def test_public_data_matches_receipt_fields(self):
        data = build_public_account(self.user)
        self.assertEqual(data["account_number"], self.user.ls)
        self.assertEqual(data["closing_debt"], 900)
        self.assertEqual(data["charged"], 1200)
        self.assertEqual(data["paid"], 300)
        self.assertNotIn("phone", data)


class PublicWebsiteTest(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(
            ls="1517227-4", fio="Иванова Мария", address="Дом 9, кв. 12",
            area=50, rate=24, saldo=-1200, period_charge=1200,
        )

    def test_homepage_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Вся информация по дому")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_lookup_renders_digital_receipt(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        response = csrf_client.post(reverse("home"), {"account_number": "15172274"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.fio)
        self.assertContains(response, self.user.address)
        self.assertContains(response, "1200,00", html=False)

    def test_lookup_not_found_has_safe_message(self):
        response = self.client.post(reverse("home"), {"account_number": "99999999"})
        self.assertContains(response, "Лицевой счёт не найден")


@override_settings(INTERNAL_API_TOKEN="test-secret")
class AccountApiTest(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(
            ls="1517227-4", fio="Иванова Мария", address="Дом 9",
            area=50, rate=24, saldo=-1200, period_charge=1200,
        )
        self.url = reverse("account_lookup_api")

    def post(self, account_number, token="test-secret"):
        return self.client.post(
            self.url,
            data=json.dumps({"account_number": account_number}),
            content_type="application/json",
            HTTP_X_AVLI_API_KEY=token,
        )

    def test_requires_internal_token(self):
        response = self.post(self.user.ls, token="wrong")
        self.assertEqual(response.status_code, 403)

    @override_settings(INTERNAL_API_TOKEN="", DEBUG=False)
    def test_production_api_refuses_to_start_without_token(self):
        response = self.post(self.user.ls, token="")
        self.assertEqual(response.status_code, 503)

    def test_returns_account(self):
        response = self.post("15172274")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["account"]["total_due"], 1200)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_returns_404_for_unknown_account(self):
        response = self.post("99999999")
        self.assertEqual(response.status_code, 404)

    def test_rejects_non_object_json(self):
        response = self.client.post(
            self.url,
            data="[]",
            content_type="application/json",
            HTTP_X_AVLI_API_KEY="test-secret",
        )
        self.assertEqual(response.status_code, 400)

    def test_healthcheck(self):
        response = self.client.get(reverse("healthcheck"))
        self.assertEqual(response.json(), {"status": "ok"})
