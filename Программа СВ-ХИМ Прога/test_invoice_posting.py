#!/usr/bin/env python3
"""Тест проведения требований-накладных: черновик и проведение."""
import os
import sys
import tempfile

# Работаем из директории проекта
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)
sys.path.insert(0, project_dir)

from modules.database import DatabaseManager


def main():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    try:
        db = DatabaseManager(db_path=db_path)

        # Создаём складскую позицию для списания
        db.execute_query(
            "INSERT INTO warehouse (component_code, component_name, current_stock, unit) VALUES (?, ?, ?, ?)",
            ('TEST-01', 'Тестовый компонент', 500.0, 'кг')
        )
        db.conn.commit()

        # 1. Создаём черновик (без проведения)
        invoice_id = db.create_invoice(
            invoice_number='ТН-ТЕСТ-0001',
            operation_type='write_off',
            source_location='Основной склад',
            destination_location='',
            notes='Тест черновика',
            items=[{'component_code': 'TEST-01', 'component_name': 'Тестовый компонент', 'quantity': 100.0, 'unit': 'кг'}],
            post=False
        )
        print(f'[OK] Создан черновик ID={invoice_id}')

        inv = db.get_invoice_details(invoice_id)
        assert inv['status'] == 'draft', f"Ожидался статус draft, получен {inv['status']}"
        print(f'[OK] Статус черновика: {inv["status"]}')

        # Остаток не должен измениться
        stock_after_draft = db.execute_query(
            "SELECT current_stock FROM warehouse WHERE component_code = ?", ('TEST-01',)
        )[0]['current_stock']
        assert stock_after_draft == 500.0, f"Остаток после черновика: {stock_after_draft}"
        print(f'[OK] Остаток после черновика не изменился: {stock_after_draft}')

        # 2. Проводим черновик
        result = db.post_invoice(invoice_id)
        assert result is True, f"post_invoice вернул {result}"
        print('[OK] post_invoice вернул True')

        inv = db.get_invoice_details(invoice_id)
        assert inv['status'] == 'active', f"Ожидался статус active, получен {inv['status']}"
        print(f'[OK] Статус после проведения: {inv["status"]}')

        stock_after_post = db.execute_query(
            "SELECT current_stock FROM warehouse WHERE component_code = ?", ('TEST-01',)
        )[0]['current_stock']
        assert stock_after_post == 400.0, f"Остаток после проведения: {stock_after_post}"
        print(f'[OK] Остаток после проведения: {stock_after_post}')

        # 3. Повторное проведение должно вернуть False
        second = db.post_invoice(invoice_id)
        assert second is False, f"Повторное проведение вернуло {second}"
        print('[OK] Повторное проведение отклонено')

        # 4. Проверка отрицательных остатков при проведении
        try:
            db.create_invoice(
                invoice_number='ТН-ТЕСТ-0002',
                operation_type='write_off',
                source_location='Основной склад',
                destination_location='',
                notes='Тест отрицательного остатка',
                items=[{'component_code': 'TEST-01', 'component_name': 'Тестовый компонент', 'quantity': 1000.0, 'unit': 'кг'}],
                post=True
            )
            assert False, "Должно было быть ValueError"
        except ValueError:
            print('[OK] Контроль отрицательных остатков работает')

        print('\nВсе тесты пройдены.')
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


if __name__ == '__main__':
    main()
