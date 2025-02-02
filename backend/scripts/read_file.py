import pandas as pd
from io import StringIO


def read_optima(file):
    df = pd.read_excel(file, header=4)
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


def read_pay24(file):
    df = pd.read_excel(file, header=3)
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


def read_quickpay(file):
    file.seek(0)
    raw_data = file.read()
    try:
        decoded_data = raw_data.decode('cp1251', errors='replace') 
        df = pd.read_csv(StringIO(decoded_data), sep=';')
    except UnicodeDecodeError:
        raise ValueError("Файл имеет некорректную кодировку.")
    
    df.columns = df.columns.str.strip()  
    df.columns = df.columns.str.replace(' ', '') 
    try:
        data = df[['Датаоплаты', 'Лицевойсчёт', 'Суммаплатежа']]
    except KeyError as e:
        print(f"Ошибка: {e}")
        return []

    data = data[~data['Суммаплатежа'].str.contains('ИТОГО', na=False)]
    data = data.dropna()
    data['Суммаплатежа'] = pd.to_numeric(data['Суммаплатежа'], errors='coerce')
    data = data.rename(columns={'Лицевойсчёт': 'Лицевой счет', 'Суммаплатежа': 'Сумма', 'Датаоплаты': 'Дата'})

    return data.to_dict(orient='records')


def read_umai(file):
    df = pd.read_excel(file, header=4)
    df.columns = df.columns.str.strip()
    df_cleaned = df.dropna(subset=['Лицевой счет', 'Сумма', 'Дата оплаты'])
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