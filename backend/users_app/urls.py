from django.urls import path

from .views import (
    account_lookup_api,
    healthcheck,
    home,
    monthly_report,
    monthly_report_excel,
    monthly_report_pdf,
    product_detail,
    receipts_pdf,
)

urlpatterns = [
    path("", home, name="home"),
    path("api/v1/account/lookup/", account_lookup_api, name="account_lookup_api"),
    path("healthz", healthcheck, name="healthcheck"),
    path("receipts", product_detail, name="product_detail"),
    path("receipts/pdf", receipts_pdf, name="receipts_pdf"),
    path("reports/monthly", monthly_report, name="monthly_report"),
    path("reports/monthly/pdf", monthly_report_pdf, name="monthly_report_pdf"),
    path("reports/monthly/excel", monthly_report_excel, name="monthly_report_excel"),
]
