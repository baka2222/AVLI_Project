from django.urls import path
from .views import product_detail

urlpatterns = [
    path("receipts", product_detail, name="product_detail"),
]