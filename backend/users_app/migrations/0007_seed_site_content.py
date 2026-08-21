from django.db import migrations


def seed_site_content(apps, schema_editor):
    SiteSettings = apps.get_model('users_app', 'SiteSettings')
    HeroSlide = apps.get_model('users_app', 'HeroSlide')
    SiteFeature = apps.get_model('users_app', 'SiteFeature')
    SiteMetric = apps.get_model('users_app', 'SiteMetric')
    Service = apps.get_model('users_app', 'Service')
    Testimonial = apps.get_model('users_app', 'Testimonial')
    FrequentlyAskedQuestion = apps.get_model('users_app', 'FrequentlyAskedQuestion')

    SiteSettings.objects.update_or_create(pk=1, defaults={
        'company_name': 'ОсОО «АВЛИ»',
        'short_name': 'АВЛИ',
        'tagline': 'Надёжное управление многоквартирными домами в Бишкеке',
        'about_title': 'Надёжный партнёр вашего дома',
        'about_text': (
            'ОсОО «АВЛИ» — современная управляющая компания, которая берёт на себя '
            'полную ответственность за управление многоквартирными домами. Мы '
            'обеспечиваем прозрачный финансовый учёт, регулярную отчётность и '
            'эффективное расходование средств жителей исключительно на благоустройство '
            'и содержание дома.'
        ),
        'about_text_secondary': (
            'Наши профессиональные бригады выполняют все необходимые работы: уборку '
            'подъездов и территории, ремонт, обслуживание кровли, освещения и входных '
            'групп. Собственные подрядчики позволяют предлагать жителям честные условия '
            'и качественно выполнять задачи в установленные сроки.'
        ),
        'mission': (
            'Наша миссия — порядок, прозрачность и комфорт. Мы работаем в соответствии '
            'с законодательством Кыргызской Республики и регулярно отчитываемся перед '
            'жителями о поступлениях и расходах.'
        ),
        'footer_text': (
            'ОсОО «АВЛИ» — ваш надёжный партнёр в управлении многоквартирными домами. '
            'Порядок, прозрачность и забота о каждом доме — для комфортной жизни жителей.'
        ),
        'address': 'г. Бишкек, мкр. Улан-2, дом 2/25, офис 3',
        'phone_primary': '+996 225 215 740',
        'phone_secondary': '+996 555 215 740',
        'email': 'uk-avli@yandex.ru',
        'whatsapp_number': '996225215740',
        'telegram_url': '',
        'map_embed_url': (
            'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1462.6587746889343!'
            '2d74.63196153882579!3d42.845027642787976!2m3!1f0!2f0!3f0!3m2!1i1024!'
            '2i768!4f13.1!3m3!1m2!1s0x389eb66758988fcd%3A0x3c7b52b85d774065!'
            '2sUlan-2%2C%20Bishkek!5e0!3m2!1sen!2skg!4v1784060257213!5m2!1sen!2skg'
        ),
        'seo_title': 'Управляющая компания АВЛИ в Бишкеке — обслуживание жилых домов',
        'seo_description': (
            'ОсОО «АВЛИ» — управление многоквартирными домами в Бишкеке: прозрачная '
            'отчётность, уборка, ремонт, обслуживание инженерных сетей и поддержка 24/7.'
        ),
    })

    hero_slides = [
        {
            'title': 'Прозрачное управление вашим домом',
            'eyebrow': 'Приветствуем!',
            'description': (
                'ОсОО «АВЛИ» берёт на себя полное управление многоквартирным домом: '
                'прозрачный учёт платежей, своевременные ремонты, уборку и содержание '
                'территории. Ваши деньги работают именно на благоустройство дома.'
            ),
            'button_text': 'Заказать звонок',
            'image_path': '/images/hero/bishkek.jpg',
            'sort_order': 10,
        },
        {
            'title': 'Комфорт и порядок каждый день',
            'eyebrow': 'Дом в надёжных руках',
            'description': (
                'Профессиональные бригады, собственные подрядчики и полный цикл работ: '
                'уборка, ремонт входных групп и кровли, освещение и оперативное решение '
                'бытовых вопросов.'
            ),
            'button_text': 'Получить консультацию',
            'image_path': '/images/hero/management.png',
            'sort_order': 20,
        },
        {
            'title': 'Полная прозрачность и контроль',
            'eyebrow': 'Понятно каждому жителю',
            'description': (
                'Регулярная отчётность, понятный единый тариф, профессиональная '
                'бухгалтерия и сдача налоговых документов. Вы всегда видите, куда идут '
                'ваши средства.'
            ),
            'button_text': 'Оставить заявку',
            'image_path': '/images/hero/modern-house.jpg',
            'sort_order': 30,
        },
    ]
    for item in hero_slides:
        title = item.pop('title')
        HeroSlide.objects.update_or_create(title=title, defaults=item)

    features = [
        ('Прозрачный учёт и контроль',
         'Ваши платежи идут строго на благоустройство дома. Мы ведём подробный учёт '
         'всех поступлений и расходов и регулярно отчитываемся перед жителями.',
         'shield-check'),
        ('Полная бухгалтерия и отчётность',
         'Берём на себя бухгалтерский учёт, взаимодействие с налоговыми органами, '
         'сдачу отчётности и оплату необходимых платежей.', 'file-chart'),
        ('Комфорт и чистота в доме',
         'Уборка подъездов и территории, ремонт, освещение, кровельные работы и другие '
         'услуги для поддержания порядка и уюта.', 'house-heart'),
        ('Профессиональные подрядчики',
         'Собственные проверенные бригады, бесплатное обследование дома и составление '
         'сметы расходов.', 'hard-hat'),
    ]
    for order, (title, description, icon) in enumerate(features, start=1):
        SiteFeature.objects.update_or_create(
            title=title,
            defaults={'description': description, 'icon': icon, 'sort_order': order * 10},
        )

    metrics = [
        ('5+', 'Домов под управлением', 'building'),
        ('98%', 'Довольных жильцов', 'users'),
        ('24/7', 'Служба поддержки', 'headphones'),
        ('504', 'Улыбок', 'smile'),
    ]
    for order, (value, label, icon) in enumerate(metrics, start=1):
        SiteMetric.objects.update_or_create(
            label=label,
            defaults={'value': value, 'icon': icon, 'sort_order': order * 10},
        )

    services = [
        {
            'slug': 'zamena-prokladki-dusha',
            'title': 'Смена прокладки в соединении душа со смесителем',
            'short_description': 'Устранение протечек и восстановление герметичности соединения душа со смесителем.',
            'description': (
                'Протечки в соединении душа со смесителем — распространённая проблема, '
                'которая может привести к утечке воды и снижению давления. Специалисты '
                'ОсОО «АВЛИ» оперативно заменят изношенную прокладку и восстановят '
                'герметичность соединения.\n\nВсе работы выполняются по современным '
                'стандартам и с гарантией качества.'
            ),
            'image_path': '/images/services/smena-prokladki-dusha.webp',
            'legacy_path': '/uslugi/platnie-uslugi/16-smena-prokladki-v-soedinenii-dusha-so-smesitelem.html.htm',
        },
        {
            'slug': 'zamena-gibkoy-podvodki',
            'title': 'Смена гибкой подводки',
            'short_description': 'Быстрая замена подводки для надёжного и безопасного подключения воды.',
            'description': (
                'Гибкая подводка подключает воду к смесителям, унитазам, бойлерам и '
                'другим приборам. Со временем она изнашивается, что может привести к '
                'протечкам и авариям.\n\nНаши специалисты выполняют замену быстро и '
                'аккуратно, используя надёжные материалы, соответствующие стандартам безопасности.'
            ),
            'image_path': '/images/services/smena-gibkoy-podvodki.webp',
            'legacy_path': '/uslugi/platnie-uslugi/15-smena-gibkoj-podvodki.html.htm',
        },
        {
            'slug': 'remont-smesitelya-salnik',
            'title': 'Ремонт смесителя при набивке сальника',
            'short_description': 'Ремонт смесителя без демонтажа с восстановлением герметичности сальника.',
            'description': (
                'Набивка сальника помогает устранить протечку, восстановить герметичность '
                'и продлить срок службы смесителя. Работы выполняются на месте без '
                'демонтажа оборудования.\n\nИспользуем качественные материалы, чтобы '
                'обеспечить надёжный и долговечный результат.'
            ),
            'image_path': '/images/services/nabivka-salnika.webp',
            'legacy_path': '/uslugi/platnie-uslugi/14-remont-smesitelja-bez-snjatija-s-mesta-pri-nabivke-salnika.html.htm',
        },
        {
            'slug': 'remont-smesitelya-prokladki',
            'title': 'Ремонт смесителя с заменой прокладок',
            'short_description': 'Устранение течи и восстановление работы смесителя без снятия с места.',
            'description': (
                'Специалисты ОсОО «АВЛИ» устраняют протечки и восстанавливают '
                'работоспособность смесителей прямо на месте установки.\n\nМы используем '
                'качественные прокладки и профессиональный инструмент, что обеспечивает '
                'долговечность выполненного ремонта.'
            ),
            'image_path': '/images/services/remont-krana-prokladok.webp',
            'legacy_path': '/uslugi/platnie-uslugi/13-remont-vodorazbornogo-krana-bez-snjatija-s-mesta.html.htm',
            'is_featured': True,
        },
        {
            'slug': 'remont-vodorazbornogo-krana',
            'title': 'Ремонт водоразборного крана без снятия',
            'short_description': 'Оперативное устранение протечек и замена изношенных деталей без демонтажа.',
            'description': (
                'Ремонт крана без снятия — удобный способ устранить протечку, заменить '
                'изношенные детали и восстановить его работу.\n\nНаши специалисты '
                'используют качественные материалы и современный инструмент, минимизируя '
                'неудобства для жителей и обеспечивая долговечный результат.'
            ),
            'image_path': '/images/services/remont-krana.webp',
            'legacy_path': '/uslugi/platnie-uslugi/12-remont-vodorazbornogo-krana-bez-snjatija-s-mesta.html.htm',
            'is_featured': True,
        },
        {
            'slug': 'zamena-smesiteley-i-kranov',
            'title': 'Замена смесителей и кранов',
            'short_description': 'Профессиональная установка и замена смесителей и водоразборных кранов.',
            'description': (
                'ОсОО «АВЛИ» выполняет установку и замену смесителей для кухни и ванной, '
                'а также кранов для водоснабжения.\n\nСовременный инструмент и проверенные '
                'материалы обеспечивают долгий срок службы нового оборудования.'
            ),
            'image_path': '/images/services/zamena-smesiteley.webp',
            'legacy_path': '/uslugi/platnie-uslugi/11-zamena-smesitelej-i-kranov.html.htm',
        },
        {
            'slug': 'ustanovka-santehpriborov',
            'title': 'Установка сантехприборов и водоразборной арматуры',
            'short_description': 'Монтаж раковин, унитазов, ванн, смесителей, кранов и вентилей.',
            'description': (
                'Наши специалисты выполняют замену смесителей, унитазов, раковин, ванн '
                'и другой сантехники, а также монтаж водоразборной арматуры.\n\nГарантируем '
                'качественное выполнение работ и соблюдение технических норм.'
            ),
            'image_path': '/images/services/zamena-vodorazbornoy-armaturi.webp',
            'legacy_path': '/uslugi/platnie-uslugi/10-zamena-ili-ustanovka-santehpriborov-i-vodorazbornoj-armatury.html.htm',
        },
        {
            'slug': 'ochistka-sten-i-potolkov',
            'title': 'Очистка стен и потолков от рисунков',
            'short_description': 'Удаление граффити, надписей и загрязнений в местах общего пользования.',
            'description': (
                'Несанкционированные рисунки ухудшают внешний вид помещений. Мы удаляем '
                'граффити и надписи безопасными средствами, не повреждающими поверхность.\n\n'
                'После очистки стены и потолки снова выглядят аккуратно и ухоженно.'
            ),
            'image_path': '/images/services/remont-podezda.webp',
            'legacy_path': '/uslugi/besplatnie-uslugi/9-obrisovany-stena-ili-potolok.html.htm',
            'category': 'included',
        },
        {
            'slug': 'montazh-truboprovoda',
            'title': 'Монтаж и замена трубопровода',
            'short_description': 'Монтаж труб для горячей и холодной воды, канализации и отопления.',
            'description': (
                'ОсОО «АВЛИ» выполняет монтаж и замену трубопроводов горячего и холодного '
                'водоснабжения, канализации и отопления. Перед началом работ специалисты '
                'оценивают состояние коммуникаций и предлагают оптимальное решение.\n\n'
                'Современные материалы и технологии обеспечивают безопасность и '
                'долговечность системы.'
            ),
            'image_path': '/images/services/montazh-truboprovoda.webp',
            'legacy_path': '/uslugi/platnie-uslugi/8-montazh-truboprovoda.html.htm',
            'is_featured': True,
        },
    ]
    for order, item in enumerate(services, start=1):
        item = item.copy()
        slug = item.pop('slug')
        item.setdefault('price_label', 'По запросу')
        item.setdefault('category', 'paid')
        item.setdefault('is_featured', False)
        item['sort_order'] = order * 10
        item['meta_title'] = f"{item['title']} в Бишкеке — ОсОО «АВЛИ»"
        item['meta_description'] = item['short_description']
        Service.objects.update_or_create(slug=slug, defaults=item)

    testimonials = [
        ('Айдарбеков Нурлан', 'Житель',
         'С «АВЛИ» в нашем доме наконец-то появился порядок. Деньги идут именно на '
         'нужды дома: убирают подъезды, вовремя делают ремонт, отчитываются по расходам. '
         'Очень довольны прозрачностью!', 'АН'),
        ('Светлана Петрова', 'Жительница',
         'Благодаря «АВЛИ» у нас чистый двор, отремонтировали крышу и входную группу. '
         'Бухгалтерия прозрачная, всегда можно посмотреть отчёт. Рекомендую!', 'СП'),
        ('Эсенбекова Айгуль', 'Жительница',
         '«АВЛИ» — настоящие профессионалы. Быстро реагируют на заявки, качественно '
         'делают ремонт в подъездах. Особенно радует, что есть свои бригады.', 'ЭА'),
        ('Дмитрий Ким', 'Житель',
         'Раньше были проблемы с отчётностью, а с «АВЛИ» всё прозрачно. Видим, куда '
         'идут деньги, подъезды всегда чистые, территория ухоженная.', 'ДК'),
    ]
    for order, (name, role, text, initials) in enumerate(testimonials, start=1):
        Testimonial.objects.update_or_create(
            name=name,
            defaults={'role': role, 'text': text, 'initials': initials, 'sort_order': order * 10},
        )

    faq = [
        ('Как работает управление домом в «АВЛИ»?',
         'Жители оплачивают единый тариф. Часть средств идёт на административные расходы '
         '(бухгалтерия, налоги), а основная часть направляется на уборку, ремонты, '
         'освещение и благоустройство. Мы полностью берём на себя управление домом.'),
        ('Куда идут деньги жителей и насколько прозрачно управление?',
         'Все платежи идут на содержание и благоустройство вашего дома. Мы ведём '
         'прозрачный учёт и регулярно предоставляем отчёты о поступлениях и расходах.'),
        ('Входит ли ремонт подъездов, крыши и территории в ваши обязанности?',
         'Да. За счёт накопленных средств мы организуем уборку подъездов и территории, '
         'ремонт входных групп и кровли, освещение и другие работы по содержанию дома.'),
        ('Как заключить договор с «АВЛИ»?',
         'Обсудите предложение с жильцами и обратитесь к домовому комитету. Наши '
         'специалисты проведут встречу, ответят на вопросы и помогут оформить документы.'),
    ]
    for order, (question, answer) in enumerate(faq, start=1):
        FrequentlyAskedQuestion.objects.update_or_create(
            question=question,
            defaults={'answer': answer, 'sort_order': order * 10},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('users_app', '0006_frequentlyaskedquestion_heroslide_service_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_site_content, migrations.RunPython.noop),
    ]
