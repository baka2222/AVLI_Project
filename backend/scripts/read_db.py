from dbfread import DBF
import os
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from users_app.models import UserModel


def get_dbf_data():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, '../files/BD_AVLI0624.dbf')
    table = DBF(file_path, encoding='cp866') 
    records = [dict(record) for record in table]
    
    return records


def save_dbf_data_to_model():
    dbf_data = get_dbf_data() 

    for record in dbf_data:
        user = UserModel(
            ls=record['LS'],
            fio=record['FIO'],
            area=0,
            rate=0,
            address=record['ADDRESS'],
            saldo=-record['BALANCE'],
            phone=record['PHONE']
        )
        user.save() 


save_dbf_data_to_model()
# print(get_dbf_data())