"""Привязать абонентов к справочнику домов по строке адреса.

    python manage.py sync_houses            # только те, у кого дом не заполнен
    python manage.py sync_houses --all      # перепривязать всех
    python manage.py sync_houses --dry-run  # показать, что получится

Нужна после загрузки абонентов из DBF или другого внешнего источника: там
адрес приходит одной строкой. Разбор тот же, что в миграции 0005, — общий код
в `users_app.addresses`.
"""

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from users_app.addresses import format_address, house_title, parse_address
from users_app.models import DEFAULT_SERVICE_TYPE, House, UserModel


BATCH = 500


class Command(BaseCommand):
    help = 'Разобрать адреса абонентов на дом и квартиру'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='Перепривязать и тех, у кого дом уже указан')
        parser.add_argument('--dry-run', action='store_true',
                            help='Ничего не сохранять, только показать итог')

    def handle(self, *args, **options):
        queryset = UserModel.objects.all()
        if not options['all']:
            queryset = queryset.filter(house__isnull=True)

        houses = {(h.street, h.number): h for h in House.objects.all()}
        created_houses, linked, updated, skipped = 0, 0, [], []

        with transaction.atomic():
            for user in queryset.iterator(chunk_size=BATCH):
                street, number, apartment = parse_address(user.address)
                if not street and not number:
                    skipped.append(user.ls)
                    continue

                house = houses.get((street, number))
                if house is None:
                    leading = re.match(r'\d+', number)
                    if options['dry_run']:
                        house = House(street=street, number=number)
                    else:
                        house = House.objects.create(
                            street=street, number=number,
                            number_order=int(leading.group()) if leading else 0,
                            service_type=DEFAULT_SERVICE_TYPE,
                        )
                    houses[(street, number)] = house
                    created_houses += 1

                user.house = house
                user.apartment = apartment
                user.address = format_address(house_title(street, number), apartment)
                updated.append(user)
                linked += 1

                if not options['dry_run'] and len(updated) >= BATCH:
                    UserModel.objects.bulk_update(updated, ['house', 'apartment', 'address'])
                    updated = []

            if not options['dry_run'] and updated:
                UserModel.objects.bulk_update(updated, ['house', 'apartment', 'address'])

            if options['dry_run']:
                transaction.set_rollback(True)

        prefix = '[dry-run] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Привязано абонентов: {linked}. '
            f'Домов в справочнике: {len(houses)} (создано новых: {created_houses}).'
        ))
        if skipped:
            shown = ', '.join(skipped[:10])
            more = f' и ещё {len(skipped) - 10}' if len(skipped) > 10 else ''
            self.stdout.write(self.style.WARNING(
                f'{prefix}Не удалось разобрать адрес у {len(skipped)} абонент(ов): {shown}{more}. '
                f'Укажите дом в карточке вручную.'
            ))
