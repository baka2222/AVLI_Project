import pandas as pd
import os
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from users_app.models import PaymentModel, UserModel


def read_optima():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, '../files/optima.xls')
    df = pd.read_excel(file_path, header=4)
    df.columns = df.columns.str.strip()
    df_cleaned = df.dropna(subset=['Лицевой счет', 'Сумма', 'Дата'])
    df_cleaned = df_cleaned[~df_cleaned['Лицевой счет'].str.contains('Итог', na=False)]
    df_cleaned['Сумма'] = pd.to_numeric(df_cleaned['Сумма'], errors='coerce')
    df_cleaned = df_cleaned.dropna(subset=['Сумма', 'Дата'])
    extracted_data = df_cleaned[['Лицевой счет', 'Сумма', 'Дата']]
    result_as_list = [
        {
            'Лицевой счет': row['Лицевой счет'],
            'Сумма': row['Сумма'],
            'Дата': row['Дата'].strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(row['Дата']) else None
        }
        for row in extracted_data.to_dict(orient='records')
    ]

    return result_as_list


def read_pay24():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, '../files/pay24.xls')
    df = pd.read_excel(file_path, header=3)
    df.columns = df.columns.str.strip()
    df_cleaned = df.dropna(subset=['Реквизит', 'Сумма', 'Дата и время'])
    df_cleaned = df_cleaned[~df_cleaned['Реквизит'].str.contains('Итог', na=False)]
    df_cleaned['Сумма'] = pd.to_numeric(df_cleaned['Сумма'], errors='coerce')
    df_cleaned = df_cleaned.dropna(subset=['Сумма', 'Дата и время'])
    extracted_data = df_cleaned[['Реквизит', 'Сумма', 'Дата и время']]
    result_as_list = [
        {
            'Лицевой счет': row['Реквизит'],
            'Сумма': row['Сумма'],
            'Дата': row['Дата и время']
        }
        for row in extracted_data.to_dict(orient='records')
    ]

    return result_as_list


def read_quickpay():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, '../files/quickpay.csv')
    df = pd.read_csv(file_path, sep=';', encoding='cp1251')
    data = df[['Дата оплаты', 'Лицевой счёт', 'Сумма платежа']]
    data = data[~data['Сумма платежа'].str.contains('ИТОГО', na=False)]
    data = data.dropna()
    data['Сумма платежа'] = pd.to_numeric(data['Сумма платежа'], errors='coerce')
    data = data.rename(columns={'Лицевой счёт': 'Лицевой счет', 'Сумма платежа': 'Сумма', 'Дата оплаты': 'Дата'})
    data_dict = data.to_dict(orient='records')

    return data_dict


def read_umai():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, '../files/umai.xlsx')
    df = pd.read_excel(file_path, header=4)
    df.columns = df.columns.str.strip()
    df_cleaned = df.dropna(subset=['Лицевой счет', 'Сумма', 'Дата оплаты'])
    df_cleaned = df_cleaned[~df_cleaned['Лицевой счет'].str.contains('Итог', na=False)]
    df_cleaned['Сумма'] = pd.to_numeric(df_cleaned['Сумма'], errors='coerce')
    df_cleaned = df_cleaned.dropna(subset=['Сумма', 'Дата оплаты'])
    extracted_data = df_cleaned[['Лицевой счет', 'Сумма', 'Дата оплаты']]
    result_as_list = [
        {
            'Лицевой счет': row['Лицевой счет'],
            'Сумма': row['Сумма'],
            'Дата': row['Дата оплаты']
        }
        for row in extracted_data.to_dict(orient='records')
    ]

    return result_as_list


def save_dbf_data_to_model():
    data = []

    data += read_optima()
    data += read_pay24()
    data += read_quickpay()
    data += read_umai()

    for record in data:
        user = UserModel.objects.get(ls=record['Лицевой счет'])
        pm = PaymentModel(
            date=record['Дата'],
            payment=record['Сумма'],
            user=user
        )
        pm.save() 


save_dbf_data_to_model()