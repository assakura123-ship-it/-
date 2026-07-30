# modules/invoice_pdf.py
"""
Генерация PDF-бланка требования-накладной (списание/перемещение/приход).

Вынесено в отдельный модуль, чтобы:
  - не дублировать код построения PDF в нескольких местах интерфейса
    (ручной экспорт, печать, автосохранение после создания документа);
  - гарантированно использовать шрифт с поддержкой кириллицы — стандартный
    Helvetica у reportlab кириллицу не поддерживает и выводит "кракозябры"
    вместо русского текста.
"""
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from modules.logger import system_logger

logger = system_logger.get_logger('InvoicePDF')

# ---- Регистрация шрифта с поддержкой кириллицы (один раз при импорте) ----
_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONTS_REGISTERED = False


def _register_fonts():
    """Регистрирует DejaVuSans (поддерживает кириллицу) для reportlab.

    Если по каким-то причинам файлы шрифтов не найдены, откатывается на
    стандартный Helvetica (латиница) — чтобы PDF всё равно создавался,
    хоть и без корректного отображения русского текста.
    """
    global _FONT_REGULAR, _FONT_BOLD, _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    regular_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
    bold_path = os.path.join(fonts_dir, 'DejaVuSans-Bold.ttf')

    try:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont('InvoiceFont', regular_path))
            pdfmetrics.registerFont(TTFont('InvoiceFont-Bold', bold_path))
            _FONT_REGULAR = 'InvoiceFont'
            _FONT_BOLD = 'InvoiceFont-Bold'
        else:
            logger.warning(
                "Файлы шрифта DejaVuSans не найдены в modules/fonts — "
                "русский текст в PDF может отображаться некорректно"
            )
    except Exception as e:
        logger.warning(f"Не удалось зарегистрировать шрифт с кириллицей: {e}")
    finally:
        _FONTS_REGISTERED = True


OP_LABELS = {
    'write_off': 'СПИСАНИЕ',
    'transfer': 'ПЕРЕМЕЩЕНИЕ',
    'receipt': 'ПРИХОД',
}

STATUS_LABELS = {
    'active': 'Активна',
    'reverted': 'Отменена',
}


def default_invoice_filename(invoice: dict) -> str:
    """Сформировать имя файла по умолчанию для бланка накладной."""
    number = str(invoice.get('invoice_number', 'без_номера')).replace('/', '-')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"Накладная_{number}_{stamp}.pdf"


def get_invoices_dir(base_dir: str = None) -> str:
    """Вернуть (и создать при необходимости) папку для автосохранённых накладных."""
    base_dir = base_dir or os.getcwd()
    invoices_dir = os.path.join(base_dir, "Накладные")
    os.makedirs(invoices_dir, exist_ok=True)
    return invoices_dir


def generate_invoice_pdf(invoice: dict, items: list, output_path: str) -> bool:
    """Построить PDF-бланк требования-накладной и сохранить его в output_path.

    invoice: словарь с полями requirement_invoices (invoice_number,
        operation_type, source_location, destination_location, notes,
        status, created_date, ...)
    items: список позиций invoice_items (component_code, component_name,
        quantity, unit)

    Возвращает True при успехе.
    """
    try:
        _register_fonts()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)

        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        op_label = OP_LABELS.get(invoice.get('operation_type'), str(invoice.get('operation_type', '')).upper())
        status_label = STATUS_LABELS.get(invoice.get('status'), invoice.get('status', ''))

        # ---- Заголовок ----
        c.setFont(_FONT_BOLD, 16)
        c.drawString(30 * mm, height - 25 * mm,
                     f"ТРЕБОВАНИЕ-НАКЛАДНАЯ №{invoice.get('invoice_number', '')}")

        c.setFont(_FONT_BOLD, 14)
        c.drawString(30 * mm, height - 35 * mm, f"Тип операции: {op_label}")

        c.line(30 * mm, height - 40 * mm, 180 * mm, height - 40 * mm)

        # ---- Информация о документе ----
        c.setFont(_FONT_REGULAR, 10)
        y = height - 48 * mm

        c.drawString(30 * mm, y, f"Откуда: {invoice.get('source_location') or '—'}")
        c.drawString(120 * mm, y, f"Куда: {invoice.get('destination_location') or '—'}")
        y -= 6 * mm

        created_date = invoice.get('created_date') or ''
        c.drawString(30 * mm, y, f"Дата: {created_date[:16] if created_date else '—'}")
        c.drawString(120 * mm, y, f"Статус: {status_label}")

        if invoice.get('notes'):
            y -= 6 * mm
            c.drawString(30 * mm, y, f"Примечание: {invoice['notes']}")

        # ---- Таблица позиций ----
        y -= 10 * mm
        c.setFont(_FONT_BOLD, 9)
        c.drawString(10 * mm, y, "№")
        c.drawString(30 * mm, y, "Код")
        c.drawString(80 * mm, y, "Наименование")
        c.drawString(150 * mm, y, "Кол-во")
        c.drawString(175 * mm, y, "Ед.")

        c.line(10 * mm, y - 1 * mm, 190 * mm, y - 1 * mm)
        y -= 6 * mm

        c.setFont(_FONT_REGULAR, 9)
        total_qty = 0.0
        for i, item in enumerate(items, 1):
            if y < 35 * mm:
                c.showPage()
                y = height - 30 * mm
                c.setFont(_FONT_REGULAR, 9)

            c.drawString(12 * mm, y, str(i))
            c.drawString(30 * mm, y, str(item.get('component_code', '')))

            name = str(item.get('component_name', ''))
            if len(name) > 34:
                name = name[:31] + "..."
            c.drawString(80 * mm, y, name)

            qty = float(item.get('quantity', 0) or 0)
            c.drawRightString(168 * mm, y, f"{qty:.2f}")
            c.drawString(175 * mm, y, str(item.get('unit', 'кг')))
            total_qty += qty
            y -= 5 * mm

        # ---- Итог ----
        c.line(10 * mm, y - 1 * mm, 190 * mm, y - 1 * mm)
        y -= 6 * mm
        c.setFont(_FONT_BOLD, 10)
        c.drawString(30 * mm, y, f"ИТОГО позиций: {len(items)}")
        c.drawRightString(168 * mm, y, f"{total_qty:.2f}")

        # ---- Подписи ----
        y -= 20 * mm
        if y < 25 * mm:
            c.showPage()
            y = height - 40 * mm

        c.setFont(_FONT_REGULAR, 10)
        if invoice.get('operation_type') == 'receipt':
            c.drawString(30 * mm, y, "Сдал: _________________")
            c.drawString(120 * mm, y, "Принял: _________________")
        else:
            c.drawString(30 * mm, y, "Отпустил: _________________")
            c.drawString(120 * mm, y, "Получил: _________________")
        y -= 8 * mm
        c.drawString(30 * mm, y, f"Дата: {datetime.now().strftime('%d.%m.%Y')}")

        c.save()

        logger.info(f"PDF накладной сохранён: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Ошибка создания PDF накладной: {e}")
        return False
