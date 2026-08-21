JAZZMIN_SETTINGS = {
    "site_brand": "АВЛИ",
    "welcome_sign": "Вход в систему",
    "site_title": "АВЛИ",
    "site_header": "АВЛИ",
    "topmenu_links": [
        {"name": "Печать квитанций", "url": "/receipts", "permissions": ["auth.view_user"]},
        {"name": "Свод за месяц", "url": "/reports/monthly", "permissions": ["auth.view_user"]},
    ],
    "navigation_expanded": True,
    "order_with_respect_to": [
        "subscribers", "charge_archive", "houses", "payments", "website", "auth",
    ],
    "icons": {
        "subscribers": "fas fa-users",
        "charge_archive": "fas fa-calendar-alt",
        "houses": "fas fa-building",
        "payments": "fas fa-credit-card",
        "website": "fas fa-globe",
        "subscribers.usermodel": "fas fa-user-friends",
        "charge_archive.periodsnapshot": "fas fa-file-invoice",
        "houses.house": "fas fa-home",
        "payments.paymentmodel": "fas fa-money-check-alt",
        "website.callbackrequest": "fas fa-phone-volume",
        "website.service": "fas fa-tools",
        "website.sitesettings": "fas fa-cog",
    },
}
