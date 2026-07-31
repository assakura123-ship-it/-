#!/usr/bin/env python3
"""Тест генерации Excel-бланка требования-накладной."""
import os
import sys
import tempfile

project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)
sys.path.insert(0, project_dir)

from modules import invoice_excel


def main():
    invoice = {
        'invoice_number': 'ТН-ТЕСТ-0001',
        'operation_type': 'write_off',
        'source_location': 'Основной склад',
        'destination_location': 'Цех производства',
        'notes': 'Тест Excel-экспорта',
        'status': 'draft',
        'created_date': '2026-07-31 06:43:04',
    }
    items = [
        {'component_code': 'TEST-01', 'component_name': 'Тестовый компонент', 'quantity': 100.0, 'unit': 'кг'},
        {'component_code': 'TEST-02', 'component_name': 'Другой компонент', 'quantity': 25.5, 'unit': 'кг'},
    ]

    fd, output_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    try:
        result = invoice_excel.generate_invoice_excel(invoice, items, output_path)
        assert result is True, "generate_invoice_excel вернул False"
        assert os.path.exists(output_path), f"Файл не создан: {output_path}"
        assert os.path.getsize(output_path) > 0, "Файл пустой"
        print(f'[OK] Excel-бланк создан: {output_path}')
        print(f'[OK] Размер файла: {os.path.getsize(output_path)} байт')
    finally:
        try:
            os.remove(output_path)
        except Exception:
            pass


if __name__ == '__main__':
    main()
