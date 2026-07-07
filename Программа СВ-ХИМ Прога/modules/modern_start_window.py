# modules/modern_start_window.py
import tkinter as tk
from tkinter import (
    Frame, Label, Listbox, END, StringVar, Entry, Scrollbar,
    BooleanVar, Text
)
from tkinter import messagebox, filedialog
from tkinter import ttk

import os
from datetime import datetime
import pandas as pd

from modules.logger import system_logger, LogLevel
from modules.database import db_manager
from modules.ui_theme import COLORS, FONTS


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

        self.open_editors = {}

        # Переменные для импорт/экспорт и логов
        self.import_file_var = StringVar(value="")
        self.export_path_var = StringVar(value="")
        self.norms_file_var = StringVar(value="")
        self.norms_export_path_var = StringVar(value="")
        self.log_search_var = StringVar(value="")

        self.center_window()
        self.create_widgets()
        self.load_saved_cards()
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
            bordercolor=[("active", colors['primary'])]
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

    def create_dialog(self, title: str, width: int, height: int, header_color=None):
        """Создание типового диалога с центрированием и опциональной цветной шапкой"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.configure(bg=self.colors['background'])
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

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

            # Верхняя панель: минималистичный брендинг слева + статус справа
            header_frame = Frame(self.root,
                                 bg=self.colors['surface'],
                                 height=52)
            header_frame.pack(fill='x', side='top')
            header_frame.pack_propagate(False)

            brand_frame = Frame(header_frame, bg=self.colors['surface'])
            brand_frame.pack(side='left', padx=24)

            # Небольшой акцентный квадрат-логотип + название приложения
            logo_badge = Frame(brand_frame, bg=self.colors['primary'], width=8, height=24)
            logo_badge.pack(side='left', pady=14)
            logo_badge.pack_propagate(False)

            Label(brand_frame,
                  text="MOZER",
                  font=('Segoe UI', 14, 'bold'),
                  bg=self.colors['surface'],
                  fg=self.colors['on_surface']).pack(side='left', padx=(12, 6))

            Label(brand_frame,
                  text="Управление производством",
                  font=self.fonts['caption'],
                  bg=self.colors['surface'],
                  fg=self.colors['text_muted']).pack(side='left')

            # Справа статус
            status_frame = Frame(header_frame, bg=self.colors['surface'])
            status_frame.pack(side='right', padx=24)

            self.status_label = Label(status_frame,
                                      text="Готов к работе",
                                      font=self.fonts['caption'],
                                      bg=self.colors['surface'],
                                      fg=self.colors['text_muted'])
            self.status_label.pack(side='right')

            separator = Frame(self.root, height=1, bg=self.colors['border'])
            separator.pack(fill='x', side='top')

            main_frame = Frame(self.root, bg=self.colors['background'])
            main_frame.pack(fill='both', expand=True, padx=24, pady=(16, 20))

            self.notebook = ttk.Notebook(main_frame, style="TNotebook")
            self.notebook.pack(fill='both', expand=True)

            # Создаем вкладки
            self.create_home_tab()
            self.create_cards_tab()
            self.create_warehouse_tab()
            self.create_products_tab()
            self.create_nomenclature_tab()
            self.create_logs_tab()
            self.create_import_export_tab()

            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

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
        """Создание главной вкладки в современном стиле"""
        try:
            home_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(home_tab, text="🏠 Главная")

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
            header_frame.pack(fill='x', padx=20, pady=(20, 10))

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
            date_str = now.strftime(f"Сегодня {weekday} %d.%m.%Y г. время %H:%M МСК")

            Label(header_frame,
                  text=date_str,
                  font=self.fonts['body'],
                  bg=self.colors['background'],
                  fg=self.colors['on_background']).pack(anchor='w', pady=(0, 5))

            # Быстрый доступ
            quick_access_frame = Frame(scrollable_frame, bg=self.colors['background'])
            quick_access_frame.pack(fill='x', padx=40, pady=40)

            Label(quick_access_frame, text="Быстрый доступ",
                  font=self.fonts['h3'],
                  bg=self.colors['background'],
                  fg=self.colors['on_background']).pack(anchor='w', pady=(0, 20))

            quick_buttons = [
                ("📄 Создать карту", self.open_editor_tab, 'primary'),
                ("📋 Просмотр карт", lambda: self.notebook.select(1), 'secondary'),
                ("🏭 Управление складом", lambda: self.notebook.select(2), 'secondary'),
                ("📦 Продукты", lambda: self.notebook.select(3), 'secondary'),
                ("📤 Импорт/Экспорт", lambda: self.notebook.select(5), 'secondary'),
                ("📊 Системные логи", lambda: self.notebook.select(4), 'secondary')
            ]

            grid_frame = Frame(quick_access_frame, bg=self.colors['background'])
            grid_frame.pack(fill='x')

            for i, (text, command, color_type) in enumerate(quick_buttons):
                row = i // 3
                col = i % 3

                btn_frame = Frame(grid_frame, bg=self.colors['background'])
                btn_frame.grid(row=row, column=col, sticky='nsew', padx=10, pady=10)

                btn = self.create_modern_button(btn_frame, text, command, color_type)
                btn.pack(fill='x', expand=True)

                grid_frame.columnconfigure(col, weight=1)

            self.logger.debug("Главная вкладка создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания главной вкладки: {e}")
            raise

    def create_cards_tab(self):
        """Создание вкладки карт загрузок в современном стиле"""
        try:
            cards_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(cards_tab, text="📋 Карты загрузок")

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

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки карт: {e}")
            raise

    def create_warehouse_tab(self):
        """Создание вкладки склада в современном стиле"""
        try:
            warehouse_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(warehouse_tab, text="🏭 Склад")

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

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки склада: {e}")
            raise

    def create_products_tab(self):
        """Создание вкладки продуктов в современном стиле"""
        try:
            products_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(products_tab, text="📦 Продукты")

            container = Frame(products_tab, bg=self.colors['background'])
            container.pack(fill='both', expand=True, padx=20, pady=20)

            header_frame = Frame(container, bg=self.colors['background'])
            header_frame.pack(fill='x', pady=(0, 5))

            control_frame = Frame(header_frame, bg=self.colors['background'])
            control_frame.pack(side='right')

            refresh_btn = ttk.Button(
                control_frame,
                text="🔄",
                command=self.load_products_data,
                style="Compact.TButton"
            )
            refresh_btn.pack(side='left', padx=3)

            add_btn = ttk.Button(
                control_frame,
                text="➕",
                command=self.add_product_dialog,
                style="Compact.TButton"
            )
            add_btn.pack(side='left', padx=3)

            edit_btn = ttk.Button(
                control_frame,
                text="📝",
                command=self.edit_product_dialog,
                style="Compact.TButton"
            )
            edit_btn.pack(side='left', padx=3)

            ToolTip(refresh_btn, "Обновить список продуктов")
            ToolTip(add_btn, "Добавить продукт")
            ToolTip(edit_btn, "Редактировать выбранный продукт")

            list_inner = self.create_card_frame(container, padding=(0, 0))

            headers_frame = Frame(list_inner, bg=self.colors['hover'], height=40)
            headers_frame.pack(fill='x')
            headers_frame.pack_propagate(False)

            headers = ['Код', 'Наименование', 'Описание', 'Рецептур', 'Дата создания']
            for header in headers:
                Label(headers_frame, text=header,
                      font=self.fonts['body_semibold'],
                      bg=self.colors['hover'],
                      fg=self.colors['on_surface']).pack(side='left', padx=20, pady=10)

            list_container = Frame(list_inner, bg=self.colors['surface'])
            list_container.pack(fill='both', expand=True, padx=20, pady=20)

            scrollbar = Scrollbar(list_container)
            scrollbar.pack(side='right', fill='y')

            self.products_listbox = Listbox(list_container,
                                            yscrollcommand=scrollbar.set,
                                            font=self.fonts['body'],
                                            bg=self.colors['surface'],
                                            fg=self.colors['on_surface'],
                                            relief='flat',
                                            borderwidth=0,
                                            selectbackground=self.colors['primary_light'],
                                            selectforeground=self.colors['on_surface'],
                                            height=15)
            self.products_listbox.pack(side='left', fill='both', expand=True)

            scrollbar.config(command=self.products_listbox.yview)

            self.load_products_data()

            self.logger.debug("Вкладка 'Продукты' создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки продуктов: {e}")
            raise

    def create_nomenclature_tab(self):
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

            nom_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(nom_tab, text="🗂️ Номенклатура")

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

            ToolTip(refresh_btn, "Обновить дерево номенклатуры")
            ToolTip(add_folder_btn, "Добавить папку (группу)")
            ToolTip(add_item_btn, "Добавить позицию номенклатуры (продукт + шаблон карты)")
            ToolTip(edit_btn, "Редактировать выбранный элемент")
            ToolTip(delete_btn, "Удалить выбранный элемент (и вложенные)")

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
        """Диалог добавления новой позиции номенклатуры (продукт + шаблон карты)"""
        try:
            from modules.excel_template_processor import ExcelTemplateProcessor

            selected = self._get_selected_nomenclature_node()
            default_parent_id = None
            if selected:
                default_parent_id = selected['id'] if selected['item_type'] == 'folder' else selected['parent_id']

            dialog, main_frame = self.create_dialog(
                "Новая позиция номенклатуры", 520, 420, header_color=self.colors['primary']
            )

            Label(main_frame, text="Название позиции*:",
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

            Label(main_frame, text="Продукт (из справочника):",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

            products = db_manager.get_products()
            product_options = [('(не выбран)', None)] + [
                (f"{p['product_name']} ({p['product_code']})", p['product_code']) for p in products
            ]
            product_var = StringVar(value=product_options[0][0])
            product_combo = ttk.Combobox(main_frame, textvariable=product_var,
                                          values=[label for label, _ in product_options],
                                          state='readonly', style="Modern.TCombobox")
            product_combo.pack(fill='x', pady=(0, 10))

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
                if not name:
                    messagebox.showwarning("Внимание", "Введите название позиции")
                    return

                parent_id = None
                for label, node_id in folder_options:
                    if label == parent_var.get():
                        parent_id = node_id
                        break

                product_code = None
                for label, code in product_options:
                    if label == product_var.get():
                        product_code = code
                        break

                template_type = None
                for label, key in template_options:
                    if label == template_var.get():
                        template_type = key
                        break

                try:
                    db_manager.create_nomenclature_item(
                        name, parent_id=parent_id,
                        product_code=product_code, template_type=template_type
                    )
                    dialog.destroy()
                    self.load_nomenclature_tree()
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

            product_var = None
            product_options = []
            template_var = None
            template_options = []

            if not is_folder:
                Label(main_frame, text="Продукт (из справочника):",
                      font=self.fonts['body_semibold'],
                      bg=self.colors['background']).pack(anchor='w', pady=(5, 0))

                products = db_manager.get_products()
                product_options = [('(не выбран)', None)] + [
                    (f"{p['product_name']} ({p['product_code']})", p['product_code']) for p in products
                ]
                product_var = StringVar()
                product_combo = ttk.Combobox(main_frame, textvariable=product_var,
                                              values=[label for label, _ in product_options],
                                              state='readonly', style="Modern.TCombobox")
                product_combo.pack(fill='x', pady=(0, 10))
                default_product_label = '(не выбран)'
                for label, code in product_options:
                    if code == node.get('product_code'):
                        default_product_label = label
                        break
                product_var.set(default_product_label)

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
                    product_code = None
                    for label, code in product_options:
                        if label == product_var.get():
                            product_code = code
                            break
                    template_type = None
                    for label, key in template_options:
                        if label == template_var.get():
                            template_type = key
                            break
                    # Явно допускаем сброс в None: передаём отдельным UPDATE,
                    # т.к. update_nomenclature_node игнорирует None-параметры
                    # (кроме parent_id) для гибкости частичного обновления.
                    update_kwargs['product_code'] = product_code if product_code is not None else ''
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


    def create_logs_tab(self):
        """Создание вкладки логов в современном стиле"""
        try:
            logs_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(logs_tab, text="📊 Логи")

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

    def create_import_export_tab(self):
        """Создание вкладки импорта/экспорта в современном стиле"""
        try:
            import_tab = Frame(self.notebook, bg=self.colors['background'])
            self.notebook.add(import_tab, text="📤 Импорт/Экспорт")

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

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки импорта/экспорта: {e}")
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
                     ("Справочник продуктов", "products"),
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

    def load_products_data(self):
        """Загрузка данных продуктов из базы данных"""
        try:
            products = db_manager.get_products()

            if hasattr(self, 'products_listbox'):
                self.products_listbox.delete(0, END)

            if not products:
                if hasattr(self, 'products_listbox'):
                    self.products_listbox.insert(END, "Нет продуктов в базе данных")
                return

            for product in products:
                product_name = (product.get('product_name') or '')[:30]
                description = (product.get('description') or '')[:25]
                created_date = (product.get('created_date') or '')[:10]
                display_text = f"{product['product_code']:<15} {product_name:<30} "
                display_text += f"{description:<25} {product.get('recipe_count', 0):<10} "
                display_text += f"{created_date:<12}"

                if hasattr(self, 'products_listbox'):
                    self.products_listbox.insert(END, display_text)

            self.logger.info(f"Загружено {len(products)} продуктов")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных продуктов: {e}")
            if hasattr(self, 'products_listbox'):
                self.products_listbox.insert(END, f"Ошибка загрузки: {str(e)}")

    def add_product_dialog(self):
        """Диалоговое окно добавления нового продукта"""
        try:
            dialog, main_frame = self.create_dialog(
                "Добавление нового продукта", 500, 350, header_color=self.colors['primary']
            )

            Label(main_frame, text="ДОБАВЛЕНИЕ НОВОГО ПРОДУКТА",
                  font=self.fonts['h3'],
                  bg=self.colors['background']).pack(pady=5)

            form_frame = Frame(main_frame, padx=10, pady=10, bg=self.colors['background'])
            form_frame.pack(fill='both', expand=True)

            Label(form_frame, text="Код продукта*:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            code_var = StringVar()
            ttk.Entry(form_frame, textvariable=code_var,
                      font=self.fonts['body']).pack(fill='x', pady=(0, 10))

            Label(form_frame, text="Наименование*:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            name_var = StringVar()
            ttk.Entry(form_frame, textvariable=name_var,
                      font=self.fonts['body']).pack(fill='x', pady=(0, 10))

            Label(form_frame, text="Описание:",
                  font=self.fonts['body_semibold'],
                  bg=self.colors['background']).pack(anchor='w', pady=(5, 0))
            desc_text = Text(form_frame, height=4, font=self.fonts['body'])
            desc_text.pack(fill='x', pady=(0, 20))

            button_frame = Frame(main_frame, bg=self.colors['background'])
            button_frame.pack(pady=(0, 10), fill='x')

            def save_product():
                if not code_var.get() or not name_var.get():
                    messagebox.showwarning("Внимание", "Заполните обязательные поля (*)")
                    return

                description = desc_text.get("1.0", tk.END).strip()

                db_manager.create_product(
                    product_code=code_var.get(),
                    product_name=name_var.get(),
                    description=description
                )

                dialog.destroy()
                self.load_products_data()

                self.logger.info(f"Добавлен продукт: {code_var.get()} - {name_var.get()}")
                system_logger.log_operation("add_product",
                                            f"Добавлен продукт: {name_var.get()} ({code_var.get()})",
                                            user="user")

            save_btn = self.create_modern_button(
                button_frame, "Сохранить", save_product, 'success'
            )
            save_btn.pack(side='left', padx=10)

            cancel_btn = self.create_modern_button(
                button_frame, "Отмена", dialog.destroy, 'secondary'
            )
            cancel_btn.pack(side='right', padx=10)

        except Exception as e:
            self.logger.error(f"Ошибка добавления продукта: {e}")

    def edit_product_dialog(self):
        """Диалоговое окно редактирования продукта"""
        if not hasattr(self, 'products_listbox'):
            return

        selection = self.products_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите продукт для редактирования")
            return

        messagebox.showinfo("Информация", "Функционал редактирования продуктов будет реализован в следующей версии")
        self.logger.debug("Вызов метода редактирования продукта (в разработке)")

    def open_editor_tab(self):
        """Открыть новую вкладку с редактором"""
        try:
            system_logger.log_operation("open_editor_tab",
                                        "Создание новой вкладки редактора",
                                        user="user")

            tab_id = f"editor_{len(self.open_editors) + 1}"

            tab_frame = Frame(self.notebook, bg=self.colors['background'])

            try:
                from modules.loading_card_tab import LoadingCardTab
                editor = LoadingCardTab(tab_frame, self)
                editor.pack(fill='both', expand=True)
            except ImportError as e:
                self.logger.error(f"Не удалось импортировать LoadingCardTab: {e}")
                messagebox.showwarning("Предупреждение",
                                       "Модуль редактора карт не найден. Функционал будет доступен после установки.")
                return
            except Exception as e:
                self.logger.error(f"Ошибка создания редактора: {e}")
                messagebox.showerror("Ошибка", f"Не удалось создать редактор:\n{str(e)}")
                return

            tab_title = f"📝 РЕДАКТОР {len(self.open_editors) + 1}"
            self.notebook.add(tab_frame, text=tab_title)

            self.notebook.select(tab_frame)

            self.open_editors[tab_id] = editor

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

    def close_editor_tab(self, tab_frame):
        """Закрыть вкладку редактора"""
        try:
            # Находим индекс вкладки в notebook
            for i in range(self.notebook.index('end')):
                if self.notebook.nametowidget(self.notebook.tabs()[i]) == tab_frame:
                    # Удаляем вкладку из notebook
                    self.notebook.forget(i)

                    # Удаляем редактор из словаря открытых редакторов
                    for tab_id, editor in list(self.open_editors.items()):
                        if editor.master == tab_frame:
                            del self.open_editors[tab_id]
                            break

                    self.logger.info(f"Вкладка редактора закрыта. Осталось {len(self.open_editors)} вкладок.")
                    break

        except Exception as e:
            self.logger.error(f"Ошибка закрытия вкладки редактора: {e}")
            messagebox.showerror("Ошибка", f"Не удалось закрыть вкладку:\n{str(e)}")

    def on_tab_changed(self, event):
        """Обработчик изменения вкладки"""
        try:
            current_tab = self.notebook.select()
            if current_tab:
                tab_index = self.notebook.index(current_tab)
                tab_text = self.notebook.tab(tab_index, "text")

                status_texts = {
                    "🏠 Главная": "Главная страница • Готов к работе",
                    "📋 Карты загрузок": "Просмотр карт загрузок",
                    "🏭 Склад": "Управление складом",
                    "📦 Продукты": "Управление продуктами",
                    "📊 Логи": "Просмотр системных логов",
                    "📤 Импорт/Экспорт": "Импорт и экспорт данных"
                }

                self.status_label.config(text=status_texts.get(tab_text, "Готов к работе"))

                self.logger.debug(f"Переключена вкладка: {tab_text}")

        except Exception as e:
            self.logger.error(f"Ошибка обработки переключения вкладки: {e}")

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

                self.load_products_data()
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