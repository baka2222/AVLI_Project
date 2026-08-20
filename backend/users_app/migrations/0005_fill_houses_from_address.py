"""Разбор существующих адресов на справочник домов и номер квартиры.

Адреса были одной строкой из старой DBF-базы: 5021 абонент, 96 домов, 23 улицы,
причём одна улица встречалась в нескольких написаниях. Разбор делает
`users_app.addresses`, здесь только запись результата.

Поле `address` тоже переписывается — на нормализованный вид («8 мкр-н дом 11
кв.19» вместо «8 микр-он дом 11 кв.19»). Иначе адрес в базе разъедется с домом
из справочника при первом же сохранении абонента: `UserModel.save()` теперь
собирает адрес из дома и квартиры.
"""

import re

from django.db import migrations

from users_app.addresses import format_address, house_title, parse_address


BATCH = 500


def fill_houses(apps, schema_editor):
    UserModel = apps.get_model('users_app', 'UserModel')
    House = apps.get_model('users_app', 'House')

    houses = {}
    for house in House.objects.all():
        houses[(house.street, house.number)] = house

    updated = []
    for user in UserModel.objects.all().iterator(chunk_size=BATCH):
        street, number, apartment = parse_address(user.address)
        if not street and not number:
            # Адрес вида «кв.» — дом определить нечем, оставляем как есть.
            continue

        key = (street, number)
        house = houses.get(key)
        if house is None:
            leading = re.match(r'\d+', number)
            house = House.objects.create(
                street=street,
                number=number,
                number_order=int(leading.group()) if leading else 0,
                service_type='ТО',
            )
            houses[key] = house

        user.house = house
        user.apartment = apartment
        user.address = format_address(house_title(street, number), apartment)
        updated.append(user)

        if len(updated) >= BATCH:
            UserModel.objects.bulk_update(updated, ['house', 'apartment', 'address'])
            updated = []

    if updated:
        UserModel.objects.bulk_update(updated, ['house', 'apartment', 'address'])


def clear_houses(apps, schema_editor):
    """Откат: отвязать абонентов от домов. Сами адреса-строки остаются."""
    UserModel = apps.get_model('users_app', 'UserModel')
    UserModel.objects.update(house=None, apartment='')


class Migration(migrations.Migration):

    dependencies = [
        ('users_app', '0004_usermodel_apartment_house_usermodel_house_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_houses, clear_houses),
    ]
