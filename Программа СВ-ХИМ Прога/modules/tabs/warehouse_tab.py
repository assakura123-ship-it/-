import tkinter as tk
from tkinter import ttk, Frame, Label, Button, Scrollbar, Entry, StringVar, messagebox, END
import os
from modules.database import db_manager
from modules.logger import system_logger, log_operation, LogLevel


class WarehouseTab:
    def __init__(self, master, notebook, start_window):  # ДОБАВИТЕ ЭТОТ КОНСТРУКТОР
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('WarehouseTab')
        self.create_tab()

    def create_tab(self):
        """Создание вкладки склада (обновленная версия с SQLite)"""
        try:
            self.tab = Frame(self.notebook, bg='white')
            self.notebook.add(self.tab, text="🏭 СКЛАД")

            self.create_header()
            self.create_controls()
            self.create_table()

            self.logger.debug("Вкладка 'Склад' создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки склада: {e}")
            raise

    def create_header(self):
        """Создание заголовка вкладки"""
        header_frame = Frame(self.tab, bg='#e67e22', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        Label(header_frame, text="УПРАВЛЕНИЕ СКЛАДОМ",
              font=('Arial', 16, 'bold'), bg='#e67e22', fg='white').pack(pady=20)

    def create_controls(self):
        """Создание панели управления"""
        control_frame = Frame(self.tab, bg='#f8f9fa')
        control_frame.pack(fill='x', padx=20, pady=20)

        Button(control_frame, text="🔄 ОБНОВИТЬ",
               command=self.load_warehouse_data,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="➕ ДОБАВИТЬ ПОЗИЦИЮ",
               command=self.add_warehouse_item,
               bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📥 ИМПОРТ ИЗ EXCEL",
               command=self.import_warehouse_from_excel,
               bg='#1abc9c', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📊 ОБНОВИТЬ ОСТАТКИ",
               command=self.update_stock_dialog,
               bg='#f39c12', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        # Поиск
        search_frame = Frame(control_frame, bg='#f8f9fa')
        search_frame.pack(side='right', padx=5)

        Label(search_frame, text="Поиск:", font=('Arial', 10), bg='#f8f9fa').pack(side='left')

        self.warehouse_search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=self.warehouse_search_var,
                             font=('Arial', 10), width=30)
        search_entry.pack(side='left', padx=(5, 0))
        search_entry.bind('<KeyRelease>', lambda e: self.filter_warehouse_items())

    def create_table(self):
        """Создание таблицы склада"""
        table_frame = Frame(self.tab)
        table_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # Создаем Treeview для склада
        columns_warehouse = ('Код', 'Наименование', 'Остаток', 'Ед. изм.', 'Мин.', 'Макс.')  # Убрали 'Местоположение'
        self.warehouse_tree = ttk.Treeview(table_frame, columns=columns_warehouse, show='headings', height=15)

        # Настройка колонок
        column_widths_warehouse = [100, 250, 100, 80, 80, 80]  # Убрали ширину для 'Местоположение'
        for idx, col in enumerate(columns_warehouse):
            self.warehouse_tree.heading(col, text=col)
            self.warehouse_tree.column(col, width=column_widths_warehouse[idx], anchor='center')

        # Стилизация
        style = ttk.Style()
        style.configure("Treeview",
                        background="white",
                        foreground="black",
                        rowheight=25,
                        fieldbackground="white")
        style.map('Treeview', background=[('selected', '#3498db')])

        # Полоса прокрутки для таблицы склада
        warehouse_scrollbar = Scrollbar(table_frame, orient='vertical', command=self.warehouse_tree.yview)
        self.warehouse_tree.configure(yscrollcommand=warehouse_scrollbar.set)

        self.warehouse_tree.pack(side='left', fill='both', expand=True)
        warehouse_scrollbar.pack(side='right', fill='y')

        # Загружаем данные склада
        self.load_warehouse_data()

    @log_operation("Загрузка данных склада", LogLevel.INFO)
    def load_warehouse_data(self):
        """Загрузка данных склада из базы данных в Treeview"""
        try:
            items = db_manager.get_warehouse_items()

            # Очищаем таблицу
            for item in self.warehouse_tree.get_children():
                self.warehouse_tree.delete(item)

            if not items:
                # Вставляем сообщение, если нет данных
                self.warehouse_tree.insert('', 'end', values=(
                    "Нет данных", "", "", "", "", ""  # 6 значений вместо 7
                ))
                return

            for item in items:
                # Форматируем значения
                component_code = item['component_code']
                component_name = item['component_name']
                current_stock = f"{item['current_stock']:.2f}"
                unit = item.get('unit', 'кг')
                min_stock = f"{item.get('min_stock', 0):.1f}"
                max_stock = f"{item.get('max_stock', 0):.1f}"

                # Вставляем строку в таблицу (6 значений вместо 7)
                self.warehouse_tree.insert('', 'end', values=(
                    component_code,
                    component_name,
                    current_stock,
                    unit,
                    min_stock,
                    max_stock
                ))

            self.logger.info(f"Загружено {len(items)} позиций со склада")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных склада: {e}")
            # Вставляем сообщение об ошибке
            for item in self.warehouse_tree.get_children():
                self.warehouse_tree.delete(item)
            self.warehouse_tree.insert('', 'end', values=(
                f"Ошибка загрузки", str(e)[:50], "", "", "", ""  # 6 значений вместо 7
            ))

    def filter_warehouse_items(self):
        """Фильтрация позиций склада по поисковому запросу"""
        search_text = self.warehouse_search_var.get().lower()

        if not search_text:
            self.load_warehouse_data()
            return

        try:
            items = db_manager.get_warehouse_items()

            # Очищаем таблицу
            for item in self.warehouse_tree.get_children():
                self.warehouse_tree.delete(item)

            filtered_items = [item for item in items
                              if search_text in item['component_code'].lower()
                              or search_text in item['component_name'].lower()]

            if not filtered_items:
                self.warehouse_tree.insert('', 'end', values=(
                    "Ничего не найдено", "", "", "", "", ""  # 6 значений вместо 7
                ))
                return

            for item in filtered_items:
                component_code = item['component_code']
                component_name = item['component_name']
                current_stock = f"{item['current_stock']:.2f}"
                unit = item.get('unit', 'кг')
                min_stock = f"{item.get('min_stock', 0):.1f}"
                max_stock = f"{item.get('max_stock', 0):.1f}"

                self.warehouse_tree.insert('', 'end', values=(
                    component_code,
                    component_name,
                    current_stock,
                    unit,
                    min_stock,
                    max_stock
                ))

        except Exception as e:
            self.logger.error(f"Ошибка фильтрации склада: {e}")

    @log_operation("Добавление позиции на склад", LogLevel.INFO)
    def add_warehouse_item(self):
        """Добавление новой позиции на склад"""
        try:
            dialog = tk.Toplevel(self.master)
            dialog.title("Добавить позицию на склад")
            dialog.geometry("500x400")  # Уменьшили высоту, так как убрали поле
            dialog.resizable(False, False)
            dialog.grab_set()

            # Центрируем окно
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')

            # Заголовок
            header_frame = Frame(dialog, bg='#2ecc71', height=50)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)

            Label(header_frame, text="ДОБАВЛЕНИЕ ПОЗИЦИИ НА СКЛАД",
                  font=('Arial', 14, 'bold'), bg='#2ecc71', fg='white').pack(pady=15)

            # Основной контейнер с прокруткой
            main_frame = Frame(dialog, bg='white', padx=20, pady=10)
            main_frame.pack(fill='both', expand=True)

            # Поля ввода с метками
            fields_frame = Frame(main_frame, bg='white')
            fields_frame.pack(fill='x', pady=(0, 20))

            # Код компонента
            Label(fields_frame, text="Код компонента*:",
                  font=('Arial', 10, 'bold'), bg='white', anchor='w').grid(row=0, column=0, sticky='w', pady=(0, 5))
            code_var = StringVar()
            code_entry = Entry(fields_frame, textvariable=code_var, font=('Arial', 10), width=40)
            code_entry.grid(row=1, column=0, sticky='ew', pady=(0, 15))

            # Наименование
            Label(fields_frame, text="Наименование*:",
                  font=('Arial', 10, 'bold'), bg='white', anchor='w').grid(row=2, column=0, sticky='w', pady=(0, 5))
            name_var = StringVar()
            name_entry = Entry(fields_frame, textvariable=name_var, font=('Arial', 10), width=40)
            name_entry.grid(row=3, column=0, sticky='ew', pady=(0, 15))

            # Единица измерения
            Label(fields_frame, text="Единица измерения:",
                  font=('Arial', 10, 'bold'), bg='white', anchor='w').grid(row=4, column=0, sticky='w', pady=(0, 5))
            unit_var = StringVar(value="кг")
            unit_entry = Entry(fields_frame, textvariable=unit_var, font=('Arial', 10), width=40)
            unit_entry.grid(row=5, column=0, sticky='ew', pady=(0, 15))

            # Остаток
            Label(fields_frame, text="Начальный остаток:",
                  font=('Arial', 10, 'bold'), bg='white', anchor='w').grid(row=6, column=0, sticky='w', pady=(0, 5))
            stock_var = StringVar(value="0.0")
            stock_entry = Entry(fields_frame, textvariable=stock_var, font=('Arial', 10), width=40)
            stock_entry.grid(row=7, column=0, sticky='ew', pady=(0, 15))

            # Установить фокус на первое поле
            code_entry.focus_set()

            # Функция сохранения
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
                    # Проверяем, существует ли уже такой код
                    existing = db_manager.get_warehouse_items()
                    for item in existing:
                        if item['component_code'] == code_var.get().strip():
                            if not messagebox.askyesno("Подтверждение",
                                                       f"Компонент с кодом '{code_var.get()}' уже существует.\n"
                                                       "Продолжить?"):
                                return

                    # Добавляем в базу данных (без location)
                    db_manager.add_warehouse_item(
                        component_code=code_var.get().strip(),
                        component_name=name_var.get().strip(),
                        current_stock=stock,
                        unit=unit_var.get().strip(),
                        min_stock=0.0,
                        max_stock=1000.0
                    )

                    self.logger.info(f"Добавлена позиция на склад: {code_var.get()} - {name_var.get()}")

                    # Обновляем таблицу склада
                    self.load_warehouse_data()

                    # Закрываем диалог
                    dialog.destroy()

                    messagebox.showinfo("Успех", "Позиция успешно добавлена на склад!")

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось добавить позицию:\n{str(e)}")
                    self.logger.error(f"Ошибка добавления позиции: {e}")

            # Функция для обработки нажатия Enter
            def on_enter(event):
                save_item()

            # Привязываем Enter к сохранению
            dialog.bind('<Return>', on_enter)

            # Кнопки внизу
            button_frame = Frame(main_frame, bg='white', pady=10)
            button_frame.pack(side='bottom', fill='x')

            # Кнопка "Добавить"
            add_button = Button(button_frame, text="➕ ДОБАВИТЬ",
                                command=save_item,
                                bg='#2ecc71', fg='white',
                                font=('Arial', 11, 'bold'),
                                padx=30, pady=10,
                                cursor="hand2",
                                relief="flat")
            add_button.pack(side='left', padx=(0, 10))

            # Кнопка "Отмена"
            cancel_button = Button(button_frame, text="❌ ОТМЕНА",
                                   command=dialog.destroy,
                                   bg='#e74c3c', fg='white',
                                   font=('Arial', 11, 'bold'),
                                   padx=30, pady=10,
                                   cursor="hand2",
                                   relief="flat")
            cancel_button.pack(side='right')

            # Эффекты при наведении
            def on_enter_button(button, color):
                button.config(bg=color)

            def on_leave_button(button, original_color):
                button.config(bg=original_color)

            add_button.bind("<Enter>", lambda e: on_enter_button(add_button, '#27ae60'))
            add_button.bind("<Leave>", lambda e: on_leave_button(add_button, '#2ecc71'))

            cancel_button.bind("<Enter>", lambda e: on_enter_button(cancel_button, '#c0392b'))
            cancel_button.bind("<Leave>", lambda e: on_leave_button(cancel_button, '#e74c3c'))

            self.logger.debug("Открыто диалоговое окно добавления позиции на склад")

        except Exception as e:
            self.logger.error(f"Ошибка открытия диалога добавления позиции: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть диалог добавления:\n{str(e)}")

    @log_operation("Импорт склада из Excel", LogLevel.INFO)
    def import_warehouse_from_excel(self):
        """Импорт данных склада из Excel файла"""
        try:
            # Выбираем файл
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

            # Показываем сообщение о начале импорта
            self.start_window.status_bar.set_status("Импорт данных склада...")
            self.master.update()

            # Выполняем импорт
            success = db_manager.import_warehouse_from_excel(filename)

            if success:
                # Обновляем данные на вкладке склада
                self.load_warehouse_data()

                # Показываем сообщение об успехе
                self.start_window.status_bar.set_status(f"Данные склада импортированы из {os.path.basename(filename)}")

                messagebox.showinfo("Успех",
                                    f"Данные склада успешно импортированы!\n\n"
                                    f"Файл: {os.path.basename(filename)}")
            else:
                self.start_window.status_bar.set_status("Ошибка импорта данных склада")
                messagebox.showerror("Ошибка",
                                     "Не удалось импортировать данные склада из файла.\n"
                                     "Проверьте формат файла и наличие обязательных колонок.")

        except Exception as e:
            self.logger.error(f"Ошибка импорта склада: {e}")
            self.start_window.status_bar.set_status("Ошибка импорта склада")
            messagebox.showerror("Ошибка", f"Не удалось импортировать данные склада:\n{str(e)}")

    def update_stock_dialog(self):
        """Диалоговое окно для обновления остатков на складе"""
        messagebox.showinfo("Информация", "Функционал обновления остатков будет реализован в следующей версии")
        self.logger.debug("Вызов метода обновления остатков (в разработке)")