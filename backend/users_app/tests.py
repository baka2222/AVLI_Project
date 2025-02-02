from django.test import TestCase

from django.test import TestCase
from users_app.models import UserModel, PaymentModel

class PaymentModelTest(TestCase):
    
    def setUp(self):
        """Создаём тестовые данные."""
        self.user = UserModel.objects.create(
            ls="12345678",
            fio="Иван Иванов",
            area=50.0,
            rate=10.0,
            saldo=100.0,
            address="г. Бишкек, ул. Тестовая, д. 1"
        )
    
    def test_payment_model_save(self):
        """Проверяем, что платеж корректно обновляет сальдо."""
        initial_saldo = self.user.saldo
        payment = PaymentModel.objects.create(
            date="20.12.2024",
            payment=200.0,
            user=self.user
        )
        self.user.refresh_from_db()  # Обновляем объект из базы данных
        self.assertEqual(self.user.saldo, initial_saldo + payment.payment)
    
    def test_payment_model_no_user(self):
        """Проверяем, что ошибка возникает, если user не указан."""
        with self.assertRaises(ValueError) as context:
            payment = PaymentModel(
                date="20.12.2024",
                payment=200.0,
                user=None  # user не указан
            )
            payment.save()
        self.assertIn("Поле 'user' должно быть заполнено.", str(context.exception))
    
    def test_payment_model_user_not_found(self):
        """Проверяем, что ошибка возникает, если лицевой счёт не найден."""
        with self.assertRaises(ValueError) as context:
            non_existent_user = UserModel(ls="99999999")  # Пользователь не существует
            payment = PaymentModel(
                date="20.12.2024",
                payment=200.0,
                user=non_existent_user
            )
            payment.save()
        self.assertIn("не найден", str(context.exception))
