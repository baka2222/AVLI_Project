from django.urls import path

from .views import account_lookup_api, healthcheck, home, product_detail, receipts_pdf

urlpatterns = [
    path("", home, name="home"),
    path("api/v1/account/lookup/", account_lookup_api, name="account_lookup_api"),
    path("healthz", healthcheck, name="healthcheck"),
    path("receipts", product_detail, name="product_detail"),
    path("receipts/pdf", receipts_pdf, name="receipts_pdf"),
]
