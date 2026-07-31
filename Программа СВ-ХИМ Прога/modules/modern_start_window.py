# modules/modern_start_window.py
import tkinter as tk
from tkinter import (
    Frame, Label, LabelFrame, Listbox, END, StringVar, Entry, Scrollbar,
    BooleanVar, Text
)
from tkinter import messagebox, filedialog, simpledialog
from tkinter import ttk

import os
from datetime import datetime
import pandas as pd

from modules.logger import system_logger, LogLevel
from modules.database import db_manager
from modules.ui_theme import COLORS, FONTS
from modules import invoice_excel
from modules import raw_material_requirement as rm_req
from modules import finished_product_requirement as fp_req
from modules.tabs import FinishedProductsTab


class ToolTip:
    """Простейший tooltip для виджетов ttk/tk"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None

        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(700, self.showtip)  # задержка 0.7 сек

    def unschedule(self):
        _id = self.id
        self.id = None
        if _id:
            self.widget.after_cancel(_id)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify='left',
            background="#FFFFE0",  # тут важно: background=... с '='
            relief='solid',
            borderwidth=1,
            font=('Segoe UI', 8)
        )
        label.pack(ipadx=4, ipady=2)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()




class TabButton:
    """Кнопка одной вкладки в кастомном таб-баре — мягкая, пилюлевидная."""

    def __init__(self, parent, text, tab_id, tab_manager, closable=True):
        self.tab_id = tab_id
        self.tab_manager = tab_manager
        self.colors = tab_manager.colors
        self.fonts = tab_manager.fonts
        self.closable = closable
        self.radius = 16          # сильное скругление для мягкости
        self.height = 32
        self.padding_x = 14
        self.close_area = 26

        self.frame = Frame(parent, bg=self.colors['background'])

        self.canvas = tk.Canvas(
            self.frame,
            height=self.height,
            bg=self.colors['background'],
            highlightthickness=0,
            cursor='hand2'
        )
        self.canvas.pack(side='left')

        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Enter>', self._on_enter)
        self.canvas.bind('<Leave>', self._on_leave)

        self.text = text
        self.selected = False
        self.hovered = False
        self.close_hovered = False

        self._measure_and_draw()

    def _measure_and_draw(self):
        self.frame.update_idletasks()
        font = self.fonts['caption']
        close_width = self.close_area if self.closable else 0
        # Approximate text width: 7px per char for small font
        text_width = max(50, len(self.text) * 7 + self.padding_x * 2 + close_width)
        total_width = text_width + 8
        self.canvas.config(width=total_width)

        self.canvas.delete('all')
        self._draw_background(total_width)
        self.canvas.create_text(
            total_width / 2 - (close_width / 2) + 3,
            self.height / 2 + 1,
            text=self.text,
            font=font,
            fill=self.colors['tab_selected'] if self.selected else self.colors['tab_unselected'],
            anchor='center',
            tags='text'
        )
        if self.closable:
            self.close_id = self.canvas.create_text(
                total_width - 14,
                self.height / 2 + 1,
                text='×',
                font=(font[0], font[1] + 2, 'normal'),
                fill=self.colors['danger'] if self.close_hovered else self.colors['text_muted'],
                anchor='center',
                tags='close'
            )
            self.canvas.tag_bind('close', '<Enter>', self._on_close_enter)
            self.canvas.tag_bind('close', '<Leave>', self._on_close_leave)
            self.canvas.tag_bind('close', '<Button-1>', self._on_close_click)

    def _rounded_capsule(self, x, y, width, height, radius, **kwargs):
        r = min(radius, height / 2)
        points = [
            x + r, y,
            x + width - r, y,
            x + width, y + r,
            x + width, y + height - r,
            x + width - r, y + height,
            x + r, y + height,
            x, y + height - r,
            x, y + r,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_background(self, width):
        if self.selected:
            bg = self.colors['primary_light']
            fg = self.colors['primary']
        else:
            bg = self.colors['hover'] if self.hovered else self.colors['background']
            fg = self.colors['tab_unselected']
        self._rounded_capsule(2, 2, width - 4, self.height - 4, self.radius,
                              fill=bg, outline=fg, width=1, tags='bg')
        self.canvas.tag_lower('bg')

    def _on_click(self, event=None):
        self.tab_manager.select_tab(self.tab_id)

    def _on_enter(self, event=None):
        if self.tab_manager.current_tab != self.tab_id:
            self.hovered = True
            self._measure_and_draw()

    def _on_leave(self, event=None):
        self.hovered = False
        self.close_hovered = False
        self._measure_and_draw()

    def _on_close_enter(self, event=None):
        self.close_hovered = True
        self._measure_and_draw()

    def _on_close_leave(self, event=None):
        self.close_hovered = False
        self._measure_and_draw()

    def _on_close_click(self, event=None):
        self.tab_manager.close_tab(self.tab_id)
        return 'break'

    def set_text(self, text):
        self.text = text
        self._measure_and_draw()

    def select(self):
        self.selected = True
        self._measure_and_draw()

    def deselect(self):
        self.selected = False
        self._measure_and_draw()


class TabManager:
    """Кастомный менеджер вкладок: главная вкладка фиксирована, остальные
    открываются/закрываются как в браузере."""

    def __init__(self, parent, root, colors, fonts, on_tab_change=None, on_tab_close=None):
        self.parent = parent
        self.root = root
        self.colors = colors
        self.fonts = fonts
        self.on_tab_change = on_tab_change
        self.on_tab_close = on_tab_close
        self.current_tab = None
        self.tabs = {}
        self.counter = 0

        # Верхняя панель вкладок — компактная, без лишних отступов
        self.tab_bar = Frame(parent, bg=colors['background'], height=42)
        self.tab_bar.pack(fill='x', side='top')
        self.tab_bar.pack_propagate(False)

        # Разделитель
        self.separator = Frame(parent, height=1, bg=colors['border'])
        self.separator.pack(fill='x', side='top')

        # Область содержимого
        self.content_area = Frame(parent, bg=colors['background'])
        self.content_area.pack(fill='both', expand=True, side='top')

    def add_tab(self, tab_id, text, content_frame, closable=True, select=True):
        """Добавить новую вкладку. Если tab_id уже есть — просто активировать."""
        if tab_id in self.tabs:
            if select:
                self.select_tab(tab_id)
            return self.tabs[tab_id]['frame']

        tab_button = TabButton(self.tab_bar, text, tab_id, self, closable=closable)
        tab_button.frame.pack(side='left', padx=(6, 0), pady=(5, 0))

        content_frame.pack(in_=self.content_area, fill='both', expand=True)
        content_frame.pack_forget()

        self.tabs[tab_id] = {
            'frame': content_frame,
            'button': tab_button,
            'text': text,
            'closable': closable,
        }

        if select or self.current_tab is None:
            self.select_tab(tab_id)

        return content_frame

    def select_tab(self, tab_id):
        if tab_id not in self.tabs:
            return

        for tid, info in self.tabs.items():
            if tid == tab_id:
                info['frame'].pack(fill='both', expand=True)
                info['button'].select()
            else:
                info['frame'].pack_forget()
                info['button'].deselect()

        self.current_tab = tab_id

        if self.on_tab_change:
            self.on_tab_change(tab_id, self.tabs[tab_id]['text'])

    def close_tab(self, tab_id):
        if tab_id not in self.tabs or not self.tabs[tab_id]['closable']:
            return

        if self.on_tab_close:
            self.on_tab_close(tab_id)

        info = self.tabs.pop(tab_id)
        info['button'].frame.destroy()
        info['frame'].destroy()

        if self.current_tab == tab_id:
            if self.tabs:
                self.select_tab(list(self.tabs.keys())[0])

    def get_tab_text(self, tab_id):
        return self.tabs.get(tab_id, {}).get('text', '')

    def set_tab_text(self, tab_id, text):
        if tab_id in self.tabs:
            self.tabs[tab_id]['text'] = text
            self.tabs[tab_id]['button'].set_text(text)

    def get_current_tab(self):
        return self.current_tab


class ModernStartWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Управление Производством MOZER")
        self.root.geometry("1400x900")

        # Современная минималистичная цветовая палитра (см. modules/ui_theme.py)
        self.colors = COLORS
        self.fonts = FONTS

        # Тема 'clam' даёт полный контроль над отрисовкой ttk-виджетов
        # (в отличие от 'vista', который игнорирует часть style.configure на Windows)
        self.root.configure(bg=self.colors['background'])
        self.style = ttk.Style()

        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        # Настройка стилей
        self.configure_styles()

        self.logger = system_logger.get_logger('ModernStartWindow')
        self.logger.info("Инициализация современного интерфейса")

        # Глобальный перехватчик исключений Tkinter — предотвращает закрытие всех окон
        original_rep = self.root.report_callback_exception
        def safe_report(exc, val, tb):
            try:
                self.logger.error(f"Tkinter callback error: {exc.__name__}: {val}")
            except Exception:
                pass
            try:
                original_rep(exc, val, tb)
            except Exception:
                pass
        self.root.report_callback_exception = safe_report

        self.open_editors = {}

        # Переменные для импорт/экспорт и логов
        self.import_file_var = StringVar(value="")
        self.export_path_var = StringVar(value="")
        self.norms_file_var = StringVar(value="")
        self.norms_export_path_var = StringVar(value="")
        self.log_search_var = StringVar(value="")

        self.center_window()
        self.create_widgets()
        self.logger.info("Современный интерфейс успешно инициализирован")

    # ===================== НАСТРОЙКА СТИЛЕЙ =====================

    def configure_styles(self):
        """Настройка стилей в духе современного минимализма."""
        style = self.style
        colors = self.colors
        fonts = self.fonts

        # Общий фон / текст по умолчанию для всех ttk-виджетов
        style.configure(
            ".",
            background=colors['background'],
            foreground=colors['on_background'],
            font=fonts['body']
        )

        # ===== Notebook (вкладки) =====
        style.configure(
            "TNotebook",
            background=colors['background'],
            borderwidth=0,
            tabmargins=[0, 6, 0, 0]
        )
        style.configure(
            "TNotebook.Tab",
            padding=[16, 9],
            font=fonts['body_semibold'],
            background=colors['background'],
            foreground=colors['tab_unselected'],
            borderwidth=0,
            focuscolor=colors['background']
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", colors['background']),
                ("active", colors['background'])
            ],
            foreground=[
                ("selected", colors['tab_selected']),
                ("active", colors['primary'])
            ]
        )

        # ===== Кнопки =====
        def _configure_button(style_name, bg, fg, hover, pressed):
            style.configure(
                style_name,
                padding=[16, 10],
                font=fonts['body_semibold'],
                borderwidth=0,
                relief="flat",
                background=bg,
                foreground=fg,
                focuscolor=bg
            )
            style.map(
                style_name,
                background=[("active", hover), ("pressed", pressed), ("disabled", colors['border'])],
                foreground=[("disabled", colors['text_muted'])]
            )

        _configure_button("Modern.TButton", colors['primary'], colors['text_on_accent'],
                           colors['primary_hover'], colors['primary_pressed'])
        _configure_button("Success.TButton", colors['success'], colors['text_on_accent'],
                           colors['success_hover'], colors['success_pressed'])
        _configure_button("Danger.TButton", colors['danger'], colors['text_on_accent'],
                           colors['danger_hover'], colors['danger_pressed'])
        _configure_button("Warning.TButton", colors['warning'], colors['text_on_accent'],
                           colors['warning_hover'], colors['warning_pressed'])

            # Вторичная кнопка — контурная, на фоне поверхности
        style.configure(
            "Secondary.TButton",
            padding=[16, 10],
            font=fonts['body_semibold'],
            borderwidth=1,
            relief="flat",
            background=colors['surface'],
            foreground=colors['on_surface'],
            bordercolor=colors['border_strong'],
            focuscolor=colors['surface']
        )
        style.map(
            "Secondary.TButton",
            background=[("active", colors['hover']), ("pressed", colors['border'])],
            foreground=[("active", colors['on_surface']), ("pressed", colors['on_surface'])],
            bordercolor=[("active", colors['primary']), ("pressed", colors['primary'])]
        )

        # Компактная кнопка (панели инструментов / тулбары)
        style.configure(
            "Compact.TButton",
            padding=[8, 4],
            font=fonts['caption'],
            borderwidth=0,
            relief="flat",
            background=colors['surface'],
            foreground=colors['on_surface'],
            focuscolor=colors['surface']
        )
        style.map(
            "Compact.TButton",
            background=[("active", colors['hover']), ("pressed", colors['border'])]
        )

        # ===== Поля ввода =====
        style.configure(
            "Modern.TEntry",
            padding=[10, 8],
            relief="flat",
            borderwidth=1,
            bordercolor=colors['border'],
            lightcolor=colors['border'],
            darkcolor=colors['border'],
            fieldbackground=colors['surface'],
            insertcolor=colors['on_surface']
        )
        style.map(
            "Modern.TEntry",
            bordercolor=[("focus", colors['primary'])],
            lightcolor=[("focus", colors['primary'])],
            darkcolor=[("focus", colors['primary'])]
        )

        style.configure(
            "Compact.TEntry",
            padding=[6, 4],
            relief="flat",
            borderwidth=1,
            bordercolor=colors['border'],
            lightcolor=colors['border'],
            darkcolor=colors['border'],
            fieldbackground=colors['surface'],
            font=fonts['caption']
        )
        style.map(
            "Compact.TEntry",
            bordercolor=[("focus", colors['primary'])],
            lightcolor=[("focus", colors['primary'])],
            darkcolor=[("focus", colors['primary'])]
        )

        # ===== Combobox =====
        style.configure(
            "Modern.TCombobox",
            padding=[10, 8],
            relief="flat",
            borderwidth=1,
            bordercolor=colors['border'],
            lightcolor=colors['border'],
            darkcolor=colors['border'],
            fieldbackground=colors['surface'],
            background=colors['surface'],
            arrowcolor=colors['secondary']
        )
        style.map(
            "Modern.TCombobox",
            fieldbackground=[("readonly", colors['surface'])],
            bordercolor=[("focus", colors['primary'])]
        )
        style.configure(
            "TCombobox",
            padding=[8, 6],
            relief="flat",
            borderwidth=1,
            bordercolor=colors['border'],
            fieldbackground=colors['surface'],
            arrowcolor=colors['secondary']
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", colors['surface'])],
            bordercolor=[("focus", colors['primary'])]
        )

        # ===== Checkbutton / Radiobutton =====
        style.configure("Modern.TCheckbutton",
                        font=fonts['body'],
                        background=colors['surface'],
                        foreground=colors['on_surface'])
        style.configure("Modern.TRadiobutton",
                        font=fonts['body'],
                        background=colors['surface'],
                        foreground=colors['on_surface'])

        # ===== Treeview (таблицы) =====
        style.configure(
            "Treeview",
            background=colors['surface'],
            foreground=colors['on_surface'],
            rowheight=30,
            fieldbackground=colors['surface'],
            borderwidth=0,
            relief="flat",
            font=fonts['body']
        )
        # Без разделительной рамки внутри поля — рамку рисует внешний контейнер-карточка
        style.layout("Treeview", [
            ('Treeview.field', {'sticky': 'nswe', 'children': [
                ('Treeview.padding', {'sticky': 'nswe', 'children': [
                    ('Treeview.treearea', {'sticky': 'nswe'})
                ]})
            ]})
        ])

        style.configure(
            "Treeview.Heading",
            background=colors['surface_alt'],
            foreground=colors['text_muted'],
            relief='flat',
            borderwidth=0,
            font=fonts['caption']
        )
        style.map(
            "Treeview.Heading",
            background=[("active", colors['surface_alt'])]
        )
        style.map(
            "Treeview",
            background=[('selected', colors['selected_row'])],
            foreground=[('selected', colors['on_surface'])]
        )

        # Зебра для строк (применяется через tag_configure("odd"/"even", ...) на самих Treeview)
        style.configure("Odd.Treeview", background=colors['surface'])
        style.configure("Even.Treeview", background=colors['row_alt'])

        # ===== Скроллбар (тонкий, минималистичный) =====
        style.configure(
            "Vertical.TScrollbar",
            background=colors['border_strong'],
            troughcolor=colors['background'],
            bordercolor=colors['background'],
            arrowcolor=colors['background'],
            relief='flat',
            arrowsize=12,
            width=10
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", colors['secondary'])]
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=colors['border_strong'],
            troughcolor=colors['background'],
            bordercolor=colors['background'],
            arrowcolor=colors['background'],
            relief='flat',
            arrowsize=12,
            width=10
        )
        style.map(
            "Horizontal.TScrollbar",
            background=[("active", colors['secondary'])]
        )

        # ===== LabelFrame (используется в диалогах заполнения шаблона) =====
        style.configure(
            "TLabelframe",
            background=colors['surface'],
            bordercolor=colors['border'],
            borderwidth=1,
            relief='solid'
        )
        style.configure(
            "TLabelframe.Label",
            background=colors['surface'],
            foreground=colors['on_surface'],
            font=fonts['body_semibold']
        )

    def center_window(self):
        """Центрировать окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def safe_destroy_dialog(self, dialog):
        """Безопасное закрытие диалога — grab_release перед destroy"""
        try:
            if dialog and dialog.winfo_exists():
                try:
                    dialog.grab_release()
                except Exception:
                    pass
                dialog.destroy()
        except Exception:
            pass

    def create_dialog(self, title: str, width: int, height: int, header_color=None):
        """Создание типового диалога с центрированием и опциональной цветной шапкой"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.configure(bg=self.colors['background'])
        dialog.resizable(False, False)

        dialog.update_idletasks()
        try:
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

        if header_color:
            header_frame = Frame(dialog, bg=header_color, height=52)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)
            Label(header_frame, text=title,
                  font=self.fonts['h3'],
                  bg=header_color,
                  fg=self.colors['text_on_accent']).pack(pady=10)

        main_frame = Frame(dialog, bg=self.colors['background'], padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        # Модальность через grab_set — требует grab_release() перед destroy
        try:
            dialog.grab_set()
        except Exception:
            pass

        return dialog, main_frame

    def create_card_frame(self, parent, padding=(20, 20)):
        """Создание "карточки" с белым фоном и тонкой границей"""
        card = Frame(parent,
                     bg=self.colors['surface'],
                     bd=0,
                     highlightbackground=self.colors['border'],
                     highlightthickness=1)
        card.pack(fill='both', expand=True, padx=5, pady=5)
        inner = Frame(card, bg=self.colors['surface'])
        inner.pack(fill='both', expand=True, padx=padding[0], pady=padding[1])
        return inner

    def create_modern_button(self, parent, text, command, color_type='primary', icon=None):
        """
        Создание современной кнопки на базе ttk.Button с готовыми стилями.
        color_type: primary / secondary / success / warning / danger
        """
        style_map = {
            'primary': "Modern.TButton",
            'secondary': "Secondary.TButton",
            'success': "Success.TButton",
            'warning': "Warning.TButton",
            'danger': "Danger.TButton",
        }

        style_name = style_map.get(color_type, "Modern.TButton")
        btn_text = f"{icon + ' ' if icon else ''}{text}"

        btn = ttk.Button(parent,
                         text=btn_text,
                         command=command,
                         style=style_name,
                         cursor="hand2")
        return btn

    # ===================== СОЗДАНИЕ ОСНОВНОГО UI =====================

    def create_widgets(self):
        """Создание виджетов с современным дизайном"""
        try:
            self.logger.info("Создание виджетов с современным дизайном")

            # Единственная верхняя панель: таб-бар + микро-брендинг.
            # Большой заголовок MOZER убран, чтобы освободить полезное пространство.
            top_frame = Frame(self.root, bg=self.colors['surface'], height=42)
            top_frame.pack(fill='x', side='top')
            top_frame.pack_propagate(False)

            # Микро-брендинг слева
            brand_frame = Frame(top_frame, bg=self.colors['surface'])
            brand_frame.pack(side='left', padx=(14, 8), pady=0)

            Label(brand_frame,
                  text="MZ",
                  font=('Segoe UI', 10, 'bold'),
                  bg=self.colors['surface'],
                  fg=self.colors['primary']).pack(side='left')
            Label(brand_frame,
                  text="производство",
                  font=self.fonts['small'],
                  bg=self.colors['surface'],
                  fg=self.colors['text_muted']).pack(side='left', padx=(4, 0))

            # Статус справа — мелкий, строгий
            self.status_label = Label(top_frame,
                                      text="Готов к работе",
                                      font=self.fonts['small'],
                                      bg=self.colors['surface'],
                                      fg=self.colors['text_muted'],
                                      anchor='e')
            self.status_label.pack(side='right', padx=(8, 14))

            separator = Frame(self.root, height=1, bg=self.colors['border'])
            separator.pack(fill='x', side='top')

            main_frame = Frame(self.root, bg=self.colors['background'])
            main_frame.pack(fill='both', expand=True, padx=10, pady=(6, 10))

            # Кастомный менеджер вкладок: главная фиксирована, остальные
            # открываются по кнопкам на главной и закрываются как в браузере.
            self.tab_manager = TabManager(main_frame, self.root, self.colors, self.fonts,
                                           on_tab_change=self.on_tab_changed,
                                           on_tab_close=self.on_tab_closed)

            # Создаем вкладки. Главная открывается всегда, остальные можно
            # открывать из меню быстрого доступа на главной.
            # Примечание: отдельная вкладка "Продукты" удалена — "Номенклатура"
            # теперь является единственным (расширенным) справочником продуктов:
            # каждая позиция дерева номенклатуры одновременно хранит код,
            # наименование и служит записью в products (см. database.py).
            self.create_home_tab()

            footer_frame = Frame(self.root,
                                 bg=self.colors['surface'],
                                 height=40)
            footer_frame.pack(fill='x', side='bottom')
            footer_frame.pack_propagate(False)

            self.date_label = Label(footer_frame,
                                    text="",
                                    font=self.fonts['small'],
                                    bg=self.colors['surface'],
                                    fg=self.colors['text_muted'],
                                    anchor='w')
            self.date_label.pack(side='left', padx=30)

            version_label = Label(footer_frame,
                                  text="Версия 2.0 • SQLite",
                                  font=self.fonts['small'],
                                  bg=self.colors['surface'],
                                  fg=self.colors['text_muted'],
                                  anchor='e')
            version_label.pack(side='right', padx=30)

            self.update_date_time()

            self.logger.info("Виджеты успешно созданы")

        except Exception as e:
            self.logger.error(f"Ошибка создания виджетов: {e}")
            system_logger.log_error_with_traceback("Ошибка создания виджетов", e)
            raise

    # ===================== ВКЛАДКИ =====================

    def create_home_tab(self):
        """Создание главной вкладки в современном стиле (фиксированная)."""
        try:
            home_tab = Frame(self.tab_manager.content_area, bg=self.colors['background'])
            self.tab_manager.add_tab("home", "🏠 Главная", home_tab, closable=False, select=True)

            canvas = tk.Canvas(home_tab, bg=self.colors['background'], highlightthickness=0)
            scrollbar = Scrollbar(home_tab, orient='vertical', command=canvas.yview)
            scrollable_frame = Frame(canvas, bg=self.colors['background'])

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Верхняя секция: компактная строка с датой/днём недели
            header_frame = Frame(scrollable_frame, bg=self.colors['background'])
            header_frame.pack(fill='x', padx=20, pady=(16, 8))

            now = datetime.now()
            weekday_map = {
                0: "Понедельник",
                1: "Вторник",
                2: "Среда",
                3: "Четверг",
                4: "Пятница",
                5: "Суббота",
                6: "Воскресенье",
            }
            weekday = weekday_map[now.weekday()]
            date_str = now.strftime(f"{weekday}, %d.%m.%Y · %H:%M")

            Label(header_frame,
                  text=date_str,
                  font=self.fonts['body'],
                  bg=self.colors['background'],
                  fg=self.colors['text_muted']).pack(anchor='w')

            # Быстрый доступ — строгая, минималистичная сетка
            quick_access_frame = Frame(scrollable_frame, bg=self.colors['background'])
            quick_access_frame.pack(fill='x', padx=28, pady=(20, 24))

            Label(quick_access_frame, text="Быстрый доступ",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background'],
                  fg=self.colors['on_background']).pack(anchor='w', pady=(0, 12))

            # Кнопки открывают модули в новых закрываемых вкладках.
            # Если вкладка уже открыта — просто переключается на неё.
            quick_buttons = [
                ("Создать карту", self.open_editor_tab, 'primary'),
                ("Просмотр карт", self.open_cards_tab, 'secondary'),
                ("Управление складом", self.open_warehouse_tab, 'secondary'),
                ("Потребность сырья", self.open_raw_material_requirement, 'secondary'),
                ("Потребность готовой продукции", self.open_finished_product_requirement, 'secondary'),
                ("Номенклатура", self.open_nomenclature_tab, 'secondary'),
                ("Требование-накладная", self.open_invoice_tab, 'secondary'),
                ("Готовая продукция", self.open_finished_products_tab, 'secondary'),
                ("Импорт/Экспорт", self.open_import_export_tab, 'secondary'),
                ("Системные логи", self.open_logs_tab, 'secondary')
            ]

            grid_frame = Frame(quick_access_frame, bg=self.colors['background'])
            grid_frame.pack(fill='x')

            for i, (text, command, color_type) in enumerate(quick_buttons):
                row = i // 4
                col = i % 4

                btn_frame = Frame(grid_frame, bg=self.colors['background'])
                btn_frame.grid(row=row, column=col, sticky='nsew', padx=6, pady=6)

                btn = self.create_modern_button(btn_frame, text, command, color_type)
                btn.pack(fill='x', expand=True)

                grid_frame.columnconfigure(col, weight=1)

            self.logger.debug("Главная вкладка создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания главной вкладки: {e}")
            raise


    # ===================== ОТКРЫТИЕ ВКЛАДОК =====================

    def open_cards_tab(self):
        """Открыть вкладку 'Карты загрузок' (или переключиться, если уже открыта)."""
        if self.tab_manager.tabs.get('cards'):
            self.tab_manager.select_tab('cards')
            return
        cards_tab = self.create_cards_tab()
        self.tab_manager.add_tab("cards", "📋 Карты загрузок", cards_tab, closable=True, select=True)
        self.load_saved_cards()
        self.logger.info("Открыта вкладка: Карты загрузок")

    def open_warehouse_tab(self):
        """Открыть вкладку 'Склад'."""
        if self.tab_manager.tabs.get('warehouse'):
            self.tab_manager.select_tab('warehouse')
            return
        warehouse_tab = self.create_warehouse_tab()
        self.tab_manager.add_tab("warehouse", "🏭 Склад", warehouse_tab, closable=True, select=True)
        self.load_warehouse_data()
        self.logger.info("Открыта вкладка: Склад")

    def open_nomenclature_tab(self):
        """Открыть вкладку 'Номенклатура'."""
        if self.tab_manager.tabs.get('nomenclature'):
            self.tab_manager.select_tab('nomenclature')
            return
        nom_tab = self.create_nomenclature_tab()
        self.tab_manager.add_tab("nomenclature", "🗂️ Номенклатура", nom_tab, closable=True, select=True)
        self.load_nomenclature_tree()
        self.logger.info("Открыта вкладка: Номенклатура")

    def open_logs_tab(self):
        """Открыть вкладку 'Логи'."""
        if self.tab_manager.tabs.get('logs'):
            self.tab_manager.select_tab('logs')
            return
        logs_tab = self.create_logs_tab()
        self.tab_manager.add_tab("logs", "📊 Логи", logs_tab, closable=True, select=True)
        self.load_log_files()
        self.logger.info("Открыта вкладка: Логи")

    def open_import_export_tab(self):
        """Открыть вкладку 'Импорт/Экспорт'."""
        if self.tab_manager.tabs.get('import_export'):
            self.tab_manager.select_tab('import_export')
            return
        import_tab = self.create_import_export_tab()
        self.tab_manager.add_tab("import_export", "📤 Импорт/Экспорт", import_tab, closable=True, select=True)
        self.logger.info("Открыта вкладка: Импорт/Экспорт")

    def open_finished_products_tab(self):
        """Открыть вкладку 'Готовая продукция'."""
        if self.tab_manager.tabs.get('finished_products'):
            self.tab_manager.select_tab('finished_products')
            return
        fp_tab = self.create_finished_products_tab()
        self.tab_manager.add_tab("finished_products", "📦 Готовая продукция", fp_tab, closable=True, select=True)
        self.logger.info("Открыта вкладка: Готовая продукция")

    def open_invoice_tab(self):
        """Открыть вкладку 'Требование-накладная'."""
        if self.tab_manager.tabs.get('invoice'):
            self.tab_manager.select_tab('invoice')
            return
        inv_tab = self.create_invoice_tab()
        self.tab_manager.add_tab("invoice", "📄 Требование-накладная", inv_tab, closable=True, select=True)
        self.load_invoices_list()
        self.logger.info("Открыта вкладка: Требование-накладная")

    def create_cards_tab(self, parent=None):
        """Создание вкладки карт загрузок в современном стиле"""
        try:
            if parent is None:
                parent = self.tab_manager.content_area
            cards_tab = Frame(parent, bg=self.colors['background'])

            container = Frame(cards_tab, bg=self.colors['background'])
            container.pack(fill='both', expand=True, padx=20, pady=20)

            header_frame = Frame(container, bg=self.colors['background'])
            header_frame.pack(fill='x', pady=(0, 5))

            # Панель кнопок справа
            actions_frame = Frame(header_frame, bg=self.colors['background'])
            actions_frame.pack(side='right')

            refresh_btn = ttk.Button(
                actions_frame,
                text="🔄",
                command=self.load_saved_cards,
                style="Compact.TButton"
            )
            refresh_btn.pack(side='left', padx=3)

            export_btn = ttk.Button(
                actions_frame,
                text="📤",
                command=self.export_selected_card,
                style="Compact.TButton"
            )
            export_btn.pack(side='left', padx=3)

            delete_btn = ttk.Button(
                actions_frame,
                text="🗑️",
                command=self.delete_selected_card,
                style="Compact.TButton"
            )
            delete_btn.pack(side='left', padx=3)

            ToolTip(refresh_btn, "Обновить список карт")
            ToolTip(export_btn, "Экспорт выбранной карты в Excel")
            ToolTip(delete_btn, "Удалить выбранную карту")

            table_inner = self.create_card_frame(container, padding=(10, 10))

            columns = ('ID', 'Название', 'Продукт', 'Рецептура', 'Дата', 'Статус')
            self.cards_tree = ttk.Treeview(table_inner, columns=columns, show='headings', height=15)

            column_widths = [50, 250, 150, 100, 120, 100]
            for idx, col in enumerate(columns):
                self.cards_tree.heading(col, text=col)
                self.cards_tree.column(col, width=column_widths[idx], anchor='center')

            scrollbar = Scrollbar(table_inner, orient='vertical', command=self.cards_tree.yview)
            self.cards_tree.configure(yscrollcommand=scrollbar.set)

            self.cards_tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            self.cards_tree.bind('<Double-Button-1>', lambda e: self.view_card_details())

            self.logger.debug("Вкладка 'Карты загрузок' создана успешно")
            return cards_tab

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки карт: {e}")
            raise

    def create_warehouse_tab(self, parent=None):
        """Создание вкладки склада в современном стиле"""
        try:
            if parent is None:
                parent = self.tab_manager.content_area
            warehouse_tab = Frame(parent, bg=self.colors['background'])

            container = Frame(warehouse_tab, bg=self.colors['background'])
            container.pack(fill='both', expand=True, padx=20, pady=20)

            # Верхняя панель: только поиск
            top_bar = Frame(container, bg=self.colors['background'])
            top_bar.pack(fill='x', pady=(0, 5))

            search_frame = Frame(top_bar, bg=self.colors['background'])
            search_frame.pack(side='left')

            Label(
                search_frame,
                text="Поиск:",
                font=self.fonts['body'],
                bg=self.colors['background'],
                fg=self.colors['secondary']
            ).pack(side='left', padx=(0, 5))

            self.warehouse_search_var = StringVar()
            search_entry = ttk.Entry(
                search_frame,
                textvariable=self.warehouse_search_var,
                width=18,
                style="Compact.TEntry"
            )
            search_entry.pack(side='left')
            search_entry.bind('<KeyRelease>', lambda e: self.filter_warehouse_items())

            # Панель маленьких кнопок ниже поиска
            buttons_frame = Frame(container, bg=self.colors['background'])
            buttons_frame.pack(fill='x', pady=(0, 5))

            refresh_btn = ttk.Button(
                buttons_frame,
                text="🔄",
                command=self.load_warehouse_data,
                style="Compact.TButton"
            )
            refresh_btn.pack(side='left', padx=(0, 5))

            import_btn = ttk.Button(
                buttons_frame,
                text="📥",
                command=self.import_warehouse_from_excel,
                style="Compact.TButton"
            )
            import_btn.pack(side='left', padx=5)

            export_btn = ttk.Button(
                buttons_frame,
                text="📤",
                command=self.export_warehouse_via_dialog,
                style="Compact.TButton"
            )
            export_btn.pack(side='left', padx=5)

            add_btn = ttk.Button(
                buttons_frame,
                text="➕",
                command=self.add_warehouse_item,
                style="Compact.TButton"
            )
            add_btn.pack(side='left', padx=5)

            ToolTip(refresh_btn, "Обновить данные склада")
            ToolTip(import_btn, "Импорт данных склада из Excel")
            ToolTip(export_btn, "Экспорт данных склада в Excel")
            ToolTip(add_btn, "Добавить новую позицию на склад")

            # Отдельная карточка с рамкой вокруг таблицы склада
            table_card = Frame(
                container,
                bg=self.colors['surface'],
                bd=0,
                highlightbackground=self.colors['border'],
                highlightthickness=1
            )
            table_card.pack(fill='both', expand=True, padx=5, pady=5)

            table_inner = Frame(table_card, bg=self.colors['surface'])
            table_inner.pack(fill='both', expand=True, padx=1, pady=1)

            columns = ('Код', 'Наименование', 'Остаток', 'Ед.', 'Мин.', 'Макс.', 'Место')
            self.warehouse_tree = ttk.Treeview(table_inner, columns=columns, show='headings', height=18)

            column_widths = [100, 350, 90, 60, 80, 80, 200]
            for idx, col in enumerate(columns):
                self.warehouse_tree.heading(col, text=col)
                self.warehouse_tree.column(col, width=column_widths[idx], anchor='center', stretch=True)

            scrollbar = Scrollbar(table_inner, orient='vertical', command=self.warehouse_tree.yview)
            self.warehouse_tree.configure(yscrollcommand=scrollbar.set)

            self.warehouse_tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            self.load_warehouse_data()

            self.logger.debug("Вкладка 'Склад' создана успешно")
            return warehouse_tab

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки склада: {e}")
            raise

    def create_nomenclature_tab(self, parent=None):
        """Создание вкладки 'Номенклатура' — иерархия папок/групп и позиций.

        Позволяет строить произвольную вложенность папок ("масла", "цех 2",
        "цех 3", "концентраты", "цех 1" и т.д.), а внутри папок создавать
        позиции номенклатуры, привязанные к конкретному продукту и к типу
        шаблона карты загрузки (ExcelTemplateProcessor.TEMPLATE_TYPES).
        Эти позиции затем можно использовать при создании карты загрузки
        для автоматического выбора нужного шаблона.
        """
        try:
            from modules.excel_template_processor import ExcelTemplateProcessor

            if parent is None:
                parent = self.tab_manager.content_area
            nom_tab = Frame(parent, bg=self.colors['background'])

            container = Frame(nom_tab, bg=self.colors['background'])
            container.pack(fill='both', expand=True, padx=20, pady=20)

            header_frame = Frame(container, bg=self.colors['background'])
            header_frame.pack(fill='x', pady=(0, 5))

            actions_frame = Frame(header_frame, bg=self.colors['background'])
            actions_frame.pack(side='right')

            refresh_btn = ttk.Button(
                actions_frame, text="🔄", command=self.load_nomenclature_tree,
                style="Compact.TButton"
            )
            refresh_btn.pack(side='left', padx=3)

            add_folder_btn = ttk.Button(
                actions_frame, text="📁➕", command=self.add_nomenclature_folder_dialog,
                style="Compact.TButton"
            )
            add_folder_btn.pack(side='left', padx=3)

            add_item_btn = ttk.Button(
                actions_frame, text="🧪➕", command=self.add_nomenclature_item_dialog,
                style="Compact.TButton"
            )
            add_item_btn.pack(side='left', padx=3)

            edit_btn = ttk.Button(
                actions_frame, text="📝", command=self.edit_nomenclature_dialog,
                style="Compact.TButton"
            )
            edit_btn.pack(side='left', padx=3)

            delete_btn = ttk.Button(
                actions_frame, text="🗑️", command=self.delete_nomenclature_dialog,
                style="Compact.TButton"
            )
            delete_btn.pack(side='left', padx=3)

            import_btn = ttk.Button(
                actions_frame, text="📥 Импорт из Excel", command=self.import_nomenclature_dialog,
                style="Compact.TButton"
            )
            import_btn.pack(side='left', padx=3)

            export_btn = ttk.Button(
                actions_frame, text="📤 Экспорт в Excel", command=self.export_nomenclature_dialog,
                style="Compact.TButton"
            )
            export_btn.pack(side='left', padx=3)

            ToolTip(refresh_btn, "Обновить дерево номенклатуры")
            ToolTip(add_folder_btn, "Добавить папку (группу)")
            ToolTip(add_item_btn, "Добавить позицию номенклатуры (продукт + шаблон карты)")
            ToolTip(edit_btn, "Редактировать выбранный элемент")
            ToolTip(delete_btn, "Удалить выбранный элемент (и вложенные)")
            ToolTip(import_btn, "Импорт позиций номенклатуры из Excel (Код, Наименование) в выбранную папку")
            ToolTip(export_btn, "Экспорт позиций номенклатуры выбранной папки (со всеми вложенными) в Excel")

            info_label = Label(
                container,
                text=("Стройте папки/группы для наименований (масла цех 2/3, концентраты, цех 1 и т.д.). "
                      "Позиции внутри папок привязываются к продукту и к типу шаблона карты загрузки — "
                      "этот шаблон будет предложен автоматически при создании карты."),
                font=self.fonts['caption'],
                bg=self.colors['background'],
                fg=self.colors['secondary'],
                wraplength=900,
                justify='left'
            )
            info_label.pack(fill='x', pady=(0, 8))

            table_inner = self.create_card_frame(container, padding=(10, 10))

            columns = ('type', 'product', 'template')
            self.nomenclature_tree = ttk.Treeview(
                table_inner, columns=columns, show='tree headings', height=18
            )
            self.nomenclature_tree.heading('#0', text='Наименование / папка')
            self.nomenclature_tree.heading('type', text='Тип')
            self.nomenclature_tree.heading('product', text='Продукт (код)')
            self.nomenclature_tree.heading('template', text='Шаблон карты')

            self.nomenclature_tree.column('#0', width=320, anchor='w')
            self.nomenclature_tree.column('type', width=90, anchor='center')
            self.nomenclature_tree.column('product', width=220, anchor='w')
            self.nomenclature_tree.column('template', width=220, anchor='w')

            scrollbar = Scrollbar(table_inner, orient='vertical', command=self.nomenclature_tree.yview)
            self.nomenclature_tree.configure(yscrollcommand=scrollbar.set)

            self.nomenclature_tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            self.nomenclature_tree.bind('<Double-Button-1>', lambda e: self.edit_nomenclature_dialog())

            self.load_nomenclature_tree()

            self.logger.debug("Вкладка 'Номенклатура' создана успешно")
            return nom_tab

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки номенклатуры: {e}")
            raise

    def load_nomenclature_tree(self):
        """Загрузить и отобразить дерево номенклатуры из БД"""
        try:
            if not hasattr(self, 'nomenclature_tree'):
                return

            # Запоминаем какие узлы были раскрыты, чтобы восстановить после обновления
            expanded_ids = set()
            for iid in self.nomenclature_tree.get_children(''):
                self._collect_expanded(iid, expanded_ids)

            self.nomenclature_tree.delete(*self.nomenclature_tree.get_children())

            nodes = db_manager.get_nomenclature_tree()

            from modules.excel_template_processor import ExcelTemplateProcessor
            template_labels = ExcelTemplateProcessor.TEMPLATE_LABELS

            children_map = {}
            for node in nodes:
                children_map.setdefault(node['parent_id'], []).append(node)

            row_counter = {'i': 0}

            def insert_children(parent_iid, parent_key):
                for node in children_map.get(parent_key, []):
                    is_folder = node['item_type'] == 'folder'
                    icon = '📁 ' if is_folder else '🧪 '
                    type_label = 'Папка' if is_folder else 'Позиция'
                    product_label = node.get('product_code') or ''
                    template_label = template_labels.get(node.get('template_type'), node.get('template_type') or '')

                    row_tag = "even" if row_counter['i'] % 2 == 0 else "odd"
                    row_counter['i'] += 1

                    iid = str(node['id'])
                    self.nomenclature_tree.insert(
                        parent_iid, 'end', iid=iid,
                        text=f"{icon}{node['name']}",
                        values=(type_label, product_label, template_label),
                        open=(iid in expanded_ids),
                        tags=(row_tag,)
                    )
                    insert_children(iid, node['id'])

            insert_children('', None)

            self.nomenclature_tree.tag_configure("odd", background=self.colors['surface'])
            self.nomenclature_tree.tag_configure("even", background=self.colors['row_alt'])

        except Exception as e:
            self.logger.error(f"Ошибка загрузки дерева номенклатуры: {e}")

    def _collect_expanded(self, iid, expanded_ids):
        """Рекурсивно собрать id раскрытых узлов дерева номенклатуры"""
        try:
            if self.nomenclature_tree.item(iid, 'open'):
                expanded_ids.add(iid)
            for child in self.nomenclature_tree.get_children(iid):
                self._collect_expanded(child, expanded_ids)
        except Exception:
            pass

    def _get_selected_nomenclature_node(self):
        """Получить данные выбранного узла дерева номенклатуры (или None)"""
        if not hasattr(self, 'nomenclature_tree'):
            return None
        selection = self.nomenclature_tree.selection()
        if not selection:
            return None
        node_id = int(selection[0])
        return db_manager.get_nomenclature_node(node_id)

    def import_nomenclature_dialog(self):
        """Диалог импорта позиций номенклатуры из Excel-файла.

        Формат файла: 2 колонки — 'Код' и 'Наименование'. Группа/папка не
        указывается в файле — пользователь выбирает целевую папку заранее
        (текущий выбранный узел дерева, либо его родитель, если выбрана
        позиция). Позиции импортируются в выбранную папку.
        """
        try:
            selected = self._get_selected_nomenclature_node()
            target_parent_id = None
            target_label = '(корень)'
            if selected:
                if selected['item_type'] == 'folder':
                    target_parent_id = selected['id']
                    target_label = selected['name']
                else:
                    target_parent_id = selected['parent_id']
                    if target_parent_id:
                        parent_node = db_manager.get_nomenclature_node(target_parent_id)
                        target_label = parent_node['name'] if parent_node else '(корень)'

            filename = filedialog.askopenfilename(
                title="Выберите Excel-файл для импорта номенклатуры",
                filetypes=[("Excel файлы", "*.xlsx *.xls"), ("Все файлы", "*.*")]
            )
            if not filename:
                return

            if not messagebox.askyesno(
                "Подтверждение импорта",
                f"Импортировать позиции из файла:\n{filename}\n\nв папку: {target_label}?"
            ):
                return

            replace_existing = messagebox.askyesno(
                "Режим импорта",
                "Обновлять уже существующие позиции с совпадающим кодом?\n\n"
                "Да — обновить наименование у существующих позиций.\n"
                "Нет — пропускать позиции с уже существующим кодом."
            )

            stats = db_manager.import_nomenclature_from_excel(
                filename, parent_id=target_parent_id, replace_existing=replace_existing
            )

            self.load_nomenclature_tree()

            summary = (
                f"Импортировано: {stats.get('imported', 0)}\n"
                f"Обновлено: {stats.get('updated', 0)}\n"
                f"Пропущено: {stats.get('skipped', 0)}"
            )
            errors = stats.get('errors') or []
            if errors:
                shown_errors = "\n".join(str(e) for e in errors[:10])
                if len(errors) > 10:
                    shown_errors += f"\n… и ещё {len(errors) - 10} ошибок"
                summary += f"\n\nОшибки ({len(errors)}):\n{shown_errors}"

            messagebox.showinfo("Импорт номенклатуры завершён", summary)
            self.logger.info(f"Импорт номенклатуры из {filename}: {stats}")
            system_logger.log_operation("import_nomenclature",
                                        f"Импорт из файла: {filename}, папка: {target_label}",
                                        user="user")

        except Exception as e:
            self.logger.error(f"Ошибка импорта номенклатуры из Excel: {e}")
            messagebox.showerror("Ошибка", f"Не удалось импортировать номенклатуру:\n{e}")

    def export_nomenclature_dialog(self):
        """Диалог экспорта позиций номенклатуры выбранной папки (рекурсивно
        со всеми вложенными подпапками) в Excel-файл с колонками
        'Код' и 'Наименование'. Если ничего не выбрано — экспортируется
        всё дерево номенклатуры."""
        try:
            selected = self._get_selected_nomenclature_node()
            folder_id = None
            folder_label = 'вся номенклатура'
            if selected:
                if selected['item_type'] == 'folder':
                    folder_id = selected['id']
                    folder_label = selected['name']
                else:
                    folder_id = selected['parent_id']
                    if folder_id:
                        parent_node = db_manager.get_nomenclature_node(folder_id)
                        folder_label = parent_node['name'] if parent_node else 'вся номенклатура'

            filename = filedialog.asksaveasfilename(
                title="Сохранить экспорт номенклатуры как",
                defaultextension=".xlsx",
                filetypes=[("Excel файлы", "*.xlsx")],
                initialfile=f"nomenclature_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            if not filename:
                return

            success = db_manager.export_nomenclature_to_excel(filename, folder_id=folder_id)

            if success:
                messagebox.showinfo(
                    "Успех",
                    f"Номенклатура ({folder_label}) экспортирована в:\n{filename}"
                )
                self.logger.info(f"Экспорт номенклатуры ({folder_label}) в {filename}")
                system_logger.log_operation("export_nomenclature",
                                            f"Экспорт в файл: {filename}, папка: {folder_label}",
                                            user="user")
            else:
                messagebox.showerror("Ошибка", "Не удалось экспортировать номенклатуру")

        except Exception as e:
            self.logger.error(f"Ошибка экспорта номенклатуры в Excel: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать номенклатуру:\n{e}")

    def add_nomenclature_folder_dialog(self):
        """Диалог добавления новой папки (группы) номенклатуры"""
        try:
            selected = self._get_selected_nomenclature_node()
            default_parent_id = None
            if selected:
                default_parent_id = selected['id'] if selected['item_type'] == 'folder' else selected['parent_id']

            dialog, main_frame = self.create_dialog(
                "Новая папка номенклатуры", 480, 240, header_color=self.colors['primary']
            )

            Label(main_frame, text="Название папки*:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            name_var = StringVar()
            ttk.Entry(main_frame, textvariable=name_var, font=self.fonts['body']).pack(fill='x', pady=(0, 10))

            Label(main_frame, text="Родительская папка:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

            folder_options = self._get_folder_options()
            parent_var = StringVar()
            parent_combo = ttk.Combobox(main_frame, textvariable=parent_var,
                                         values=[label for label, _ in folder_options],
                                         state='readonly', style="Modern.TCombobox")
            parent_combo.pack(fill='x', pady=(0, 15))

            default_label = '(корень)'
            for label, node_id in folder_options:
                if node_id == default_parent_id:
                    default_label = label
                    break
            parent_var.set(default_label)

            button_frame = Frame(main_frame, bg=self.colors['background'])
            button_frame.pack(fill='x', pady=(0, 5))

            def save_folder():
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("Внимание", "Введите название папки")
                    return
                parent_id = None
                for label, node_id in folder_options:
                    if label == parent_var.get():
                        parent_id = node_id
                        break
                try:
                    db_manager.create_nomenclature_folder(name, parent_id=parent_id)
                    dialog.destroy()
                    self.load_nomenclature_tree()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось создать папку:\n{e}")

            save_btn = self.create_modern_button(button_frame, "Сохранить", save_folder, 'success')
            save_btn.pack(side='left', padx=10)
            cancel_btn = self.create_modern_button(button_frame, "Отмена", dialog.destroy, 'secondary')
            cancel_btn.pack(side='right', padx=10)

        except Exception as e:
            self.logger.error(f"Ошибка диалога добавления папки номенклатуры: {e}")

    def add_nomenclature_item_dialog(self):
        """Диалог добавления новой позиции номенклатуры.

        Номенклатура — единственная точка ввода продукта: код и наименование
        вводятся напрямую (как две колонки в Excel-импорте — Код и
        Наименование), без выбора из отдельного справочника продуктов.
        При сохранении запись в products создаётся/обновляется автоматически
        (см. DatabaseManager.upsert_product)."""
        try:
            from modules.excel_template_processor import ExcelTemplateProcessor

            selected = self._get_selected_nomenclature_node()
            default_parent_id = None
            if selected:
                default_parent_id = selected['id'] if selected['item_type'] == 'folder' else selected['parent_id']

            dialog, main_frame = self.create_dialog(
                "Новая позиция номенклатуры", 520, 460, header_color=self.colors['primary']
            )

            Label(main_frame, text="Код*:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            code_var = StringVar()
            ttk.Entry(main_frame, textvariable=code_var, font=self.fonts['body']).pack(fill='x', pady=(0, 10))

            Label(main_frame, text="Наименование*:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            name_var = StringVar()
            ttk.Entry(main_frame, textvariable=name_var, font=self.fonts['body']).pack(fill='x', pady=(0, 10))

            Label(main_frame, text="Папка (группа):",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

            folder_options = self._get_folder_options()
            parent_var = StringVar()
            parent_combo = ttk.Combobox(main_frame, textvariable=parent_var,
                                         values=[label for label, _ in folder_options],
                                         state='readonly', style="Modern.TCombobox")
            parent_combo.pack(fill='x', pady=(0, 10))

            default_label = '(корень)'
            for label, node_id in folder_options:
                if node_id == default_parent_id:
                    default_label = label
                    break
            parent_var.set(default_label)

            Label(main_frame, text="Тип шаблона карты загрузки:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

            template_options = [('(не выбран)', None)] + [
                (label, key) for key, label in ExcelTemplateProcessor.TEMPLATE_LABELS.items()
            ]
            template_var = StringVar(value=template_options[0][0])
            template_combo = ttk.Combobox(main_frame, textvariable=template_var,
                                           values=[label for label, _ in template_options],
                                           state='readonly', style="Modern.TCombobox")
            template_combo.pack(fill='x', pady=(0, 15))

            button_frame = Frame(main_frame, bg=self.colors['background'])
            button_frame.pack(fill='x', pady=(0, 5))

            def save_item():
                name = name_var.get().strip()
                code = code_var.get().strip()
                if not name:
                    messagebox.showwarning("Внимание", "Введите наименование позиции")
                    return
                if not code:
                    messagebox.showwarning("Внимание", "Введите код позиции")
                    return

                parent_id = None
                for label, node_id in folder_options:
                    if label == parent_var.get():
                        parent_id = node_id
                        break

                template_type = None
                for label, key in template_options:
                    if label == template_var.get():
                        template_type = key
                        break

                try:
                    db_manager.create_nomenclature_item(
                        name, parent_id=parent_id,
                        product_code=code, template_type=template_type
                    )
                    dialog.destroy()
                    self.load_nomenclature_tree()
                except ValueError as e:
                    messagebox.showerror("Ошибка", str(e))
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось создать позицию:\n{e}")

            save_btn = self.create_modern_button(button_frame, "Сохранить", save_item, 'success')
            save_btn.pack(side='left', padx=10)
            cancel_btn = self.create_modern_button(button_frame, "Отмена", dialog.destroy, 'secondary')
            cancel_btn.pack(side='right', padx=10)

        except Exception as e:
            self.logger.error(f"Ошибка диалога добавления позиции номенклатуры: {e}")

    def edit_nomenclature_dialog(self):
        """Диалог редактирования выбранного узла номенклатуры (папка или позиция)"""
        try:
            node = self._get_selected_nomenclature_node()
            if not node:
                messagebox.showwarning("Внимание", "Выберите элемент для редактирования")
                return

            from modules.excel_template_processor import ExcelTemplateProcessor

            is_folder = node['item_type'] == 'folder'
            title = "Редактирование папки" if is_folder else "Редактирование позиции"
            dialog, main_frame = self.create_dialog(
                title, 520, 420 if not is_folder else 260, header_color=self.colors['primary']
            )

            Label(main_frame, text="Название*:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            name_var = StringVar(value=node['name'])
            ttk.Entry(main_frame, textvariable=name_var, font=self.fonts['body']).pack(fill='x', pady=(0, 10))

            Label(main_frame, text="Родительская папка:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

            folder_options = self._get_folder_options(exclude_id=node['id'])
            parent_var = StringVar()
            parent_combo = ttk.Combobox(main_frame, textvariable=parent_var,
                                         values=[label for label, _ in folder_options],
                                         state='readonly', style="Modern.TCombobox")
            parent_combo.pack(fill='x', pady=(0, 10))
            default_label = '(корень)'
            for label, node_id in folder_options:
                if node_id == node['parent_id']:
                    default_label = label
                    break
            parent_var.set(default_label)

            code_var = None
            template_var = None
            template_options = []

            if not is_folder:
                Label(main_frame, text="Код*:",
                      font=self.fonts['body_semibold'],
                      bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
                code_var = StringVar(value=node.get('product_code') or '')
                ttk.Entry(main_frame, textvariable=code_var, font=self.fonts['body']).pack(fill='x', pady=(0, 10))

                Label(main_frame, text="Тип шаблона карты загрузки:",
                      font=self.fonts['body_semibold'],
                      bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

                template_options = [('(не выбран)', None)] + [
                    (label, key) for key, label in ExcelTemplateProcessor.TEMPLATE_LABELS.items()
                ]
                template_var = StringVar()
                template_combo = ttk.Combobox(main_frame, textvariable=template_var,
                                               values=[label for label, _ in template_options],
                                               state='readonly', style="Modern.TCombobox")
                template_combo.pack(fill='x', pady=(0, 15))
                default_template_label = '(не выбран)'
                for label, key in template_options:
                    if key == node.get('template_type'):
                        default_template_label = label
                        break
                template_var.set(default_template_label)

            button_frame = Frame(main_frame, bg=self.colors['background'])
            button_frame.pack(fill='x', pady=(0, 5))

            def save_changes():
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("Внимание", "Введите название")
                    return

                parent_id = None
                for label, pid in folder_options:
                    if label == parent_var.get():
                        parent_id = pid
                        break

                if parent_id == node['id']:
                    messagebox.showwarning("Внимание", "Нельзя выбрать саму папку в качестве родителя")
                    return

                update_kwargs = {'name': name, 'parent_id': parent_id}

                if not is_folder:
                    code = code_var.get().strip()
                    if not code:
                        messagebox.showwarning("Внимание", "Введите код позиции")
                        return
                    template_type = None
                    for label, key in template_options:
                        if label == template_var.get():
                            template_type = key
                            break
                    update_kwargs['product_code'] = code
                    # Явно допускаем сброс в None: передаём отдельным UPDATE,
                    # т.к. update_nomenclature_node игнорирует None-параметры
                    # (кроме parent_id) для гибкости частичного обновления.
                    update_kwargs['template_type'] = template_type if template_type is not None else ''

                try:
                    ok = db_manager.update_nomenclature_node(node['id'], **update_kwargs)
                    if not ok:
                        messagebox.showerror("Ошибка", "Не удалось сохранить изменения")
                        return
                    if parent_id != node['parent_id']:
                        move_ok = db_manager.move_nomenclature_node(node['id'], parent_id)
                        if not move_ok:
                            messagebox.showwarning(
                                "Внимание",
                                "Не удалось переместить элемент (нельзя переместить папку в саму себя или в её потомка)"
                            )
                    dialog.destroy()
                    self.load_nomenclature_tree()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить изменения:\n{e}")

            save_btn = self.create_modern_button(button_frame, "Сохранить", save_changes, 'success')
            save_btn.pack(side='left', padx=10)
            cancel_btn = self.create_modern_button(button_frame, "Отмена", dialog.destroy, 'secondary')
            cancel_btn.pack(side='right', padx=10)

        except Exception as e:
            self.logger.error(f"Ошибка диалога редактирования номенклатуры: {e}")

    def delete_nomenclature_dialog(self):
        """Удаление выбранного узла номенклатуры (с подтверждением)"""
        try:
            node = self._get_selected_nomenclature_node()
            if not node:
                messagebox.showwarning("Внимание", "Выберите элемент для удаления")
                return

            is_folder = node['item_type'] == 'folder'
            warning = ""
            if is_folder:
                warning = "\n\nВНИМАНИЕ: все вложенные папки и позиции также будут удалены!"

            if not messagebox.askyesno(
                "Подтверждение удаления",
                f"Удалить '{node['name']}'?{warning}"
            ):
                return

            if db_manager.delete_nomenclature_node(node['id']):
                self.load_nomenclature_tree()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить элемент")

        except Exception as e:
            self.logger.error(f"Ошибка удаления узла номенклатуры: {e}")

    def _get_folder_options(self, exclude_id=None):
        """Построить список (метка, id) для выбора родительской папки в комбобоксах.

        Метки формируются с отступами по уровню вложенности для наглядности.
        exclude_id позволяет исключить саму редактируемую папку (и не
        исключает её потомков — защита от цикличности выполняется отдельно
        в move_nomenclature_node на уровне БД).
        """
        nodes = db_manager.get_nomenclature_tree()
        folders = [n for n in nodes if n['item_type'] == 'folder' and n['id'] != exclude_id]

        children_map = {}
        for node in folders:
            children_map.setdefault(node['parent_id'], []).append(node)

        options = [('(корень)', None)]

        def walk(parent_key, depth):
            for node in children_map.get(parent_key, []):
                prefix = '—' * depth + ' ' if depth else ''
                options.append((f"{prefix}{node['name']}", node['id']))
                walk(node['id'], depth + 1)

        walk(None, 0)
        return options


    def create_logs_tab(self, parent=None):
        """Создание вкладки логов в современном стиле"""
        try:
            if parent is None:
                parent = self.tab_manager.content_area
            logs_tab = Frame(parent, bg=self.colors['background'])

            container = Frame(logs_tab, bg=self.colors['background'])
            container.pack(fill='both', expand=True, padx=20, pady=20)

            control_frame = Frame(container, bg=self.colors['background'])
            control_frame.pack(fill='x', pady=(0, 5))

            refresh_btn = ttk.Button(
                control_frame,
                text="🔄",
                command=self.load_logs,
                style="Compact.TButton"
            )
            refresh_btn.pack(side='left', padx=3)

            clear_btn = ttk.Button(
                control_frame,
                text="🗑️",
                command=self.clear_logs,
                style="Compact.TButton"
            )
            clear_btn.pack(side='left', padx=3)

            ToolTip(refresh_btn, "Обновить текущий файл логов")
            ToolTip(clear_btn, "Очистить все файлы логов")

            main_frame = Frame(container, bg=self.colors['background'])
            main_frame.pack(fill='both', expand=True)

            # Левая панель - список файлов логов
            left_inner = self.create_card_frame(main_frame, padding=(15, 15))
            left_inner.config(width=300)
            left_inner.pack(side='left', fill='y', padx=(0, 10))

            Label(left_inner, text="Файлы логов",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['surface'],
                  fg=self.colors['on_surface']).pack(fill='x', pady=(0, 10))

            list_container = Frame(left_inner, bg=self.colors['surface'])
            list_container.pack(fill='both', expand=True)

            scrollbar = Scrollbar(list_container)
            scrollbar.pack(side='right', fill='y')

            self.log_files_listbox = Listbox(list_container,
                                             yscrollcommand=scrollbar.set,
                                             font=self.fonts['body'],
                                             bg=self.colors['surface'],
                                             fg=self.colors['on_surface'],
                                             relief='flat',
                                             borderwidth=0,
                                             selectbackground=self.colors['primary_light'])
            self.log_files_listbox.pack(side='left', fill='both', expand=True)
            self.log_files_listbox.bind('<<ListboxSelect>>', self.on_log_file_selected)

            scrollbar.config(command=self.log_files_listbox.yview)

            # Правая панель - содержимое логов
            right_inner = self.create_card_frame(main_frame, padding=(10, 10))
            right_inner.pack(side='right', fill='both', expand=True)

            header_frame2 = Frame(right_inner, bg=self.colors['surface'])
            header_frame2.pack(fill='x', padx=10, pady=10)

            Label(header_frame2, text="Содержимое лога",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['surface'],
                  fg=self.colors['on_surface']).pack(side='left')

            # Фильтры и поиск
            filters_frame = Frame(header_frame2, bg=self.colors['surface'])
            filters_frame.pack(side='right')

            # Поиск
            search_frame = Frame(filters_frame, bg=self.colors['surface'])
            search_frame.pack(side='top', anchor='e')

            Label(search_frame, text="Поиск:",
                  font=self.fonts['body'],
                  bg=self.colors['surface'],
                  fg=self.colors['secondary']).pack(side='left', padx=(0, 5))

            search_entry = ttk.Entry(search_frame,
                                     textvariable=self.log_search_var,
                                     font=self.fonts['body'],
                                     width=18)
            search_entry.pack(side='left')
            search_entry.bind('<KeyRelease>', lambda e: self.load_logs())

            # Уровень логов
            level_frame = Frame(filters_frame, bg=self.colors['surface'])
            level_frame.pack(side='top', anchor='e', pady=(5, 0))

            Label(level_frame, text="Уровень:",
                  font=self.fonts['body'],
                  bg=self.colors['surface'],
                  fg=self.colors['secondary']).pack(side='left', padx=(0, 5))

            self.log_level_var = StringVar(value="ALL")
            log_level_combo = ttk.Combobox(level_frame,
                                           textvariable=self.log_level_var,
                                           values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                           state='readonly',
                                           width=12)
            log_level_combo.pack(side='left')
            log_level_combo.bind('<<ComboboxSelected>>', lambda e: self.load_logs())

            text_frame = Frame(right_inner, bg=self.colors['surface'])
            text_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

            scrollbar_text = Scrollbar(text_frame)
            scrollbar_text.pack(side='right', fill='y')

            # Чёрный фон логов (как IDE)
            self.log_text = Text(
                text_frame,
                yscrollcommand=scrollbar_text.set,
                font=('Consolas', 10),
                bg='#1E1E1E',
                fg='#D4D4D4',
                wrap='word',
                height=20,
                relief='flat',
                borderwidth=0
            )
            self.log_text.pack(side='left', fill='both', expand=True)

            scrollbar_text.config(command=self.log_text.yview)

            self.log_text.tag_config('DEBUG', foreground='#569CD6')
            self.log_text.tag_config('INFO', foreground='#4EC9B0')
            self.log_text.tag_config('WARNING', foreground='#CE9178')
            self.log_text.tag_config('ERROR', foreground='#F44747')
            self.log_text.tag_config('CRITICAL', foreground='#FF6B6B', background='#2C2C2C')

            self.load_log_files()

            self.logger.debug("Вкладка 'Логи' создана успешно")
            return logs_tab

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки логов: {e}")
            raise

    def _make_scrollable(self, parent):
        """Оборачивает содержимое вкладки в Canvas+Scrollbar, чтобы контент
        не обрезался, если не помещается по высоте окна (как на вкладке
        "Главная"). Возвращает Frame, в который нужно класть содержимое.
        Дополнительно навешивает прокрутку колесом мыши на весь canvas."""
        canvas = tk.Canvas(parent, bg=self.colors['background'], highlightthickness=0)
        scrollbar = Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.colors['background'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Растягиваем внутренний frame по ширине канваса
        def _resize_inner(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _resize_inner)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        def _on_mousewheel(event):
            delta = 0
            if getattr(event, 'num', None) == 4:
                delta = -1
            elif getattr(event, 'num', None) == 5:
                delta = 1
            elif getattr(event, 'delta', 0):
                delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, "units")

        def _bind_wheel(_event=None):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_wheel(_event=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        return scrollable_frame

    def create_import_export_tab(self, parent=None):
        """Создание вкладки импорта/экспорта в современном стиле"""
        try:
            if parent is None:
                parent = self.tab_manager.content_area
            import_tab = Frame(parent, bg=self.colors['background'])

            main_notebook = ttk.Notebook(import_tab)
            main_notebook.pack(fill='both', expand=True, padx=20, pady=20)

            recipes_tab = Frame(main_notebook, bg=self.colors['background'])
            main_notebook.add(recipes_tab, text="📋 Рецептуры")

            norms_tab = Frame(main_notebook, bg=self.colors['background'])
            main_notebook.add(norms_tab, text="📊 Нормы показателей")

            # Контент оборачиваем в прокручиваемую область, т.к. на маленьких
            # экранах/окнах кнопки "Начать импорт/экспорт" не помещались по
            # высоте и были недоступны (баг: кнопка "исчезает" после выбора файла)
            recipes_scrollable = self._make_scrollable(recipes_tab)
            norms_scrollable = self._make_scrollable(norms_tab)

            self.create_import_export_content(recipes_scrollable, is_norms=False)
            self.create_import_export_content(norms_scrollable, is_norms=True)

            self.logger.debug("Вкладка 'Импорт/Экспорт' создана успешно")
            return import_tab

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки импорта/экспорта: {e}")
            raise

    def create_finished_products_tab(self, parent=None):
        """Создание вкладки 'Готовая продукция' со спецификациями."""
        try:
            if parent is None:
                parent = self.tab_manager.content_area
            fp_tab = Frame(parent, bg=self.colors['background'])
            fp_tab.pack(fill='both', expand=True)
            FinishedProductsTab(fp_tab, self)
            self.logger.debug("Вкладка 'Готовая продукция' создана успешно")
            return fp_tab
        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки готовой продукции: {e}")
            raise

    def create_import_export_content(self, parent, is_norms=False):
        """Создание содержимого для вкладки импорта/экспорта"""
        container = Frame(parent, bg=self.colors['background'])
        container.pack(fill='both', expand=True, padx=30, pady=30)

        title = "Нормы показателей" if is_norms else "Рецептуры"
        Label(container, text=f"Импорт и экспорт {title}",
              font=self.fonts['h3'],
              bg=self.colors['background'],
              fg=self.colors['on_background']).pack(anchor='w', pady=(0, 30))

        columns_frame = Frame(container, bg=self.colors['background'])
        columns_frame.pack(fill='both', expand=True)

        import_frame = self.create_card_frame(columns_frame, padding=(30, 30))
        import_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        export_frame = self.create_card_frame(columns_frame, padding=(30, 30))
        export_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        self.fill_import_column(import_frame, is_norms)
        self.fill_export_column(export_frame, is_norms)

    def fill_import_column(self, parent, is_norms):
        """Заполнение колонки импорта"""
        content = parent

        Label(content, text="📥 Импорт из Excel",
              font=self.fonts['h3'],
              bg=self.colors['surface'],
              fg=self.colors['on_background']).pack(anchor='w', pady=(0, 20))

        desc_text = "норм физико-химических показателей" if is_norms else "рецептур и данных"
        Label(content, text=f"Импорт {desc_text} из файла Excel:",
              font=self.fonts['body'],
              bg=self.colors['surface'],
              fg=self.colors['secondary']).pack(anchor='w', pady=(0, 15))

        req_frame = Frame(content,
                          bg=self.colors['primary_light'],
                          relief='flat',
                          borderwidth=1,
                          highlightbackground=self.colors['primary'],
                          highlightthickness=1)
        req_frame.pack(fill='x', pady=20)

        Label(req_frame, text="Требования к файлу:",
              font=self.fonts['body_semibold'],
              bg=self.colors['primary_light'],
              fg=self.colors['primary']).pack(anchor='w', padx=15, pady=10)

        req_text = (
            "• Формат: .xlsx или .xls\n"
            "• Кодировка: UTF-8\n"
            "• Макс. размер: 50 МБ\n"
            "• Обязательные столбцы указаны в шаблоне"
        )

        Label(req_frame, text=req_text,
              font=self.fonts['small'],
              bg=self.colors['primary_light'],
              fg=self.colors['on_surface'],
              justify='left').pack(anchor='w', padx=15, pady=(0, 10))

        file_frame = Frame(content, bg=self.colors['surface'])
        file_frame.pack(fill='x', pady=20)

        if is_norms:
            file_btn = self.create_modern_button(file_frame, "Выбрать файл",
                                                 self.select_norms_file,
                                                 'secondary', '📁')
        else:
            file_btn = self.create_modern_button(file_frame, "Выбрать файл",
                                                 self.select_import_file,
                                                 'secondary', '📁')
        file_btn.pack()

        options_frame = Frame(content, bg=self.colors['surface'])
        options_frame.pack(fill='x', pady=30)

        if is_norms:
            self.norms_replace_var = BooleanVar(value=True)
            tk.Checkbutton(options_frame, text="Заменить существующие нормы",
                           variable=self.norms_replace_var,
                           font=self.fonts['body'],
                           bg=self.colors['surface'],
                           fg=self.colors['on_surface'],
                           selectcolor=self.colors['primary'],
                           activebackground=self.colors['surface'],
                           activeforeground=self.colors['on_surface'],
                           highlightthickness=0).pack(anchor='w', pady=5)
        else:
            self.create_backup_var = BooleanVar(value=True)
            tk.Checkbutton(options_frame, text="Создать резервную копию",
                           variable=self.create_backup_var,
                           font=self.fonts['body'],
                           bg=self.colors['surface'],
                           fg=self.colors['on_surface'],
                           selectcolor=self.colors['primary'],
                           activebackground=self.colors['surface'],
                           activeforeground=self.colors['on_surface'],
                           highlightthickness=0).pack(anchor='w', pady=5)

            self.replace_existing_var = BooleanVar(value=False)
            tk.Checkbutton(options_frame, text="Заменить существующие записи",
                           variable=self.replace_existing_var,
                           font=self.fonts['body'],
                           bg=self.colors['surface'],
                           fg=self.colors['on_surface'],
                           selectcolor=self.colors['primary'],
                           activebackground=self.colors['surface'],
                           activeforeground=self.colors['on_surface'],
                           highlightthickness=0).pack(anchor='w', pady=5)

        if is_norms:
            import_btn = self.create_modern_button(content,
                                                   "Начать импорт",
                                                   self.start_norms_import,
                                                   'primary', '🚀')
        else:
            import_btn = self.create_modern_button(content,
                                                   "Начать импорт данных",
                                                   self.start_import,
                                                   'primary', '🚀')
        import_btn.pack()

        if is_norms:
            self.norms_import_status_label = Label(content, text="",
                                                   font=self.fonts['caption'],
                                                   bg=self.colors['surface'],
                                                   fg=self.colors['secondary'])
            self.norms_import_status_label.pack(pady=20)
        else:
            self.import_status_label = Label(content, text="",
                                             font=self.fonts['caption'],
                                             bg=self.colors['surface'],
                                             fg=self.colors['secondary'])
            self.import_status_label.pack(pady=20)

    def fill_export_column(self, parent, is_norms):
        """Заполнение колонки экспорта"""
        content = parent

        Label(content, text="📤 Экспорт в Excel",
              font=self.fonts['h3'],
              bg=self.colors['surface'],
              fg=self.colors['on_background']).pack(anchor='w', pady=(0, 20))

        desc_text = "норм показателей" if is_norms else "данных"
        Label(content, text=f"Экспорт {desc_text} в файл Excel:",
              font=self.fonts['body'],
              bg=self.colors['surface'],
              fg=self.colors['secondary']).pack(anchor='w', pady=(0, 15))

        if is_norms:
            Label(content, text="Выберите продукт:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['surface'],
                  fg=self.colors['on_surface']).pack(anchor='w', pady=10)

            self.export_norms_product_var = StringVar()
            self.export_norms_combo = ttk.Combobox(content,
                                                   textvariable=self.export_norms_product_var,
                                                   font=self.fonts['body'],
                                                   state='readonly')
            self.export_norms_combo.pack(fill='x', pady=20)
            self.load_products_with_norms()

            export_type_frame = Frame(content, bg=self.colors['surface'])
            export_type_frame.pack(fill='x', pady=20)

            self.export_norms_type_var = StringVar(value="selected")
            tk.Radiobutton(export_type_frame, text="Выбранный продукт",
                           variable=self.export_norms_type_var, value="selected",
                           font=self.fonts['body'],
                           bg=self.colors['surface'],
                           fg=self.colors['on_surface'],
                           selectcolor=self.colors['primary'],
                           activebackground=self.colors['surface'],
                           activeforeground=self.colors['on_surface'],
                           highlightthickness=0).pack(anchor='w', pady=5)

            tk.Radiobutton(export_type_frame, text="Все продукты",
                           variable=self.export_norms_type_var, value="all",
                           font=self.fonts['body'],
                           bg=self.colors['surface'],
                           fg=self.colors['on_surface'],
                           selectcolor=self.colors['primary'],
                           activebackground=self.colors['surface'],
                           activeforeground=self.colors['on_surface'],
                           highlightthickness=0).pack(anchor='w', pady=5)
        else:
            Label(content, text="Тип данных для экспорта:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['surface'],
                  fg=self.colors['on_surface']).pack(anchor='w', pady=10)

            export_type_frame = Frame(content, bg=self.colors['surface'])
            export_type_frame.pack(fill='x', pady=20)

            self.export_type_var = StringVar(value="cards")
            types = [("Карты загрузок", "cards"),
                     ("Справочник номенклатуры/продуктов", "products"),
                     ("Данные склада", "warehouse")]

            for text, value in types:
                tk.Radiobutton(export_type_frame, text=text,
                               variable=self.export_type_var, value=value,
                               font=self.fonts['body'],
                               bg=self.colors['surface'],
                               fg=self.colors['on_surface'],
                               selectcolor=self.colors['primary'],
                               activebackground=self.colors['surface'],
                               activeforeground=self.colors['on_surface'],
                               highlightthickness=0).pack(anchor='w', pady=5)

        if is_norms:
            path_btn = self.create_modern_button(content, "Выбрать путь для сохранения",
                                                 self.select_norms_export_path,
                                                 'secondary', '📁')
        else:
            path_btn = self.create_modern_button(content, "Выбрать путь для сохранения",
                                                 self.select_export_path,
                                                 'secondary', '📁')
        path_btn.pack(pady=30)

        if is_norms:
            export_btn = self.create_modern_button(content,
                                                   "Начать экспорт",
                                                   self.start_norms_export,
                                                   'primary', '🚀')
        else:
            export_btn = self.create_modern_button(content,
                                                   "Начать экспорт данных",
                                                   self.start_export,
                                                   'primary', '🚀')
        export_btn.pack()

        if is_norms:
            self.norms_export_status_label = Label(content, text="",
                                                   font=self.fonts['caption'],
                                                   bg=self.colors['surface'],
                                                   fg=self.colors['secondary'])
            self.norms_export_status_label.pack(pady=20)
        else:
            self.export_status_label = Label(content, text="",
                                             font=self.fonts['caption'],
                                             bg=self.colors['surface'],
                                             fg=self.colors['secondary'])
            self.export_status_label.pack(pady=20)

    # ===================== ОСНОВНЫЕ МЕТОДЫ ФУНКЦИОНАЛЬНОСТИ =====================

    def update_date_time(self):
        """Обновление даты и времени в нижнем статусе"""
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y %H:%M:%S")
        self.date_label.config(text=f"📅 {date_str}")
        self.root.after(1000, self.update_date_time)

    def load_saved_cards(self):
        """Загрузка списка сохраненных карт загрузок из базы данных"""
        try:
            system_logger.log_operation("load_saved_cards", "Начало загрузки списка карт из БД")

            cards = db_manager.get_loading_cards(limit=100)

            for item in self.cards_tree.get_children():
                self.cards_tree.delete(item)

            if not cards:
                self.status_label.config(text="Сохраненные карты не найдены")
                self.logger.info("Сохраненные карты не найдены")
                return

            for idx, card in enumerate(cards):
                try:
                    date_str = card['created_date'][:16] if card['created_date'] else "Неизвестно"
                    row_tag = "even" if idx % 2 == 0 else "odd"

                    self.cards_tree.insert('', 'end', values=(
                        card['id'],
                        card['card_name'],
                        (card.get('product_name') or '')[:20],
                        (card.get('recipe_number') or '')[:10],
                        date_str,
                        card.get('status', 'draft')
                    ), tags=(row_tag,))

                except Exception as e:
                    self.logger.warning(f"Ошибка обработки карты {card.get('id')}: {e}")

            self.cards_tree.tag_configure("odd", background=self.colors['surface'])
            self.cards_tree.tag_configure("even", background=self.colors['row_alt'])

            self.status_label.config(text=f"Загружено {len(cards)} карт загрузок")
            self.logger.info(f"Загружено {len(cards)} карт загрузок из БД")

            system_logger.log_operation("load_saved_cards",
                                        f"Успешно загружено {len(cards)} карт из БД",
                                        level=LogLevel.INFO)

        except Exception as e:
            self.status_label.config(text="Ошибка загрузки списка карт")
            self.logger.error(f"Ошибка загрузки списка карт: {e}")
            system_logger.log_error_with_traceback("Ошибка загрузки списка карт", e)

    def view_card_details(self):
        """Просмотр деталей выбранной карты загрузки"""
        selection = self.cards_tree.selection()
        if not selection:
            self.logger.warning("Попытка просмотра карты без выбора")
            messagebox.showwarning("Внимание", "Выберите карту для просмотра")
            return

        item = self.cards_tree.item(selection[0])
        card_id = item['values'][0]

        try:
            card = db_manager.get_loading_card_details(card_id)
            components = db_manager.get_card_components(card_id)

            if not card:
                messagebox.showerror("Ошибка", "Карта не найдена")
                return

            dialog, main_frame = self.create_dialog(
                f"Детали карты загрузки: {card['card_name']}",
                width=900,
                height=600,
                header_color=self.colors['primary']
            )

            info_frame = Frame(main_frame, bg=self.colors['background'], padx=0, pady=10)
            info_frame.pack(fill='x')

            info_data = [
                ("Продукт:", f"{card.get('product_name', '')} ({card['product_code']})"),
                ("Рецептура:", f"{card.get('recipe_number', '')} - {card.get('recipe_name', '')}"),
                ("Реактор:", card.get('reactor', 'Р-1')),
                ("Количество, кг:", f"{card.get('batch_quantity', 0.0):.2f}"),
                ("Общая масса, кг:", f"{card.get('total_mass', 0.0):.2f}"),
                ("Дата создания:", card['created_date']),
                ("Статус:", card.get('status', 'draft'))
            ]

            for i, (label_text, value) in enumerate(info_data):
                row_frame = Frame(info_frame, bg=self.colors['background'])
                row_frame.pack(fill='x', pady=2)

                Label(row_frame, text=label_text, font=self.fonts['body_semibold'],
                      bg=self.colors['background'], width=20, anchor='w').pack(side='left')
                Label(row_frame, text=value, font=self.fonts['body'],
                      bg=self.colors['background'], anchor='w').pack(side='left')

            comp_card = self.create_card_frame(main_frame, padding=(10, 10))

            Label(comp_card, text="КОМПОНЕНТЫ:",
                  font=self.fonts['h3'],
                  bg=self.colors['surface']).pack(anchor='w', pady=(0, 10))

            columns = ('№', 'Код компонента', 'Наименование', 'Процент, %', 'Масса, кг')
            tree = ttk.Treeview(comp_card, columns=columns, show='headings', height=10)

            column_widths = [50, 120, 300, 100, 100]
            for idx, col in enumerate(columns):
                tree.heading(col, text=col)
                tree.column(col, width=column_widths[idx], anchor='center')

            for i, comp in enumerate(components, 1):
                tree.insert('', 'end', values=(
                    str(i),
                    comp['component_code'],
                    comp['component_name'],
                    f"{comp['percentage']:.4f}",
                    f"{comp['calculated_mass']:.3f}"
                ))

            if components:
                total_percent = sum(comp['percentage'] for comp in components)
                total_mass = sum(comp['calculated_mass'] for comp in components)

                tree.insert('', 'end', values=(
                    '',
                    'ВСЕГО:',
                    f"{len(components)} компонентов",
                    f"{total_percent:.4f}",
                    f"{total_mass:.3f}"
                ))

            scrollbar = Scrollbar(comp_card, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            button_frame = Frame(main_frame, bg=self.colors['background'], pady=10)
            button_frame.pack(fill='x')

            export_btn = self.create_modern_button(
                button_frame,
                "ЭКСПОРТ В EXCEL",
                lambda: self.export_card_to_excel(card_id),
                'success',
                '📤'
            )
            export_btn.pack(side='left', padx=10)

            close_btn = self.create_modern_button(
                button_frame,
                "Закрыть",
                dialog.destroy,
                'secondary'
            )
            close_btn.pack(side='right', padx=10)

            self.logger.info(f"Открыты детали карты загрузки ID: {card_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить детали карты:\n{str(e)}")
            self.logger.error(f"Ошибка просмотра деталей карты {card_id}: {e}")

    def delete_selected_card(self):
        """Удалить выбранную карту загрузки из базы данных"""
        selection = self.cards_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите карту для удаления")
            self.logger.warning("Попытка удаления карты без выбора")
            return

        item = self.cards_tree.item(selection[0])
        card_id = item['values'][0]

        if not messagebox.askyesno("Подтверждение",
                                   f"Удалить карту загрузки ID {card_id}?\n\n"
                                   "Это действие нельзя отменить!"):
            self.logger.info("Пользователь отменил удаление карты")
            return

        try:
            system_logger.log_operation("delete_card",
                                        f"Удаление карты ID: {card_id}",
                                        user="user",
                                        level=LogLevel.WARNING)

            db_manager.delete_loading_card(card_id)

            self.load_saved_cards()

            self.status_label.config(text=f"Удалена карта ID: {card_id}")
            messagebox.showinfo("Успех", "Карта загрузки удалена")
            self.logger.warning(f"Карта загрузки удалена ID: {card_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить карту:\n{str(e)}")
            self.logger.error(f"Ошибка удаления карты {card_id}: {e}")
            system_logger.log_error_with_traceback(f"Ошибка удаления карты {card_id}", e)

    def export_selected_card(self):
        """Экспорт выбранной карты в Excel"""
        selection = self.cards_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите карту для экспорта")
            self.logger.warning("Попытка экспорта карты без выбора")
            return

        item = self.cards_tree.item(selection[0])
        card_id = item['values'][0]

        self.export_card_to_excel(card_id)

    def export_card_to_excel(self, card_id: int):
        """Экспорт карты в Excel файл"""
        try:
            filetypes = [
                ("Файлы Excel", "*.xlsx"),
                ("Все файлы", "*.*")
            ]

            filename = filedialog.asksaveasfilename(
                title="Сохранить карту загрузки как Excel",
                initialdir=".",
                initialfile=f"карта_загрузки_{card_id}.xlsx",
                defaultextension=".xlsx",
                filetypes=filetypes
            )

            if filename:
                if db_manager.export_to_excel(card_id, filename):
                    messagebox.showinfo("Успех", f"Карта экспортирована в файл:\n{filename}")
                    self.logger.info(f"Карта ID:{card_id} экспортирована в {filename}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось экспортировать карту")
                    self.logger.error(f"Ошибка экспорта карты ID:{card_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать карту:\n{str(e)}")
            self.logger.error(f"Ошибка экспорта карты {card_id}: {e}")

    def load_warehouse_data(self):
        """Загрузка данных склада из базы данных в Treeview"""
        try:
            items = db_manager.get_warehouse_items()

            for item in self.warehouse_tree.get_children():
                self.warehouse_tree.delete(item)

            if not items:
                self.warehouse_tree.insert('', 'end', values=(
                    "Нет данных", "", "", "", "", "", ""
                ))
                return

            for idx, item in enumerate(items):
                tag = "even" if idx % 2 == 0 else "odd"
                self.warehouse_tree.insert(
                    '',
                    'end',
                    values=(
                        item['component_code'],
                        item['component_name'],
                        f"{item['current_stock']:.2f}",
                        item.get('unit', 'кг'),
                        f"{item.get('min_stock', 0):.1f}",
                        f"{item.get('max_stock', 0):.1f}",
                        item.get('location', '')
                    ),
                    tags=(tag,)
                )

            # Привязать стили к тегам (зебра)
            self.warehouse_tree.tag_configure("odd", background=self.colors['surface'])
            self.warehouse_tree.tag_configure("even", background=self.colors["row_alt"])

            self.logger.info(f"Загружено {len(items)} позиций со склада")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных склада: {e}")
            for item in self.warehouse_tree.get_children():
                self.warehouse_tree.delete(item)
            self.warehouse_tree.insert('', 'end', values=(
                f"Ошибка загрузки", str(e)[:50], "", "", "", "", ""
            ))

    def filter_warehouse_items(self):
        """Фильтрация позиций склада по поисковому запросу"""
        if not hasattr(self, 'warehouse_search_var'):
            return

        search_text = self.warehouse_search_var.get().lower()

        if not search_text:
            self.load_warehouse_data()
            return

        try:
            items = db_manager.get_warehouse_items()

            for item in self.warehouse_tree.get_children():
                self.warehouse_tree.delete(item)

            filtered_items = [item for item in items
                              if search_text in item['component_code'].lower()
                              or search_text in item['component_name'].lower()
                              or search_text in item.get('location', '').lower()]

            if not filtered_items:
                self.warehouse_tree.insert('', 'end', values=(
                    "Ничего не найдено", "", "", "", "", "", ""
                ))
                return

            for idx, item in enumerate(filtered_items):
                tag = "even" if idx % 2 == 0 else "odd"
                self.warehouse_tree.insert(
                    '',
                    'end',
                    values=(
                        item['component_code'],
                        item['component_name'],
                        f"{item['current_stock']:.2f}",
                        item.get('unit', 'кг'),
                        f"{item.get('min_stock', 0):.1f}",
                        f"{item.get('max_stock', 0):.1f}",
                        item.get('location', '')
                    ),
                    tags=(tag,)
                )

            self.warehouse_tree.tag_configure("odd", background=self.colors['surface'])
            self.warehouse_tree.tag_configure("even", background=self.colors["row_alt"])

        except Exception as e:
            self.logger.error(f"Ошибка фильтрации склада: {e}")

    def add_warehouse_item(self):
        """Добавление новой позиции на склад"""
        try:
            dialog, main_frame = self.create_dialog(
                "Добавление позиции на склад", 520, 520, header_color=self.colors['success']
            )

            fields_frame = Frame(main_frame, bg=self.colors['background'])
            fields_frame.pack(fill='x', pady=(0, 20))

            # Код
            Label(fields_frame, text="Код компонента*:",
                  font=self.fonts['body_semibold'], bg=self.colors['background'],
                  anchor='w').grid(row=0, column=0, sticky='w', pady=(0, 5))
            code_var = StringVar()
            code_entry = ttk.Entry(fields_frame, textvariable=code_var, font=self.fonts['body'],
                                   width=40)
            code_entry.grid(row=1, column=0, sticky='ew', pady=(0, 15))

            # Наименование
            Label(fields_frame, text="Наименование*:",
                  font=self.fonts['body_semibold'], bg=self.colors['background'],
                  anchor='w').grid(row=2, column=0, sticky='w', pady=(0, 5))
            name_var = StringVar()
            name_entry = ttk.Entry(fields_frame, textvariable=name_var, font=self.fonts['body'],
                                   width=40)
            name_entry.grid(row=3, column=0, sticky='ew', pady=(0, 15))

            # Ед. изм.
            Label(fields_frame, text="Единица измерения:",
                  font=self.fonts['body_semibold'], bg=self.colors['background'],
                  anchor='w').grid(row=4, column=0, sticky='w', pady=(0, 5))
            unit_var = StringVar(value="кг")
            unit_entry = ttk.Entry(fields_frame, textvariable=unit_var, font=self.fonts['body'],
                                   width=40)
            unit_entry.grid(row=5, column=0, sticky='ew', pady=(0, 15))

            # Остаток
            Label(fields_frame, text="Начальный остаток:",
                  font=self.fonts['body_semibold'], bg=self.colors['background'],
                  anchor='w').grid(row=6, column=0, sticky='w', pady=(0, 5))
            stock_var = StringVar(value="0.0")
            stock_entry = ttk.Entry(fields_frame, textvariable=stock_var, font=self.fonts['body'],
                                    width=40)
            stock_entry.grid(row=7, column=0, sticky='ew', pady=(0, 15))

            # Местоположение
            Label(fields_frame, text="Местоположение:",
                  font=self.fonts['body_semibold'], bg=self.colors['background'],
                  anchor='w').grid(row=8, column=0, sticky='w', pady=(0, 5))
            location_var = StringVar()
            location_entry = ttk.Entry(fields_frame, textvariable=location_var, font=self.fonts['body'],
                                       width=40)
            location_entry.grid(row=9, column=0, sticky='ew', pady=(0, 15))

            code_entry.focus_set()

            def save_item():
                if not code_var.get().strip():
                    messagebox.showwarning("Внимание", "Введите код компонента!")
                    code_entry.focus_set()
                    return

                if not name_var.get().strip():
                    messagebox.showwarning("Внимание", "Введите наименование!")
                    name_entry.focus_set()
                    return

                try:
                    stock = float(stock_var.get().replace(',', '.'))
                except ValueError:
                    messagebox.showwarning("Внимание", "Остаток должен быть числом!")
                    stock_entry.focus_set()
                    return

                try:
                    existing = db_manager.get_warehouse_items()
                    for item in existing:
                        if item['component_code'] == code_var.get().strip():
                            if not messagebox.askyesno("Подтверждение",
                                                       f"Компонент с кодом '{code_var.get()}' уже существует.\n"
                                                       "Продолжить?"):
                                return

                    db_manager.add_warehouse_item(
                        component_code=code_var.get().strip(),
                        component_name=name_var.get().strip(),
                        current_stock=stock,
                        unit=unit_var.get().strip(),
                        location=location_var.get().strip(),
                        min_stock=0.0,
                        max_stock=1000.0
                    )

                    self.logger.info(f"Добавлена позиция на склад: {code_var.get()} - {name_var.get()}")
                    system_logger.log_operation("add_warehouse_item",
                                                f"Добавлен компонент: {name_var.get()} ({code_var.get()})",
                                                user="user")

                    self.load_warehouse_data()
                    dialog.destroy()
                    messagebox.showinfo("Успех", "Позиция успешно добавлена на склад!")

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось добавить позицию:\n{str(e)}")
                    self.logger.error(f"Ошибка добавления позиции: {e}")

            dialog.bind('<Return>', lambda e: save_item())

            button_frame = Frame(main_frame, bg=self.colors['background'], pady=10)
            button_frame.pack(side='bottom', fill='x')

            add_button = self.create_modern_button(
                button_frame, "Добавить", save_item, 'success', '➕'
            )
            add_button.pack(side='left', padx=(0, 10))

            cancel_button = self.create_modern_button(
                button_frame, "Отмена", dialog.destroy, 'secondary', '❌'
            )
            cancel_button.pack(side='right')

            self.logger.debug("Открыто диалоговое окно добавления позиции на склад")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога добавления позиции: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть диалог добавления:\n{str(e)}")

    def import_warehouse_from_excel(self):
        """Импорт данных склада из Excel файла"""
        try:
            filetypes = [
                ("Файлы Excel", "*.xlsx *.xls"),
                ("Все файлы", "*.*")
            ]

            filename = filedialog.askopenfilename(
                title="Выберите файл Excel для импорта склада",
                initialdir=".",
                filetypes=filetypes
            )

            if not filename:
                return

            system_logger.log_operation("import_warehouse_excel",
                                        f"Начало импорта склада из файла: {filename}",
                                        user="user")

            self.status_label.config(text="Импорт данных склада...")
            self.root.update()

            success = db_manager.import_warehouse_from_excel(filename)

            if success:
                self.load_warehouse_data()
                self.status_label.config(text=f"Данные склада импортированы из {os.path.basename(filename)}")

                system_logger.log_operation("import_warehouse_excel",
                                            f"Успешный импорт склада из {filename}",
                                            user="user",
                                            level=LogLevel.INFO)

                messagebox.showinfo("Успех",
                                    f"Данные склада успешно импортированы!\n\n"
                                    f"Файл: {os.path.basename(filename)}")
            else:
                self.status_label.config(text="Ошибка импорта данных склада")
                messagebox.showerror("Ошибка",
                                     "Не удалось импортировать данные склада из файла.\n"
                                     "Проверьте формат файла и наличие обязательных колонок.")

        except Exception as e:
            self.logger.error(f"Ошибка импорта склада: {e}")
            self.status_label.config(text="Ошибка импорта склада")
            messagebox.showerror("Ошибка", f"Не удалось импортировать данные склада:\n{str(e)}")
            system_logger.log_error_with_traceback("Ошибка импорта склада", e)

    def export_warehouse_via_dialog(self):
        """Выбор файла и экспорт склада (для маленькой кнопки 📤 на вкладке Склад)"""
        filetypes = [
            ("Файлы Excel", "*.xlsx"),
            ("Все файлы", "*.*")
        ]

        default_name = f"склад_{datetime.now().strftime('%Y%m%d')}.xlsx"
        filename = filedialog.asksaveasfilename(
            title="Сохранить данные склада",
            initialdir=".",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=filetypes
        )

        if not filename:
            return

        try:
            self.export_warehouse(filename)
            messagebox.showinfo("Успех", f"Данные склада экспортированы в:\n{filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные склада:\n{e}")
            self.logger.error(f"Ошибка экспорта склада: {e}")

    def open_editor_tab(self):
        """Открыть новую вкладку с редактором"""
        try:
            system_logger.log_operation("open_editor_tab",
                                        "Создание новой вкладки редактора",
                                        user="user")

            tab_id = f"editor_{len(self.open_editors) + 1}"
            tab_title = f"📝 РЕДАКТОР {len(self.open_editors) + 1}"

            tab_frame = Frame(self.tab_manager.content_area, bg=self.colors['background'])
            self.tab_manager.add_tab(tab_id, tab_title, tab_frame, closable=True)

            try:
                from modules.loading_card_tab import LoadingCardTab
                editor = LoadingCardTab(tab_frame, self)
                editor.pack(fill='both', expand=True)
            except ImportError as e:
                self.logger.error(f"Не удалось импортировать LoadingCardTab: {e}")
                self.tab_manager.close_tab(tab_id)
                messagebox.showwarning("Предупреждение",
                                       "Модуль редактора карт не найден. Функционал будет доступен после установки.")
                return
            except Exception as e:
                self.logger.error(f"Ошибка создания редактора: {e}")
                self.tab_manager.close_tab(tab_id)
                messagebox.showerror("Ошибка", f"Не удалось создать редактор:\n{str(e)}")
                return

            self.open_editors[tab_id] = editor
            self.tab_manager.select_tab(tab_id)

            self.status_label.config(text=f"Открыт редактор {len(self.open_editors)}")
            self.logger.info(f"Открыта новая вкладка редактора: {tab_title}")

            system_logger.log_operation("open_editor_tab",
                                        f"Создана вкладка редактора {tab_id}",
                                        user="user",
                                        level=LogLevel.INFO)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть редактор:\n{str(e)}")
            self.logger.error(f"Ошибка открытия редактора: {e}")
            system_logger.log_error_with_traceback("Ошибка открытия редактора", e)

    def close_editor_tab(self, tab_id):
        """Закрыть вкладку редактора по идентификатору"""
        try:
            if tab_id in self.open_editors:
                del self.open_editors[tab_id]

            self.tab_manager.close_tab(tab_id)

            self.logger.info(f"Вкладка редактора {tab_id} закрыта. Осталось {len(self.open_editors)} вкладок.")

        except Exception as e:
            self.logger.error(f"Ошибка закрытия вкладки редактора: {e}")
            messagebox.showerror("Ошибка", f"Не удалось закрыть вкладку:\n{str(e)}")

    def on_tab_changed(self, tab_id, tab_text):
        """Обработчик изменения вкладки (вызывается TabManager)"""
        try:

            status_texts = {
                "home": "Главная страница • Готов к работе",
                "cards": "Просмотр карт загрузок",
                "warehouse": "Управление складом",
                "nomenclature": "Справочник номенклатуры (продуктов)",
                "logs": "Просмотр системных логов",
                "import_export": "Импорт и экспорт данных",
                "finished_products": "Управление готовой продукцией",
                "invoice": "Формирование счетов"
            }

            self.status_label.config(text=status_texts.get(tab_id, "Готов к работе"))
            self.logger.debug(f"Переключена вкладка: {tab_text} ({tab_id})")

        except Exception as e:
            self.logger.error(f"Ошибка обработки переключения вкладки: {e}")

    def on_tab_closed(self, tab_id):
        """Обработчик закрытия вкладки (вызывается TabManager)"""
        try:
            if tab_id in self.open_editors:
                del self.open_editors[tab_id]
                self.logger.info(f"Редактор {tab_id} удален из списка открытых")
        except Exception as e:
            self.logger.error(f"Ошибка обработки закрытия вкладки: {e}")

    # ===================== МЕТОДЫ ДЛЯ РАБОТЫ С ЛОГАМИ =====================

    def load_log_files(self):
        """Загрузка списка файлов логов"""
        try:
            log_files = system_logger.get_log_files()

            if hasattr(self, 'log_files_listbox'):
                self.log_files_listbox.delete(0, END)

            if not log_files:
                if hasattr(self, 'log_files_listbox'):
                    self.log_files_listbox.insert(END, "Файлы логов не найдены")
                return

            for log_file in log_files:
                size_mb = log_file['size'] / (1024 * 1024)
                if size_mb < 1:
                    size_str = f"{log_file['size'] / 1024:.1f} КБ"
                else:
                    size_str = f"{size_mb:.1f} МБ"

                display_text = f"{log_file['name']} ({size_str})"
                if hasattr(self, 'log_files_listbox'):
                    self.log_files_listbox.insert(END, display_text)

            if log_files and hasattr(self, 'log_files_listbox'):
                self.log_files_listbox.selection_set(0)
                self.on_log_file_selected()

            self.logger.debug(f"Загружено {len(log_files)} файлов логов")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки списка файлов логов: {e}")
            if hasattr(self, 'log_files_listbox'):
                self.log_files_listbox.insert(END, f"Ошибка загрузки: {str(e)}")

    def load_logs(self):
        """Загрузка и фильтрация содержимого логов"""
        try:
            if not hasattr(self, 'log_files_listbox'):
                return

            selection = self.log_files_listbox.curselection()
            if not selection:
                return

            selected_text = self.log_files_listbox.get(selection[0])
            file_name = selected_text.split(' (')[0]

            log_files = system_logger.get_log_files()
            selected_file = None
            for log_file in log_files:
                if log_file['name'] == file_name:
                    selected_file = log_file
                    break

            if not selected_file:
                if hasattr(self, 'log_text'):
                    self.log_text.delete(1.0, END)
                    self.log_text.insert(END, "Файл не найден")
                return

            with open(selected_file['path'], 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if hasattr(self, 'log_text'):
                self.log_text.delete(1.0, END)

            log_level = self.log_level_var.get() if hasattr(self, 'log_level_var') else "ALL"
            search_text = self.log_search_var.get().lower() if hasattr(self, 'log_search_var') else ""

            filtered_count = 0
            total_count = 0

            for line in lines:
                total_count += 1

                if log_level != "ALL":
                    if not any(level in line for level in [' - ' + log_level + ' - ', ' ' + log_level + ' ']):
                        continue

                if search_text and search_text not in line.lower():
                    continue

                if ' - DEBUG - ' in line:
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(END, line, 'DEBUG')
                elif ' - INFO - ' in line:
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(END, line, 'INFO')
                elif ' - WARNING - ' in line:
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(END, line, 'WARNING')
                elif ' - ERROR - ' in line:
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(END, line, 'ERROR')
                elif ' - CRITICAL - ' in line:
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(END, line, 'CRITICAL')
                else:
                    if hasattr(self, 'log_text'):
                        self.log_text.insert(END, line)

                filtered_count += 1

            if hasattr(self, 'log_text'):
                self.log_text.see(END)

            self.logger.debug(f"Загружено {filtered_count}/{total_count} строк из лога {file_name}")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки логов: {e}")
            if hasattr(self, 'log_text'):
                self.log_text.delete(1.0, END)
                self.log_text.insert(END, f"Ошибка загрузки файла: {str(e)}")

    def on_log_file_selected(self, event=None):
        """Обработчик выбора файла лога"""
        self.load_logs()

    def clear_logs(self):
        """Очистка файлов логов"""
        if not messagebox.askyesno("Подтверждение",
                                   "Очистить все файлы логов?\n\n"
                                   "Это действие необратимо!"):
            self.logger.info("Пользователь отменил очистку логов")
            return

        try:
            system_logger.log_operation("clear_logs",
                                        "Очистка всех файлов логов",
                                        user="user",
                                        level=LogLevel.WARNING)

            deleted_count = 0
            for log_file in system_logger.log_dir.glob("*.log*"):
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Ошибка удаления файла {log_file}: {e}")

            self.load_log_files()

            if hasattr(self, 'log_text'):
                self.log_text.delete(1.0, END)

            messagebox.showinfo("Успех", f"Удалено {deleted_count} файлов логов")
            self.logger.warning(f"Очищено {deleted_count} файлов логов")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить логи:\n{str(e)}")
            self.logger.error(f"Ошибка очистки логов: {e}")
            system_logger.log_error_with_traceback("Ошибка очистки логов", e)

    # ===================== МЕТОДЫ ДЛЯ ИМПОРТА/ЭКСПОРТА ОСНОВНЫХ ДАННЫХ =====================

    def select_import_file(self):
        """Выбор файла для импорта"""
        filetypes = [
            ("Файлы Excel", "*.xlsx *.xls"),
            ("Все файлы", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Выберите файл Excel для импорта",
            initialdir=".",
            filetypes=filetypes
        )

        if filename:
            self.import_file_var.set(filename)
            if hasattr(self, 'import_status_label'):
                self.import_status_label.config(text=f"Выбран файл: {os.path.basename(filename)}",
                                                fg=self.colors['primary'])

    def start_import(self):
        """Запуск импорта данных из Excel"""
        filename = self.import_file_var.get()

        if not filename or not os.path.exists(filename):
            messagebox.showwarning("Внимание", "Выберите файл для импорта")
            return

        try:
            if hasattr(self, 'import_status_label'):
                self.import_status_label.config(text="Импорт данных...", fg=self.colors['warning'])
            self.root.update()

            if hasattr(self, 'create_backup_var') and self.create_backup_var.get():
                backup_name = f"loading_cards_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                import shutil
                shutil.copy2(db_manager.db_path, backup_name)
                self.logger.info(f"Создана резервная копия базы данных: {backup_name}")

            success = db_manager.import_from_excel(
                filename,
                self.replace_existing_var.get() if hasattr(self, 'replace_existing_var') else False
            )

            if success:
                if hasattr(self, 'import_status_label'):
                    self.import_status_label.config(text="✓ Импорт успешно завершен", fg=self.colors['success'])
                messagebox.showinfo("Успех", f"Данные успешно импортированы из файла:\n{filename}")

                if hasattr(self, 'load_nomenclature_tree'):
                    self.load_nomenclature_tree()
                self.load_saved_cards()
                self.load_warehouse_data()

                self.logger.info(f"Импорт данных из {filename} выполнен успешно")
                system_logger.log_operation("import_data",
                                            f"Импорт из файла: {filename}",
                                            user="user",
                                            level=LogLevel.INFO)
            else:
                if hasattr(self, 'import_status_label'):
                    self.import_status_label.config(text="✗ Ошибка импорта", fg=self.colors['danger'])
                messagebox.showerror("Ошибка", "Не удалось импортировать данные из файла")
                self.logger.error(f"Ошибка импорта данных из {filename}")

        except Exception as e:
            if hasattr(self, 'import_status_label'):
                self.import_status_label.config(text="✗ Ошибка импорта", fg=self.colors['danger'])
            messagebox.showerror("Ошибка", f"Ошибка импорта:\n{str(e)}")
            self.logger.error(f"Ошибка импорта: {e}")
            system_logger.log_error_with_traceback("Ошибка импорта", e)

    def select_export_path(self):
        """Выбор пути для экспорта"""
        filetypes = [
            ("Файлы Excel", "*.xlsx"),
            ("Все файлы", "*.*")
        ]

        export_type = self.export_type_var.get() if hasattr(self, 'export_type_var') else "cards"
        default_name = f"export_{export_type}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        filename = filedialog.asksaveasfilename(
            title="Выберите путь для экспорта",
            initialdir=".",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=filetypes
        )

        if filename:
            self.export_path_var.set(filename)
            if hasattr(self, 'export_status_label'):
                self.export_status_label.config(text=f"Путь для экспорта: {os.path.basename(filename)}",
                                                fg=self.colors['primary'])

    def start_export(self):
        """Запуск экспорта данных в Excel"""
        export_path = self.export_path_var.get()
        export_type = self.export_type_var.get() if hasattr(self, 'export_type_var') else "cards"

        if not export_path:
            messagebox.showwarning("Внимание", "Выберите путь для экспорта")
            return

        try:
            if hasattr(self, 'export_status_label'):
                self.export_status_label.config(text="Экспорт данных...", fg=self.colors['warning'])
            self.root.update()

            if export_type == "cards":
                self.export_all_cards(export_path)
            elif export_type == "products":
                self.export_products(export_path)
            elif export_type == "warehouse":
                self.export_warehouse(export_path)

            if hasattr(self, 'export_status_label'):
                self.export_status_label.config(text="✓ Экспорт успешно завершен", fg=self.colors['success'])
            messagebox.showinfo("Успех", f"Данные успешно экспортированы в файл:\n{export_path}")

            self.logger.info(f"Экспорт {export_type} данных в {export_path} выполнен успешно")
            system_logger.log_operation("export_data",
                                        f"Экспорт {export_type} в файл: {export_path}",
                                        user="user",
                                        level=LogLevel.INFO)

        except Exception as e:
            if hasattr(self, 'export_status_label'):
                self.export_status_label.config(text="✗ Ошибка экспорта", fg=self.colors['danger'])
            messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{str(e)}")
            self.logger.error(f"Ошибка экспорта: {e}")
            system_logger.log_error_with_traceback("Ошибка экспорта", e)

    def export_all_cards(self, output_path: str):
        """Экспорт всех карт загрузок в Excel"""
        cards = db_manager.get_loading_cards(limit=1000)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            cards_list = []
            for card in cards:
                cards_list.append({
                    'ID': card['id'],
                    'Название карты': card['card_name'],
                    'Продукт': card.get('product_name', ''),
                    'Код продукта': card['product_code'],
                    'Рецептура': card.get('recipe_number', ''),
                    'Реактор': card.get('reactor', ''),
                    'Количество, кг': card.get('batch_quantity', 0.0),
                    'Общая масса, кг': card.get('total_mass', 0.0),
                    'Дата создания': card['created_date'],
                    'Статус': card.get('status', '')
                })

            if cards_list:
                pd.DataFrame(cards_list).to_excel(writer, sheet_name='Список карт', index=False)

            for card in cards[:10]:
                components = db_manager.get_card_components(card['id'])
                if components:
                    comp_data = []
                    for i, comp in enumerate(components, 1):
                        comp_data.append({
                            '№': i,
                            'Код компонента': comp['component_code'],
                            'Наименование': comp['component_name'],
                            'Процент, %': comp['percentage'],
                            'Масса, кг': comp['calculated_mass']
                        })

                    sheet_name = f"Карта_{card['id']}"[:31]
                    pd.DataFrame(comp_data).to_excel(writer, sheet_name=sheet_name, index=False)

    def export_products(self, output_path: str):
        """Экспорт справочника продуктов в Excel"""
        products = db_manager.get_products()

        products_list = []
        for product in products:
            products_list.append({
                'Код продукта': product['product_code'],
                'Наименование': product['product_name'],
                'Описание': product.get('description', ''),
                'Количество рецептур': product.get('recipe_count', 0),
                'Дата создания': product['created_date'],
                'Дата обновления': product.get('updated_date', '')
            })

        if products_list:
            df = pd.DataFrame(products_list)
            df.to_excel(output_path, index=False, engine='openpyxl')

    def export_warehouse(self, output_path: str):
        """Экспорт данных склада в Excel"""
        items = db_manager.get_warehouse_items()

        warehouse_list = []
        for item in items:
            warehouse_list.append({
                'Код компонента': item['component_code'],
                'Наименование': item['component_name'],
                'Текущий остаток': item['current_stock'],
                'Единица измерения': item.get('unit', 'кг'),
                'Минимальный запас': item.get('min_stock', 0.0),
                'Максимальный запас': item.get('max_stock', 0.0),
                'Местоположение': item.get('location', ''),
                'Поставщик': item.get('supplier', ''),
                'Дата обновления': item.get('last_updated', '')
            })

        if warehouse_list:
            df = pd.DataFrame(warehouse_list)
            df.to_excel(output_path, index=False, engine='openpyxl')

    # ===================== МЕТОДЫ ДЛЯ ИМПОРТА/ЭКСПОРТА НОРМ =====================

    def select_norms_file(self):
        """Выбор файла Excel с нормами"""
        filetypes = [
            ("Файлы Excel", "*.xlsx *.xls"),
            ("Все файлы", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Выберите файл Excel с нормами показателей",
            initialdir=".",
            filetypes=filetypes
        )

        if filename:
            self.norms_file_var.set(filename)
            if hasattr(self, 'norms_import_status_label'):
                self.norms_import_status_label.config(text=f"Выбран файл: {os.path.basename(filename)}",
                                                      fg=self.colors['primary'])

    def start_norms_import(self):
        """Запуск импорта норм из Excel"""
        filename = self.norms_file_var.get()

        if not filename or not os.path.exists(filename):
            messagebox.showwarning("Внимание", "Выберите файл для импорта норм")
            return

        try:
            if hasattr(self, 'norms_import_status_label'):
                self.norms_import_status_label.config(text="Импорт норм...", fg=self.colors['warning'])
            self.root.update()

            replace_existing = self.norms_replace_var.get() if hasattr(self, 'norms_replace_var') else False

            success = db_manager.import_norms_from_excel(filename, replace_existing)

            if success:
                if hasattr(self, 'norms_import_status_label'):
                    self.norms_import_status_label.config(text="✓ Нормы успешно импортированы",
                                                          fg=self.colors['success'])

                self.load_products_with_norms()

                messagebox.showinfo("Успех",
                                    f"Нормы физико-химических показателей успешно импортированы из файла:\n{filename}\n\n"
                                    f"Файл: {os.path.basename(filename)}\n"
                                    f"Тип импорта: {'Заменить существующие' if replace_existing else 'Добавить новые'}")

                self.logger.info(f"Нормы импортированы из {filename}")

            else:
                if hasattr(self, 'norms_import_status_label'):
                    self.norms_import_status_label.config(text="✗ Ошибка импорта норм", fg=self.colors['danger'])
                messagebox.showerror("Ошибка",
                                     "Не удалось импортировать нормы из файла.\n"
                                     "Проверьте формат файла и наличие обязательных колонок.")

        except Exception as e:
            if hasattr(self, 'norms_import_status_label'):
                self.norms_import_status_label.config(text="✗ Ошибка импорта норм", fg=self.colors['danger'])
            messagebox.showerror("Ошибка", f"Ошибка импорта норм:\n{str(e)}")
            self.logger.error(f"Ошибка импорта норм: {e}")

    def load_products_with_norms(self):
        """Загрузка списка продуктов с нормами"""
        try:
            products = db_manager.get_products_with_norms()

            if hasattr(self, 'export_norms_combo'):
                product_list = [f"{p['product_code']} - {p['product_name']} ({p.get('norm_count', 0)} норм)"
                                for p in products]
                self.export_norms_combo['values'] = product_list

                if product_list:
                    self.export_norms_combo.current(0)

        except Exception as e:
            self.logger.error(f"Ошибка загрузки продуктов с нормами: {e}")

    def select_norms_export_path(self):
        """Выбор пути для экспорта норм"""
        filetypes = [
            ("Файлы Excel", "*.xlsx"),
            ("Все файлы", "*.*")
        ]

        export_type = self.export_norms_type_var.get() if hasattr(self, 'export_norms_type_var') else "selected"
        default_name = f"нормы_показателей_{datetime.now().strftime('%Y%m%d')}.xlsx"

        if export_type == "selected" and hasattr(self, 'export_norms_product_var'):
            selected = self.export_norms_product_var.get()
            if selected and " - " in selected:
                product_code = selected.split(" - ")[0]
                default_name = f"нормы_{product_code}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        filename = filedialog.asksaveasfilename(
            title="Выберите путь для экспорта норм",
            initialdir=".",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=filetypes
        )

        if filename:
            self.norms_export_path_var.set(filename)
            if hasattr(self, 'norms_export_status_label'):
                self.norms_export_status_label.config(text=f"Путь для экспорта: {os.path.basename(filename)}",
                                                      fg=self.colors['primary'])

    def start_norms_export(self):
        """Запуск экспорта норм в Excel"""
        export_path = self.norms_export_path_var.get()
        export_type = self.export_norms_type_var.get() if hasattr(self, 'export_norms_type_var') else "selected"

        if not export_path:
            messagebox.showwarning("Внимание", "Выберите путь для экспорта норм")
            return

        try:
            if hasattr(self, 'norms_export_status_label'):
                self.norms_export_status_label.config(text="Экспорт норм...", fg=self.colors['warning'])
            self.root.update()

            product_code = None
            if export_type == "selected" and hasattr(self, 'export_norms_product_var'):
                selected = self.export_norms_product_var.get()
                if selected and " - " in selected:
                    product_code = selected.split(" - ")[0]

            success = db_manager.export_norms_to_excel(export_path, product_code)

            if success:
                if hasattr(self, 'norms_export_status_label'):
                    self.norms_export_status_label.config(text="✓ Нормы успешно экспортированы",
                                                          fg=self.colors['success'])
                messagebox.showinfo("Успех",
                                    f"Нормы физико-химических показателей успешно экспортированы в файл:\n{export_path}\n\n"
                                    f"Тип экспорта: {'Выбранный продукт' if product_code else 'Все продукты'}")

                self.logger.info(f"Нормы экспортированы в {export_path}")

            else:
                if hasattr(self, 'norms_export_status_label'):
                    self.norms_export_status_label.config(text="✗ Ошибка экспорта норм", fg=self.colors['danger'])
                messagebox.showerror("Ошибка", "Не удалось экспортировать нормы.")
        except Exception as e:
            if hasattr(self, 'norms_export_status_label'):
                self.norms_export_status_label.config(text="✗ Ошибка экспорта норм", fg=self.colors['danger'])
            messagebox.showerror("Ошибка", f"Ошибка экспорта норм:\n{str(e)}")
            self.logger.error(f"Ошибка экспорта норм: {e}")

    # ===================== ВКЛАДКА ТРЕБОВАНИЕ-НАКЛАДНАЯ =====================

    def create_invoice_tab(self, parent=None):
        """Создание вкладки требования-накладной"""
        try:
            if parent is None:
                parent = self.tab_manager.content_area
            inv_tab = Frame(parent, bg=self.colors['background'])

            container = Frame(inv_tab, bg=self.colors['background'])
            container.pack(fill='both', expand=True, padx=20, pady=20)

            # ===== ВЕРХНЯЯ ПАНЕЛЬ: КНОПКИ =====
            header_frame = Frame(container, bg=self.colors['background'])
            header_frame.pack(fill='x', pady=(0, 5))

            # Заголовок
            title_frame = Frame(header_frame, bg=self.colors['background'])
            title_frame.pack(side='left', fill='x', expand=True)

            Label(title_frame, text="📄 Требования-накладные",
                  font=self.fonts['h2'],
                  bg=self.colors['background'],
                  fg=self.colors['on_background']).pack(anchor='w')

            Label(title_frame,
                  text="Списание, перемещение и приход сырья на склад",
                  font=self.fonts['caption'],
                  bg=self.colors['background'],
                  fg=self.colors['text_muted']).pack(anchor='w', pady=(2, 0))

            # Панель действий справа
            actions_frame = Frame(header_frame, bg=self.colors['background'])
            actions_frame.pack(side='right')

            create_btn = ttk.Button(
                actions_frame,
                text="➕ Создать накладную",
                command=self.create_invoice_dialog,
                style="Modern.TButton",
                cursor="hand2"
            )
            create_btn.pack(side='left', padx=3)

            post_btn = ttk.Button(
                actions_frame,
                text="✅ Провести",
                command=self.post_selected_invoice,
                style="Modern.TButton",
                cursor="hand2"
            )
            post_btn.pack(side='left', padx=3)

            refresh_btn = ttk.Button(
                actions_frame,
                text="🔄",
                command=self.load_invoices_list,
                style="Compact.TButton"
            )
            refresh_btn.pack(side='left', padx=3)

            ToolTip(create_btn, "Создать новый документ требования-накладной")
            ToolTip(post_btn, "Провести выбранную накладную: обновить складские остатки согласно документу")
            ToolTip(refresh_btn, "Обновить список накладных")

            # ===== КАРТОЧКА С ТАБЛИЦЕЙ АРХИВА =====
            table_card = Frame(
                container,
                bg=self.colors['surface'],
                bd=0,
                highlightbackground=self.colors['border'],
                highlightthickness=1
            )
            table_card.pack(fill='both', expand=True, padx=5, pady=5)

            table_inner = Frame(table_card, bg=self.colors['surface'])
            table_inner.pack(fill='both', expand=True, padx=1, pady=1)

            columns = ('ID', 'Номер', 'Тип', 'Откуда', 'Куда', 'Позиций', 'Всего, кг', 'Статус', 'Дата')
            self.invoices_tree = ttk.Treeview(table_inner, columns=columns, show='headings', height=18)

            column_widths = [40, 160, 100, 120, 120, 70, 90, 80, 140]
            for idx, col in enumerate(columns):
                self.invoices_tree.heading(col, text=col)
                self.invoices_tree.column(col, width=column_widths[idx], anchor='center', stretch=True)

            # Настройка отображения типа операции
            self.invoices_tree.tag_configure('write_off', foreground=self.colors['danger'])
            self.invoices_tree.tag_configure('transfer', foreground=self.colors['warning'])
            self.invoices_tree.tag_configure('receipt', foreground=self.colors['success'])
            self.invoices_tree.tag_configure('active', foreground=self.colors['on_surface'])
            self.invoices_tree.tag_configure('reverted', foreground=self.colors['text_muted'])

            scrollbar = Scrollbar(table_inner, orient='vertical', command=self.invoices_tree.yview)
            self.invoices_tree.configure(yscrollcommand=scrollbar.set)

            self.invoices_tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            self.invoices_tree.bind('<Double-Button-1>', lambda e: self.view_invoice_details())

            # ===== НИЖНЯЯ ПАНЕЛЬ ИНФОРМАЦИИ =====
            info_frame = Frame(container, bg=self.colors['background'])
            info_frame.pack(fill='x', pady=(8, 0))

            self.invoice_info_label = Label(
                info_frame,
                text="Дважды кликните по накладной для просмотра деталей",
                font=self.fonts['caption'],
                bg=self.colors['background'],
                fg=self.colors['text_muted']
            )
            self.invoice_info_label.pack(side='left')

            delete_btn = ttk.Button(
                info_frame,
                text="🗑️ Удалить",
                command=self.delete_selected_invoice,
                style="Compact.TButton"
            )
            delete_btn.pack(side='right', padx=3)

            pdf_btn = ttk.Button(
                info_frame,
                text="📄 PDF",
                command=self.export_invoice_pdf,
                style="Compact.TButton"
            )
            pdf_btn.pack(side='right', padx=3)

            print_btn = ttk.Button(
                info_frame,
                text="🖨️ Печать",
                command=self.print_invoice,
                style="Compact.TButton"
            )
            print_btn.pack(side='right', padx=3)

            ToolTip(pdf_btn, "Экспорт выбранной накладной в PDF")
            ToolTip(print_btn, "Печать выбранной накладной")
            ToolTip(delete_btn, "Удалить выбранную накладную")

            # Загружаем список накладных
            self.load_invoices_list()

            self.logger.debug("Вкладка 'Требование-накладная' создана успешно")
            return inv_tab

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки накладных: {e}")
            raise

    def load_invoices_list(self):
        """Загрузить список требований-накладных"""
        try:
            if not hasattr(self, 'invoices_tree'):
                return

            for item in self.invoices_tree.get_children():
                self.invoices_tree.delete(item)

            invoices = db_manager.get_invoices(limit=200)

            if not invoices:
                self.invoice_info_label.config(text="Нет сохранённых накладных. Создайте новую.")
                return

            op_labels = {
                'write_off': 'Списание',
                'transfer': 'Перемещение',
                'receipt': 'Приход'
            }
            status_labels = {
                'active': 'Активна',
                'draft': 'Черновик',
                'reverted': 'Отменена'
            }

            for inv in invoices:
                op_type = inv['operation_type']
                op_label = op_labels.get(op_type, op_type)
                status = inv['status']
                status_label = status_labels.get(status, status)

                row_tag = inv['status'] if inv['status'] in ('active', 'reverted') else 'active'

                self.invoices_tree.insert('', 'end', values=(
                    inv['id'],
                    inv['invoice_number'],
                    op_label,
                    inv.get('source_location') or '',
                    inv.get('destination_location') or '',
                    inv.get('item_count', 0),
                    f"{inv.get('total_quantity', 0):.1f}" if inv.get('total_quantity') else '0',
                    status_label,
                    (inv['created_date'][:16] if inv.get('created_date') else '')
                ), tags=(op_type, inv['status']))

            self.invoice_info_label.config(text=f"Загружено накладных: {len(invoices)}")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки списка накладных: {e}")

    def create_invoice_dialog(self):
        """Диалог создания нового требования-накладной"""
        try:
            warehouse_items = db_manager.get_warehouse_items()
            warehouse_map = {w['component_code']: w for w in warehouse_items}

            dialog, main_frame = self.create_dialog(
                "Создание требования-накладной", 950, 850,
                header_color=self.colors['primary']
            )
            dialog.resizable(True, True)

            # ===== ПАРАМЕТРЫ ДОКУМЕНТА =====
            params_frame = LabelFrame(main_frame, text="Параметры документа",
                                      font=self.fonts['body_semibold'],
                                      padx=15, pady=10, bg=self.colors['background'])
            params_frame.pack(fill='x', pady=(0, 15))

            # Первая строка: номер и тип операции
            row1 = Frame(params_frame, bg=self.colors['background'])
            row1.pack(fill='x', pady=5)

            Label(row1, text="Номер накладной:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(side='left')
            inv_number = StringVar(value=db_manager.get_next_invoice_number())
            ttk.Entry(row1, textvariable=inv_number, width=28,
                      font=self.fonts['body']).pack(side='left', padx=(10, 30))

            Label(row1, text="Тип операции:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(side='left')
            op_type_var = StringVar(value='write_off')
            op_combo = ttk.Combobox(row1, textvariable=op_type_var,
                                    values=['Списание', 'Перемещение', 'Приход'],
                                    state='readonly', width=18, style="Modern.TCombobox")
            op_combo.pack(side='left', padx=(10, 0))

            # Вторая строка: откуда/куда (зависит от типа)
            row2 = Frame(params_frame, bg=self.colors['background'])
            row2.pack(fill='x', pady=5)

            self._inv_source_label = Label(row2, text="Откуда (склад/цех):",
                                           font=self.fonts['body'],
                                           bg=self.colors['background'])
            self._inv_source_label.pack(side='left')
            source_var = StringVar(value="Основной склад")
            source_entry = ttk.Entry(row2, textvariable=source_var, width=28,
                                     font=self.fonts['body'])
            source_entry.pack(side='left', padx=(10, 30))

            self._inv_dest_label = Label(row2, text="Куда (цех/склад):",
                                         font=self.fonts['body'],
                                         bg=self.colors['background'])
            self._inv_dest_label.pack(side='left')
            dest_var = StringVar(value="Цех производства")
            dest_entry = ttk.Entry(row2, textvariable=dest_var, width=28,
                                   font=self.fonts['body'])
            dest_entry.pack(side='left', padx=(10, 0))

            # Скрываем/показываем поля в зависимости от типа операции
            def on_op_type_change(*args):
                try:
                    op = op_type_var.get()
                    if op == 'Списание':
                        self._inv_source_label.config(text="Откуда (склад/цех):")
                        source_var.set("Основной склад")
                        dest_entry.pack_forget()
                        self._inv_dest_label.pack_forget()
                        dest_entry.config(state='disabled')
                        dest_var.set("— списание —")
                    elif op == 'Приход':
                        self._inv_source_label.config(text="Поставщик:")
                        source_var.set("Поставщик")
                        dest_entry.pack_forget()
                        self._inv_dest_label.pack_forget()
                        dest_entry.config(state='disabled')
                        dest_var.set("— приход —")
                    else:  # Перемещение
                        self._inv_source_label.config(text="Откуда (склад/цех):")
                        source_var.set("Основной склад")
                        self._inv_dest_label.pack()
                        dest_entry.config(state='normal')
                        dest_entry.pack(side='left', padx=(10, 0))
                        dest_var.set("Цех производства")
                except Exception as ex:
                    self.logger.error(f"Ошибка on_op_type_change: {ex}")

            op_combo.bind('<<ComboboxSelected>>', on_op_type_change)
            on_op_type_change()

            # Примечание
            Label(params_frame, text="Примечание:",
                  font=self.fonts['body'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 2))
            notes_var = StringVar()
            ttk.Entry(params_frame, textvariable=notes_var, font=self.fonts['body']).pack(fill='x')

            # ===== ТАБЛИЦА ПОЗИЦИЙ =====
            items_frame = LabelFrame(main_frame, text="Позиции накладной",
                                     font=self.fonts['body_semibold'],
                                     padx=10, pady=10, bg=self.colors['background'])
            items_frame.pack(fill='both', expand=True, pady=(0, 10))

            # Кнопки управления таблицей
            btn_row = Frame(items_frame, bg=self.colors['background'])
            btn_row.pack(fill='x', pady=(0, 8))

            # Кнопки управления таблицей будут добавлены позже,
            # после создания таблицы и определения функций сохранения/экспорта,
            # чтобы избежать ошибки захвата неопределённых переменных.

            # Таблица позиций
            table_container = Frame(items_frame, bg=self.colors['surface'],
                                    highlightbackground=self.colors['border'],
                                    highlightthickness=1)
            table_container.pack(fill='both', expand=True)

            columns = ('Код', 'Наименование', 'Кол-во, кг', 'Ед.')
            inv_items_tree = ttk.Treeview(table_container, columns=columns,
                                           show='headings', height=10)

            col_widths = [140, 350, 120, 60]
            for idx, col in enumerate(columns):
                inv_items_tree.heading(col, text=col)
                inv_items_tree.column(col, width=col_widths[idx], anchor='center')

            tree_scrollbar = Scrollbar(table_container, orient='vertical',
                                       command=inv_items_tree.yview)
            inv_items_tree.configure(yscrollcommand=tree_scrollbar.set)

            inv_items_tree.pack(side='left', fill='both', expand=True)
            tree_scrollbar.pack(side='right', fill='y')

            # Двойной клик для редактирования количества
            inv_items_tree.bind('<Double-Button-1>',
                                lambda e: self._edit_invoice_item_quantity(e, inv_items_tree))

            # Добавляем первую пустую строку
            self._add_invoice_item_row(inv_items_tree, warehouse_map)

            # ===== НИЖНИЕ КНОПКИ =====
            button_frame = Frame(main_frame, bg=self.colors['background'])
            button_frame.pack(fill='x', pady=(10, 5))

            # Подсказка в отдельной строке, чтобы не перекрывать кнопки
            info_label = Label(
                button_frame,
                text="При проведении документа складские остатки изменятся согласно типу операции",
                font=self.fonts['caption'],
                bg=self.colors['background'],
                fg=self.colors['text_muted']
            )
            info_label.pack(side='top', anchor='w', pady=(0, 8))

            # Фрейм, в котором располагаются кнопки действий
            action_frame = Frame(button_frame, bg=self.colors['background'])
            action_frame.pack(fill='x')

            def collect_invoice_data():
                """Собрать данные накладной из полей диалога."""
                op_map = {'Списание': 'write_off', 'Перемещение': 'transfer', 'Приход': 'receipt'}
                operation_type = op_map.get(op_type_var.get(), 'write_off')

                source = source_var.get().strip()
                dest = dest_var.get().strip()
                if '—' in dest:
                    dest = ''

                items_data = []
                for item in inv_items_tree.get_children():
                    values = inv_items_tree.item(item, 'values')
                    if values and values[0] and values[1]:
                        try:
                            qty = float(values[2].replace(',', '.'))
                            if qty > 0:
                                items_data.append({
                                    'component_code': values[0],
                                    'component_name': values[1],
                                    'quantity': qty,
                                    'unit': values[3] if values[3] else 'кг'
                                })
                        except (ValueError, IndexError):
                            continue

                number = inv_number.get().strip()
                notes = notes_var.get().strip()
                return {
                    'number': number,
                    'operation_type': operation_type,
                    'source': source,
                    'destination': dest,
                    'notes': notes,
                    'items': items_data,
                    'op_name': op_type_var.get()
                }

            def save_invoice(post: bool = True):
                """Сохранить накладную (с проведением или как черновик)."""
                try:
                    data = collect_invoice_data()
                    items_data = data['items']
                    number = data['number']
                    operation_type = data['operation_type']
                    source = data['source']
                    dest = data['destination']
                    notes = data['notes']
                    op_name = data['op_name']

                    if not items_data:
                        messagebox.showwarning("Внимание", "Добавьте хотя бы одну позицию с количеством > 0")
                        return

                    if not number:
                        messagebox.showwarning("Внимание", "Введите номер накладной")
                        return

                    try:
                        invoice_id = db_manager.create_invoice(
                            invoice_number=number,
                            operation_type=operation_type,
                            source_location=source,
                            destination_location=dest,
                            notes=notes,
                            items=items_data,
                            post=post
                        )
                    except ValueError as ve:
                        # Недостаточно остатков на складе для списания/перемещения —
                        # понятное сообщение пользователю, накладная НЕ создаётся
                        messagebox.showerror("Недостаточно остатков", str(ve))
                        self.logger.warning(f"Накладная №{number} не создана: {ve}")
                        return

                    self.load_invoices_list()
                    self.load_warehouse_data()

                    self.logger.info(f"Создана накладная №{number}, тип={operation_type}, позиций={len(items_data)}, проведена={post}")

                    # ---- Автосохранение PDF-бланка накладной (только для проведённых) ----
                    pdf_path = None
                    if post:
                        try:
                            from modules.invoice_pdf import (
                                generate_invoice_pdf, default_invoice_filename, get_invoices_dir
                            )
                            invoice = db_manager.get_invoice_details(invoice_id)
                            saved_items = db_manager.get_invoice_items(invoice_id)
                            invoices_dir = get_invoices_dir()
                            pdf_path = os.path.join(invoices_dir, default_invoice_filename(invoice))
                            if not generate_invoice_pdf(invoice, saved_items, pdf_path):
                                pdf_path = None
                        except Exception as pdf_err:
                            self.logger.error(f"Не удалось автоматически сохранить PDF накладной: {pdf_err}")
                            pdf_path = None

                    self.safe_destroy_dialog(dialog)

                    if post:
                        if pdf_path:
                            messagebox.showinfo("Успех",
                                                f"Требование-накладная №{number} создана и проведена!\n\n"
                                                f"Тип: {op_name}\n"
                                                f"Позиций: {len(items_data)}\n"
                                                f"ID документа: {invoice_id}\n\n"
                                                f"Бланк PDF сохранён:\n{pdf_path}")
                        else:
                            messagebox.showwarning("Накладная проведена, но PDF не сохранён",
                                                f"Требование-накладная №{number} проведена (ID: {invoice_id}),\n"
                                                f"однако автоматически сохранить PDF-бланк не удалось.\n"
                                                f"Вы можете экспортировать PDF вручную кнопкой «PDF» "
                                                f"в списке накладных.")
                    else:
                        messagebox.showinfo("Успех",
                                            f"Требование-накладная №{number} сохранена как черновик.\n\n"
                                            f"Тип: {op_name}\n"
                                            f"Позиций: {len(items_data)}\n"
                                            f"ID документа: {invoice_id}\n\n"
                                            f"Для проведения документа выберите её в списке и нажмите «Провести».")

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось создать накладную:\n{str(e)}")
                    self.logger.error(f"Ошибка создания накладной: {e}")

            def export_invoice_pdf():
                """Экспортировать текущее требование-накладную в PDF без сохранения в базу."""
                try:
                    data = collect_invoice_data()
                    if not data['items']:
                        messagebox.showwarning("Внимание", "Добавьте хотя бы одну позицию с количеством > 0")
                        return

                    from modules.invoice_pdf import generate_invoice_pdf, default_invoice_filename, get_invoices_dir

                    invoice_stub = {
                        'invoice_number': data['number'] or 'без_номера',
                        'operation_type': data['operation_type'],
                        'source_location': data['source'] or '—',
                        'destination_location': data['destination'] or '—',
                        'notes': data['notes'],
                        'status': 'draft',
                        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    items_stub = [
                        {
                            'component_code': it['component_code'],
                            'component_name': it['component_name'],
                            'quantity': it['quantity'],
                            'unit': it['unit'],
                        }
                        for it in data['items']
                    ]

                    invoices_dir = get_invoices_dir()
                    default_name = default_invoice_filename(invoice_stub)
                    file_path = filedialog.asksaveasfilename(
                        parent=dialog,
                        defaultextension=".pdf",
                        filetypes=[("PDF файлы", "*.pdf")],
                        initialdir=invoices_dir,
                        initialfile=default_name
                    )
                    if not file_path:
                        return

                    if generate_invoice_pdf(invoice_stub, items_stub, file_path):
                        messagebox.showinfo("Успех", f"PDF-бланк сохранён:\n{file_path}")
                        self.logger.info(f"Экспорт PDF из диалога создания: {file_path}")
                    else:
                        messagebox.showerror("Ошибка", "Не удалось сохранить PDF-бланк.")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось экспортировать PDF:\n{str(e)}")
                    self.logger.error(f"Ошибка экспорта PDF из диалога создания: {e}")

            def export_invoice_excel():
                """Экспортировать текущее требование-накладную в Excel без сохранения в базу."""
                try:
                    data = collect_invoice_data()
                    if not data['items']:
                        messagebox.showwarning("Внимание", "Добавьте хотя бы одну позицию с количеством > 0")
                        return

                    invoice_stub = {
                        'invoice_number': data['number'] or 'без_номера',
                        'operation_type': data['operation_type'],
                        'source_location': data['source'] or '—',
                        'destination_location': data['destination'] or '—',
                        'notes': data['notes'],
                        'status': 'draft',
                        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    items_stub = [
                        {
                            'component_code': it['component_code'],
                            'component_name': it['component_name'],
                            'quantity': it['quantity'],
                            'unit': it['unit'],
                        }
                        for it in data['items']
                    ]

                    invoices_dir = invoice_excel.get_invoices_dir()
                    default_name = invoice_excel.default_invoice_excel_filename(invoice_stub)
                    file_path = filedialog.asksaveasfilename(
                        parent=dialog,
                        defaultextension=".xlsx",
                        filetypes=[("Excel файлы", "*.xlsx")],
                        initialdir=invoices_dir,
                        initialfile=default_name
                    )
                    if not file_path:
                        return

                    if invoice_excel.generate_invoice_excel(invoice_stub, items_stub, file_path):
                        messagebox.showinfo("Успех", f"Excel-бланк сохранён:\n{file_path}")
                        self.logger.info(f"Экспорт Excel из диалога создания: {file_path}")
                    else:
                        messagebox.showerror("Ошибка", "Не удалось сохранить Excel-бланк.")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось экспортировать Excel:\n{str(e)}")
                    self.logger.error(f"Ошибка экспорта Excel из диалога создания: {e}")

            # ===== КНОПКИ УПРАВЛЕНИЯ В ВЕРХНЕМ РЯДУ =====
            # Добавляем после определения inv_items_tree и функций сохранения/экспорта
            add_item_btn = self.create_modern_button(
                btn_row, "➕ Добавить позицию",
                lambda: self._add_invoice_item_row(inv_items_tree, warehouse_map),
                'success', '➕'
            )
            add_item_btn.pack(side='left', padx=3)

            remove_item_btn = self.create_modern_button(
                btn_row, "🗑️ Удалить",
                lambda: self._remove_invoice_item_row(inv_items_tree),
                'danger', '🗑️'
            )
            remove_item_btn.pack(side='left', padx=3)

            clear_items_btn = self.create_modern_button(
                btn_row, "Очистить всё",
                lambda: self._clear_invoice_items(inv_items_tree),
                'warning', ''
            )
            clear_items_btn.pack(side='left', padx=3)

            # Разделитель
            separator = Frame(btn_row, bg=self.colors['background'], width=20)
            separator.pack(side='left', padx=5)

            # Кнопки сохранения / проведения / экспорта в верхнем ряду
            draft_btn = self.create_modern_button(
                btn_row, "💾 Сохранить черновик",
                lambda: save_invoice(post=False), 'secondary'
            )
            draft_btn.pack(side='left', padx=3)
            ToolTip(draft_btn, "Сохранить документ как черновик без изменения остатков")

            post_btn = self.create_modern_button(
                btn_row, "✅ Провести накладную",
                lambda: save_invoice(post=True), 'success'
            )
            post_btn.pack(side='left', padx=3)
            ToolTip(post_btn, "Сохранить документ и сразу провести его по складу")

            pdf_btn = self.create_modern_button(
                btn_row, "📄 PDF", export_invoice_pdf, 'primary'
            )
            pdf_btn.pack(side='left', padx=3)
            ToolTip(pdf_btn, "Экспортировать текущий документ в PDF без сохранения в базу")

            excel_btn = self.create_modern_button(
                btn_row, "📊 Excel", export_invoice_excel, 'primary'
            )
            excel_btn.pack(side='left', padx=3)
            ToolTip(excel_btn, "Экспортировать текущий документ в Excel без сохранения в базу")

            # Кнопка «Отмена» — в одном ряду с остальными, чтобы всегда была видна
            cancel_btn = self.create_modern_button(
                btn_row, "❌ Отмена", lambda: self.safe_destroy_dialog(dialog), 'secondary'
            )
            cancel_btn.pack(side='right', padx=(12, 0))
            ToolTip(cancel_btn, "Закрыть диалог без сохранения")

            self.logger.info("Открыт диалог создания/проведения накладной")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _add_invoice_item_row(self, tree, warehouse_map):
        """Добавить строку в таблицу позиций накладной"""
        try:
            # ---- Освобождаем grab родительского диалога, если он есть ----
            # Родительский диалог (create_invoice_dialog) уже держит grab_set().
            # Tcl/Tk не поддерживает вложенные grab — вторая попытка grab_set()
            # тихо провалится, и события мыши будут уходить родителю.
            parent_dialog = None
            for w in self.root.winfo_children():
                if isinstance(w, tk.Toplevel) and w.winfo_exists():
                    try:
                        if w.grab_current():
                            parent_dialog = w
                            break
                    except Exception:
                        continue

            # Создаём пикер как дочернее окно родительского диалога (или root)
            dialog = tk.Toplevel(parent_dialog or self.root)
            dialog.title("Добавить позицию")
            dialog.geometry("700x500")
            dialog.configure(bg=self.colors['background'])
            dialog.resizable(False, False)
            dialog.transient(parent_dialog or self.root)

            # Освобождаем grab родителя ПЕРЕД установкой собственного grab
            parent_grab_released = False
            if parent_dialog:
                try:
                    parent_dialog.grab_release()
                    parent_grab_released = True
                except Exception:
                    pass

            # Теперь устанавливаем grab на пикере — это сработает,
            # т.к. родительский grab уже отпущен
            try:
                dialog.grab_set()
            except Exception:
                pass

            # Обработчик закрытия окна (X) — восстанавливаем grab родителя
            def on_picker_close():
                _closing[0] = True
                self.safe_destroy_dialog(dialog)

            dialog.protocol('WM_DELETE_WINDOW', on_picker_close)

            dialog.update_idletasks()
            try:
                x = (dialog.winfo_screenwidth() // 2) - 350
                y = (dialog.winfo_screenheight() // 2) - 250
                dialog.geometry(f"+{x}+{y}")
            except Exception:
                pass

            # Шапка
            header_frame = Frame(dialog, bg=self.colors['primary'], height=52)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)
            Label(header_frame, text="Добавить позицию",
                  font=self.fonts['h3'],
                  bg=self.colors['primary'],
                  fg=self.colors['text_on_accent']).pack(pady=10)

            main = Frame(dialog, bg=self.colors['background'], padx=20, pady=20)
            main.pack(fill='both', expand=True)

            Label(main, text="Выберите компонент со склада или введите вручную:",
                  font=self.fonts['body'],
                  bg=self.colors['background']).pack(anchor='w', pady=(0, 10))

            # Поиск
            search_frame = Frame(main, bg=self.colors['background'])
            search_frame.pack(fill='x', pady=(0, 10))

            Label(search_frame, text="Поиск:",
                  font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left')
            search_var = StringVar()
            search_entry = ttk.Entry(search_frame, textvariable=search_var,
                                     width=30, font=self.fonts['body'])
            search_entry.pack(side='left', padx=(5, 0))

            # Таблица компонентов склада
            table_frame = Frame(main, bg=self.colors['surface'],
                                highlightbackground=self.colors['border'],
                                highlightthickness=1)
            table_frame.pack(fill='both', expand=True, pady=(0, 10))

            columns = ('Код', 'Наименование', 'Остаток, кг', 'Ед.')
            pick_tree = ttk.Treeview(table_frame, columns=columns,
                                     show='headings', height=12)
            col_widths = [120, 350, 100, 60]
            for idx, col in enumerate(columns):
                pick_tree.heading(col, text=col)
                pick_tree.column(col, width=col_widths[idx], anchor='center')

            scroll = Scrollbar(table_frame, orient='vertical', command=pick_tree.yview)
            pick_tree.configure(yscrollcommand=scroll.set)
            pick_tree.pack(side='left', fill='both', expand=True)
            scroll.pack(side='right', fill='y')

            # Заполняем таблицу
            all_items = list(warehouse_map.values())
            for item in all_items:
                pick_tree.insert('', 'end', values=(
                    item['component_code'],
                    item['component_name'],
                    f"{item['current_stock']:.1f}",
                    item.get('unit', 'кг')
                ))

            # Фильтрация
            def filter_items(*args):
                try:
                    if not pick_tree.winfo_exists():
                        return
                    text = search_var.get().lower().strip()
                    try:
                        children = pick_tree.get_children()
                    except Exception:
                        return
                    for item in children:
                        try:
                            pick_tree.delete(item)
                        except Exception:
                            pass
                    for w_item in all_items:
                        if (not text or
                                text in w_item['component_code'].lower() or
                                text in w_item['component_name'].lower()):
                            try:
                                pick_tree.insert('', 'end', values=(
                                    w_item['component_code'],
                                    w_item['component_name'],
                                    f"{w_item['current_stock']:.1f}",
                                    w_item.get('unit', 'кг')
                                ))
                            except Exception:
                                pass
                except Exception:
                    pass

            # Флаг защиты — при закрытии диалога trace не должен трогать виджеты
            _closing = [False]

            # Сохраняем trace_id для возможности отключения
            _trace_id = search_var.trace('w', lambda *a: filter_items(*a) if not _closing[0] else None)

            # Поле для ручного ввода количества
            qty_frame = Frame(main, bg=self.colors['background'])
            qty_frame.pack(fill='x', pady=(0, 10))

            Label(qty_frame, text="Количество, кг:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(side='left')
            qty_var = StringVar(value="100")
            qty_entry = ttk.Entry(qty_frame, textvariable=qty_var,
                                  width=15, font=self.fonts['body'])
            qty_entry.pack(side='left', padx=(10, 0))

            def confirm_selection():
                try:
                    selection = pick_tree.selection()
                    if selection:
                        values = pick_tree.item(selection[0], 'values')
                        code = values[0]
                        name = values[1]
                    else:
                        code = search_var.get().strip()
                        name = code
                        if not code:
                            messagebox.showwarning("Внимание",
                                                   "Выберите компонент из списка или введите код в поиске")
                            return

                    try:
                        qty = float(qty_var.get().replace(',', '.'))
                    except ValueError:
                        qty = 0

                    if qty <= 0:
                        messagebox.showwarning("Внимание", "Введите количество больше 0")
                        return

                    tree.insert('', 'end', values=(code, name, f"{qty:.1f}", 'кг'))
                    _closing[0] = True
                    self.safe_destroy_dialog(dialog)
                except Exception as e:
                    self.logger.error(f"Ошибка в confirm_selection: {e}")
                    _closing[0] = True
                    self.safe_destroy_dialog(dialog)

            def safe_add_call(event):
                try:
                    confirm_selection()
                except Exception as ex:
                    self.logger.error(f"Ошибка при быстром добавлении: {ex}")

            pick_tree.bind('<Double-Button-1>', safe_add_call)
            search_entry.bind('<Return>', safe_add_call)

            btn_frame = Frame(main, bg=self.colors['background'])
            btn_frame.pack(fill='x')

            self.create_modern_button(btn_frame, "✅ Добавить",
                                      confirm_selection, 'success').pack(side='left', padx=10)

            def cancel_picker():
                _closing[0] = True
                self.safe_destroy_dialog(dialog)

            self.create_modern_button(btn_frame, "Отмена",
                                      cancel_picker, 'secondary').pack(side='right', padx=10)

            # ===== КЛЮЧЕВОЙ МОМЕНТ: ждём закрытия пикера =====
            # wait_window() создаёт вложенный цикл событий, который
            # блокирует выполнение до уничтожения dialog.
            # Всё это время grab_set() на пикере активен и работает,
            # потому что родительский grab был отпущен выше.
            dialog.wait_window()

            # После закрытия пикера — восстанавливаем grab родителя
            if parent_dialog and parent_grab_released:
                try:
                    parent_dialog.grab_set()
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"Ошибка добавления позиции: {e}")

    def _remove_invoice_item_row(self, tree):
        """Удалить выбранные строки из таблицы позиций"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите позиции для удаления")
            return
        for item in selection:
            tree.delete(item)

    def _clear_invoice_items(self, tree):
        """Очистить все строки таблицы позиций"""
        for item in tree.get_children():
            tree.delete(item)

    def _edit_invoice_item_quantity(self, event, tree):
        """Редактирование количества через двойной клик"""
        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if not item or column != '#3':  # Только колонка количества
            return

        values = tree.item(item, 'values')
        if not values:
            return

        current_qty = values[2]

        # Создаём простой диалог редактирования
        edit_dialog = tk.Toplevel(tree.winfo_toplevel())
        edit_dialog.title("Изменить количество")
        edit_dialog.geometry("300x150")
        edit_dialog.configure(bg=self.colors['background'])
        edit_dialog.transient(tree.winfo_toplevel())
        edit_dialog.grab_set()
        edit_dialog.resizable(False, False)

        edit_dialog.update_idletasks()
        x = (edit_dialog.winfo_screenwidth() // 2) - 150
        y = (edit_dialog.winfo_screenheight() // 2) - 75
        edit_dialog.geometry(f"+{x}+{y}")

        frame = Frame(edit_dialog, bg=self.colors['background'], padx=20, pady=20)
        frame.pack(fill='both', expand=True)

        Label(frame, text=f"Количество для {values[0]} ({values[1]}):",
              font=self.fonts['body'],
              bg=self.colors['background']).pack(anchor='w')

        new_qty_var = StringVar(value=current_qty)
        ttk.Entry(frame, textvariable=new_qty_var,
                  font=self.fonts['body'], width=20).pack(fill='x', pady=10)

        def save_qty():
            try:
                qty = float(new_qty_var.get().replace(',', '.'))
                new_values = list(values)
                new_values[2] = f"{qty:.1f}"
                tree.item(item, values=tuple(new_values))
                edit_dialog.destroy()
            except ValueError:
                messagebox.showwarning("Внимание", "Введите корректное число")

        btn_frame = Frame(frame, bg=self.colors['background'])
        btn_frame.pack(fill='x', pady=(10, 0))

        self.create_modern_button(btn_frame, "OK", save_qty, 'success').pack(side='left', padx=5)
        self.create_modern_button(btn_frame, "Отмена", edit_dialog.destroy, 'secondary').pack(side='right', padx=5)

    def view_invoice_details(self):
        """Просмотр деталей выбранной накладной"""
        try:
            selection = self.invoices_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите накладную из списка")
                return

            values = self.invoices_tree.item(selection[0], 'values')
            invoice_id = int(values[0])

            invoice = db_manager.get_invoice_details(invoice_id)
            if not invoice:
                messagebox.showerror("Ошибка", "Накладная не найдена")
                return

            items = db_manager.get_invoice_items(invoice_id)

            # Создаем диалог просмотра
            op_labels = {'write_off': 'Списание', 'transfer': 'Перемещение', 'receipt': 'Приход'}
            op_label = op_labels.get(invoice['operation_type'], invoice['operation_type'])

            status_labels = {'active': 'Активна', 'reverted': 'Отменена'}
            status_label = status_labels.get(invoice['status'], invoice['status'])

            dialog, main_frame = self.create_dialog(
                f"Накладная №{invoice['invoice_number']}", 800, 600,
                header_color=self.colors['primary']
            )
            dialog.resizable(True, True)

            # Информация о документе
            info_frame = LabelFrame(main_frame, text="Информация о документе",
                                    font=self.fonts['body_semibold'],
                                    padx=15, pady=10, bg=self.colors['background'])
            info_frame.pack(fill='x', pady=(0, 15))

            info_text = (
                f"Номер: {invoice['invoice_number']}\n"
                f"Тип операции: {op_label}\n"
                f"Откуда: {invoice.get('source_location') or '—'}\n"
                f"Куда: {invoice.get('destination_location') or '—'}\n"
                f"Статус: {status_label}\n"
                f"Примечание: {invoice.get('notes') or '—'}\n"
                f"Дата создания: {invoice['created_date']}"
            )
            Label(info_frame, text=info_text,
                  font=self.fonts['body'],
                  bg=self.colors['background'],
                  fg=self.colors['on_surface'],
                  justify='left').pack(anchor='w')

            # Таблица позиций
            items_frame = LabelFrame(main_frame, text="Позиции",
                                     font=self.fonts['body_semibold'],
                                     padx=10, pady=10, bg=self.colors['background'])
            items_frame.pack(fill='both', expand=True, pady=(0, 10))

            columns = ('№', 'Код', 'Наименование', 'Количество, кг', 'Ед.')
            detail_tree = ttk.Treeview(items_frame, columns=columns,
                                       show='headings', height=12)
            col_widths = [40, 140, 350, 120, 60]
            for idx, col in enumerate(columns):
                detail_tree.heading(col, text=col)
                detail_tree.column(col, width=col_widths[idx], anchor='center')

            scroll = Scrollbar(items_frame, orient='vertical', command=detail_tree.yview)
            detail_tree.configure(yscrollcommand=scroll.set)
            detail_tree.pack(side='left', fill='both', expand=True)
            scroll.pack(side='right', fill='y')

            total_qty = 0
            for i, item in enumerate(items, 1):
                detail_tree.insert('', 'end', values=(
                    str(i),
                    item['component_code'],
                    item['component_name'],
                    f"{item['quantity']:.1f}",
                    item.get('unit', 'кг')
                ))
                total_qty += item['quantity']

            # Итоговая строка
            detail_tree.insert('', 'end', values=(
                '', 'ИТОГО:', f"{len(items)} позиций",
                f"{total_qty:.1f}", 'кг'
            ))

            # Кнопки
            btn_frame = Frame(main_frame, bg=self.colors['background'])
            btn_frame.pack(fill='x', pady=(0, 5))

            def export_pdf():
                try:
                    self._export_invoice_pdf(invoice, items)
                except Exception as ex:
                    self.logger.error(f"Ошибка PDF из деталей: {ex}")
                self.safe_destroy_dialog(dialog)

            def print_inv():
                try:
                    self._print_invoice_direct(invoice, items)
                except Exception as ex:
                    self.logger.error(f"Ошибка печати из деталей: {ex}")
                self.safe_destroy_dialog(dialog)

            self.create_modern_button(btn_frame, "📄 PDF", export_pdf, 'primary').pack(side='left', padx=10)
            self.create_modern_button(btn_frame, "🖨️ Печать", print_inv, 'secondary').pack(side='left', padx=10)
            self.create_modern_button(btn_frame, "Закрыть", lambda: self.safe_destroy_dialog(dialog), 'secondary').pack(side='right', padx=10)

        except Exception as e:
            self.logger.error(f"Ошибка просмотра накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть детали:\n{str(e)}")

    def post_selected_invoice(self):
        """Провести выбранную накладную из списка."""
        try:
            selection = self.invoices_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите накладную для проведения")
                return

            values = self.invoices_tree.item(selection[0], 'values')
            invoice_id = int(values[0])
            invoice_number = values[1]
            status_label = values[7] if len(values) > 7 else ''

            if status_label not in ('', 'Черновик'):
                messagebox.showinfo("Информация",
                                    f"Накладная №{invoice_number} уже проведена или отменена.")
                return

            if not messagebox.askyesno(
                "Подтверждение",
                f"Провести накладную №{invoice_number}?\n\n"
                "При проведении складские остатки изменятся согласно типу операции."
            ):
                return

            try:
                if db_manager.post_invoice(invoice_id):
                    self.load_invoices_list()
                    self.load_warehouse_data()
                    messagebox.showinfo("Успех", f"Накладная №{invoice_number} проведена")
                    self.logger.info(f"Проведена накладная №{invoice_number} (ID={invoice_id})")
                else:
                    messagebox.showwarning("Внимание",
                                           f"Не удалось провести накладную №{invoice_number}.\n"
                                           "Возможно, она уже проведена, отменена или не содержит позиций.")
            except ValueError as ve:
                messagebox.showerror("Недостаточно остатков", str(ve))
                self.logger.warning(f"Накладная №{invoice_number} не проведена: {ve}")

        except Exception as e:
            self.logger.error(f"Ошибка проведения накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось провести накладную:\n{str(e)}")

    def delete_selected_invoice(self):
        """Удалить выбранную накладную"""
        try:
            selection = self.invoices_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите накладную для удаления")
                return

            values = self.invoices_tree.item(selection[0], 'values')
            invoice_id = int(values[0])
            invoice_number = values[1]
            status_label = values[7] if len(values) > 7 else ''

            revert_note = (
                "Остатки на складе будут автоматически возвращены к состоянию "
                "до проведения этой накладной.\n\n"
                if status_label == 'Активна' else ""
            )

            if not messagebox.askyesno(
                "Подтверждение",
                f"Удалить накладную №{invoice_number}?\n\n"
                f"{revert_note}"
                "Это действие нельзя отменить."
            ):
                return

            if db_manager.delete_invoice(invoice_id):
                self.load_invoices_list()
                self.load_warehouse_data()
                messagebox.showinfo("Успех", f"Накладная №{invoice_number} удалена, остатки склада восстановлены")
                self.logger.info(f"Удалена накладная №{invoice_number}")
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить накладную")

        except Exception as e:
            self.logger.error(f"Ошибка удаления накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось удалить накладную:\n{str(e)}")

    def export_invoice_pdf(self):
        """Экспорт выбранной накладной в PDF (сохранение по указанному пути)"""
        try:
            selection = self.invoices_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите накладную из списка")
                return

            values = self.invoices_tree.item(selection[0], 'values')
            invoice_id = int(values[0])

            invoice = db_manager.get_invoice_details(invoice_id)
            if not invoice:
                messagebox.showerror("Ошибка", "Накладная не найдена")
                return

            items = db_manager.get_invoice_items(invoice_id)
            self._export_invoice_pdf(invoice, items)

        except Exception as e:
            self.logger.error(f"Ошибка экспорта PDF: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать PDF:\n{str(e)}")

    def _export_invoice_pdf(self, invoice, items):
        """Создать PDF файл накладной, спросив у пользователя путь сохранения"""
        try:
            from modules.invoice_pdf import generate_invoice_pdf, default_invoice_filename
            from tkinter import filedialog

            filename = filedialog.asksaveasfilename(
                title="Сохранить накладную как PDF",
                initialdir=".",
                initialfile=default_invoice_filename(invoice),
                defaultextension=".pdf",
                filetypes=[("PDF файлы", "*.pdf"), ("Все файлы", "*.*")]
            )
            if not filename:
                return

            if generate_invoice_pdf(invoice, items, filename):
                messagebox.showinfo("Успех", f"PDF сохранён:\n{filename}")
                self.logger.info(f"PDF накладной создан: {filename}")
            else:
                messagebox.showerror("Ошибка", "Не удалось создать PDF накладной")

        except Exception as e:
            self.logger.error(f"Ошибка создания PDF накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать PDF:\n{str(e)}")

    def print_invoice(self):
        """Печать выбранной накладной"""
        try:
            selection = self.invoices_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите накладную из списка")
                return

            values = self.invoices_tree.item(selection[0], 'values')
            invoice_id = int(values[0])

            invoice = db_manager.get_invoice_details(invoice_id)
            if not invoice:
                messagebox.showerror("Ошибка", "Накладная не найдена")
                return

            items = db_manager.get_invoice_items(invoice_id)
            self._print_invoice_direct(invoice, items)

        except Exception as e:
            self.logger.error(f"Ошибка печати накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось распечатать:\n{str(e)}")

    def _print_invoice_direct(self, invoice, items):
        """Печать накладной через системный PDF viewer"""
        try:
            import tempfile
            import subprocess
            import os
            from modules.invoice_pdf import generate_invoice_pdf

            with tempfile.NamedTemporaryFile(
                suffix='.pdf', prefix=f'invoice_{invoice["invoice_number"]}_',
                delete=False
            ) as tmp:
                tmp_path = tmp.name

            if not generate_invoice_pdf(invoice, items, tmp_path):
                messagebox.showerror("Ошибка", "Не удалось создать PDF накладной")
                return

            # Открываем PDF в системном просмотрщике
            if os.name == 'nt':  # Windows
                os.startfile(tmp_path)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.run(['xdg-open', tmp_path], check=False)

            self.logger.info(f"Накладная отправлена на печать: {invoice['invoice_number']}")

        except Exception as e:
            self.logger.error(f"Ошибка печати накладной: {e}")
            messagebox.showerror("Ошибка", f"Не удалось распечатать:\n{str(e)}")

    # ===================== ПОТРЕБНОСТЬ СЫРЬЯ =====================

    def open_raw_material_requirement(self):
        """Открыть диалог расчёта потребности сырья на полуфабрикаты."""
        try:
            self.logger.info("Открытие диалога расчёта потребности сырья")
            dialog, main_frame = self.create_dialog(
                "Потребность сырья на полуфабрикаты", 1100, 750,
                header_color=self.colors['primary']
            )
            dialog.resizable(True, True)

            # Верхняя панель: загрузка файлов
            load_frame = Frame(main_frame, bg=self.colors['background'])
            load_frame.pack(fill='x', pady=(0, 10))

            self._rmr_recipes_path = StringVar()
            self._rmr_inventory_path = StringVar()
            self._rmr_recipes = []
            self._rmr_inventory_summary = {}
            self._rmr_inventory_details = []
            self._rmr_inventory_df = None
            self._rmr_cart = []
            self._rmr_current_available = []

            def choose_recipes():
                path = filedialog.askopenfilename(
                    parent=dialog,
                    filetypes=[("Excel файлы", "*.xlsx *.xls")],
                    title="Выберите файл рецептур"
                )
                if path:
                    self._rmr_recipes_path.set(path)
                    try:
                        self._rmr_recipes = rm_req.load_recipes_from_excel(path)
                        self._rmr_refresh_recipe_list()
                        self.status_label.config(text=f"Загружено {len(self._rmr_recipes)} рецептур")
                        self.logger.info(f"Загружены рецептуры: {path}")
                    except Exception as e:
                        messagebox.showerror("Ошибка загрузки рецептур", str(e), parent=dialog)
                        self.logger.error(f"Ошибка загрузки рецептур: {e}")

            def choose_inventory():
                path = filedialog.askopenfilename(
                    parent=dialog,
                    filetypes=[("Excel файлы", "*.xlsx *.xls")],
                    title="Выберите файл склада"
                )
                if path:
                    self._rmr_inventory_path.set(path)
                    try:
                        summary, details, orig_df = rm_req.load_inventory_from_excel(path)
                        self._rmr_inventory_summary = summary
                        self._rmr_inventory_details = details
                        self._rmr_inventory_df = orig_df
                        self._rmr_refresh_inventory_tree()
                        self._rmr_refresh_recipe_list()
                        self.status_label.config(
                            text=f"Склад: {len(details)} позиций, {len(summary)} компонентов"
                        )
                        self.logger.info(f"Загружен склад: {path}")
                    except Exception as e:
                        messagebox.showerror("Ошибка загрузки склада", str(e), parent=dialog)
                        self.logger.error(f"Ошибка загрузки склада: {e}")

            Label(load_frame, text="Рецептуры:", font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left')
            Entry(load_frame, textvariable=self._rmr_recipes_path, font=self.fonts['body'],
                  width=40, state='readonly').pack(side='left', padx=(5, 5))
            self.create_modern_button(load_frame, "Выбрать...", choose_recipes, 'secondary').pack(side='left', padx=5)

            Label(load_frame, text="Склад:", font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left', padx=(20, 0))
            Entry(load_frame, textvariable=self._rmr_inventory_path, font=self.fonts['body'],
                  width=40, state='readonly').pack(side='left', padx=(5, 5))
            self.create_modern_button(load_frame, "Выбрать...", choose_inventory, 'secondary').pack(side='left', padx=5)

            # Основная панель: PanedWindow
            paned = ttk.PanedWindow(main_frame, orient='horizontal')
            paned.pack(fill='both', expand=True, pady=10)

            # Левая часть: рецептуры
            left_frame = Frame(paned, bg=self.colors['background'])
            paned.add(left_frame, weight=50)

            recipe_card = LabelFrame(left_frame, text="Рецептуры полуфабрикатов",
                                     font=self.fonts['body_semibold'],
                                     padx=10, pady=10, bg=self.colors['background'])
            recipe_card.pack(fill='both', expand=True)

            search_frame = Frame(recipe_card, bg=self.colors['background'])
            search_frame.pack(fill='x', pady=(0, 5))
            Label(search_frame, text="Поиск:", font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left')
            self._rmr_search_var = StringVar()
            self._rmr_search_var.trace('w', lambda *a: self._rmr_refresh_recipe_list())
            Entry(search_frame, textvariable=self._rmr_search_var, font=self.fonts['body'],
                  width=20).pack(side='left', padx=(5, 0))

            self._rmr_recipe_tree = ttk.Treeview(
                recipe_card, columns=('code', 'name', 'rc', 'max'), show='headings', height=10
            )
            self._rmr_recipe_tree.heading('code', text='Код')
            self._rmr_recipe_tree.heading('name', text='Наименование')
            self._rmr_recipe_tree.heading('rc', text='РЦ')
            self._rmr_recipe_tree.heading('max', text='Макс. ед.')
            self._rmr_recipe_tree.column('code', width=80, anchor='center')
            self._rmr_recipe_tree.column('name', width=180, anchor='w')
            self._rmr_recipe_tree.column('rc', width=50, anchor='center')
            self._rmr_recipe_tree.column('max', width=80, anchor='center')
            self._rmr_recipe_tree.pack(side='left', fill='both', expand=True)
            rec_scroll = Scrollbar(recipe_card, orient='vertical', command=self._rmr_recipe_tree.yview)
            self._rmr_recipe_tree.configure(yscrollcommand=rec_scroll.set)
            rec_scroll.pack(side='right', fill='y')
            self._rmr_recipe_tree.bind('<<TreeviewSelect>>', self._rmr_on_recipe_select)
            self._rmr_recipe_tree.bind('<Double-Button-1>', lambda e: self._rmr_add_to_cart(dialog))

            # Правая часть: детали, корзина, склад
            right_frame = Frame(paned, bg=self.colors['background'])
            paned.add(right_frame, weight=50)

            detail_card = LabelFrame(right_frame, text="Состав рецепта",
                                     font=self.fonts['body_semibold'],
                                     padx=10, pady=10, bg=self.colors['background'])
            detail_card.pack(fill='both', expand=True, pady=(0, 5))

            self._rmr_comp_tree = ttk.Treeview(
                detail_card, columns=('comp', 'name', 'percent'), show='headings', height=5
            )
            self._rmr_comp_tree.heading('comp', text='Код сырья')
            self._rmr_comp_tree.heading('name', text='Наименование')
            self._rmr_comp_tree.heading('percent', text='Доля, %')
            self._rmr_comp_tree.column('comp', width=80, anchor='center')
            self._rmr_comp_tree.column('name', width=150, anchor='w')
            self._rmr_comp_tree.column('percent', width=70, anchor='center')
            self._rmr_comp_tree.pack(fill='both', expand=True)

            btn_frame = Frame(right_frame, bg=self.colors['background'])
            btn_frame.pack(fill='x', pady=5)
            self.create_modern_button(btn_frame, "➕ В корзину",
                                      lambda: self._rmr_add_to_cart(dialog), 'success').pack(side='left', padx=3)
            self.create_modern_button(btn_frame, "🗑️ Удалить",
                                      lambda: self._rmr_remove_from_cart(dialog), 'danger').pack(side='left', padx=3)
            self.create_modern_button(btn_frame, "🧮 Потребность",
                                      lambda: self._rmr_show_requirements(dialog), 'primary').pack(side='left', padx=3)

            cart_card = LabelFrame(right_frame, text="Корзина производства",
                                 font=self.fonts['body_semibold'],
                                 padx=10, pady=10, bg=self.colors['background'])
            cart_card.pack(fill='both', expand=True, pady=(0, 5))

            self._rmr_cart_tree = ttk.Treeview(
                cart_card, columns=('code', 'name', 'qty'), show='headings', height=5
            )
            self._rmr_cart_tree.heading('code', text='Код')
            self._rmr_cart_tree.heading('name', text='Наименование')
            self._rmr_cart_tree.heading('qty', text='Кол-во')
            self._rmr_cart_tree.column('code', width=80, anchor='center')
            self._rmr_cart_tree.column('name', width=150, anchor='w')
            self._rmr_cart_tree.column('qty', width=60, anchor='center')
            self._rmr_cart_tree.pack(side='left', fill='both', expand=True)
            cart_scroll = Scrollbar(cart_card, orient='vertical', command=self._rmr_cart_tree.yview)
            self._rmr_cart_tree.configure(yscrollcommand=cart_scroll.set)
            cart_scroll.pack(side='right', fill='y')

            inv_card = LabelFrame(right_frame, text="Остатки на складе",
                                  font=self.fonts['body_semibold'],
                                  padx=10, pady=10, bg=self.colors['background'])
            inv_card.pack(fill='both', expand=True)

            inv_toolbar = Frame(inv_card, bg=self.colors['background'])
            inv_toolbar.pack(fill='x', pady=(0, 5))
            self.create_modern_button(inv_toolbar, "Развернуть",
                                      lambda: self._rmr_expand_all_inventory(), 'secondary').pack(side='left', padx=3)
            self.create_modern_button(inv_toolbar, "Свернуть",
                                      lambda: self._rmr_collapse_all_inventory(), 'secondary').pack(side='left', padx=3)

            self._rmr_inv_tree = ttk.Treeview(
                inv_card, columns=('location', 'start', 'income', 'expense', 'ending'),
                show='tree headings', height=8
            )
            self._rmr_inv_tree.heading('#0', text='Код / Наименование')
            self._rmr_inv_tree.heading('location', text='Место')
            self._rmr_inv_tree.heading('start', text='Нач. остаток')
            self._rmr_inv_tree.heading('income', text='Приход')
            self._rmr_inv_tree.heading('expense', text='Расход')
            self._rmr_inv_tree.heading('ending', text='Кон. остаток')
            self._rmr_inv_tree.column('#0', width=220, anchor='w')
            self._rmr_inv_tree.column('location', width=100, anchor='center')
            self._rmr_inv_tree.column('start', width=80, anchor='center')
            self._rmr_inv_tree.column('income', width=80, anchor='center')
            self._rmr_inv_tree.column('expense', width=80, anchor='center')
            self._rmr_inv_tree.column('ending', width=80, anchor='center')
            self._rmr_inv_tree.pack(side='left', fill='both', expand=True)
            inv_scroll = Scrollbar(inv_card, orient='vertical', command=self._rmr_inv_tree.yview)
            self._rmr_inv_tree.configure(yscrollcommand=inv_scroll.set)
            inv_scroll.pack(side='right', fill='y')

            # Нижняя панель: кнопки закрытия и подсказка
            bottom_frame = Frame(main_frame, bg=self.colors['background'])
            bottom_frame.pack(fill='x', pady=(10, 0))
            self.create_modern_button(bottom_frame, "❌ Закрыть",
                                      lambda: self.safe_destroy_dialog(dialog), 'secondary').pack(side='right')
            Label(bottom_frame,
                  text="Двойной клик по рецептуре добавляет её в корзину. Загрузите рецептуры и склад для расчёта.",
                  font=self.fonts['caption'],
                  bg=self.colors['background'],
                  fg=self.colors['text_muted']).pack(side='left')

            self._rmr_refresh_recipe_list()
            self._rmr_refresh_inventory_tree()
            self.logger.info("Диалог расчёта потребности сырья открыт")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога потребности сырья: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _rmr_refresh_recipe_list(self):
        """Обновить список рецептур в диалоге потребности сырья."""
        try:
            if not hasattr(self, '_rmr_recipe_tree'):
                return

            for item in self._rmr_recipe_tree.get_children():
                self._rmr_recipe_tree.delete(item)

            recipes = rm_req.enrich_recipes_with_availability(
                getattr(self, '_rmr_recipes', []),
                getattr(self, '_rmr_inventory_summary', {})
            )

            search_text = self._rmr_search_var.get().strip().lower() if hasattr(self, '_rmr_search_var') else ''
            if search_text:
                recipes = [r for r in recipes if search_text in r['code'].lower() or search_text in r['name'].lower()]

            self._rmr_current_available = recipes
            for rec in recipes:
                self._rmr_recipe_tree.insert('', 'end',
                    values=(rec['code'], rec['name'], rec['rc_number'], rec['max_units']))

            for item in self._rmr_comp_tree.get_children():
                self._rmr_comp_tree.delete(item)
        except Exception as e:
            self.logger.error(f"Ошибка обновления списка рецептур: {e}")

    def _rmr_on_recipe_select(self, event=None):
        """Показать состав выбранного рецепта."""
        try:
            selected = self._rmr_recipe_tree.selection()
            if not selected:
                return
            idx = self._rmr_recipe_tree.index(selected[0])
            if idx < 0 or idx >= len(self._rmr_current_available):
                return
            rec = self._rmr_current_available[idx]
            for item in self._rmr_comp_tree.get_children():
                self._rmr_comp_tree.delete(item)
            for comp_code, share in rec['components'].items():
                comp_name = rec.get('component_names', {}).get(comp_code, '')
                for det in self._rmr_inventory_details:
                    if det['code'] == comp_code:
                        comp_name = det['name'] or comp_name
                        break
                self._rmr_comp_tree.insert('', 'end',
                    values=(comp_code, comp_name, f"{share * 100:.1f}"))
        except Exception as e:
            self.logger.error(f"Ошибка отображения состава рецепта: {e}")

    def _rmr_add_to_cart(self, parent_dialog):
        """Добавить выбранную рецептуру в корзину."""
        try:
            selected = self._rmr_recipe_tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите рецептуру в таблице", parent=parent_dialog)
                return

            idx = self._rmr_recipe_tree.index(selected[0])
            if idx < 0 or idx >= len(self._rmr_current_available):
                return
            rec = self._rmr_current_available[idx]

            qty_str = simpledialog.askstring("Количество", "Введите количество:", parent=parent_dialog)
            if not qty_str:
                return
            try:
                qty = int(qty_str)
            except ValueError:
                messagebox.showerror("Ошибка", "Количество должно быть целым числом", parent=parent_dialog)
                return
            if qty < 1:
                messagebox.showerror("Ошибка", "Количество должно быть положительным", parent=parent_dialog)
                return

            for item in self._rmr_cart:
                if item['recipe']['code'] == rec['code'] and item['recipe']['rc_number'] == rec['rc_number']:
                    item['qty'] = qty
                    self._rmr_refresh_cart_view()
                    return

            self._rmr_cart.append({'recipe': rec, 'qty': qty})
            self._rmr_refresh_cart_view()
        except Exception as e:
            self.logger.error(f"Ошибка добавления в корзину: {e}")

    def _rmr_remove_from_cart(self, parent_dialog):
        """Удалить выбранную позицию из корзины."""
        try:
            selected = self._rmr_cart_tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите позицию в корзине", parent=parent_dialog)
                return
            idx = self._rmr_cart_tree.index(selected[0])
            if idx < len(self._rmr_cart):
                del self._rmr_cart[idx]
                self._rmr_refresh_cart_view()
        except Exception as e:
            self.logger.error(f"Ошибка удаления из корзины: {e}")

    def _rmr_refresh_cart_view(self):
        """Обновить отображение корзины."""
        try:
            for item in self._rmr_cart_tree.get_children():
                self._rmr_cart_tree.delete(item)
            for item in self._rmr_cart:
                rec = item['recipe']
                self._rmr_cart_tree.insert('', 'end',
                    values=(rec['code'], rec['name'], item['qty']))
        except Exception as e:
            self.logger.error(f"Ошибка обновления корзины: {e}")

    def _rmr_refresh_inventory_tree(self):
        """Обновить дерево остатков склада."""
        try:
            if not hasattr(self, '_rmr_inv_tree'):
                return

            expanded = set()
            for item in self._rmr_inv_tree.get_children():
                if self._rmr_inv_tree.item(item, 'open'):
                    expanded.add(self._rmr_inv_tree.item(item, 'text'))

            for item in self._rmr_inv_tree.get_children():
                self._rmr_inv_tree.delete(item)

            grouped = {}
            for det in self._rmr_inventory_details:
                code = det['code']
                if code not in grouped:
                    grouped[code] = {
                        'name': det['name'],
                        'locations': [],
                        'start': 0.0,
                        'income': 0.0,
                        'expense': 0.0,
                        'ending': 0.0
                    }
                grouped[code]['start'] += det['start']
                grouped[code]['income'] += det['income']
                grouped[code]['expense'] += det['expense']
                grouped[code]['ending'] += det['ending']
                grouped[code]['locations'].append(det)

            for code, data in grouped.items():
                parent = self._rmr_inv_tree.insert('', 'end',
                    text=f"{code} - {data['name']}",
                    values=('Сумма', data['start'], data['income'], data['expense'], data['ending']),
                    open=True)
                for det in data['locations']:
                    self._rmr_inv_tree.insert(parent, 'end',
                        text=det['location'],
                        values=(det['location'], det['start'], det['income'], det['expense'], det['ending']))

            for item in self._rmr_inv_tree.get_children():
                if self._rmr_inv_tree.item(item, 'text') in expanded:
                    self._rmr_inv_tree.item(item, open=True)
        except Exception as e:
            self.logger.error(f"Ошибка обновления дерева склада: {e}")

    def _rmr_expand_all_inventory(self):
        for item in self._rmr_inv_tree.get_children():
            self._rmr_expand_recursive(self._rmr_inv_tree, item)

    def _rmr_collapse_all_inventory(self):
        for item in self._rmr_inv_tree.get_children():
            self._rmr_collapse_recursive(self._rmr_inv_tree, item)

    def _rmr_expand_recursive(self, tree, item):
        tree.item(item, open=True)
        for child in tree.get_children(item):
            self._rmr_expand_recursive(tree, child)

    def _rmr_collapse_recursive(self, tree, item):
        tree.item(item, open=False)
        for child in tree.get_children(item):
            self._rmr_collapse_recursive(tree, child)

    def _rmr_show_requirements(self, parent_dialog):
        """Показать диалог с расчётом потребности сырья."""
        try:
            if not self._rmr_cart:
                messagebox.showwarning("Предупреждение", "Корзина пуста", parent=parent_dialog)
                return

            req = rm_req.calculate_requirements(
                self._rmr_cart,
                self._rmr_inventory_summary,
                self._rmr_inventory_details
            )

            if not req:
                messagebox.showinfo("Информация", "Нет данных для расчёта потребности", parent=parent_dialog)
                return

            dlg = tk.Toplevel(parent_dialog)
            dlg.title("Потребность в сырье")
            dlg.geometry("1000x700")
            dlg.configure(bg=self.colors['background'])
            dlg.transient(parent_dialog)
            dlg.resizable(True, True)

            ctrl_frame = Frame(dlg, bg=self.colors['background'])
            ctrl_frame.pack(fill='x', padx=10, pady=10)

            tree = ttk.Treeview(dlg, columns=('name', 'recipe', 'need', 'stock', 'deficit'),
                                show='tree headings', height=20)
            tree.heading('#0', text='Код компонента')
            tree.heading('name', text='Наименование')
            tree.heading('recipe', text='Полуфабрикат')
            tree.heading('need', text='Требуется')
            tree.heading('stock', text='На складе')
            tree.heading('deficit', text='Дефицит')
            tree.column('#0', width=120, anchor='w')
            tree.column('name', width=150, anchor='w')
            tree.column('recipe', width=220, anchor='w')
            tree.column('need', width=90, anchor='center')
            tree.column('stock', width=90, anchor='center')
            tree.column('deficit', width=90, anchor='center')
            tree.pack(fill='both', expand=True, padx=10, pady=(0, 10))

            for comp_code, data in req.items():
                stock = self._rmr_inventory_summary.get(comp_code, 0.0) if self._rmr_inventory_summary else 0.0
                deficit = data['total'] - stock
                parent = tree.insert('', 'end',
                    text=comp_code,
                    values=(
                        data['name'],
                        'Сумма',
                        f"{data['total']:.2f}",
                        f"{stock:.2f}" if self._rmr_inventory_summary else "—",
                        f"{deficit:.2f}" if self._rmr_inventory_summary and deficit > 0 else (
                            "0.00" if self._rmr_inventory_summary else "—")
                    ),
                    open=True)
                for det in data['details']:
                    tree.insert(parent, 'end',
                        text='',
                        values=(
                            data['name'],
                            f"{det['recipe_code']} {det['recipe_name']} (x{det['qty_recipe']})",
                            f"{det['need']:.2f}",
                            '',
                            ''
                        ))

            btn_frame = Frame(dlg, bg=self.colors['background'])
            btn_frame.pack(pady=10)

            def do_export():
                file_path = filedialog.asksaveasfilename(
                    parent=dlg,
                    defaultextension=".xlsx",
                    filetypes=[("Excel файлы", "*.xlsx")],
                    title="Сохранить потребность"
                )
                if not file_path:
                    return
                try:
                    rm_req.export_requirements_to_excel(req, self._rmr_inventory_summary, file_path)
                    messagebox.showinfo("Экспорт", f"Данные сохранены в {file_path}", parent=dlg)
                    self.logger.info(f"Экспорт потребности сырья: {file_path}")
                except Exception as e:
                    messagebox.showerror("Ошибка экспорта", str(e), parent=dlg)
                    self.logger.error(f"Ошибка экспорта потребности: {e}")

            def do_produce():
                if not self._rmr_inventory_summary:
                    messagebox.showwarning("Предупреждение", "Склад не загружен", parent=dlg)
                    return
                for comp_code, data in req.items():
                    if self._rmr_inventory_summary.get(comp_code, 0) < data['total']:
                        messagebox.showerror("Ошибка", f"Недостаточно сырья '{comp_code}'", parent=dlg)
                        return
                for item in self._rmr_cart:
                    rec = item['recipe']
                    qty = item['qty']
                    self._rmr_inventory_summary, self._rmr_inventory_details = rm_req.produce(
                        rec, qty, self._rmr_inventory_summary, self._rmr_inventory_details)
                self._rmr_cart.clear()
                self._rmr_refresh_cart_view()
                self._rmr_refresh_inventory_tree()
                self._rmr_refresh_recipe_list()
                self.status_label.config(text="Производство по корзине выполнено")
                self.logger.info("Производство по корзине выполнено")
                messagebox.showinfo("Успех", "Производство выполнено, остатки склада обновлены", parent=dlg)
                dlg.destroy()

            self.create_modern_button(btn_frame, "⚙️ Произвести", do_produce, 'success').pack(side='left', padx=5)
            self.create_modern_button(btn_frame, "📊 Экспорт в Excel", do_export, 'primary').pack(side='left', padx=5)
            self.create_modern_button(btn_frame, "Закрыть", lambda: self.safe_destroy_dialog(dlg), 'secondary').pack(side='left', padx=5)

        except Exception as e:
            self.logger.error(f"Ошибка расчёта потребности: {e}")
            messagebox.showerror("Ошибка", f"Не удалось рассчитать потребность:\n{str(e)}", parent=parent_dialog)

    # ===================== ПОТРЕБНОСТЬ ГОТОВОЙ ПРОДУКЦИИ =====================

    def open_finished_product_requirement(self):
        """Открыть диалог расчёта потребности компонентов на готовую продукцию."""
        try:
            self.logger.info("Открытие диалога расчёта потребности готовой продукции")
            dialog, main_frame = self.create_dialog(
                "Потребность компонентов на готовую продукцию", 1100, 750,
                header_color=self.colors['primary']
            )
            dialog.resizable(True, True)

            load_frame = Frame(main_frame, bg=self.colors['background'])
            load_frame.pack(fill='x', pady=(0, 10))

            self._fpr_recipes_path = StringVar()
            self._fpr_inventory_path = StringVar()
            self._fpr_recipes = []
            self._fpr_inventory_summary = {}
            self._fpr_inventory_details = []
            self._fpr_inventory_df = None
            self._fpr_cart = []
            self._fpr_current_available = []

            def choose_recipes():
                path = filedialog.askopenfilename(
                    parent=dialog,
                    filetypes=[("Excel файлы", "*.xlsx *.xls")],
                    title="Выберите файл спецификаций готовой продукции"
                )
                if path:
                    self._fpr_recipes_path.set(path)
                    try:
                        self._fpr_recipes = fp_req.load_recipes_from_excel(path)
                        self._fpr_refresh_recipe_list()
                        self.status_label.config(text=f"Загружено {len(self._fpr_recipes)} спецификаций")
                        self.logger.info(f"Загружены спецификации готовой продукции: {path}")
                    except Exception as e:
                        messagebox.showerror("Ошибка загрузки спецификаций", str(e), parent=dialog)
                        self.logger.error(f"Ошибка загрузки спецификаций: {e}")

            def choose_inventory():
                path = filedialog.askopenfilename(
                    parent=dialog,
                    filetypes=[("Excel файлы", "*.xlsx *.xls")],
                    title="Выберите файл склада компонентов"
                )
                if path:
                    self._fpr_inventory_path.set(path)
                    try:
                        summary, details, orig_df = fp_req.load_inventory_from_excel(path)
                        self._fpr_inventory_summary = summary
                        self._fpr_inventory_details = details
                        self._fpr_inventory_df = orig_df
                        self._fpr_refresh_inventory_tree()
                        self._fpr_refresh_recipe_list()
                        self.status_label.config(
                            text=f"Склад: {len(details)} позиций, {len(summary)} компонентов"
                        )
                        self.logger.info(f"Загружен склад компонентов: {path}")
                    except Exception as e:
                        messagebox.showerror("Ошибка загрузки склада", str(e), parent=dialog)
                        self.logger.error(f"Ошибка загрузки склада: {e}")

            Label(load_frame, text="Спецификации:", font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left')
            Entry(load_frame, textvariable=self._fpr_recipes_path, font=self.fonts['body'],
                  width=40, state='readonly').pack(side='left', padx=(5, 5))
            self.create_modern_button(load_frame, "Выбрать...", choose_recipes, 'secondary').pack(side='left', padx=5)

            Label(load_frame, text="Склад:", font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left', padx=(20, 0))
            Entry(load_frame, textvariable=self._fpr_inventory_path, font=self.fonts['body'],
                  width=40, state='readonly').pack(side='left', padx=(5, 5))
            self.create_modern_button(load_frame, "Выбрать...", choose_inventory, 'secondary').pack(side='left', padx=5)

            paned = ttk.PanedWindow(main_frame, orient='horizontal')
            paned.pack(fill='both', expand=True, pady=10)

            left_frame = Frame(paned, bg=self.colors['background'])
            paned.add(left_frame, weight=50)

            recipe_card = LabelFrame(left_frame, text="Готовая продукция",
                                     font=self.fonts['body_semibold'],
                                     padx=10, pady=10, bg=self.colors['background'])
            recipe_card.pack(fill='both', expand=True)

            search_frame = Frame(recipe_card, bg=self.colors['background'])
            search_frame.pack(fill='x', pady=(0, 5))
            Label(search_frame, text="Поиск:", font=self.fonts['body'],
                  bg=self.colors['background']).pack(side='left')
            self._fpr_search_var = StringVar()
            self._fpr_search_var.trace('w', lambda *a: self._fpr_refresh_recipe_list())
            Entry(search_frame, textvariable=self._fpr_search_var, font=self.fonts['body'],
                  width=20).pack(side='left', padx=(5, 0))

            self._fpr_recipe_tree = ttk.Treeview(
                recipe_card, columns=('code', 'name', 'rc', 'max'), show='headings', height=10
            )
            self._fpr_recipe_tree.heading('code', text='Код')
            self._fpr_recipe_tree.heading('name', text='Наименование')
            self._fpr_recipe_tree.heading('rc', text='РЦ')
            self._fpr_recipe_tree.heading('max', text='Макс. ед.')
            self._fpr_recipe_tree.column('code', width=80, anchor='center')
            self._fpr_recipe_tree.column('name', width=180, anchor='w')
            self._fpr_recipe_tree.column('rc', width=50, anchor='center')
            self._fpr_recipe_tree.column('max', width=80, anchor='center')
            self._fpr_recipe_tree.pack(side='left', fill='both', expand=True)
            rec_scroll = Scrollbar(recipe_card, orient='vertical', command=self._fpr_recipe_tree.yview)
            self._fpr_recipe_tree.configure(yscrollcommand=rec_scroll.set)
            rec_scroll.pack(side='right', fill='y')
            self._fpr_recipe_tree.bind('<<TreeviewSelect>>', self._fpr_on_recipe_select)
            self._fpr_recipe_tree.bind('<Double-Button-1>', lambda e: self._fpr_add_to_cart(dialog))

            right_frame = Frame(paned, bg=self.colors['background'])
            paned.add(right_frame, weight=50)

            detail_card = LabelFrame(right_frame, text="Состав спецификации",
                                     font=self.fonts['body_semibold'],
                                     padx=10, pady=10, bg=self.colors['background'])
            detail_card.pack(fill='both', expand=True, pady=(0, 5))

            self._fpr_comp_tree = ttk.Treeview(
                detail_card, columns=('comp', 'name', 'percent'), show='headings', height=5
            )
            self._fpr_comp_tree.heading('comp', text='Код компонента')
            self._fpr_comp_tree.heading('name', text='Наименование')
            self._fpr_comp_tree.heading('percent', text='Доля, %')
            self._fpr_comp_tree.column('comp', width=80, anchor='center')
            self._fpr_comp_tree.column('name', width=150, anchor='w')
            self._fpr_comp_tree.column('percent', width=70, anchor='center')
            self._fpr_comp_tree.pack(fill='both', expand=True)

            btn_frame = Frame(right_frame, bg=self.colors['background'])
            btn_frame.pack(fill='x', pady=5)
            self.create_modern_button(btn_frame, "➕ В корзину",
                                      lambda: self._fpr_add_to_cart(dialog), 'success').pack(side='left', padx=3)
            self.create_modern_button(btn_frame, "🗑️ Удалить",
                                      lambda: self._fpr_remove_from_cart(dialog), 'danger').pack(side='left', padx=3)
            self.create_modern_button(btn_frame, "🧮 Потребность",
                                      lambda: self._fpr_show_requirements(dialog), 'primary').pack(side='left', padx=3)
            self.create_modern_button(btn_frame, "📉 Дефицит ГП",
                                      lambda: self._fpr_calculate_deficit(dialog), 'warning').pack(side='left', padx=3)

            cart_card = LabelFrame(right_frame, text="Корзина производства",
                                 font=self.fonts['body_semibold'],
                                 padx=10, pady=10, bg=self.colors['background'])
            cart_card.pack(fill='both', expand=True, pady=(0, 5))

            self._fpr_cart_tree = ttk.Treeview(
                cart_card, columns=('code', 'name', 'qty'), show='headings', height=5
            )
            self._fpr_cart_tree.heading('code', text='Код')
            self._fpr_cart_tree.heading('name', text='Наименование')
            self._fpr_cart_tree.heading('qty', text='Кол-во')
            self._fpr_cart_tree.column('code', width=80, anchor='center')
            self._fpr_cart_tree.column('name', width=150, anchor='w')
            self._fpr_cart_tree.column('qty', width=60, anchor='center')
            self._fpr_cart_tree.pack(side='left', fill='both', expand=True)
            cart_scroll = Scrollbar(cart_card, orient='vertical', command=self._fpr_cart_tree.yview)
            self._fpr_cart_tree.configure(yscrollcommand=cart_scroll.set)
            cart_scroll.pack(side='right', fill='y')

            inv_card = LabelFrame(right_frame, text="Остатки на складе",
                                  font=self.fonts['body_semibold'],
                                  padx=10, pady=10, bg=self.colors['background'])
            inv_card.pack(fill='both', expand=True)

            inv_toolbar = Frame(inv_card, bg=self.colors['background'])
            inv_toolbar.pack(fill='x', pady=(0, 5))
            self.create_modern_button(inv_toolbar, "Развернуть",
                                      lambda: self._fpr_expand_all_inventory(), 'secondary').pack(side='left', padx=3)
            self.create_modern_button(inv_toolbar, "Свернуть",
                                      lambda: self._fpr_collapse_all_inventory(), 'secondary').pack(side='left', padx=3)

            self._fpr_inv_tree = ttk.Treeview(
                inv_card, columns=('location', 'start', 'income', 'expense', 'ending'),
                show='tree headings', height=8
            )
            self._fpr_inv_tree.heading('#0', text='Код / Наименование')
            self._fpr_inv_tree.heading('location', text='Место')
            self._fpr_inv_tree.heading('start', text='Нач. остаток')
            self._fpr_inv_tree.heading('income', text='Приход')
            self._fpr_inv_tree.heading('expense', text='Расход')
            self._fpr_inv_tree.heading('ending', text='Кон. остаток')
            self._fpr_inv_tree.column('#0', width=220, anchor='w')
            self._fpr_inv_tree.column('location', width=100, anchor='center')
            self._fpr_inv_tree.column('start', width=80, anchor='center')
            self._fpr_inv_tree.column('income', width=80, anchor='center')
            self._fpr_inv_tree.column('expense', width=80, anchor='center')
            self._fpr_inv_tree.column('ending', width=80, anchor='center')
            self._fpr_inv_tree.pack(side='left', fill='both', expand=True)
            inv_scroll = Scrollbar(inv_card, orient='vertical', command=self._fpr_inv_tree.yview)
            self._fpr_inv_tree.configure(yscrollcommand=inv_scroll.set)
            inv_scroll.pack(side='right', fill='y')

            bottom_frame = Frame(main_frame, bg=self.colors['background'])
            bottom_frame.pack(fill='x', pady=(10, 0))
            self.create_modern_button(bottom_frame, "❌ Закрыть",
                                      lambda: self.safe_destroy_dialog(dialog), 'secondary').pack(side='right')
            Label(bottom_frame,
                  text="Двойной клик по продукции добавляет её в корзину. Загрузите спецификации и склад для расчёта.",
                  font=self.fonts['caption'],
                  bg=self.colors['background'],
                  fg=self.colors['text_muted']).pack(side='left')

            self._fpr_refresh_recipe_list()
            self._fpr_refresh_inventory_tree()
            self.logger.info("Диалог расчёта потребности готовой продукции открыт")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога потребности готовой продукции: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _fpr_calculate_deficit(self, parent_dialog):
        """Рассчитать дефицит готовой продукции из Excel по отрицательным конечным остаткам."""
        try:
            file_path = filedialog.askopenfilename(
                parent=parent_dialog,
                title="Выберите файл Дефицит по готовой продукции",
                filetypes=[("Excel файлы", "*.xlsx *.xls"), ("Все файлы", "*.*")]
            )
            if not file_path:
                return

            df = pd.read_excel(file_path)
            if df.empty:
                messagebox.showinfo("Информация", "Файл пуст", parent=parent_dialog)
                return

            # Нормализация заголовков
            header_map = {
                'код гп': 'КОД ГП',
                'наименование гп': 'Наименование ГП',
                'бренд': 'Бренд',
                'нач. остаток': 'Нач. остаток',
                'расход': 'Расход',
                'кон. остаток': 'Кон. Остаток',
                'кон остаток': 'Кон. Остаток',
                'кон.остаток': 'Кон. Остаток',
            }
            df.columns = [str(c).strip() for c in df.columns]
            normalized = {}
            for col in df.columns:
                key = col.lower().replace('ё', 'е')
                normalized[col] = header_map.get(key, col)
            df.rename(columns=normalized, inplace=True)

            required = ['КОД ГП', 'Наименование ГП', 'Бренд', 'Нач. остаток', 'Расход', 'Кон. Остаток']
            missing = [c for c in required if c not in df.columns]
            if missing:
                messagebox.showerror(
                    "Ошибка",
                    f"В файле отсутствуют столбцы: {', '.join(missing)}\n\nНайденные столбцы: {', '.join(df.columns)}",
                    parent=parent_dialog
                )
                return

            # Приведение к числовому типу
            for col in ['Нач. остаток', 'Расход', 'Кон. Остаток']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Оставляем только строки с отрицательным конечным остатком
            deficit_df = df[df['Кон. Остаток'] < 0].copy()
            # Сортируем по величине дефицита (наибольший по модулю вверху)
            deficit_df = deficit_df.sort_values(by='Кон. Остаток', ascending=True).reset_index(drop=True)

            if deficit_df.empty:
                messagebox.showinfo(
                    "Дефицит ГП",
                    "Отрицательных конечных остатков не найдено. Дефицит отсутствует.",
                    parent=parent_dialog
                )
                return

            # Суммарный дефицит по модулю
            total_deficit = abs(deficit_df['Кон. Остаток'].sum())
            rows = deficit_df[required].copy()
            rows['Дефицит (модуль)'] = rows['Кон. Остаток'].abs()

            self._fpr_show_deficit_window(parent_dialog, rows, total_deficit)
            self.logger.info(f"Дефицит ГП рассчитан: {len(rows)} позиций, суммарный дефицит {total_deficit:.2f}")

        except Exception as e:
            self.logger.error(f"Ошибка расчёта дефицита ГП: {e}")
            messagebox.showerror("Ошибка", f"Не удалось рассчитать дефицит:\n{str(e)}", parent=parent_dialog)

    def _fpr_show_deficit_window(self, parent_dialog, rows_df, total_deficit):
        """Показать окно с результатами дефицита готовой продукции."""
        dlg = tk.Toplevel(parent_dialog)
        dlg.title("Дефицит по готовой продукции")
        dlg.geometry("1100x650")
        dlg.configure(bg=self.colors['background'])
        dlg.transient(parent_dialog)
        dlg.resizable(True, True)

        top_frame = Frame(dlg, bg=self.colors['background'])
        top_frame.pack(fill='x', padx=10, pady=10)

        Label(top_frame,
              text=f"Всего позиций с дефицитом: {len(rows_df)}    Суммарный дефицит: {total_deficit:.2f}",
              font=self.fonts['body_semibold'],
              bg=self.colors['background'],
              fg=self.colors['text']).pack(side='left')

        tree_frame = Frame(dlg, bg=self.colors['background'])
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        tree = ttk.Treeview(tree_frame,
                            columns=('code', 'name', 'brand', 'start', 'expense', 'ending', 'deficit_abs'),
                            show='headings', height=20)
        tree.heading('code', text='КОД ГП')
        tree.heading('name', text='Наименование ГП')
        tree.heading('brand', text='Бренд')
        tree.heading('start', text='Нач. остаток')
        tree.heading('expense', text='Расход')
        tree.heading('ending', text='Кон. Остаток')
        tree.heading('deficit_abs', text='Дефицит (модуль)')

        tree.column('code', width=120, anchor='center')
        tree.column('name', width=280, anchor='w')
        tree.column('brand', width=120, anchor='center')
        tree.column('start', width=110, anchor='center')
        tree.column('expense', width=110, anchor='center')
        tree.column('ending', width=110, anchor='center')
        tree.column('deficit_abs', width=130, anchor='center')

        tree.pack(side='left', fill='both', expand=True)
        scroll = Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')

        for _, row in rows_df.iterrows():
            tree.insert('', 'end', values=(
                row['КОД ГП'],
                row['Наименование ГП'],
                row['Бренд'],
                f"{row['Нач. остаток']:.2f}" if pd.notna(row['Нач. остаток']) else "",
                f"{row['Расход']:.2f}" if pd.notna(row['Расход']) else "",
                f"{row['Кон. Остаток']:.2f}" if pd.notna(row['Кон. Остаток']) else "",
                f"{row['Дефицит (модуль)']:.2f}" if pd.notna(row['Дефицит (модуль)']) else ""
            ))

        btn_frame = Frame(dlg, bg=self.colors['background'])
        btn_frame.pack(pady=10)

        def do_export():
            save_path = filedialog.asksaveasfilename(
                parent=dlg,
                defaultextension=".xlsx",
                filetypes=[("Excel файлы", "*.xlsx")],
                title="Сохранить дефицит ГП"
            )
            if not save_path:
                return
            try:
                export_df = rows_df[['КОД ГП', 'Наименование ГП', 'Бренд', 'Нач. остаток', 'Расход', 'Кон. Остаток', 'Дефицит (модуль)']].copy()
                export_df.to_excel(save_path, index=False, engine='openpyxl')
                messagebox.showinfo("Экспорт", f"Данные сохранены в {save_path}", parent=dlg)
                self.logger.info(f"Экспорт дефицита ГП: {save_path}")
            except Exception as e:
                messagebox.showerror("Ошибка экспорта", str(e), parent=dlg)
                self.logger.error(f"Ошибка экспорта дефицита ГП: {e}")

        self.create_modern_button(btn_frame, "📊 Экспорт в Excel", do_export, 'primary').pack(side='left', padx=5)
        self.create_modern_button(btn_frame, "Закрыть", lambda: self.safe_destroy_dialog(dlg), 'secondary').pack(side='left', padx=5)

    def _fpr_refresh_recipe_list(self):
        """Обновить список готовой продукции в диалоге."""
        try:
            if not hasattr(self, '_fpr_recipe_tree'):
                return

            for item in self._fpr_recipe_tree.get_children():
                self._fpr_recipe_tree.delete(item)

            recipes = fp_req.enrich_recipes_with_availability(
                getattr(self, '_fpr_recipes', []),
                getattr(self, '_fpr_inventory_summary', {})
            )

            search_text = self._fpr_search_var.get().strip().lower() if hasattr(self, '_fpr_search_var') else ''
            if search_text:
                recipes = [r for r in recipes if search_text in r['code'].lower() or search_text in r['name'].lower()]

            self._fpr_current_available = recipes
            for rec in recipes:
                self._fpr_recipe_tree.insert('', 'end',
                    values=(rec['code'], rec['name'], rec['rc_number'], rec['max_units']))

            for item in self._fpr_comp_tree.get_children():
                self._fpr_comp_tree.delete(item)
        except Exception as e:
            self.logger.error(f"Ошибка обновления списка готовой продукции: {e}")

    def _fpr_on_recipe_select(self, event=None):
        """Показать состав выбранной спецификации."""
        try:
            selected = self._fpr_recipe_tree.selection()
            if not selected:
                return
            idx = self._fpr_recipe_tree.index(selected[0])
            if idx < 0 or idx >= len(self._fpr_current_available):
                return
            rec = self._fpr_current_available[idx]
            for item in self._fpr_comp_tree.get_children():
                self._fpr_comp_tree.delete(item)
            for comp_code, share in rec['components'].items():
                comp_name = ''
                for det in self._fpr_inventory_details:
                    if det['code'] == comp_code:
                        comp_name = det['name']
                        break
                self._fpr_comp_tree.insert('', 'end',
                    values=(comp_code, comp_name, f"{share * 100:.1f}"))
        except Exception as e:
            self.logger.error(f"Ошибка отображения состава спецификации: {e}")

    def _fpr_add_to_cart(self, parent_dialog):
        """Добавить выбранную готовую продукцию в корзину."""
        try:
            selected = self._fpr_recipe_tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите продукцию в таблице", parent=parent_dialog)
                return

            idx = self._fpr_recipe_tree.index(selected[0])
            if idx < 0 or idx >= len(self._fpr_current_available):
                return
            rec = self._fpr_current_available[idx]

            qty_str = simpledialog.askstring("Количество", "Введите количество:", parent=parent_dialog)
            if not qty_str:
                return
            try:
                qty = int(qty_str)
            except ValueError:
                messagebox.showerror("Ошибка", "Количество должно быть целым числом", parent=parent_dialog)
                return
            if qty < 1:
                messagebox.showerror("Ошибка", "Количество должно быть положительным", parent=parent_dialog)
                return

            for item in self._fpr_cart:
                if item['recipe']['code'] == rec['code'] and item['recipe']['rc_number'] == rec['rc_number']:
                    item['qty'] = qty
                    self._fpr_refresh_cart_view()
                    return

            self._fpr_cart.append({'recipe': rec, 'qty': qty})
            self._fpr_refresh_cart_view()
        except Exception as e:
            self.logger.error(f"Ошибка добавления в корзину: {e}")

    def _fpr_remove_from_cart(self, parent_dialog):
        """Удалить выбранную позицию из корзины."""
        try:
            selected = self._fpr_cart_tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите позицию в корзине", parent=parent_dialog)
                return
            idx = self._fpr_cart_tree.index(selected[0])
            if idx < len(self._fpr_cart):
                del self._fpr_cart[idx]
                self._fpr_refresh_cart_view()
        except Exception as e:
            self.logger.error(f"Ошибка удаления из корзины: {e}")

    def _fpr_refresh_cart_view(self):
        """Обновить отображение корзины."""
        try:
            for item in self._fpr_cart_tree.get_children():
                self._fpr_cart_tree.delete(item)
            for item in self._fpr_cart:
                rec = item['recipe']
                self._fpr_cart_tree.insert('', 'end',
                    values=(rec['code'], rec['name'], item['qty']))
        except Exception as e:
            self.logger.error(f"Ошибка обновления корзины: {e}")

    def _fpr_refresh_inventory_tree(self):
        """Обновить дерево остатков склада."""
        try:
            if not hasattr(self, '_fpr_inv_tree'):
                return

            expanded = set()
            for item in self._fpr_inv_tree.get_children():
                if self._fpr_inv_tree.item(item, 'open'):
                    expanded.add(self._fpr_inv_tree.item(item, 'text'))

            for item in self._fpr_inv_tree.get_children():
                self._fpr_inv_tree.delete(item)

            grouped = {}
            for det in self._fpr_inventory_details:
                code = det['code']
                if code not in grouped:
                    grouped[code] = {
                        'name': det['name'],
                        'locations': [],
                        'start': 0.0,
                        'income': 0.0,
                        'expense': 0.0,
                        'ending': 0.0
                    }
                grouped[code]['start'] += det['start']
                grouped[code]['income'] += det['income']
                grouped[code]['expense'] += det['expense']
                grouped[code]['ending'] += det['ending']
                grouped[code]['locations'].append(det)

            for code, data in grouped.items():
                parent = self._fpr_inv_tree.insert('', 'end',
                    text=f"{code} - {data['name']}",
                    values=('Сумма', data['start'], data['income'], data['expense'], data['ending']),
                    open=True)
                for det in data['locations']:
                    self._fpr_inv_tree.insert(parent, 'end',
                        text=det['location'],
                        values=(det['location'], det['start'], det['income'], det['expense'], det['ending']))

            for item in self._fpr_inv_tree.get_children():
                if self._fpr_inv_tree.item(item, 'text') in expanded:
                    self._fpr_inv_tree.item(item, open=True)
        except Exception as e:
            self.logger.error(f"Ошибка обновления дерева склада: {e}")

    def _fpr_expand_all_inventory(self):
        for item in self._fpr_inv_tree.get_children():
            self._fpr_expand_recursive(self._fpr_inv_tree, item)

    def _fpr_collapse_all_inventory(self):
        for item in self._fpr_inv_tree.get_children():
            self._fpr_collapse_recursive(self._fpr_inv_tree, item)

    def _fpr_expand_recursive(self, tree, item):
        tree.item(item, open=True)
        for child in tree.get_children(item):
            self._fpr_expand_recursive(tree, child)

    def _fpr_collapse_recursive(self, tree, item):
        tree.item(item, open=False)
        for child in tree.get_children(item):
            self._fpr_collapse_recursive(tree, child)

    def _fpr_show_requirements(self, parent_dialog):
        """Показать диалог с расчётом потребности компонентов."""
        try:
            if not self._fpr_cart:
                messagebox.showwarning("Предупреждение", "Корзина пуста", parent=parent_dialog)
                return

            req = fp_req.calculate_requirements(
                self._fpr_cart,
                self._fpr_inventory_summary,
                self._fpr_inventory_details
            )

            if not req:
                messagebox.showinfo("Информация", "Нет данных для расчёта потребности", parent=parent_dialog)
                return

            dlg = tk.Toplevel(parent_dialog)
            dlg.title("Потребность компонентов")
            dlg.geometry("1000x700")
            dlg.configure(bg=self.colors['background'])
            dlg.transient(parent_dialog)
            dlg.resizable(True, True)

            ctrl_frame = Frame(dlg, bg=self.colors['background'])
            ctrl_frame.pack(fill='x', padx=10, pady=10)

            tree = ttk.Treeview(dlg, columns=('name', 'recipe', 'need', 'stock', 'deficit'),
                                show='tree headings', height=20)
            tree.heading('#0', text='Код компонента')
            tree.heading('name', text='Наименование')
            tree.heading('recipe', text='Готовая продукция')
            tree.heading('need', text='Требуется')
            tree.heading('stock', text='На складе')
            tree.heading('deficit', text='Дефицит')
            tree.column('#0', width=120, anchor='w')
            tree.column('name', width=150, anchor='w')
            tree.column('recipe', width=220, anchor='w')
            tree.column('need', width=90, anchor='center')
            tree.column('stock', width=90, anchor='center')
            tree.column('deficit', width=90, anchor='center')
            tree.pack(fill='both', expand=True, padx=10, pady=(0, 10))

            for comp_code, data in req.items():
                stock = self._fpr_inventory_summary.get(comp_code, 0.0) if self._fpr_inventory_summary else 0.0
                deficit = data['total'] - stock
                parent = tree.insert('', 'end',
                    text=comp_code,
                    values=(
                        data['name'],
                        'Сумма',
                        f"{data['total']:.2f}",
                        f"{stock:.2f}" if self._fpr_inventory_summary else "—",
                        f"{deficit:.2f}" if self._fpr_inventory_summary and deficit > 0 else (
                            "0.00" if self._fpr_inventory_summary else "—")
                    ),
                    open=True)
                for det in data['details']:
                    tree.insert(parent, 'end',
                        text='',
                        values=(
                            data['name'],
                            f"{det['recipe_code']} {det['recipe_name']} (x{det['qty_recipe']})",
                            f"{det['need']:.2f}",
                            '',
                            ''
                        ))

            btn_frame = Frame(dlg, bg=self.colors['background'])
            btn_frame.pack(pady=10)

            def do_export():
                file_path = filedialog.asksaveasfilename(
                    parent=dlg,
                    defaultextension=".xlsx",
                    filetypes=[("Excel файлы", "*.xlsx")],
                    title="Сохранить потребность"
                )
                if not file_path:
                    return
                try:
                    fp_req.export_requirements_to_excel(req, self._fpr_inventory_summary, file_path)
                    messagebox.showinfo("Экспорт", f"Данные сохранены в {file_path}", parent=dlg)
                    self.logger.info(f"Экспорт потребности готовой продукции: {file_path}")
                except Exception as e:
                    messagebox.showerror("Ошибка экспорта", str(e), parent=dlg)
                    self.logger.error(f"Ошибка экспорта потребности: {e}")

            def do_produce():
                if not self._fpr_inventory_summary:
                    messagebox.showwarning("Предупреждение", "Склад не загружен", parent=dlg)
                    return
                for comp_code, data in req.items():
                    if self._fpr_inventory_summary.get(comp_code, 0) < data['total']:
                        messagebox.showerror("Ошибка", f"Недостаточно компонента '{comp_code}'", parent=dlg)
                        return
                for item in self._fpr_cart:
                    rec = item['recipe']
                    qty = item['qty']
                    self._fpr_inventory_summary, self._fpr_inventory_details = fp_req.produce(
                        rec, qty, self._fpr_inventory_summary, self._fpr_inventory_details)
                self._fpr_cart.clear()
                self._fpr_refresh_cart_view()
                self._fpr_refresh_inventory_tree()
                self._fpr_refresh_recipe_list()
                self.status_label.config(text="Производство готовой продукции по корзине выполнено")
                self.logger.info("Производство готовой продукции по корзине выполнено")
                messagebox.showinfo("Успех", "Производство выполнено, остатки склада обновлены", parent=dlg)
                dlg.destroy()

            self.create_modern_button(btn_frame, "⚙️ Произвести", do_produce, 'success').pack(side='left', padx=5)
            self.create_modern_button(btn_frame, "📊 Экспорт в Excel", do_export, 'primary').pack(side='left', padx=5)
            self.create_modern_button(btn_frame, "Закрыть", lambda: self.safe_destroy_dialog(dlg), 'secondary').pack(side='left', padx=5)

        except Exception as e:
            self.logger.error(f"Ошибка расчёта потребности: {e}")
            messagebox.showerror("Ошибка", f"Не удалось рассчитать потребность:\n{str(e)}", parent=parent_dialog)