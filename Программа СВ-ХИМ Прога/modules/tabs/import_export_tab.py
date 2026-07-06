import tkinter as tk
from tkinter import ttk, Frame, Label, Button, Entry, StringVar, BooleanVar, Checkbutton, Radiobutton, Scrollbar, \
    Canvas, messagebox, filedialog
import os
import pandas as pd
from datetime import datetime
from modules.database import db_manager
from modules.logger import system_logger, log_operation, LogLevel


class ImportExportTab:
    def __init__(self, master, notebook, start_window):
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('ImportExportTab')
        self.create_tab()

    def create_tab(self):
        """Создание вкладки для импорта/экспорта данных"""
        try:
            self.tab = Frame(self.notebook, bg='white')
            self.notebook.add(self.tab, text="📤 ИМПОРТ/ЭКСПОРТ")

            self.create_header()
            self.create_main_container()

            self.logger.debug("Вкладка 'Импорт/Экспорт' создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки импорта/экспорта: {e}")
            raise

    def create_header(self):
        """Создание заголовка вкладки"""
        header_frame = Frame(self.tab, bg='#1abc9c', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        Label(header_frame, text="ИМПОРТ И ЭКСПОРТ ДАННЫХ",
              font=('Arial', 16, 'bold'), bg='#1abc9c', fg='white').pack(pady=20)

    def create_main_container(self):
        """Создание основного контейнера с прокруткой"""
        # Основной контейнер
        main_container = Frame(self.tab, bg='white', padx=40, pady=40)
        main_container.pack(fill='both', expand=True)

        # Создаем Canvas с прокруткой
        canvas = Canvas(main_container, bg='white')
        scrollbar = Scrollbar(main_container, orient='vertical', command=canvas.yview)
        scrollable_frame = Frame(canvas, bg='white')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Теперь создаем notebook внутри scrollable_frame
        self.main_notebook = ttk.Notebook(scrollable_frame)
        self.main_notebook.pack(fill='both', expand=True, padx=20, pady=20)

        # Создаем вкладки
        self.create_recipes_tab()
        self.create_norms_tab()

    def create_recipes_tab(self):
        """Создание вкладки рецептур"""
        recipes_tab = Frame(self.main_notebook, bg='white')
        self.main_notebook.add(recipes_tab, text="📋 РЕЦЕПТУРЫ")

        # Левая панель - импорт рецептур
        import_frame = Frame(recipes_tab, bg='#ecf0f1', relief='solid', bd=1)
        import_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        Label(import_frame, text="📥 ИМПОРТ ИЗ EXCEL",
              font=('Arial', 14, 'bold'), bg='#1abc9c', fg='white').pack(fill='x', pady=10)

        import_content = Frame(import_frame, bg='#ecf0f1', padx=20, pady=20)
        import_content.pack(fill='both', expand=True)

        Label(import_content, text="Импорт данных рецептур из Excel файла:",
              font=('Arial', 11), bg='#ecf0f1').pack(anchor='w', pady=(0, 10))

        # Требования к файлу
        requirements_frame = Frame(import_content, bg='#fff3cd', relief='solid', bd=1, padx=10, pady=10)
        requirements_frame.pack(fill='x', pady=(0, 15))

        Label(requirements_frame, text="Требования к файлу Excel:",
              font=('Arial', 10, 'bold'), bg='#fff3cd', fg='#856404').pack(anchor='w')

        requirements_text = """
        Файл должен содержать следующие столбцы:
        1. Код продукта
        2. Наименование продукта
        3. Код рецептуры
        4. Наименование рецептуры
        5. Код компонента
        6. Наименование компонента
        7. Процент содержания
        8. Масса
        """

        Label(requirements_frame, text=requirements_text,
              font=('Consolas', 9), bg='#fff3cd', fg='#856404', justify='left').pack(anchor='w', pady=(5, 0))

        # Поле для отображения выбранного файла
        self.import_file_var = StringVar()
        Entry(import_content, textvariable=self.import_file_var,
              font=('Arial', 10), state='readonly',
              bg='white').pack(fill='x', pady=(0, 10))

        Button(import_content, text="📁 ВЫБРАТЬ ФАЙЛ EXCEL",
               command=self.select_import_file,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(pady=(0, 20))

        # Опции импорта
        import_options_frame = Frame(import_content, bg='#ecf0f1')
        import_options_frame.pack(fill='x', pady=(0, 20))

        self.create_backup_var = BooleanVar(value=True)
        Checkbutton(import_options_frame, text="Создать резервную копию базы данных перед импортом",
                    variable=self.create_backup_var,
                    font=('Arial', 10), bg='#ecf0f1').pack(anchor='w', pady=5)

        self.replace_existing_var = BooleanVar(value=False)
        Checkbutton(import_options_frame, text="Заменить существующие записи",
                    variable=self.replace_existing_var,
                    font=('Arial', 10), bg='#ecf0f1').pack(anchor='w', pady=5)

        # Кнопка импорта
        Button(import_content, text="🚀 НАЧАТЬ ИМПОРТ",
               command=self.start_import,
               bg='#2ecc71', fg='white', font=('Arial', 12, 'bold'),
               padx=20, pady=12, cursor="hand2").pack(pady=(10, 0))

        # Статус импорта
        self.import_status_label = Label(import_content, text="",
                                         font=('Arial', 10), bg='#ecf0f1')
        self.import_status_label.pack(pady=(20, 0))

        # Правая панель - экспорт рецептур
        export_frame = Frame(recipes_tab, bg='#ecf0f1', relief='solid', bd=1)
        export_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        Label(export_frame, text="📤 ЭКСПОРТ В EXCEL",
              font=('Arial', 14, 'bold'), bg='#1abc9c', fg='white').pack(fill='x', pady=10)

        export_content = Frame(export_frame, bg='#ecf0f1', padx=20, pady=20)
        export_content.pack(fill='both', expand=True)

        Label(export_content, text="Экспорт данных в Excel файл:",
              font=('Arial', 11), bg='#ecf0f1').pack(anchor='w', pady=(0, 10))

        # Выбор типа экспорта
        Label(export_content, text="Тип данных для экспорта:",
              font=('Arial', 10, 'bold'), bg='#ecf0f1').pack(anchor='w', pady=(5, 0))

        export_type_frame = Frame(export_content, bg='#ecf0f1')
        export_type_frame.pack(fill='x', pady=(0, 15))

        self.export_type_var = StringVar(value="cards")
        Radiobutton(export_type_frame, text="Карты загрузок",
                    variable=self.export_type_var, value="cards",
                    font=('Arial', 10), bg='#ecf0f1').pack(side='left', padx=10)

        Radiobutton(export_type_frame, text="Справочник продуктов",
                    variable=self.export_type_var, value="products",
                    font=('Arial', 10), bg='#ecf0f1').pack(side='left', padx=10)

        Radiobutton(export_type_frame, text="Данные склада",
                    variable=self.export_type_var, value="warehouse",
                    font=('Arial', 10), bg='#ecf0f1').pack(side='left', padx=10)

        # Поле для отображения выбранного пути
        self.export_path_var = StringVar()
        Entry(export_content, textvariable=self.export_path_var,
              font=('Arial', 10), state='readonly',
              bg='white').pack(fill='x', pady=(0, 10))

        Button(export_content, text="📁 ВЫБРАТЬ ПУТЬ ДЛЯ ЭКСПОРТА",
               command=self.select_export_path,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(pady=(0, 20))

        Button(export_content, text="🚀 НАЧАТЬ ЭКСПОРТ",
               command=self.start_export,
               bg='#2ecc71', fg='white', font=('Arial', 12, 'bold'),
               padx=20, pady=12, cursor="hand2").pack(pady=(10, 0))

        # Статус экспорта
        self.export_status_label = Label(export_content, text="",
                                         font=('Arial', 10), bg='#ecf0f1')
        self.export_status_label.pack(pady=(20, 0))

    def create_norms_tab(self):
        """Создание вкладки норм показателей"""
        norms_tab = Frame(self.main_notebook, bg='white')
        self.main_notebook.add(norms_tab, text="📊 НОРМЫ ПОКАЗАТЕЛЕЙ")

        # Заголовок
        norms_header = Frame(norms_tab, bg='#9b59b6', height=50)
        norms_header.pack(fill='x')
        norms_header.pack_propagate(False)

        Label(norms_header, text="ИМПОРТ И ЭКСПОРТ НОРМ ФИЗИКО-ХИМИЧЕСКИХ ПОКАЗАТЕЛЕЙ",
              font=('Arial', 14, 'bold'), bg='#9b59b6', fg='white').pack(pady=15)

        # Контейнер для норм
        norms_content = Frame(norms_tab, bg='white', padx=20, pady=20)
        norms_content.pack(fill='both', expand=True)

        # Левая панель - импорт норм
        import_norms_frame = Frame(norms_content, bg='#ecf0f1', relief='solid', bd=1)
        import_norms_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        Label(import_norms_frame, text="📥 ИМПОРТ НОРМ ИЗ EXCEL",
              font=('Arial', 14, 'bold'), bg='#9b59b6', fg='white').pack(fill='x', pady=10)

        import_norms_content = Frame(import_norms_frame, bg='#ecf0f1', padx=20, pady=20)
        import_norms_content.pack(fill='both', expand=True)

        Label(import_norms_content, text="Импорт норм физико-химических показателей:",
              font=('Arial', 11), bg='#ecf0f1').pack(anchor='w', pady=(0, 10))

        # Требования к файлу норм
        norms_requirements_frame = Frame(import_norms_content, bg='#fff3cd', relief='solid', bd=1, padx=10, pady=10)
        norms_requirements_frame.pack(fill='x', pady=(0, 15))

        Label(norms_requirements_frame, text="Требования к файлу Excel:",
              font=('Arial', 10, 'bold'), bg='#fff3cd', fg='#856404').pack(anchor='w')

        norms_requirements_text = """
        Файл должен содержать следующие столбцы:
        1. Код полуфабриката
        2. Наименование полуфабриката
        3. Код нормы
        4. Наименование нормы
        5. Нижняя граница
        6. Верхняя граница
        7. Строка (текстовое значение)
        8. Метод анализа
        """

        Label(norms_requirements_frame, text=norms_requirements_text,
              font=('Consolas', 9), bg='#fff3cd', fg='#856404', justify='left').pack(anchor='w', pady=(5, 0))

        # Поле для отображения выбранного файла
        self.norms_file_var = StringVar()
        Entry(import_norms_content, textvariable=self.norms_file_var,
              font=('Arial', 10), state='readonly',
              bg='white').pack(fill='x', pady=(0, 10))

        Button(import_norms_content, text="📁 ВЫБРАТЬ ФАЙЛ EXCEL С НОРМАМИ",
               command=self.select_norms_file,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(pady=(0, 20))

        # Опции импорта норм
        norms_options_frame = Frame(import_norms_content, bg='#ecf0f1')
        norms_options_frame.pack(fill='x', pady=(0, 20))

        self.norms_replace_var = BooleanVar(value=True)
        Checkbutton(norms_options_frame, text="Заменить существующие нормы",
                    variable=self.norms_replace_var,
                    font=('Arial', 10), bg='#ecf0f1').pack(anchor='w', pady=5)

        # Кнопка импорта норм
        Button(import_norms_content, text="🚀 НАЧАТЬ ИМПОРТ НОРМ",
               command=self.start_norms_import,
               bg='#2ecc71', fg='white', font=('Arial', 12, 'bold'),
               padx=20, pady=12, cursor="hand2").pack(pady=(10, 0))

        # Статус импорта норм
        self.norms_import_status_label = Label(import_norms_content, text="",
                                               font=('Arial', 10), bg='#ecf0f1')
        self.norms_import_status_label.pack(pady=(20, 0))

        # Правая панель - экспорт норм
        export_norms_frame = Frame(norms_content, bg='#ecf0f1', relief='solid', bd=1)
        export_norms_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        Label(export_norms_frame, text="📤 ЭКСПОРТ НОРМ В EXCEL",
              font=('Arial', 14, 'bold'), bg='#9b59b6', fg='white').pack(fill='x', pady=10)

        export_norms_content = Frame(export_norms_frame, bg='#ecf0f1', padx=20, pady=20)
        export_norms_content.pack(fill='both', expand=True)

        Label(export_norms_content, text="Экспорт норм физико-химических показателей:",
              font=('Arial', 11), bg='#ecf0f1').pack(anchor='w', pady=(0, 10))

        # Выбор продукта для экспорта
        Label(export_norms_content, text="Выберите продукт:",
              font=('Arial', 10, 'bold'), bg='#ecf0f1').pack(anchor='w', pady=(5, 0))

        self.export_norms_product_var = StringVar()
        self.export_norms_combo = ttk.Combobox(export_norms_content,
                                               textvariable=self.export_norms_product_var,
                                               font=('Arial', 10),
                                               state='readonly')
        self.export_norms_combo.pack(fill='x', pady=(0, 15))

        # Загружаем продукты с нормами
        self.load_products_with_norms()

        # Радиокнопки для выбора типа экспорта
        export_norms_type_frame = Frame(export_norms_content, bg='#ecf0f1')
        export_norms_type_frame.pack(fill='x', pady=(0, 20))

        self.export_norms_type_var = StringVar(value="selected")
        Radiobutton(export_norms_type_frame, text="Экспорт норм выбранного продукта",
                    variable=self.export_norms_type_var, value="selected",
                    font=('Arial', 10), bg='#ecf0f1').pack(anchor='w', pady=5)

        Radiobutton(export_norms_type_frame, text="Экспорт всех норм",
                    variable=self.export_norms_type_var, value="all",
                    font=('Arial', 10), bg='#ecf0f1').pack(anchor='w', pady=5)

        # Поле для отображения выбранного пути
        self.norms_export_path_var = StringVar()
        Entry(export_norms_content, textvariable=self.norms_export_path_var,
              font=('Arial', 10), state='readonly',
              bg='white').pack(fill='x', pady=(0, 10))

        Button(export_norms_content, text="📁 ВЫБРАТЬ ПУТЬ ДЛЯ ЭКСПОРТА",
               command=self.select_norms_export_path,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(pady=(0, 20))

        Button(export_norms_content, text="🚀 НАЧАТЬ ЭКСПОРТ НОРМ",
               command=self.start_norms_export,
               bg='#2ecc71', fg='white', font=('Arial', 12, 'bold'),
               padx=20, pady=12, cursor="hand2").pack(pady=(10, 0))

        # Статус экспорта норм
        self.norms_export_status_label = Label(export_norms_content, text="",
                                               font=('Arial', 10), bg='#ecf0f1')
        self.norms_export_status_label.pack(pady=(20, 0))

        # Статистика по нормам
        stats_frame = Frame(norms_tab, bg='#ecf0f1', height=40)
        stats_frame.pack(fill='x', padx=20, pady=(0, 20))
        stats_frame.pack_propagate(False)

        self.norms_stats_label = Label(stats_frame,
                                       text="Загружено норм: 0 | Продуктов с нормами: 0",
                                       font=('Arial', 9),
                                       bg='#ecf0f1',
                                       fg='#2c3e50')
        self.norms_stats_label.pack(pady=10)

        # Обновляем статистику
        self.update_norms_stats()

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
            self.import_status_label.config(text=f"Выбран файл: {os.path.basename(filename)}", fg='#3498db')

    @log_operation("Начало импорта", LogLevel.INFO)
    def start_import(self):
        """Запуск импорта данных из Excel"""
        filename = self.import_file_var.get()

        if not filename or not os.path.exists(filename):
            messagebox.showwarning("Внимание", "Выберите файл для импорта")
            return

        try:
            self.import_status_label.config(text="Импорт данных...", fg='#f39c12')
            self.master.update()

            # Создаем резервную копию базы данных при необходимости
            if self.create_backup_var.get():
                backup_name = f"loading_cards_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                import shutil
                shutil.copy2(db_manager.db_path, backup_name)
                self.logger.info(f"Создана резервная копия базы данных: {backup_name}")

            # Выполняем импорт
            success = db_manager.import_from_excel(filename, self.replace_existing_var.get())

            if success:
                self.import_status_label.config(text="✓ Импорт успешно завершен", fg='#27ae60')
                messagebox.showinfo("Успех", f"Данные успешно импортированы из файла:\n{filename}")

                # Обновляем данные в интерфейсе
                self.start_window.tabs['products'].load_products_data()
                self.start_window.tabs['cards'].load_saved_cards()
                self.start_window.tabs['warehouse'].load_warehouse_data()

                self.logger.info(f"Импорт данных из {filename} выполнен успешно")
            else:
                self.import_status_label.config(text="✗ Ошибка импорта", fg='#e74c3c')
                messagebox.showerror("Ошибка", "Не удалось импортировать данные из файла")
                self.logger.error(f"Ошибка импорта данных из {filename}")

        except Exception as e:
            self.import_status_label.config(text="✗ Ошибка импорта", fg='#e74c3c')
            messagebox.showerror("Ошибка", f"Ошибка импорта:\n{str(e)}")
            self.logger.error(f"Ошибка импорта: {e}")

    def select_export_path(self):
        """Выбор пути для экспорта"""
        filetypes = [
            ("Файлы Excel", "*.xlsx"),
            ("Все файлы", "*.*")
        ]

        export_type = self.export_type_var.get()
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
            self.export_status_label.config(text=f"Путь для экспорта: {os.path.basename(filename)}", fg='#3498db')

    @log_operation("Начало экспорта", LogLevel.INFO)
    def start_export(self):
        """Запуск экспорта данных в Excel"""
        export_path = self.export_path_var.get()
        export_type = self.export_type_var.get()

        if not export_path:
            messagebox.showwarning("Внимание", "Выберите путь для экспорта")
            return

        try:
            self.export_status_label.config(text="Экспорт данных...", fg='#f39c12')
            self.master.update()

            if export_type == "cards":
                # Экспорт всех карт загрузок
                self.export_all_cards(export_path)
            elif export_type == "products":
                # Экспорт справочника продуктов
                self.export_products(export_path)
            elif export_type == "warehouse":
                # Экспорт данных склада
                self.export_warehouse(export_path)

            self.export_status_label.config(text="✓ Экспорт успешно завершен", fg='#27ae60')
            messagebox.showinfo("Успех", f"Данные успешно экспортированы в файл:\n{export_path}")

            self.logger.info(f"Экспорт {export_type} данных в {export_path} выполнен успешно")

        except Exception as e:
            self.export_status_label.config(text="✗ Ошибка экспорта", fg='#e74c3c')
            messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{str(e)}")
            self.logger.error(f"Ошибка экспорта: {e}")

    def export_all_cards(self, output_path: str):
        """Экспорт всех карт загрузок в Excel"""
        cards = db_manager.get_loading_cards(limit=1000)

        # Создаем Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Лист со списком карт
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

            # Лист с деталями каждой карты
            for card in cards[:10]:  # Ограничиваем количество детализированных карт
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

                    sheet_name = f"Карта_{card['id']}"[:31]  # Ограничение длины имени листа
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
            self.norms_import_status_label.config(text=f"Выбран файл: {os.path.basename(filename)}", fg='#3498db')

    @log_operation("Импорт норм из Excel", LogLevel.INFO)
    def start_norms_import(self):
        """Запуск импорта норм из Excel"""
        filename = self.norms_file_var.get()

        if not filename or not os.path.exists(filename):
            messagebox.showwarning("Внимание", "Выберите файл для импорта норм")
            return

        try:
            self.norms_import_status_label.config(text="Импорт норм...", fg='#f39c12')
            self.master.update()

            # Получаем флаг замены существующих норм
            replace_existing = self.norms_replace_var.get()

            # Выполняем импорт
            success = db_manager.import_norms_from_excel(filename, replace_existing)

            if success:
                self.norms_import_status_label.config(text="✓ Нормы успешно импортированы", fg='#27ae60')

                # Обновляем статистику
                self.update_norms_stats()

                # Обновляем список продуктов для экспорта
                self.load_products_with_norms()

                messagebox.showinfo("Успех",
                                    f"Нормы физико-химических показателей успешно импортированы из файла:\n{filename}\n\n"
                                    f"Файл: {os.path.basename(filename)}\n"
                                    f"Тип импорта: {'Заменить существующие' if replace_existing else 'Добавить новые'}")

                self.logger.info(f"Нормы импортированы из {filename}")

            else:
                self.norms_import_status_label.config(text="✗ Ошибка импорта норм", fg='#e74c3c')
                messagebox.showerror("Ошибка",
                                     "Не удалось импортировать нормы из файла.\n"
                                     "Проверьте формат файла и наличие обязательных колонок.")

        except Exception as e:
            self.norms_import_status_label.config(text="✗ Ошибка импорта норм", fg='#e74c3c')
            messagebox.showerror("Ошибка", f"Ошибка импорта норм:\n{str(e)}")
            self.logger.error(f"Ошибка импорта норм: {e}")

    def load_products_with_norms(self):
        """Загрузка списка продуктов с нормами"""
        try:
            # Получаем продукты с нормами из базы данных
            products = db_manager.get_products_with_norms()

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

        export_type = self.export_norms_type_var.get()
        default_name = f"нормы_показателей_{datetime.now().strftime('%Y%m%d')}.xlsx"

        if export_type == "selected":
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
            self.norms_export_status_label.config(text=f"Путь для экспорта: {os.path.basename(filename)}", fg='#3498db')

    @log_operation("Экспорт норм в Excel", LogLevel.INFO)
    def start_norms_export(self):
        """Запуск экспорта норм в Excel"""
        export_path = self.norms_export_path_var.get()
        export_type = self.export_norms_type_var.get()

        if not export_path:
            messagebox.showwarning("Внимание", "Выберите путь для экспорта норм")
            return

        try:
            self.norms_export_status_label.config(text="Экспорт норм...", fg='#f39c12')
            self.master.update()

            product_code = None
            if export_type == "selected":
                selected = self.export_norms_product_var.get()
                if selected and " - " in selected:
                    product_code = selected.split(" - ")[0]

            # Выполняем экспорт
            success = db_manager.export_norms_to_excel(export_path, product_code)

            if success:
                self.norms_export_status_label.config(text="✓ Нормы успешно экспортированы", fg='#27ae60')
                messagebox.showinfo("Успех",
                                    f"Нормы физико-химических показателей успешно экспортированы в файл:\n{export_path}\n\n"
                                    f"Тип экспорта: {'Выбранный продукт' if product_code else 'Все продукты'}")

                self.logger.info(f"Нормы экспортированы в {export_path}")

            else:
                self.norms_export_status_label.config(text="✗ Ошибка экспорта норм", fg='#e74c3c')
                messagebox.showerror("Ошибка", "Не удалось экспортировать нормы.")

        except Exception as e:
            self.norms_export_status_label.config(text="✗ Ошибка экспорта норм", fg='#e74c3c')
            messagebox.showerror("Ошибка", f"Ошибка экспорта норм:\n{str(e)}")
            self.logger.error(f"Ошибка экспорта норм: {e}")

    def update_norms_stats(self):
        """Обновление статистики по нормам"""
        try:
            # Получаем статистику из базы данных
            total_norms = db_manager.get_norms_count()
            products_with_norms = db_manager.get_products_with_norms_count()

            self.norms_stats_label.config(
                text=f"Загружено норм: {total_norms} | Продуктов с нормами: {products_with_norms}"
            )

        except Exception as e:
            self.logger.error(f"Ошибка обновления статистики норм: {e}")