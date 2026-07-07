import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import Frame, Label, Button, StringVar, Entry, Scrollbar, Text, LabelFrame
import re
from datetime import datetime
import os
import tempfile
import shutil
from modules.logger import system_logger, log_operation, LogLevel
from modules.database import db_manager
from modules.excel_template_processor import ExcelTemplateProcessor


class LoadingCardTab(Frame):
    def __init__(self, parent, start_window=None):
        super().__init__(parent)
        self.start_window = start_window
        self.master = parent

        # Логгер для этого класса
        self.logger = system_logger.get_logger('LoadingCardTab')
        self.logger.info("Инициализация редактора карт загрузок (SQLite)")

        # Переменные
        self.product_code = None
        self.recipe_id = None
        self.card_id = None

        # Переменные для интерфейса
        self.product_var = StringVar()
        self.product_code_var = StringVar()
        self.recipe_var = StringVar()
        self.reactor_var = StringVar(value="Р-1")
        self.quantity_var = StringVar(value="1000")
        self.card_name_var = StringVar(value=f"Карта_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Списки для выпадающих меню
        self.product_list = []
        self.recipe_list = []

        # Данные для редактирования
        self.editable_data = []
        self.original_recipe_data = []
        self.analogs_data = []  # Данные для аналогов

        # Флаг несохраненных изменений
        self.has_unsaved_changes = False

        # Создание интерфейса
        self.create_widgets()

        # Загружаем список продуктов
        self.load_products_list()

        self.logger.info("Редактор карт загрузки успешно инициализирован")

    def create_widgets(self):
        """Создание виджетов интерфейса с тремя окнами"""
        try:
            # Главный контейнер с прокруткой
            main_container = Frame(self, bg='#f5f5f5')
            main_container.pack(fill='both', expand=True)

            # Canvas для прокрутки
            canvas = tk.Canvas(main_container, bg='#f5f5f5', highlightthickness=0)
            scrollbar = Scrollbar(main_container, orient='vertical', command=canvas.yview)
            scrollable_frame = Frame(canvas, bg='#f5f5f5')

            # Настройка прокрутки
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Упаковка canvas и scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Привязка колесика мыши к прокрутке
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # Заголовок вкладки с кнопкой закрытия
            header_frame = Frame(scrollable_frame, bg='#2c3e50', height=80)
            header_frame.pack(fill='x', pady=(0, 20))
            header_frame.pack_propagate(False)

            # Левая часть: название
            title_frame = Frame(header_frame, bg='#2c3e50')
            title_frame.pack(side='left', fill='both', expand=True)

            Label(title_frame, text="📋 РЕДАКТОР КАРТ ЗАГРУЗОК (SQLite)",
                  font=('Arial', 20, 'bold'), bg='#2c3e50', fg='white').pack(pady=20)

            # Правая часть: кнопка закрытия
            close_frame = Frame(header_frame, bg='#2c3e50')
            close_frame.pack(side='right', padx=20)

            close_btn = Button(close_frame, text="✕ ЗАКРЫТЬ ВКЛАДКУ",
                               command=self.close_tab,
                               bg='#e74c3c', fg='white',
                               font=('Arial', 10, 'bold'),
                               padx=10, pady=5,
                               cursor="hand2")
            close_btn.pack(pady=20)
            close_btn.bind("<Enter>", lambda e: close_btn.config(bg='#c0392b'))
            close_btn.bind("<Leave>", lambda e: close_btn.config(bg='#e74c3c'))

            # Панель управления
            control_frame = Frame(scrollable_frame, bg='#f5f5f5')
            control_frame.pack(fill='x', pady=(0, 20))

            # Кнопки загрузки и сохранения
            btn_frame = Frame(control_frame, bg='#f5f5f5')
            btn_frame.pack(side='left')

            self.save_card_btn = Button(btn_frame, text="💾 СОХРАНИТЬ КАРТУ В БАЗУ",
                                        command=self.save_loading_card,
                                        bg='#27ae60', fg='white', font=('Arial', 10, 'bold'),
                                        padx=15, pady=8, state='normal', cursor="hand2")
            self.save_card_btn.pack(side='left', padx=5)

            Button(btn_frame, text="📊 ЗАПОЛНИТЬ ШАБЛОН",
                   command=self.open_template_filler,
                   bg='#f39c12', fg='white', font=('Arial', 10, 'bold'),
                   padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

            Button(btn_frame, text="🔄 ОБНОВИТЬ",
                   command=self.refresh_data,
                   bg='#9b59b6', fg='white', font=('Arial', 10, 'bold'),
                   padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

            # Поле для названия карты
            name_frame = Frame(control_frame, bg='#f5f5f5')
            name_frame.pack(side='right', padx=20)

            Label(name_frame, text="Название карты:",
                  font=('Arial', 9), bg='#f5f5f5').pack(side='left')

            Entry(name_frame, textvariable=self.card_name_var,
                  font=('Arial', 9), width=30).pack(side='left', padx=(5, 0))

            # Индикатор несохраненных изменений
            self.unsaved_label = Label(control_frame, text="",
                                       font=('Arial', 9, 'bold'),
                                       bg='#f5f5f5', fg='#e74c3c')
            self.unsaved_label.pack(side='right', padx=20)

            # Панель параметров загрузки
            params_frame = Frame(scrollable_frame, bg='white', relief='solid', bd=1)
            params_frame.pack(fill='x', pady=(0, 20))

            # Внутренний фрейм для отступов
            inner_params = Frame(params_frame, bg='white', padx=20, pady=15)
            inner_params.pack(fill='x')

            Label(inner_params, text="ПАРАМЕТРЫ ЗАГРУЗКИ",
                  font=('Arial', 12, 'bold'), bg='white').pack(anchor='w', pady=(0, 15))

            # Первая строка - выбор продукта
            row1 = Frame(inner_params, bg='white')
            row1.pack(fill='x', pady=(0, 10))

            Label(row1, text="Продукт:", font=('Arial', 10, 'bold'),
                  bg='white', width=12, anchor='w').pack(side='left')

            # Поле для отображения выбранного продукта
            Entry(row1, textvariable=self.product_var,
                  font=('Arial', 10), width=100,
                  state='readonly', bg='#f8f9fa').pack(side='left', padx=(0, 5))

            # Кнопка выбора продукта
            Button(row1, text="...",
                   command=self.open_product_selector,
                   bg='#3498db', fg='white',
                   font=('Arial', 10, 'bold'),
                   width=3, cursor="hand2").pack(side='left', padx=(0, 20))

            Label(row1, text="Код продукта:", font=('Arial', 10, 'bold'),
                  bg='white', width=12, anchor='w').pack(side='left')

            Entry(row1, textvariable=self.product_code_var,
                  font=('Arial', 10), width=15, state='readonly',
                  bg='#f8f9fa').pack(side='left', padx=(0, 20))

            # Кнопка "Нормы" - ДОБАВЛЕНО
            self.norms_button = Button(row1,
                                       text="📊 НОРМЫ",
                                       command=self.show_product_norms,
                                       bg='#f39c12', fg='white',
                                       font=('Arial', 9, 'bold'),
                                       padx=10, pady=3,
                                       cursor="hand2",
                                       state='disabled')
            self.norms_button.pack(side='left')

            # Вторая строка - рецептура, реактор и количество
            row2 = Frame(inner_params, bg='white')
            row2.pack(fill='x', pady=(0, 10))

            Label(row2, text="Рецептура:", font=('Arial', 10, 'bold'),
                  bg='white', width=12, anchor='w').pack(side='left')

            # Выпадающий список рецептур
            self.recipe_combo = ttk.Combobox(row2,
                                             textvariable=self.recipe_var,
                                             font=('Arial', 10),
                                             state='readonly',
                                             width=30)
            self.recipe_combo.pack(side='left', padx=(0, 20))
            self.recipe_combo.bind('<<ComboboxSelected>>', self.on_recipe_selected)

            Label(row2, text="Реактор:", font=('Arial', 10, 'bold'),
                  bg='white', width=8, anchor='w').pack(side='left')

            Entry(row2, textvariable=self.reactor_var,
                  font=('Arial', 10), width=15).pack(side='left', padx=(0, 20))

            Label(row2, text="Количество, кг:", font=('Arial', 10, 'bold'),
                  bg='white', width=15, anchor='w').pack(side='left')

            Entry(row2, textvariable=self.quantity_var,
                  font=('Arial', 10), width=15,
                  validate='key',
                  validatecommand=(self.winfo_toplevel().register(self.validate_float), '%P')).pack(side='left')

            # Кнопка расчета
            Button(row2, text="📊 РАССЧИТАТЬ",
                   command=self.calculate_masses,
                   bg='#3498db', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='left', padx=(20, 0))

            # ===================== РЕДАКТИРУЕМАЯ РЕЦЕПТУРА =====================
            edit_frame = Frame(scrollable_frame, bg='white', relief='solid', bd=1)
            edit_frame.pack(fill='both', expand=True, pady=(0, 10))

            # Заголовок таблицы редактирования
            edit_header = Frame(edit_frame, bg='#3498db', height=40)
            edit_header.pack(fill='x')
            edit_header.pack_propagate(False)

            Label(edit_header, text="📝 РЕДАКТИРУЕМАЯ РЕЦЕПТУРА (двойной клик для редактирования)",
                  font=('Arial', 11, 'bold'), bg='#3498db', fg='white').pack(pady=10)

            # Кнопки управления редактируемой таблицей
            edit_controls = Frame(edit_frame, bg='white')
            edit_controls.pack(fill='x', padx=10, pady=10)

            Button(edit_controls, text="➕ ДОБАВИТЬ КОМПОНЕНТ",
                   command=self.add_component,
                   bg='#2ecc71', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='left', padx=5)

            Button(edit_controls, text="🗑️ УДАЛИТЬ ВЫБРАННЫЙ",
                   command=self.delete_component,
                   bg='#e74c3c', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='left', padx=5)

            Button(edit_controls, text="🔄 ОБНОВИТЬ РАСЧЕТ",
                   command=self.calculate_masses,
                   bg='#3498db', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='left', padx=5)

            Button(edit_controls, text="📋 КОПИРОВАТЬ В БУФЕР",
                   command=self.copy_to_clipboard,
                   bg='#9b59b6', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='right', padx=5)

            # Таблица для редактирования
            edit_table_frame = Frame(edit_frame)
            edit_table_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

            columns_edit = ('№', 'Код компонента', 'Наименование компонента', 'Процент, %', 'Масса, кг')
            self.edit_tree = ttk.Treeview(edit_table_frame, columns=columns_edit, show='headings', height=8)

            # Настройка колонок
            column_widths_edit = [50, 120, 250, 100, 100]
            for idx, col in enumerate(columns_edit):
                self.edit_tree.heading(col, text=col)
                self.edit_tree.column(col, width=column_widths_edit[idx], anchor='center')

            # Стилизация
            style = ttk.Style()
            style.configure("Treeview",
                            background="white",
                            foreground="black",
                            rowheight=25,
                            fieldbackground="white")
            style.map('Treeview', background=[('selected', '#3498db')])

            # Полоса прокрутки для таблицы редактирования
            edit_scrollbar = Scrollbar(edit_table_frame, orient='vertical', command=self.edit_tree.yview)
            self.edit_tree.configure(yscrollcommand=edit_scrollbar.set)

            self.edit_tree.pack(side='left', fill='both', expand=True)
            edit_scrollbar.pack(side='right', fill='y')

            # Привязываем события для редактирования
            self.edit_tree.bind('<Double-Button-1>', self.start_editing_cell)

            # Панель итогов редактируемой рецептуры
            edit_totals_frame = Frame(edit_frame, bg='#f8f9fa', height=30)
            edit_totals_frame.pack(fill='x', side='bottom')
            edit_totals_frame.pack_propagate(False)

            self.edit_totals_label = Label(edit_totals_frame,
                                           text="Сумма процентов: 0.0000% | Общая масса: 0.000 кг",
                                           font=('Arial', 9, 'bold'), bg='#f8f9fa', fg='#2c3e50')
            self.edit_totals_label.pack(pady=5)

            # ===================== НИЖНИЙ РЯД: ОРИГИНАЛЬНАЯ РЕЦЕПТУРА И АНАЛОГИ =====================
            bottom_frame = Frame(scrollable_frame, bg='#f5f5f5')
            bottom_frame.pack(fill='both', expand=True, pady=(0, 20))

            # Левая часть: оригинальная (не редактируемая) рецептура
            original_frame = Frame(bottom_frame, bg='white', relief='solid', bd=1)
            original_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

            # Заголовок оригинальной рецептуры
            original_header = Frame(original_frame, bg='#95a5a6', height=40)
            original_header.pack(fill='x')
            original_header.pack_propagate(False)

            Label(original_header, text="📄 ОРИГИНАЛЬНАЯ РЕЦЕПТУРА (не редактируется)",
                  font=('Arial', 11, 'bold'), bg='#95a5a6', fg='white').pack(pady=10)

            # Таблица оригинальной рецептуры
            original_table_frame = Frame(original_frame)
            original_table_frame.pack(fill='both', expand=True, padx=10, pady=10)

            columns_original = ('№', 'Код компонента', 'Наименование компонента', 'Процент, %')
            self.original_tree = ttk.Treeview(original_table_frame, columns=columns_original, show='headings', height=6)

            # Настройка колонок
            column_widths_original = [50, 120, 250, 100]
            for idx, col in enumerate(columns_original):
                self.original_tree.heading(col, text=col)
                self.original_tree.column(col, width=column_widths_original[idx], anchor='center')

            # Полоса прокрутки для оригинальной таблица
            original_scrollbar = Scrollbar(original_table_frame, orient='vertical', command=self.original_tree.yview)
            self.original_tree.configure(yscrollcommand=original_scrollbar.set)

            self.original_tree.pack(side='left', fill='both', expand=True)
            original_scrollbar.pack(side='right', fill='y')

            # Панель итогов оригинальной рецептуры
            original_totals_frame = Frame(original_frame, bg='#ecf0f1', height=30)
            original_totals_frame.pack(fill='x', side='bottom')
            original_totals_frame.pack_propagate(False)

            self.original_totals_label = Label(original_totals_frame,
                                               text="Сумма процентов: 0.0000%",
                                               font=('Arial', 9), bg='#ecf0f1', fg='#2c3e50')
            self.original_totals_label.pack(pady=5)

            # Правая часть: аналоги компонентов
            analogs_frame = Frame(bottom_frame, bg='white', relief='solid', bd=1)
            analogs_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

            # Заголовок аналогов
            analogs_header = Frame(analogs_frame, bg='#9b59b6', height=40)
            analogs_header.pack(fill='x')
            analogs_header.pack_propagate(False)

            Label(analogs_header, text="🔄 АНАЛОГИ КОМПОНЕНТОВ (список в разработке)",
                  font=('Arial', 11, 'bold'), bg='#9b59b6', fg='white').pack(pady=10)

            # Текстовая область для аналогов
            analogs_text_frame = Frame(analogs_frame)
            analogs_text_frame.pack(fill='both', expand=True, padx=10, pady=10)

            self.analogs_text = Text(analogs_text_frame,
                                     height=6,
                                     font=('Arial', 10),
                                     bg='#f8f9fa',
                                     wrap='word',
                                     state='normal')
            self.analogs_text.pack(fill='both', expand=True)

            # Добавляем заглушку
            self.analogs_text.insert('1.0', "Функционал аналогов компонентов находится в разработке.\n\n")
            self.analogs_text.insert('end', "Здесь будет отображаться информация о аналогах выбранного компонента.\n\n")
            self.analogs_text.insert('end', "Для использования:\n")
            self.analogs_text.insert('end', "1. Выберите компонент в таблице выше\n")
            self.analogs_text.insert('end', "2. Здесь появятся доступные аналоги\n")
            self.analogs_text.insert('end', "3. Двойной клик по аналоги - замена компонента")
            self.analogs_text.configure(state='disabled')

            # Кнопки управления аналогами
            analogs_controls = Frame(analogs_frame, bg='white')
            analogs_controls.pack(fill='x', padx=10, pady=(0, 10))

            Button(analogs_controls, text="📋 ЗАГРУЗИТЬ АНАЛОГИ",
                   command=self.load_analogs,
                   bg='#3498db', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='left', padx=5)

            Button(analogs_controls, text="➕ ДОБАВИТЬ АНАЛОГ",
                   command=self.add_analog,
                   bg='#2ecc71', fg='white', font=('Arial', 9, 'bold'),
                   padx=10, pady=3, cursor="hand2").pack(side='right', padx=5)

            # Статус бар внизу вкладки
            self.status_label = Label(self,
                                      text="Выберите продукт и рецептуру для создания карты загрузки",
                                      font=('Arial', 9),
                                      bg='#34495e',
                                      fg='white',
                                      anchor='w')
            self.status_label.pack(fill='x', side='bottom', ipady=5)

            self.logger.debug("Виджеты редактора успешно созданы (три окна)")

        except Exception as e:
            self.logger.error(f"Ошибка создания виджетов редактора: {e}")
            system_logger.log_error_with_traceback("Ошибка создания виджетов редактора", e)
            raise

    def open_product_selector(self):
        """Открыть диалоговое окно выбора продукта"""
        try:
            # Получаем список продуктов
            products = db_manager.get_products()

            if not products:
                messagebox.showwarning("Внимание", "Нет доступных продуктов. Загрузите продукты из Excel.")
                self.logger.warning("Нет доступных продуктов для выбора")
                return

            # Создаем диалоговое окно
            selector_dialog = tk.Toplevel(self)
            selector_dialog.title("Выбор продукта")
            selector_dialog.geometry("800x600")
            selector_dialog.resizable(True, True)
            selector_dialog.transient(self)
            selector_dialog.grab_set()

            # Центрируем окно
            self.center_window(selector_dialog)

            # Заголовок
            header_frame = Frame(selector_dialog, bg='#3498db', height=50)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)

            Label(header_frame, text="ВЫБОР ПРОДУКТА",
                  font=('Arial', 14, 'bold'),
                  bg='#3498db', fg='white').pack(pady=15)

            # Поиск
            search_frame = Frame(selector_dialog, bg='white', padx=20, pady=10)
            search_frame.pack(fill='x')

            Label(search_frame, text="Поиск:", font=('Arial', 10, 'bold'),
                  bg='white').pack(side='left')

            search_var = StringVar()
            search_entry = Entry(search_frame, textvariable=search_var,
                                 font=('Arial', 10), width=40)
            search_entry.pack(side='left', padx=(5, 10))

            search_entry.focus_set()

            # Таблица продуктов
            table_frame = Frame(selector_dialog, bg='white')
            table_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

            columns = ('Код', 'Наименование продукта', 'Рецептур')
            tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

            column_widths = [100, 400, 100]
            for idx, col in enumerate(columns):
                tree.heading(col, text=col)
                tree.column(col, width=column_widths[idx], anchor='center')

            # Заполняем таблицу
            for product in products:
                tree.insert('', 'end', values=(
                    product['product_code'],
                    product['product_name'],
                    product.get('recipe_count', 0)
                ))

            # Полоса прокрутки
            scrollbar = Scrollbar(table_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Кнопки
            button_frame = Frame(selector_dialog, bg='white', pady=10)
            button_frame.pack(fill='x')

            def select_product():
                """Выбрать выделенный продукт"""
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("Внимание", "Выберите продукт из списка")
                    return

                item = selection[0]
                values = tree.item(item, 'values')

                # Формируем текст для отображения
                display_text = f"{values[1]} (код: {values[0]})"

                # Устанавливаем значения в переменные
                self.product_var.set(display_text)
                self.product_code = values[0]
                self.product_code_var.set(values[0])

                # Активируем кнопку "Нормы"
                self.norms_button.config(state='normal')

                # Загружаем рецептуры для этого продукта
                self.load_recipes_for_product(values[0])

                selector_dialog.destroy()

                self.logger.info(f"Выбран продукт: {values[0]} - {values[1]}")

            def filter_products(*args):
                """Фильтрация продуктов по поисковому запросу"""
                search_text = search_var.get().strip().lower()

                # Удаляем все элементы
                for item in tree.get_children():
                    tree.delete(item)

                # Фильтруем и добавляем элементы
                for product in products:
                    product_name = product['product_name'].lower()
                    product_code = product['product_code'].lower()

                    if (search_text in product_name) or (search_text in product_code):
                        tree.insert('', 'end', values=(
                            product['product_code'],
                            product['product_name'],
                            product.get('recipe_count', 0)
                        ))

            # Привязываем поиск
            search_var.trace('w', filter_products)

            # Привязываем двойной клик по строке
            tree.bind('<Double-Button-1>', lambda e: select_product())

            # Привязываем Enter в поле поиска
            search_entry.bind('<Return>', lambda e: select_product())

            Button(button_frame, text="ВЫБРАТЬ",
                   command=select_product,
                   bg='#27ae60', fg='white',
                   font=('Arial', 10, 'bold'),
                   padx=20, pady=5, cursor="hand2").pack(side='left', padx=20)

            Button(button_frame, text="ОТМЕНА",
                   command=selector_dialog.destroy,
                   bg='#95a5a6', fg='white',
                   font=('Arial', 10, 'bold'),
                   padx=20, pady=5, cursor="hand2").pack(side='right', padx=20)

            self.logger.info("Открыт диалог выбора продукта")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога выбора продукта: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть выбор продукта: {str(e)}")

    def center_window(self, window):
        """Центрирование окна на экране"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def show_product_norms(self):
        """Отображение норм для выбранного продукта"""
        try:
            # Используем product_code_var вместо product_name_var
            product_code = self.product_code_var.get()
            if not product_code:
                messagebox.showwarning("Внимание", "Выберите продукт")
                return

            # Получаем нормы для продукта
            norms = db_manager.get_product_norms(product_code)

            if not norms:
                messagebox.showinfo("Информация", f"Для продукта {product_code} не найдено норм")
                return

            # Создаем диалоговое окно для отображения норм
            norms_window = tk.Toplevel(self)
            norms_window.title(f"Нормы физико-химических показателей: {product_code}")
            norms_window.geometry("900x600")

            # Заголовок
            header_frame = Frame(norms_window, bg='#9b59b6', height=50)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)

            Label(header_frame, text=f"НОРМЫ ФИЗИКО-ХИМИЧЕСКИХ ПОКАЗАТЕЛЕЙ: {product_code}",
                  font=('Arial', 14, 'bold'), bg='#9b59b6', fg='white').pack(pady=15)

            # Таблица норм
            table_frame = Frame(norms_window, bg='white')
            table_frame.pack(fill='both', expand=True, padx=20, pady=20)

            # Создаем таблицу
            columns = ('Код нормы', 'Наименование нормы', 'Нижняя граница', 'Верхняя граница', 'Строка',
                       'Метод анализа')
            tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

            column_widths = [100, 250, 120, 120, 150, 150]
            for idx, col in enumerate(columns):
                tree.heading(col, text=col)
                tree.column(col, width=column_widths[idx], anchor='center')

            # Заполняем таблицу
            for norm in norms:
                tree.insert('', 'end', values=(
                    norm.get('norm_code', ''),
                    norm.get('norm_name', ''),
                    norm.get('lower_limit', ''),
                    norm.get('upper_limit', ''),
                    norm.get('string_value', ''),
                    norm.get('analysis_method', '')
                ))

            # Полоса прокрутки
            scrollbar = Scrollbar(table_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Кнопки
            button_frame = Frame(norms_window, bg='white', pady=10)
            button_frame.pack(fill='x')

            Button(button_frame, text="ЗАКРЫТЬ",
                   command=norms_window.destroy,
                   bg='#95a5a6', fg='white', font=('Arial', 10, 'bold'),
                   padx=20, pady=5, cursor="hand2").pack(side='right', padx=20)

            self.logger.info(f"Отображены нормы для продукта: {product_code}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить нормы:\n{str(e)}")
            self.logger.error(f"Ошибка отображения норм: {e}")

    def open_template_filler(self):
        """Открыть диалог заполнения шаблона карты"""
        try:
            if not self.product_code or not self.editable_data:
                messagebox.showwarning("Внимание", "Сначала выберите продукт и заполните рецептуру")
                return

            # Создаем диалоговое окно
            filler_dialog = tk.Toplevel(self)
            filler_dialog.title("Заполнение шаблона карты загрузки")
            filler_dialog.geometry("900x700")
            filler_dialog.resizable(True, True)
            filler_dialog.transient(self)
            filler_dialog.grab_set()

            # Canvas для прокрутки
            canvas = tk.Canvas(filler_dialog, bg='white', highlightthickness=0)
            scrollbar = tk.Scrollbar(filler_dialog, orient='vertical', command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg='white')

            # Настройка прокрутки
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Заголовок
            header_frame = Frame(scrollable_frame, bg='#3498db', height=50)
            header_frame.pack(fill='x', pady=(0, 10))
            header_frame.pack_propagate(False)

            Label(header_frame, text="ЗАПОЛНЕНИЕ ШАБЛОНА КАРТЫ ЗАГРУЗКИ",
                  font=('Arial', 14, 'bold'), bg='#3498db', fg='white').pack(pady=15)

            # Основной контент
            content_frame = Frame(scrollable_frame, bg='white', padx=20, pady=10)
            content_frame.pack(fill='both', expand=True)

            # Основные данные
            main_frame = LabelFrame(content_frame, text="Основные данные",
                                    font=('Arial', 11, 'bold'),
                                    padx=10, pady=10, bg='white')
            main_frame.pack(fill='x', pady=(0, 10))

            # Цех
            Label(main_frame, text="Цех:", bg='white', anchor='w').grid(row=0, column=0, sticky='w', pady=5)
            workshop_var = StringVar(value="1 цех")
            Entry(main_frame, textvariable=workshop_var, width=30).grid(row=0, column=1, pady=5, padx=(10, 0))

            # Тип замеса
            Label(main_frame, text="Тип замеса:", bg='white', anchor='w').grid(row=1, column=0, sticky='w', pady=5)
            batch_type_var = StringVar(value="Замес")
            Entry(main_frame, textvariable=batch_type_var, width=30).grid(row=1, column=1, pady=5, padx=(10, 0))

            # Номер партии
            Label(main_frame, text="Номер партии:", bg='white', anchor='w').grid(row=2, column=0, sticky='w', pady=5)
            batch_num_var = StringVar(value=f"П-{datetime.now().strftime('%Y%m%d')}-{self.product_code}")
            Entry(main_frame, textvariable=batch_num_var, width=30).grid(row=2, column=1, pady=5, padx=(10, 0))

            # Временные параметры
            time_frame = LabelFrame(content_frame, text="Временные параметры",
                                    font=('Arial', 11, 'bold'),
                                    padx=10, pady=10, bg='white')
            time_frame.pack(fill='x', pady=(0, 10))

            time_params = [
                ("Время включения циркуляции:", "circulation"),
                ("Время включения нагрева:", "heating"),
                ("Время отбора пробы на вязкость:", "viscosity"),
                ("Время отбора пробы на готовность:", "readiness")
            ]

            time_vars = {}
            for i, (label, key) in enumerate(time_params):
                Label(time_frame, text=label, bg='white', anchor='w').grid(row=i, column=0, sticky='w', pady=5)
                var = StringVar()
                Entry(time_frame, textvariable=var, width=15).grid(row=i, column=1, pady=5, padx=(10, 0))
                time_vars[key] = var

            # Вязкость
            viscosity_frame = LabelFrame(content_frame, text="Вязкость",
                                         font=('Arial', 11, 'bold'),
                                         padx=10, pady=10, bg='white')
            viscosity_frame.pack(fill='x', pady=(0, 10))

            Label(viscosity_frame, text="Вязкость расчетная:", bg='white', anchor='w').grid(row=0, column=0, sticky='w',
                                                                                            pady=5)
            calc_vis_var = StringVar()
            Entry(viscosity_frame, textvariable=calc_vis_var, width=15).grid(row=0, column=1, pady=5, padx=(10, 0))

            Label(viscosity_frame, text="Вязкость фактическая:", bg='white', anchor='w').grid(row=1, column=0,
                                                                                              sticky='w', pady=5)
            actual_vis_var = StringVar()
            Entry(viscosity_frame, textvariable=actual_vis_var, width=15).grid(row=1, column=1, pady=5, padx=(10, 0))

            # Результаты испытаний
            test_frame = LabelFrame(content_frame, text="Результаты испытаний (готовое масло)",
                                    font=('Arial', 11, 'bold'),
                                    padx=10, pady=10, bg='white')
            test_frame.pack(fill='x', pady=(0, 10))

            test_params = [
                ("КВ при 100°С норма:", "kv_100_norm"),
                ("КВ при 100°С факт:", "kv_100_act"),
                ("КВ при 40°С норма:", "kv_40_norm"),
                ("КВ при 40°С факт:", "kv_40_act"),
                ("ИВ норма:", "iv_norm"),
                ("ИВ факт:", "iv_act"),
                ("CCS норма:", "ccs_norm"),
                ("CCS факт:", "ccs_act")
            ]

            test_vars = {}
            for i in range(0, len(test_params), 2):
                row = i // 2

                Label(test_frame, text=test_params[i][0], bg='white', anchor='w').grid(
                    row=row, column=0, sticky='w', pady=5)
                var1 = StringVar()
                Entry(test_frame, textvariable=var1, width=15).grid(
                    row=row, column=1, pady=5, padx=(10, 20))
                test_vars[test_params[i][1]] = var1

                if i + 1 < len(test_params):
                    Label(test_frame, text=test_params[i + 1][0], bg='white', anchor='w').grid(
                        row=row, column=2, sticky='w', pady=5)
                    var2 = StringVar()
                    Entry(test_frame, textvariable=var2, width=15).grid(
                        row=row, column=3, pady=5, padx=(10, 0))
                    test_vars[test_params[i + 1][1]] = var2

            # Подписи
            sign_frame = LabelFrame(content_frame, text="Подписи и соответствие",
                                    font=('Arial', 11, 'bold'),
                                    padx=10, pady=10, bg='white')
            sign_frame.pack(fill='x', pady=(0, 10))

            Label(sign_frame, text="Соответствие нормам (да/нет):", bg='white', anchor='w').grid(
                row=0, column=0, sticky='w', pady=5)
            compliance_var = StringVar(value="да")
            Entry(sign_frame, textvariable=compliance_var, width=10).grid(
                row=0, column=1, pady=5, padx=(10, 20))

            Label(sign_frame, text="Подпись лаборанта:", bg='white', anchor='w').grid(
                row=0, column=2, sticky='w', pady=5)
            lab_var = StringVar(value="Иванов И.И.")
            Entry(sign_frame, textvariable=lab_var, width=20).grid(
                row=0, column=3, pady=5, padx=(10, 0))

            Label(sign_frame, text="Аппаратчик:", bg='white', anchor='w').grid(
                row=1, column=0, sticky='w', pady=5)
            operator_var = StringVar(value="Петров П.П.")
            Entry(sign_frame, textvariable=operator_var, width=20).grid(
                row=1, column=1, pady=5, padx=(10, 20))

            Label(sign_frame, text="Дата завершения:", bg='white', anchor='w').grid(
                row=1, column=2, sticky='w', pady=5)
            date_var = StringVar(value=datetime.now().strftime('%d.%m.%Y'))
            Entry(sign_frame, textvariable=date_var, width=15).grid(
                row=1, column=3, pady=5, padx=(10, 0))

            # Кнопки
            button_frame = Frame(content_frame, bg='white', pady=20)
            button_frame.pack(fill='x')

            def save_excel():
                """Сохранить как Excel"""
                try:
                    from tkinter import filedialog

                    # Предлагаем сохранить файл
                    filetypes = [
                        ("Файлы Excel", "*.xlsx"),
                        ("Все файлы", "*.*")
                    ]

                    default_filename = f"карта_загрузки_{self.product_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                    filename = filedialog.asksaveasfilename(
                        title="Сохранить карту загрузки как Excel",
                        initialdir=".",
                        initialfile=default_filename,
                        defaultextension=".xlsx",
                        filetypes=filetypes
                    )

                    if not filename:
                        return

                    # Создаем данные для шаблона
                    card_data = {
                        'product_name': self.product_var.get(),
                        'product_code': self.product_code,
                        'workshop': workshop_var.get(),
                        'reactor': self.reactor_var.get(),
                        'batch_type': batch_type_var.get(),
                        'batch_quantity': self.quantity_var.get(),
                        'issue_date': datetime.now().strftime('%d.%m.%Y'),
                        'batch_number': batch_num_var.get(),
                        'start_date': datetime.now().strftime('%d.%m.%Y'),
                        'components': [],
                        'time_data': {
                            'circulation_start': time_vars['circulation'].get(),
                            'heating_start': time_vars['heating'].get(),
                            'viscosity_test_time': time_vars['viscosity'].get(),
                            'readiness_test_time': time_vars['readiness'].get(),
                            'calculated_viscosity': calc_vis_var.get(),
                            'actual_viscosity': actual_vis_var.get()
                        },
                        'test_results': {
                            'kv_100_norm': test_vars['kv_100_norm'].get(),
                            'kv_100_actual': test_vars['kv_100_act'].get(),
                            'kv_40_norm': test_vars['kv_40_norm'].get(),
                            'kv_40_actual': test_vars['kv_40_act'].get(),
                            'iv_norm': test_vars['iv_norm'].get(),
                            'iv_actual': test_vars['iv_act'].get(),
                            'ccs_norm': test_vars['ccs_norm'].get(),
                            'ccs_actual': test_vars['ccs_act'].get()
                        },
                        'signatures': {
                            'compliance': compliance_var.get(),
                            'lab_technician': lab_var.get(),
                            'operator': operator_var.get(),
                            'completion_date': date_var.get()
                        }
                    }

                    # Добавляем компоненты
                    for i, comp in enumerate(self.editable_data):
                        card_data['components'].append({
                            'name': comp.get('component_name', ''),
                            'percentage': comp.get('percentage', 0),
                            'mass': comp.get('mass', 0),
                            'container_number': '',
                            'actual_mass': '',
                            'correction': '',
                            'temperature': '',
                            'start_time': '',
                            'end_time': ''
                        })

                    # Создаем Excel файл
                    processor = ExcelTemplateProcessor()
                    success = processor.create_from_card_data(card_data, filename)

                    if success:
                        messagebox.showinfo("Успех", f"Excel файл сохранен:\n{filename}")
                        self.logger.info(f"Создан Excel файл: {filename}")
                        filler_dialog.destroy()
                    else:
                        messagebox.showerror("Ошибка", "Не удалось создать Excel файл")

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить Excel файл:\n{str(e)}")
                    self.logger.error(f"Ошибка сохранения Excel: {e}")

            def save_pdf():
                """Сохранить как PDF"""
                try:
                    from tkinter import filedialog
                    import tempfile

                    # Предлагаем сохранить файл
                    filetypes = [
                        ("PDF файлы", "*.pdf"),
                        ("Все файлы", "*.*")
                    ]

                    default_filename = f"карта_загрузки_{self.product_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                    filename = filedialog.asksaveasfilename(
                        title="Сохранить карту загрузки как PDF",
                        initialdir=".",
                        initialfile=default_filename,
                        defaultextension=".pdf",
                        filetypes=filetypes
                    )

                    if not filename:
                        return

                    # Создаем временный Excel файл
                    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                        temp_excel = tmp.name

                    # Создаем данные для шаблона (аналогично Excel)
                    card_data = {
                        'product_name': self.product_var.get(),
                        'product_code': self.product_code,
                        'workshop': workshop_var.get(),
                        'reactor': self.reactor_var.get(),
                        'batch_type': batch_type_var.get(),
                        'batch_quantity': self.quantity_var.get(),
                        'issue_date': datetime.now().strftime('%d.%m.%Y'),
                        'batch_number': batch_num_var.get(),
                        'start_date': datetime.now().strftime('%d.%m.%Y'),
                        'components': [],
                        'time_data': {
                            'circulation_start': time_vars['circulation'].get(),
                            'heating_start': time_vars['heating'].get(),
                            'viscosity_test_time': time_vars['viscosity'].get(),
                            'readiness_test_time': time_vars['readiness'].get(),
                            'calculated_viscosity': calc_vis_var.get(),
                            'actual_viscosity': actual_vis_var.get()
                        },
                        'test_results': {
                            'kv_100_norm': test_vars['kv_100_norm'].get(),
                            'kv_100_actual': test_vars['kv_100_act'].get(),
                            'kv_40_norm': test_vars['kv_40_norm'].get(),
                            'kv_40_actual': test_vars['kv_40_act'].get(),
                            'iv_norm': test_vars['iv_norm'].get(),
                            'iv_actual': test_vars['iv_act'].get(),
                            'ccs_norm': test_vars['ccs_norm'].get(),
                            'ccs_actual': test_vars['ccs_act'].get()
                        },
                        'signatures': {
                            'compliance': compliance_var.get(),
                            'lab_technician': lab_var.get(),
                            'operator': operator_var.get(),
                            'completion_date': date_var.get()
                        }
                    }

                    # Добавляем компоненты
                    for i, comp in enumerate(self.editable_data):
                        card_data['components'].append({
                            'name': comp.get('component_name', ''),
                            'percentage': comp.get('percentage', 0),
                            'mass': comp.get('mass', 0),
                            'container_number': '',
                            'actual_mass': '',
                            'correction': '',
                            'temperature': '',
                            'start_time': '',
                            'end_time': ''
                        })

                    # Создаем временный Excel
                    processor = ExcelTemplateProcessor()
                    success = processor.create_from_card_data(card_data, temp_excel)

                    if not success:
                        messagebox.showerror("Ошибка", "Не удалось создать временный Excel файл")
                        return

                    # Пытаемся конвертировать в PDF
                    if self.convert_excel_to_pdf_win32(temp_excel, filename):
                        messagebox.showinfo("Успех", f"PDF файл сохранен:\n{filename}")
                        self.logger.info(f"Создан PDF файл: {filename}")
                        filler_dialog.destroy()
                    else:
                        # Если не удалось конвертировать, предлагаем сохранить Excel
                        if messagebox.askyesno("Внимание",
                                               "Не удалось создать PDF. Сохранить как Excel файл?"):
                            excel_filename = filename.replace('.pdf', '.xlsx')
                            shutil.copy2(temp_excel, excel_filename)
                            messagebox.showinfo("Успех", f"Excel файл сохранен:\n{excel_filename}")
                            filler_dialog.destroy()

                    # Удаляем временный файл
                    try:
                        os.unlink(temp_excel)
                    except:
                        pass

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить PDF файл:\n{str(e)}")
                    self.logger.error(f"Ошибка сохранения PDF: {e}")

            Button(button_frame, text="💾 СОХРАНИТЬ EXCEL",
                   command=save_excel,
                   bg='#27ae60', fg='white', font=('Arial', 10, 'bold'),
                   padx=20, pady=8, cursor="hand2").pack(side='left', padx=10)

            Button(button_frame, text="📄 СОХРАНИТЬ PDF",
                   command=save_pdf,
                   bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
                   padx=20, pady=8, cursor="hand2").pack(side='left', padx=10)

            Button(button_frame, text="❌ ОТМЕНА",
                   command=filler_dialog.destroy,
                   bg='#95a5a6', fg='white', font=('Arial', 10, 'bold'),
                   padx=20, pady=8, cursor="hand2").pack(side='right', padx=10)

            self.logger.info("Открыт диалог заполнения шаблона карты")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога заполнения шаблона: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть форму заполнения: {str(e)}")

    def convert_excel_to_pdf_win32(self, excel_path, pdf_path):
        """Конвертация Excel в PDF с использованием win32com (Windows)"""
        try:
            import win32com.client
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False

            # Открываем Excel файл
            workbook = excel.Workbooks.Open(os.path.abspath(excel_path))

            # Экспортируем в PDF
            workbook.ExportAsFixedFormat(0, os.path.abspath(pdf_path))

            # Закрываем
            workbook.Close(SaveChanges=False)
            excel.Quit()

            return True
        except Exception as e:
            self.logger.error(f"Ошибка win32com конвертации: {e}")
            return False

    def close_tab(self):
        """Закрыть текущую вкладку"""
        try:
            self.logger.info("Закрытие вкладки редактора")
            if self.start_window:
                self.start_window.close_editor_tab(self.master)
        except Exception as e:
            self.logger.error(f"Ошибка закрытия вкладки: {e}")

    def validate_float(self, value):
        """Валидация ввода числа"""
        if value == "":
            return True
        try:
            float(value.replace(',', '.'))
            return True
        except ValueError:
            return False

    @log_operation("Загрузка списка продуктов", LogLevel.INFO)
    def load_products_list(self):
        """Загрузка списка продуктов в выпадающий список"""
        try:
            products = db_manager.get_products()

            if products:
                # Формируем список для ComboBox
                self.product_list = []
                for product in products:
                    display_text = f"{product['product_name']} (код: {product['product_code']})"
                    self.product_list.append(display_text)

                self.logger.info(f"Загружено {len(products)} продуктов")
                self.status_label.config(text=f"Загружено {len(products)} продуктов")
            else:
                self.logger.warning("В базе данных не найдено продуктов")
                self.status_label.config(text="В базе данных не найдено продуктов. Используйте импорт из Excel.")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки списка продуктов: {e}")
            self.status_label.config(text=f"Ошибка загрузки продуктов: {str(e)}")

    @log_operation("Загрузка рецептур продукта", LogLevel.INFO)
    def load_recipes_for_product(self, product_code: str):
        """Загрузка рецептур для выбранного продукта"""
        try:
            recipes = db_manager.get_recipes_for_product(product_code)

            # Формируем список рецептур
            self.recipe_list = []
            for recipe in recipes:
                display_text = f"РЦ-{recipe['recipe_number']} ({recipe.get('component_count', 0)} компон.)"
                if recipe.get('recipe_name'):
                    display_text += f" - {recipe['recipe_name']}"
                self.recipe_list.append(display_text)

            # Обновляем ComboBox
            self.recipe_combo['values'] = self.recipe_list

            if len(self.recipe_list) > 0:
                self.recipe_combo.current(0)
                self.on_recipe_selected()
                self.logger.info(f"Для продукта {product_code} найдено {len(recipes)} рецептур")
            else:
                self.recipe_var.set("")
                self.clear_tables()
                self.logger.warning(f"Для продукта {product_code} нет рецептур")
                self.status_label.config(text="Для этого продукта нет рецептур")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки рецептур для продукта {product_code}: {e}")
            self.status_label.config(text=f"Ошибка загрузки рецептур: {str(e)}")

    def on_recipe_selected(self, event=None):
        """Обработка выбора рецептуры"""
        selected_text = self.recipe_var.get()

        if not selected_text:
            return

        try:
            # Извлекаем номер рецептуры
            match = re.search(r'РЦ-(\S+)', selected_text)
            if match:
                recipe_number = match.group(1).strip()

                # Получаем рецептуру из базы данных
                recipe = db_manager.get_recipe_by_number(self.product_code, recipe_number)
                if recipe:
                    self.recipe_id = recipe['id']

                    # Загружаем состав рецептуры
                    self.load_recipe_composition()

                    self.logger.info(f"Выбрана рецептура РЦ-{recipe_number} (ID: {self.recipe_id})")
                    self.status_label.config(text=f"Выбрана рецептура РЦ-{recipe_number}")

        except Exception as e:
            self.logger.error(f"Ошибка выбора рецептуры: {e}")
            self.status_label.config(text=f"Ошибка выбора рецептуры: {str(e)}")

    @log_operation("Загрузка состава рецептуры", LogLevel.INFO)
    def load_recipe_composition(self):
        """Загрузка состава рецептуры"""
        self.clear_tables()

        if not self.recipe_id:
            return

        try:
            # Получаем компоненты рецептуры
            components = db_manager.get_recipe_components(self.recipe_id)

            # Сохраняем оригинальные данные
            self.original_recipe_data = components.copy()
            self.editable_data = components.copy()

            self.logger.info(f"Загружено {len(components)} компонентов рецептуры")

            # Обновляем обе таблицы
            self.update_edit_table()
            self.update_original_table()

            # Рассчитываем массы
            self.calculate_masses()

            # Логируем успешную загрузку
            system_logger.log_operation("load_recipe_composition",
                                        f"Рецептура загружена: {len(components)} компонентов",
                                        user="user",
                                        level=LogLevel.INFO)

        except Exception as e:
            self.logger.error(f"Ошибка загрузки состава рецептуры: {e}")
            self.status_label.config(text=f"Ошибка загрузки состава: {str(e)}")
            system_logger.log_error_with_traceback("Ошибка загрузки состава рецептуры", e)

    def update_edit_table(self):
        """Обновить редактируемую таблицу"""
        try:
            # Очищаем таблицу
            for item in self.edit_tree.get_children():
                self.edit_tree.delete(item)

            # Заполняем таблицу
            for i, item in enumerate(self.editable_data, 1):
                self.edit_tree.insert('', 'end', values=(
                    str(i),
                    item['component_code'],
                    item['component_name'],
                    f"{item['percentage']:.4f}",
                    f"{item.get('mass', 0.0):.3f}"
                ))

            # Добавляем итоговую строку
            if self.editable_data:
                total_percent = sum(item['percentage'] for item in self.editable_data)
                total_mass = sum(item.get('mass', 0.0) for item in self.editable_data)

                self.edit_tree.insert('', 'end', values=(
                    '',
                    'ВСЕГО:',
                    f"{len(self.editable_data)} компонентов",
                    f"{total_percent:.4f}",
                    f"{total_mass:.3f}"
                ))

            self.logger.debug(f"Обновлена редактируемая таблица: {len(self.editable_data)} строк")

            # Обновляем метку итогов
            self.update_edit_totals_label()

        except Exception as e:
            self.logger.error(f"Ошибка обновления редактируемой таблицы: {e}")

    def update_original_table(self):
        """Обновить таблицу оригинальной рецептуры"""
        try:
            # Очищаем таблицу
            for item in self.original_tree.get_children():
                self.original_tree.delete(item)

            # Заполняем таблицу
            for i, item in enumerate(self.original_recipe_data, 1):
                self.original_tree.insert('', 'end', values=(
                    str(i),
                    item['component_code'],
                    item['component_name'],
                    f"{item['percentage']:.4f}"
                ))

            # Добавляем итоговую строку
            if self.original_recipe_data:
                total_percent = sum(item['percentage'] for item in self.original_recipe_data)

                self.original_tree.insert('', 'end', values=(
                    '',
                    'ВСЕГО:',
                    f"{len(self.original_recipe_data)} компонентов",
                    f"{total_percent:.4f}"
                ))

            self.logger.debug(f"Обновлена оригинальная таблица: {len(self.original_recipe_data)} строк")

            # Обновляем метку итогов
            self.update_original_totals_label()

        except Exception as e:
            self.logger.error(f"Ошибка обновления оригинальной таблицы: {e}")

    def update_edit_totals_label(self):
        """Обновление метки с итогами редактируемой рецептуры"""
        if not self.editable_data:
            self.edit_totals_label.config(
                text="Сумма процентов: 0.0000% | Общая масса: 0.000 кг",
                fg='#2c3e50'
            )
            return

        try:
            total_percent = sum(item['percentage'] for item in self.editable_data)
            total_mass = sum(item.get('mass', 0.0) for item in self.editable_data)
            deviation = abs(total_percent - 100)

            if deviation > 0.0001:
                self.edit_totals_label.config(
                    text=f"⚠ Сумма процентов: {total_percent:.4f}% (отклонение: {deviation:.4f}%) | Общая масса: {total_mass:.3f} кг",
                    fg='#e74c3c'
                )
                self.logger.warning(f"Сумма процентов отклоняется от 100% на {deviation:.4f}%")
            else:
                self.edit_totals_label.config(
                    text=f"✓ Сумма процентов: {total_percent:.4f}% (100%) | Общая масса: {total_mass:.3f} кг",
                    fg='#27ae60'
                )

        except Exception as e:
            self.logger.error(f"Ошибка расчета итогов: {e}")

    def update_original_totals_label(self):
        """Обновление метки с итогами оригинальной рецептуры"""
        if not self.original_recipe_data:
            self.original_totals_label.config(
                text="Сумма процентов: 0.0000%",
                fg='#2c3e50'
            )
            return

        try:
            total_percent = sum(item['percentage'] for item in self.original_recipe_data)
            deviation = abs(total_percent - 100)

            if deviation > 0.0001:
                self.original_totals_label.config(
                    text=f"⚠ Сумма процентов: {total_percent:.4f}% (отклонение: {deviation:.4f}%)",
                    fg='#e74c3c'
                )
            else:
                self.original_totals_label.config(
                    text=f"✓ Сумма процентов: {total_percent:.4f}% (100%)",
                    fg='#27ae60'
                )

        except Exception as e:
            self.logger.error(f"Ошибка расчета итогов оригинальной рецептуры: {e}")

    @log_operation("Расчет масс компонентов", LogLevel.INFO)
    def calculate_masses(self):
        """Расчет масс компонентов на основе процентов и общего количества"""
        try:
            start_time = datetime.now()

            # Получаем общее количество
            quantity_str = self.quantity_var.get().strip()
            if not quantity_str:
                quantity = 1000.0
            else:
                quantity = float(quantity_str.replace(',', '.'))

            # Рассчитываем массы для редактируемых данных
            total_mass = 0

            for i, item in enumerate(self.editable_data):
                percent = item['percentage']
                mass = (percent / 100) * quantity

                # Обновляем данные
                item['mass'] = mass
                total_mass += mass

            # Обновляем таблицу
            self.update_edit_table()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.logger.info(f"Рассчитаны массы для {quantity:.1f} кг продукта, общая масса: {total_mass:.3f} кг")
            self.logger.debug(f"Время расчета масс: {duration:.6f} секунд")

            system_logger.log_performance("Расчет масс", start_time, end_time)
            system_logger.log_operation("calculate_masses",
                                        f"Расчет масс для {quantity:.1f} кг продукта",
                                        user="user")

            self.status_label.config(text=f"Рассчитано массы для {quantity:.1f} кг продукта")

        except Exception as e:
            self.logger.error(f"Ошибка расчета масс: {e}")
            self.status_label.config(text=f"Ошибка расчета масс: {str(e)}")
            system_logger.log_error_with_traceback("Ошибка расчета масс", e)

    def start_editing_cell(self, event):
        """Начать редактирование ячейки в редактируемой таблице"""
        try:
            # Определяем элемент и колонку
            item = self.edit_tree.identify_row(event.y)
            column = self.edit_tree.identify_column(event.x)

            if not item or column == '#0':
                return

            # Получаем индекс элемента
            children = self.edit_tree.get_children()
            if item not in children:
                return

            item_index = children.index(item)

            # Если это итоговая строка, не редактируем
            if item_index >= len(self.editable_data):
                return

            # Определяем номер колонки
            col_num = int(column[1:]) - 1

            # Получаем текущее значение
            current_values = self.edit_tree.item(item, 'values')
            if not current_values:
                return

            current_value = current_values[col_num]

            # Получаем координаты ячейки
            bbox = self.edit_tree.bbox(item, column)
            if not bbox:
                return

            x, y, width, height = bbox

            # Создаем поле ввода
            entry = Entry(self.edit_tree.master)
            entry.place(x=x + self.edit_tree.winfo_x() + 2,
                        y=y + self.edit_tree.winfo_y() + 2,
                        width=width, height=height)

            entry.insert(0, current_value)
            entry.select_range(0, tk.END)
            entry.focus_set()

            def save_edit(event=None):
                new_value = entry.get().strip()

                # Обновляем значение в дереве
                new_values = list(current_values)

                # Обрабатываем в зависимости от колонки
                if col_num == 3:  # Колонка "Процент, %"
                    try:
                        percent = float(new_value.replace(',', '.'))
                        percent = round(percent, 4)
                        new_values[col_num] = f"{percent:.4f}"

                        # Обновляем данные
                        self.editable_data[item_index]['percentage'] = percent

                        # Пересчитываем массу
                        quantity_str = self.quantity_var.get().strip()
                        if quantity_str:
                            quantity = float(quantity_str.replace(',', '.'))
                            mass = (percent / 100) * quantity
                            self.editable_data[item_index]['mass'] = mass
                            new_values[4] = f"{mass:.3f}"

                        # Устанавливаем флаг изменений
                        self.has_unsaved_changes = True
                        self.unsaved_label.config(text="⚠ Есть несохраненные изменения")

                        self.logger.info(f"Изменен процент компонента {item_index + 1} на {percent:.4f}%")

                    except ValueError:
                        # Если введено не число, оставляем старое значение
                        self.logger.warning(f"Некорректное значение процента: {new_value}")
                        pass
                elif col_num == 1:  # Колонка "Код компонента"
                    new_values[col_num] = new_value
                    self.editable_data[item_index]['component_code'] = new_value
                    self.has_unsaved_changes = True
                    self.unsaved_label.config(text="⚠ Есть несохраненные изменения")
                    self.logger.info(f"Изменен код компонента {item_index + 1} на {new_value}")
                elif col_num == 2:  # Колонка "Наименование компонента"
                    new_values[col_num] = new_value
                    self.editable_data[item_index]['component_name'] = new_value
                    self.has_unsaved_changes = True
                    self.unsaved_label.config(text="⚠ Есть несохраненные изменения")
                    self.logger.info(f"Изменено наименование компонента {item_index + 1} на {new_value}")

                self.edit_tree.item(item, values=tuple(new_values))

                # Пересчитываем итоги
                self.calculate_masses()

                entry.destroy()

            def cancel_edit(event=None):
                self.logger.debug("Отмена редактирования ячейки")
                entry.destroy()

            # Привязываем события
            entry.bind('<Return>', save_edit)
            entry.bind('<FocusOut>', save_edit)
            entry.bind('<Escape>', cancel_edit)

            self.logger.debug(f"Начато редактирование ячейки: строка {item_index}, колонка {col_num}")

        except Exception as e:
            self.logger.error(f"Ошибка начала редактирования ячейки: {e}")

    @log_operation("Добавление компонента", LogLevel.INFO)
    def add_component(self):
        """Добавить новый компонент"""
        try:
            # Создаем диалоговое окно
            add_dialog = tk.Toplevel(self.winfo_toplevel())
            add_dialog.title("Добавить компонент")
            add_dialog.geometry("400x300")

            Label(add_dialog, text="ДОБАВЛЕНИЕ НОВОГО КОМПОНЕНТА",
                  font=('Arial', 12, 'bold')).pack(pady=10)

            # Поля ввода
            input_frame = Frame(add_dialog)
            input_frame.pack(fill='both', expand=True, padx=20, pady=10)

            Label(input_frame, text="Код компонента:").pack(anchor='w', pady=(5, 0))
            code_var = StringVar()
            Entry(input_frame, textvariable=code_var, font=('Arial', 10)).pack(fill='x', pady=(0, 10))

            Label(input_frame, text="Наименование компонента:").pack(anchor='w', pady=(5, 0))
            name_var = StringVar()
            Entry(input_frame, textvariable=name_var, font=('Arial', 10)).pack(fill='x', pady=(0, 10))

            Label(input_frame, text="Процент, % (4 знака):").pack(anchor='w', pady=(5, 0))
            percent_var = StringVar(value="0.0000")
            Entry(input_frame, textvariable=percent_var, font=('Arial', 10)).pack(fill='x', pady=(0, 20))

            # Кнопки
            button_frame = Frame(add_dialog)
            button_frame.pack(fill='x', padx=20, pady=(0, 10))

            def add_component_action():
                code = code_var.get().strip()
                name = name_var.get().strip()
                percent_str = percent_var.get().strip()

                if not code or not name:
                    messagebox.showwarning("Внимание", "Заполните код и наименование компонента")
                    self.logger.warning("Попытка добавления компонента без кода или наименования")
                    return

                try:
                    percent = float(percent_str.replace(',', '.'))
                    percent = round(percent, 4)
                except:
                    messagebox.showwarning("Внимание", "Введите корректное число для процента")
                    self.logger.warning(f"Некорректное значение процента: {percent_str}")
                    return

                # Добавляем в редактируемые данные
                self.editable_data.append({
                    'id': None,
                    'recipe_id': self.recipe_id,
                    'component_code': code,
                    'component_name': name,
                    'percentage': percent,
                    'mass': 0.0
                })

                # Устанавливаем флаг изменений
                self.has_unsaved_changes = True
                self.unsaved_label.config(text="⚠ Есть несохраненные изменения")

                # Пересчитываем массы
                self.calculate_masses()

                add_dialog.destroy()

                self.logger.info(f"Добавлен новый компонент: код={code}, наименование={name}, процент={percent:.4f}%")
                system_logger.log_operation("add_component",
                                            f"Добавлен компонент: {name} ({code}) - {percent:.4f}%",
                                            user="user")

                messagebox.showinfo("Успех", "Компонент добавлен")

            Button(button_frame, text="Добавить", command=add_component_action,
                   bg='#2ecc71', fg='white', font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 10))

            Button(button_frame, text="Отмена", command=add_dialog.destroy,
                   bg='#95a5a6', fg='white', font=('Arial', 10, 'bold')).pack(side='right')

            self.logger.debug("Открыто диалоговое окно добавления компонента")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога добавления компонента: {e}")

    @log_operation("Удаление компонента", LogLevel.WARNING)
    def delete_component(self):
        """Удалить выбранный компонент"""
        try:
            selection = self.edit_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите компонент для удаления")
                self.logger.warning("Попытка удаления компонента без выбора")
                return

            # Проверяем, что выбран не итоговый ряд
            children = self.edit_tree.get_children()
            for item in selection:
                item_index = children.index(item)
                if item_index >= len(self.editable_data):
                    messagebox.showwarning("Внимание", "Нельзя удалить итоговую строку")
                    self.logger.warning("Попытка удаления итоговой строки")
                    return

            if not messagebox.askyesno("Подтверждение", "Удалить выбранный компонент?"):
                self.logger.info("Пользователь отменил удаление компонента")
                return

            # Запоминаем удаляемые компоненты для логирования
            deleted_components = []
            for item in selection:
                item_index = children.index(item)
                if item_index < len(self.editable_data):
                    deleted_components.append(self.editable_data[item_index])

            # Удаляем из редактируемых данных
            for item in reversed(selection):
                item_index = children.index(item)

                if item_index < len(self.editable_data):
                    # Удаляем из списка данных
                    del self.editable_data[item_index]

            # Устанавливаем флаг изменений
            self.has_unsaved_changes = True
            self.unsaved_label.config(text="⚠ Есть несохраненные изменения")

            # Пересчитываем массы
            self.calculate_masses()

            # Логируем удаление
            for component in deleted_components:
                self.logger.warning(
                    f"Удален компонент: код={component['component_code']}, наименование={component['component_name']}")
                system_logger.log_operation("delete_component",
                                            f"Удален компонент: {component['component_name']} ({component['component_code']})",
                                            user="user",
                                            level=LogLevel.WARNING)

            messagebox.showinfo("Успех", f"Удалено {len(deleted_components)} компонентов")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить компонент:\n{str(e)}")
            self.logger.error(f"Ошибка удаления компонента: {e}")
            system_logger.log_error_with_traceback("Ошибка удаления компонента", e)

    @log_operation("Копирование в буфер", LogLevel.INFO)
    def copy_to_clipboard(self):
        """Копировать рецептуру в буфер обмена"""
        try:
            # Логируем операцию
            system_logger.log_operation("copy_to_clipboard",
                                        f"Копирование рецептуры в буфер",
                                        user="user")

            text = "РЕЦЕПТУРА ДЛЯ КАРТЫ ЗАГРУЗКИ\n"
            text += "=" * 60 + "\n"
            text += f"Продукт: {self.product_var.get()}\n"
            text += f"Код: {self.product_code_var.get()}\n"
            text += f"Рецептура: {self.recipe_var.get()}\n"
            text += f"Реактор: {self.reactor_var.get()}\n"
            text += f"Количество: {self.quantity_var.get()} кг\n"
            text += "=" * 60 + "\n"
            text += f"{'№':<4} {'Код':<15} {'Наименование':<30} {'%':<10} {'Масса,кг':<10}\n"
            text += "-" * 60 + "\n"

            for i, item in enumerate(self.editable_data, 1):
                text += f"{i:<4} {item['component_code'][:15]:<15} {item['component_name'][:30]:<30} "
                text += f"{item['percentage']:<10.4f} {item.get('mass', 0.0):<10.3f}\n"

            # Добавляем итоги
            total_percent = sum(item['percentage'] for item in self.editable_data)
            total_mass = sum(item.get('mass', 0.0) for item in self.editable_data)

            text += "-" * 60 + "\n"
            text += f"ИТОГО: {len(self.editable_data)} компонентов | "
            text += f"Сумма %: {total_percent:.4f} | "
            text += f"Общая масса: {total_mass:.3f} кг\n"

            # Копируем в буфер
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(text)

            self.logger.info(f"Рецептура скопирована в буфер: {len(self.editable_data)} компонентов")

            messagebox.showinfo("Успех", "Рецептура скопирована в буфер обмена")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать в буфер:\n{str(e)}")
            self.logger.error(f"Ошибка копирования в буфер: {e}")
            system_logger.log_error_with_traceback("Ошибка копирования в буфер", e)

    @log_operation("Сохранение карты загрузки", LogLevel.INFO)
    def save_loading_card(self):
        """Сохранить карту загрузки в базу данных"""
        if not self.product_code or not self.recipe_id:
            messagebox.showwarning("Внимание", "Сначала выберите продукт и рецептуру")
            self.logger.warning("Попытка сохранения карты без выбора продукта и рецептуры")
            return

        if not self.editable_data:
            messagebox.showwarning("Внимание", "Нет данных для сохранения")
            self.logger.warning("Попытка сохранения пустой карты")
            return

        try:
            start_time = datetime.now()

            # Проверяем сумму процентов
            total_percent = sum(item['percentage'] for item in self.editable_data)
            deviation = abs(total_percent - 100)

            if deviation > 0.1:
                if not messagebox.askyesno("Предупреждение",
                                           f"Сумма процентов ({total_percent:.4f}%) отличается от 100% на {deviation:.4f}%\n"
                                           "Продолжить сохранение?"):
                    self.logger.warning(f"Пользователь отменил сохранение из-за отклонения процентов: {deviation:.4f}%")
                    return

            # Логируем начало сохранения
            system_logger.log_operation("save_loading_card",
                                        f"Начало сохранения карты для рецептуры {self.recipe_id}",
                                        user="user")

            # Получаем общее количество
            quantity_str = self.quantity_var.get().strip()
            if not quantity_str:
                quantity = 1000.0
            else:
                quantity = float(quantity_str.replace(',', '.'))

            # Рассчитываем общую массу
            total_mass = sum(item.get('mass', 0.0) for item in self.editable_data)

            # Создаем карту загрузки
            card_name = self.card_name_var.get().strip()
            if not card_name:
                card_name = f"Карта_{self.product_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            self.card_id = db_manager.create_loading_card(
                card_name=card_name,
                product_code=self.product_code,
                recipe_id=self.recipe_id,
                reactor=self.reactor_var.get(),
                batch_quantity=quantity
            )

            # Обновляем общую массу
            db_manager.update_card_total_mass(self.card_id, total_mass)

            # Добавляем компоненты
            warehouse_codes = {w['component_code'] for w in db_manager.get_warehouse_items()}
            missing_warehouse_components = []

            for item in self.editable_data:
                db_manager.add_card_component(
                    card_id=self.card_id,
                    component_code=item['component_code'],
                    component_name=item['component_name'],
                    percentage=item['percentage'],
                    calculated_mass=item.get('mass', 0.0)
                )

                # Списание компонента со склада (расход материалов)
                component_mass = item.get('mass', 0.0)
                if item['component_code'] in warehouse_codes and component_mass:
                    db_manager.update_warehouse_stock(item['component_code'], -component_mass)
                    self.logger.info(
                        f"Списано со склада: {item['component_code']} - {component_mass:.3f} кг")
                elif component_mass:
                    missing_warehouse_components.append(item['component_code'])

            if missing_warehouse_components:
                self.logger.warning(
                    "Компоненты отсутствуют на складе, списание не выполнено: "
                    + ", ".join(missing_warehouse_components)
                )

            # Обновляем данные склада в главном окне (если открыта вкладка склада)
            if self.start_window and hasattr(self.start_window, 'load_warehouse_data'):
                try:
                    self.start_window.load_warehouse_data()
                except Exception as refresh_err:
                    self.logger.warning(f"Не удалось обновить вкладку склада: {refresh_err}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Сбрасываем флаг изменений
            self.has_unsaved_changes = False
            self.unsaved_label.config(text="")

            # Логируем успешное сохранение
            self.logger.info(f"Карта загрузки сохранена в базу данных. ID: {self.card_id}")
            self.logger.info(f"Время сохранения: {duration:.3f} секунд")
            self.logger.info(f"Сохранено компонентов: {len(self.editable_data)}")

            system_logger.log_operation("save_loading_card",
                                        f"Карта сохранена: {card_name}, ID: {self.card_id}, компонентов: {len(self.editable_data)}",
                                        user="user",
                                        level=LogLevel.INFO)
            system_logger.log_performance("Сохранение карты загрузки", start_time, end_time)

            messagebox.showinfo("Успех", f"Карта загрузки сохранена в базу данных!\n\n"
                                         f"Название: {card_name}\n"
                                         f"ID карты: {self.card_id}\n"
                                         f"Количество компонентов: {len(self.editable_data)}")
            self.status_label.config(text=f"Карта загрузки сохранена. ID: {self.card_id}")

            # Обновляем список в главном окне
            if self.start_window:
                self.start_window.load_saved_cards()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить карту загрузки:\n{str(e)}")
            self.logger.error(f"Ошибка сохранения карты загрузки: {e}")
            system_logger.log_error_with_traceback("Ошибка сохранения карты загрузки", e)

    @log_operation("Обновление данных", LogLevel.INFO)
    def refresh_data(self):
        """Обновить данные"""
        try:
            # Перезагружаем список продуктов
            self.load_products_list()

            # Если выбран продукт, перезагружаем рецептуры
            if self.product_code:
                self.load_recipes_for_product(self.product_code)

            self.logger.info("Данные обновлены")
            self.status_label.config(text="Данные обновлены")

        except Exception as e:
            self.logger.error(f"Ошибка обновления данных: {e}")
            self.status_label.config(text=f"Ошибка обновления: {str(e)}")

    def clear_tables(self):
        """Очистка всех таблиц"""
        try:
            # Очищаем редактируемую таблицу
            for item in self.edit_tree.get_children():
                self.edit_tree.delete(item)

            # Очищаем оригинальную таблицу
            for item in self.original_tree.get_children():
                self.original_tree.delete(item)

            # Очищаем данные
            self.editable_data = []
            self.original_recipe_data = []

            # Обновляем итоговые метки
            self.update_edit_totals_label()
            self.update_original_totals_label()

            # Очищаем окно аналогов
            self.analogs_text.configure(state='normal')
            self.analogs_text.delete('1.0', tk.END)
            self.analogs_text.insert('1.0', "Функционал аналогов компонентов находится в разработке.")
            self.analogs_text.configure(state='disabled')

            self.logger.debug("Все таблицы очищены")

        except Exception as e:
            self.logger.error(f"Ошибка очистки таблиц: {e}")

    def load_analogs(self):
        """Загрузить аналоги для выбранного компонента"""
        try:
            selection = self.edit_tree.selection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите компонент для поиска аналогов")
                return

            # Получаем выбранный компонент
            item = selection[0]
            values = self.edit_tree.item(item, 'values')

            if not values:
                return

            component_code = values[1]
            component_name = values[2]

            # Очищаем окно аналогов
            self.analogs_text.configure(state='normal')
            self.analogs_text.delete('1.0', tk.END)

            # Заголовок
            self.analogs_text.insert('end', f"АНАЛОГИ ДЛЯ КОМПОНЕНТА:\n", 'header')
            self.analogs_text.insert('end', f"Код: {component_code}\n")
            self.analogs_text.insert('end', f"Наименование: {component_name}\n")
            self.analogs_text.insert('end', "-" * 40 + "\n\n")

            # Здесь будет логика поиска аналогов в базе данных
            # Пока используем заглушку
            self.analogs_text.insert('end', "Функционал поиска аналогов находится в разработке.\n\n")
            self.analogs_text.insert('end', "В будущих версиях здесь будут отображаться:\n")
            self.analogs_text.insert('end', "1. Прямые аналоги компонента\n")
            self.analogs_text.insert('end', "2. Заменители с указанием коэффициента замены\n")
            self.analogs_text.insert('end', "3. Информация о наличии на складе\n")
            self.analogs_text.insert('end', "4. Цена и поставщики\n")

            # Настройка тегов для форматирования
            self.analogs_text.tag_configure('header', font=('Arial', 10, 'bold'))

            self.analogs_text.configure(state='disabled')

            self.logger.info(f"Загружены аналоги для компонента: {component_code} - {component_name}")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки аналогов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить аналоги:\n{str(e)}")

    def add_analog(self):
        """Добавить аналог для компонента"""
        messagebox.showinfo("Информация", "Функционал добавления аналогов будет реализован в следующей версии")
        self.logger.debug("Вызов метода добавления аналога (в разработке)")