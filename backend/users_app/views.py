from django.shortcuts import render
from .models import UserModel
from datetime import datetime


months = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


def get_previous_month(date):
    previous_month = date.month - 1 if date.month > 1 else 12
    year = date.year if date.month > 1 else date.year - 1
    return previous_month, year


def product_detail(request):
    receipts = []
    receipts += UserModel.objects.all()
    date = datetime.now()
    for i in receipts:
        ls_numeric = ''.join(filter(str.isdigit, i.ls))
        i.barcode = f'http://127.0.0.1:8000/media/images/barcode_{ls_numeric}.png'
        i.rate_sum = round(i.rate_sum, 1)
        i.last_dept = round(i.last_dept, 1)
        i.date = f"{months[date.month]} {date.year} г."
        i.total = round(i.current_dept, 1)
        previous_month, _ = get_previous_month(date)
        i.current_date = f"на 1-е {months[date.month]}"
        i.previous_date = f"на 1-е {months[previous_month]}"
        if i.saldo < 0:
            i.saldo = 0.0
    return render(request, "receipt.html", context={'receipts': receipts})
    

