import tkinter as tk
from tkinter import Frame, Label, Button, Listbox, Scrollbar, END, StringVar, Entry, Text, messagebox
from modules.database import db_manager
from modules.logger import system_logger, log_operation, LogLevel


class ProductsTab:
    def __init__(self, master, notebook, start_window):
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('ProductsTab')
        self.create_tab()

    def create_tab(self):
        """Создание вкладки продуктов (обновленная версия с SQLite)"""
        try:
            self.tab = Frame(self.notebook, bg='white')
            self.notebook.add(self.tab, text="📦 ПРОДУКТЫ")

            self.create_header()
            self.create_controls()
            self.create_products_list()

            self.logger.debug("Вкладка 'Продукты' создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки продуктов: {e}")
            raise

    def create_header(self):
        """Создание заголовка вкладки"""
        header_frame = Frame(self.tab, bg='#27ae60', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        Label(header_frame, text="УПРАВЛЕНИЕ ПРОДУКТАМИ",
              font=('Arial', 16, 'bold'), bg='#27ae60', fg='white').pack(pady=20)

    def create_controls(self):
        """Создание панели управления"""
        control_frame = Frame(self.tab, bg='#f8f9fa')
        control_frame.pack(fill='x', padx=20, pady=20)

        Button(control_frame, text="🔄 ОБНОВИТЬ",
               command=self.load_products_data,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="➕ ДОБАВИТЬ ПРОДУКТ",
               command=self.add_product_dialog,
               bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📝 РЕДАКТИРОВАТЬ",
               command=self.edit_product_dialog,
               bg='#f39c12', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

    def create_products_list(self):
        """Создание списка продуктов"""
        list_frame = Frame(self.tab)
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # Заголовки колонок
        columns_frame = Frame(list_frame, bg='#ecf0f1')
        columns_frame.pack(fill='x')

        columns = ['Код', 'Наименование', 'Описание', 'Рецептур', 'Дата создания']
        column_widths = [100, 250, 200, 80, 120]

        for idx, col in enumerate(columns):
            Label(columns_frame, text=col, font=('Arial', 10, 'bold'),
                  bg='#ecf0f1', fg='#2c3e50', width=column_widths[idx] // 10).pack(side='left', padx=2)

        # Список с прокруткой
        list_container = Frame(list_frame)
        list_container.pack(fill='both', expand=True)

        scrollbar = Scrollbar(list_container)
        scrollbar.pack(side='right', fill='y')

        self.products_listbox = Listbox(list_container,
                                        yscrollcommand=scrollbar.set,
                                        font=('Arial', 10),
                                        selectmode='single',
                                        bg='white',
                                        height=15)
        self.products_listbox.pack(side='left', fill='both', expand=True)

        scrollbar.config(command=self.products_listbox.yview)

        # Загружаем данные продуктов
        self.load_products_data()

    @log_operation("Загрузка данных продуктов", LogLevel.INFO)
    def load_products_data(self):
        """Загрузка данных продуктов из базы данных"""
        try:
            products = db_manager.get_products()

            # Очищаем список
            self.products_listbox.delete(0, END)

            if not products:
                self.products_listbox.insert(END, "Нет продуктов в базе данных")
                return

            for product in products:
                product_name = (product.get('product_name') or '')[:30]
                description = (product.get('description') or '')[:25]
                created_date = (product.get('created_date') or '')[:10]
                display_text = f"{product['product_code']:<15} {product_name:<30} "
                display_text += f"{description:<25} {product.get('recipe_count', 0):<10} "
                display_text += f"{created_date:<12}"

                self.products_listbox.insert(END, display_text)

            self.logger.info(f"Загружено {len(products)} продуктов")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных продуктов: {e}")
            self.products_listbox.insert(END, f"Ошибка загрузки: {str(e)}")

    def add_product_dialog(self):
        """Диалоговое окно добавления нового продукта"""
        try:
            dialog = tk.Toplevel(self.master)
            dialog.title("Добавить продукт")
            dialog.geometry("500x350")

            Label(dialog, text="ДОБАВЛЕНИЕ НОВОГО ПРОДУКТА",
                  font=('Arial', 14, 'bold')).pack(pady=20)

            # Поля ввода
            form_frame = Frame(dialog, padx=20, pady=10)
            form_frame.pack(fill='both', expand=True)

            # Код продукта
            Label(form_frame, text="Код продукта*:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(5, 0))
            code_var = StringVar()
            Entry(form_frame, textvariable=code_var, font=('Arial', 10)).pack(fill='x', pady=(0, 10))

            # Наименование
            Label(form_frame, text="Наименование*:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(5, 0))
            name_var = StringVar()
            Entry(form_frame, textvariable=name_var, font=('Arial', 10)).pack(fill='x', pady=(0, 10))

            # Описание
            Label(form_frame, text="Описание:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(5, 0))
            desc_text = Text(form_frame, height=4, font=('Arial', 10))
            desc_text.pack(fill='x', pady=(0, 20))

            # Кнопки
            button_frame = Frame(dialog)
            button_frame.pack(pady=(0, 20))

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

            Button(button_frame, text="СОХРАНИТЬ",
                   command=save_product,
                   bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
                   padx=20, pady=8, cursor="hand2").pack(side='left', padx=10)

            Button(button_frame, text="ОТМЕНА",
                   command=dialog.destroy,
                   bg='#95a5a6', fg='white', font=('Arial', 10, 'bold'),
                   padx=20, pady=8, cursor="hand2").pack(side='right', padx=10)

        except Exception as e:
            self.logger.error(f"Ошибка добавления продукта: {e}")

    def edit_product_dialog(self):
        """Диалоговое окно редактирования продукта"""
        selection = self.products_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите продукт для редактирования")
            return

        messagebox.showinfo("Информация", "Функционал редактирования продуктов будет реализован в следующей версии")
        self.logger.debug("Вызов метода редактирования продукта (в разработке)")