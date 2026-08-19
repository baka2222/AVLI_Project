from django.urls import path

from .views import product_detail, receipts_pdf

urlpatterns = [
    path("receipts", product_detail, name="product_detail"),
    path("receipts/pdf", receipts_pdf, name="receipts_pdf"),
]
