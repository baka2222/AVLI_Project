from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase


class AdminNavigationTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username='admin-navigation-test',
            email='admin@example.com',
            password='test-password',
        )

    def test_accounting_and_site_models_are_split_into_sections(self):
        request = RequestFactory().get('/admin/')
        request.user = self.superuser

        sections = admin.site.get_app_list(request)
        sections_by_name = {section['name']: section for section in sections}

        self.assertEqual(
            [model['object_name'] for model in sections_by_name['Абоненты']['models']],
            ['UserModel'],
        )
        self.assertEqual(
            [model['object_name'] for model in sections_by_name['Архив начислений']['models']],
            ['PeriodSnapshot'],
        )
        self.assertEqual(
            [model['object_name'] for model in sections_by_name['Дома']['models']],
            ['House'],
        )
        self.assertEqual(
            [model['object_name'] for model in sections_by_name['Платежи']['models']],
            ['PaymentModel'],
        )

        site_models = {
            model['object_name']
            for model in sections_by_name['Сайт и заявки']['models']
        }
        self.assertTrue({
            'CallbackRequest',
            'FrequentlyAskedQuestion',
            'HeroSlide',
            'Service',
            'SiteFeature',
            'SiteMetric',
            'SiteSettings',
            'Testimonial',
        }.issubset(site_models))
        self.assertFalse({'UserModel', 'PeriodSnapshot', 'House', 'PaymentModel'} & site_models)

    def test_admin_index_still_renders(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Сайт и заявки')
        self.assertContains(response, 'Архив начислений')
