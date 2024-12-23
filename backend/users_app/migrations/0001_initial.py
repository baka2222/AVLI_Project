# Generated by Django 5.1.4 on 2024-12-23 14:55

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UserModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ls', models.CharField(max_length=50, verbose_name='Лицевой счет')),
                ('fio', models.CharField(max_length=100, verbose_name='ФИО')),
                ('area', models.FloatField(verbose_name='Площадь (м2)')),
                ('rate', models.FloatField(verbose_name='Тариф (сом / м2)')),
                ('rate_sum', models.FloatField(editable=False, verbose_name='Сумма по тарифу')),
                ('address', models.TextField(max_length=200, verbose_name='Адрес')),
                ('saldo', models.FloatField(verbose_name='Сальдо')),
            ],
        ),
    ]