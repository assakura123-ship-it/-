# modules/invoice_excel.py
"""
Экспорт требования-накладной в Excel.

Вынесено в отдельный модуль, чтобы не дублировать код построения Excel-файла
в интерфейсе (ручной экспорт из диалога создания, экспорт из списка накладных).
"""
import os
from datetime import datetime

import pandas as pd

from modules.logger import system_logger

logger = system_logger.get_logger('InvoiceExcel')


OP_LABELS = {
    'write_off': 'Списание',
    'transfer': 'Перемещение',
    'receipt': 'Приход',
}

STATUS_LABELS = {
    'active': 'Активна',
    'draft': 'Черновик',
    'reverted': 'Отменена',
}


def default_invoice_excel_filename(invoice: dict) -> str:
    """Сформировать имя файла по умолчанию для Excel-бланка накладной."""
    number = str(invoice.get('invoice_number', 'без_номера')).replace('/', '-')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"Накладная_{number}_{stamp}.xlsx"


def get_invoices_dir(base_dir: str = None) -> str:
    """Вернуть (и создать при необходимости) папку для сохранённых накладных."""
    base_dir = base_dir or os.getcwd()
    invoices_dir = os.path.join(base_dir, "Накладные")
    os.makedirs(invoices_dir, exist_ok=True)
    return invoices_dir


def generate_invoice_excel(invoice: dict, items: list, output_path: str) -> bool:
    """Построить Excel-бланк требования-накладной и сохранить его в output_path.

    invoice: словарь с полями requirement_invoices (invoice_number,
        operation_type, source_location, destination_location, notes,
        status, created_date, ...)
    items: список позиций invoice_items (component_code, component_name,
        quantity, unit)

    Возвращает True при успехе.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)

        op_label = OP_LABELS.get(invoice.get('operation_type'), str(invoice.get('operation_type', '')))
        status_label = STATUS_LABELS.get(invoice.get('status'), invoice.get('status', ''))
        created_date = invoice.get('created_date') or ''

        info_rows = [
            ['ТРЕБОВАНИЕ-НАКЛАДНАЯ', ''],
            ['Номер:', invoice.get('invoice_number', '')],
            ['Тип операции:', op_label],
            ['Откуда:', invoice.get('source_location') or '—'],
            ['Куда:', invoice.get('destination_location') or '—'],
            ['Дата:', created_date[:16] if created_date else '—'],
            ['Статус:', status_label],
            ['Примечание:', invoice.get('notes') or '—'],
        ]
        info_df = pd.DataFrame(info_rows, columns=['Параметр', 'Значение'])

        items_rows = []
        total_qty = 0.0
        for i, item in enumerate(items, 1):
            qty = float(item.get('quantity', 0) or 0)
            items_rows.append({
                '№': i,
                'Код': item.get('component_code', ''),
                'Наименование': item.get('component_name', ''),
                'Количество': qty,
                'Ед. изм.': item.get('unit', 'кг'),
            })
            total_qty += qty

        items_df = pd.DataFrame(items_rows)
        total_df = pd.DataFrame([{
            '№': '',
            'Код': '',
            'Наименование': 'ИТОГО',
            'Количество': total_qty,
            'Ед. изм.': 'кг',
        }])

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name='Накладная', index=False)
            ws = writer.sheets['Накладная']
            ws.column_dimensions['A'].width = 22
            ws.column_dimensions['B'].width = 45

            start_row = len(info_df) + 2
            items_df.to_excel(writer, sheet_name='Накладная', startrow=start_row, index=False)
            total_df.to_excel(
                writer, sheet_name='Накладная',
                startrow=start_row + len(items_df) + 1, index=False
            )

            ws2 = writer.sheets['Накладная']
            ws2.column_dimensions['D'].width = 15
            ws2.column_dimensions['E'].width = 12

        logger.info(f"Excel накладной сохранён: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Ошибка создания Excel накладной: {e}")
        return False
