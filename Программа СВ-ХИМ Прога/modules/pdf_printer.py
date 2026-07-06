# modules/pdf_printer.py
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, Color
from modules.database import db_manager
from modules.logger import system_logger
import tkinter as tk
from tkinter import messagebox


class PDFPrinter:
    """Класс для создания PDF карты загрузки по шаблону"""

    def __init__(self):
        self.logger = system_logger.get_logger('PDFPrinter')
        self.setup_fonts()

    def setup_fonts(self):
        """Настройка шрифтов для поддержки русского языка"""
        try:
            # Попытка зарегистрировать стандартные шрифты
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
        except:
            try:
                # Альтернативные пути к шрифтам
                pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
            except:
                self.logger.warning("Не удалось загрузить кастомные шрифты, будут использованы стандартные")

    def create_loading_card_pdf(self, card_id, output_path):
        """Создание PDF карты загрузки по шаблону"""
        try:
            self.logger.info(f"Создание PDF для карты загрузки ID: {card_id}")

            # Получаем данные карты
            card = db_manager.get_loading_card_details(card_id)
            if not card:
                raise ValueError(f"Карта с ID {card_id} не найдена")

            components = db_manager.get_card_components(card_id)

            # Создаем PDF документ
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4

            # Настраиваем шрифты
            try:
                c.setFont("Arial-Bold", 14)
            except:
                c.setFont("Helvetica-Bold", 14)

            # ====== ЗАГОЛОВОК ======
            c.drawString(30 * mm, height - 30 * mm, "Технологическая карта производства масла")

            # ====== ОБЩИЕ ДАННЫЕ ======
            c.setFont("Helvetica", 10)

            # Дата и подпись
            current_date = datetime.now().strftime("%d.%m.%Y")
            c.drawString(140 * mm, height - 40 * mm, "Карту выдал:")
            c.drawString(160 * mm, height - 40 * mm, "_________________")
            c.drawString(140 * mm, height - 45 * mm, f"дата: {current_date}")

            # Таблица общих данных
            table_y = height - 60 * mm
            self.draw_table_header(c, table_y, ["Цех", "Реактор", "Замес", "Размер партии, кг", "Дата выдачи"])

            # Данные в таблице
            c.setFont("Helvetica", 10)
            c.drawString(30 * mm, table_y - 7 * mm, card.get('reactor', 'Р-1'))
            c.drawString(55 * mm, table_y - 7 * mm, card.get('reactor', 'Р-1'))
            c.drawString(75 * mm, table_y - 7 * mm, card.get('card_name', ''))
            c.drawString(95 * mm, table_y - 7 * mm, str(card.get('batch_quantity', 1000)))
            c.drawString(130 * mm, table_y - 7 * mm, current_date)

            # ====== ТАБЛИЦА КОМПОНЕНТОВ ======
            table_y = table_y - 20 * mm
            self.draw_components_table(c, table_y, components, card.get('batch_quantity', 1000))

            # ====== БЛОК ВРЕМЕНИ ======
            time_y = table_y - 60 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(30 * mm, time_y, "ВРЕМЯ ВКЛЮЧЕНИЯ ЦИРКУЛЯЦИИ")
            c.drawString(30 * mm, time_y - 7 * mm, "ВРЕМЯ ВКЛЮЧЕНИЯ НАГРЕВА")
            c.drawString(30 * mm, time_y - 14 * mm, "ВРЕМЯ ОТБОРА ПРОБЫ НА ВЯЗКОСТЬ БАЗОВОЙ СМЕСИ")
            c.drawString(30 * mm, time_y - 21 * mm,
                         "ВРЕМЯ ОТБОРА ПРОБЫ НА ГОТОВНОСТЬ, ОТКЛЮЧЕНИЕ ПЕРЕМЕШИВАНИЯ И НАГРЕВА")

            # Вязкость
            c.drawString(30 * mm, time_y - 31 * mm, "Вязкость базовой смеси расчетная =")
            c.drawString(30 * mm, time_y - 38 * mm, "Вязкость базовой смеси фактическая =")

            # ====== РЕЗУЛЬТАТЫ ИСПЫТАНИЙ ======
            table_y = time_y - 55 * mm
            self.draw_tests_table(c, table_y)

            # ====== ПОДПИСИ ======
            signatures_y = table_y - 35 * mm
            c.setFont("Helvetica", 10)
            c.drawString(30 * mm, signatures_y, "СКАЧАЛИ В Е№")
            c.drawString(110 * mm, signatures_y, "_________________")
            c.drawString(30 * mm, signatures_y - 7 * mm, "Аппаратчик")
            c.drawString(110 * mm, signatures_y - 7 * mm, "_________________")
            c.drawString(140 * mm, signatures_y - 7 * mm, "дата")
            c.drawString(160 * mm, signatures_y - 7 * mm, current_date)

            c.save()

            self.logger.info(f"PDF успешно создан: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка создания PDF: {e}")
            return False

    def draw_table_header(self, c, y, headers):
        """Рисование заголовка таблицы"""
        c.setFont("Helvetica-Bold", 10)
        x_positions = [30, 55, 75, 95, 130]  # в мм

        for i, header in enumerate(headers):
            c.drawString(x_positions[i] * mm, y, header)

        # Линия под заголовком
        c.line(30 * mm, y - 2 * mm, 180 * mm, y - 2 * mm)

    def draw_components_table(self, c, start_y, components, batch_quantity):
        """Рисование таблицы компонентов"""
        # Заголовок таблицы компонентов
        headers = [
            "Наименование компонентов", "Рецептура", "На реактор, кг",
            "№ Емкости, партии присадки", "Факт, кг", "корректировка",
            "Темп., °С", "Продолжительность", "время начала загрузки",
            "время окончания загрузки"
        ]

        # Упрощенная таблица с основными данными
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30 * mm, start_y, "Наименование компонентов")
        c.drawString(70 * mm, start_y, "Процент, %")
        c.drawString(90 * mm, start_y, "Расчетная масса, кг")
        c.drawString(120 * mm, start_y, "Фактическая масса, кг")

        c.line(30 * mm, start_y - 1 * mm, 180 * mm, start_y - 1 * mm)

        # Данные компонентов
        c.setFont("Helvetica", 9)
        current_y = start_y - 6 * mm
        total_mass = 0

        for i, comp in enumerate(components[:10]):  # максимум 10 компонентов как в шаблоне
            if i >= 10:  # Ограничение по количеству строк в шаблоне
                break

            # Номер строки
            c.drawString(25 * mm, current_y, str(i + 1))

            # Наименование (сокращаем если слишком длинное)
            name = comp['component_name']
            if len(name) > 20:
                name = name[:17] + "..."
            c.drawString(30 * mm, current_y, name)

            # Процент
            percentage = comp['percentage']
            c.drawString(70 * mm, current_y, f"{percentage:.2f}")

            # Расчетная масса
            calculated_mass = comp['calculated_mass']
            c.drawString(90 * mm, current_y, f"{calculated_mass:.2f}")

            # Фактическая масса (оставляем пустым для заполнения вручную)
            c.drawString(120 * mm, current_y, "_________")

            total_mass += calculated_mass
            current_y -= 5 * mm

        # Итоговая строка
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30 * mm, current_y, "ИТОГО")
        c.drawString(90 * mm, current_y, f"{total_mass:.2f}")
        c.drawString(120 * mm, current_y, "_________")

        # Вторая итоговая строка (как в шаблоне)
        current_y -= 5 * mm
        c.drawString(30 * mm, current_y, "ИТОГО")
        c.drawString(90 * mm, current_y, f"{batch_quantity:.2f}")

    def draw_tests_table(self, c, start_y):
        """Рисование таблицы результатов испытаний"""
        # Заголовок
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30 * mm, start_y, "Результаты испытаний")

        # Подзаголовки
        headers_y = start_y - 6 * mm
        c.drawString(30 * mm, headers_y, "Стадия")
        c.drawString(50 * mm, headers_y, "КВ при 100°С")
        c.drawString(70 * mm, headers_y, "КВ при 40°С")
        c.drawString(90 * mm, headers_y, "ИВ")
        c.drawString(110 * mm, headers_y, "CCS")
        c.drawString(130 * mm, headers_y, "Тзаст")

        # Колонки "норма" и "факт"
        norm_y = headers_y - 4 * mm
        c.setFont("Helvetica", 8)
        c.drawString(52 * mm, norm_y, "норма")
        c.drawString(58 * mm, norm_y, "факт")
        c.drawString(72 * mm, norm_y, "норма")
        c.drawString(78 * mm, norm_y, "факт")
        c.drawString(92 * mm, norm_y, "норма")
        c.drawString(98 * mm, norm_y, "факт")
        c.drawString(112 * mm, norm_y, "норма")
        c.drawString(118 * mm, norm_y, "факт")
        c.drawString(132 * mm, norm_y, "норма")
        c.drawString(138 * mm, norm_y, "факт")

        # Данные (пустые для заполнения)
        data_y = norm_y - 6 * mm
        stages = ["готовое масло", "не норм,", "корректировка №1",
                  "определение", "корректировка №2", "обязательно"]

        for i, stage in enumerate(stages):
            c.drawString(30 * mm, data_y, stage)

            # Пустые поля для данных
            for x in [52, 58, 72, 78, 92, 98, 112, 118, 132, 138]:
                c.drawString(x * mm, data_y, "_______")

            data_y -= 4 * mm

        # Соответствие нормам
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30 * mm, data_y - 4 * mm, "Соответствие продукции требуемым нормам ТУ, ГОСТ (да/нет)")
        c.drawString(140 * mm, data_y - 4 * mm, "_______")

        # Подпись лаборанта
        c.drawString(30 * mm, data_y - 10 * mm, "Подпись лаборанта")
        c.drawString(140 * mm, data_y - 10 * mm, "_________________")


# Глобальный экземпляр принтера
pdf_printer = PDFPrinter()