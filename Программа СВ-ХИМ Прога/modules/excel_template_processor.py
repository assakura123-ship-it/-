# modules/excel_template_processor.py
import openpyxl
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, Border, Side
import os
from datetime import datetime


class ExcelTemplateProcessor:
    """Процессор для заполнения шаблона Excel карты загрузки"""

    def __init__(self, template_path=None):
        if template_path is None:
            # По умолчанию ищем шаблон в текущей директории
            template_path = "ШАБЛОН КАРТЫ.xlsx"
        self.template_path = template_path
        self.wb = None
        self.ws = None

    def load_template(self, sheet_name="п."):
        """Загрузить шаблон Excel"""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Шаблон не найден: {self.template_path}")

        self.wb = load_workbook(self.template_path)

        # Используем указанный лист или первый по умолчанию
        if sheet_name in self.wb.sheetnames:
            self.ws = self.wb[sheet_name]
        else:
            self.ws = self.wb.active

        return self.wb, self.ws

    def fill_basic_info(self, data):
        """Заполнить базовую информацию"""
        # Технологическая карта производства масла
        self.ws['A1'] = f"Технологическая карта производства {data.get('product_name', 'масла')}"

        # Цех, Реактор, Замес, Размер партии
        self.ws['E4'] = data.get('workshop', '')  # Цех
        self.ws['F4'] = data.get('reactor', '')  # Реактор
        self.ws['G4'] = data.get('batch_type', 'Замес')  # Замес
        self.ws['H4'] = data.get('batch_quantity', '')  # Размер партии

        # Дата выдачи
        if 'issue_date' in data:
            self.ws['I4'] = data['issue_date']

        # Партия №
        self.ws['F6'] = data.get('batch_number', '')

        # Дата начала приготовления
        self.ws['A7'] = data.get('start_date', '')

    def fill_components(self, components):
        """Заполнить таблицу компонентов (строки 10-19)"""
        start_row = 10

        for i, comp in enumerate(components):
            row = start_row + i
            if row > 19:  # Ограничение по строкам в шаблоне
                break

            # Наименование компонентов (столбец A)
            self.ws[f'A{row}'] = comp.get('name', '')

            # Рецептура На 100% (столбец D)
            self.ws[f'D{row}'] = comp.get('percentage', 0)

            # На реактор, кг (столбец E)
            self.ws[f'E{row}'] = comp.get('mass', 0)

            # № Емкости, партии присадки (столбец F)
            self.ws[f'F{row}'] = comp.get('container_number', '')

            # Факт, кг (столбец G)
            self.ws[f'G{row}'] = comp.get('actual_mass', '')

            # корректировка (столбец H)
            self.ws[f'H{row}'] = comp.get('correction', '')

            # Темп., °С (столбец I)
            self.ws[f'I{row}'] = comp.get('temperature', '')

            # время начала загрузки (столбец J)
            self.ws[f'J{row}'] = comp.get('start_time', '')

            # время окончания загрузки (столбец K)
            self.ws[f'K{row}'] = comp.get('end_time', '')

    def fill_time_parameters(self, time_data):
        """Заполнить временные параметры"""
        # ВРЕМЯ ВКЛЮЧЕНИЯ ЦИРКУЛЯЦИИ
        self.ws['A23'] = time_data.get('circulation_start', '')

        # ВРЕМЯ ВКЛЮЧЕНИЯ НАГРЕВА
        self.ws['D23'] = time_data.get('heating_start', '')

        # ВРЕМЯ ОТБОРА ПРОБЫ НА ВЯЗКОСТЬ БАЗОВОЙ СМЕСИ
        self.ws['G23'] = time_data.get('viscosity_test_time', '')

        # ВРЕМЯ ОТБОРА ПРОБЫ НА ГОТОВНОСТЬ
        self.ws['J23'] = time_data.get('readiness_test_time', '')

        # Вязкость расчетная и фактическая
        self.ws['A25'] = f"Вязкость базовой смеси расчетная = {time_data.get('calculated_viscosity', '')}"
        self.ws['A26'] = f"Вязкость базовой смеси фактическая = {time_data.get('actual_viscosity', '')}"

    def fill_test_results(self, test_results):
        """Заполнить результаты испытаний"""
        # Готовое масло
        row = 31
        self.ws[f'B{row}'] = test_results.get('kv_100_norm', '')
        self.ws[f'C{row}'] = test_results.get('kv_100_actual', '')
        self.ws[f'E{row}'] = test_results.get('kv_40_norm', '')
        self.ws[f'F{row}'] = test_results.get('kv_40_actual', '')
        self.ws[f'H{row}'] = test_results.get('iv_norm', '')
        self.ws[f'I{row}'] = test_results.get('iv_actual', '')
        self.ws[f'K{row}'] = test_results.get('ccs_norm', '')
        self.ws[f'L{row}'] = test_results.get('ccs_actual', '')

    def fill_signatures(self, signatures):
        """Заполнить подписи"""
        # Соответствие нормам
        self.ws['A35'] = signatures.get('compliance', '')

        # Подпись лаборанта
        self.ws['I35'] = signatures.get('lab_technician', '')

        # Аппаратчик
        self.ws['F37'] = signatures.get('operator', '')

        # Дата
        self.ws['H37'] = signatures.get('completion_date', '')

    def save(self, output_path):
        """Сохранить заполненный шаблон"""
        if self.wb:
            self.wb.save(output_path)

    def create_from_card_data(self, card_data, output_path):
        """Создать файл из данных карты"""
        try:
            # Загружаем шаблон
            self.load_template()

            # Заполняем базовую информацию
            self.fill_basic_info({
                'product_name': card_data.get('product_name', ''),
                'workshop': card_data.get('workshop', '1 цех'),
                'reactor': card_data.get('reactor', 'Р-1'),
                'batch_quantity': card_data.get('batch_quantity', 1000),
                'issue_date': datetime.now().strftime('%d.%m.%Y'),
                'batch_number': card_data.get('batch_number', f"П-{datetime.now().strftime('%Y%m%d')}"),
                'start_date': datetime.now().strftime('%d.%m.%Y'),
            })

            # Заполняем компоненты
            self.fill_components(card_data.get('components', []))

            # Заполняем временные параметры
            self.fill_time_parameters(card_data.get('time_data', {}))

            # Заполняем результаты испытаний
            self.fill_test_results(card_data.get('test_results', {}))

            # Заполняем подписи
            self.fill_signatures(card_data.get('signatures', {}))

            # Сохраняем
            self.save(output_path)
            return True

        except Exception as e:
            print(f"Ошибка создания Excel: {e}")
            return False