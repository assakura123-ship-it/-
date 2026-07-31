import tkinter as tk
from tkinter import Frame, Label, Button, Entry, StringVar, messagebox, filedialog, END
from tkinter import ttk
import os
from datetime import datetime
from modules.database import db_manager
from modules.logger import system_logger, log_operation, LogLevel


class FinishedProductsTab:
    """Вкладка «Готовая продукция» со спецификациями (тара, упаковка и т.д.)."""

    def __init__(self, master, notebook, start_window):
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('FinishedProductsTab')
        self.create_tab()

    def create_tab(self):
        """Создание вкладки готовой продукции."""
        try:
            self.tab = Frame(self.notebook, bg='white')
            self.notebook.add(self.tab, text="🏭 ГОТОВАЯ ПРОДУКЦИЯ")

            self.create_header()
            self.create_controls()
            self.create_main_content()
            self.create_status_bar()

            # Загружаем данные при открытии вкладки
            self.load_data()

            self.logger.debug("Вкладка 'Готовая продукция' создана успешно")
        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки готовой продукции: {e}")
            raise

    def create_header(self):
        """Заголовок вкладки."""
        header_frame = Frame(self.tab, bg='#2980b9', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        Label(header_frame, text="ГОТОВАЯ ПРОДУКЦИЯ И СПЕЦИФИКАЦИИ",
              font=('Arial', 16, 'bold'), bg='#2980b9', fg='white').pack(pady=20)

    def create_controls(self):
        """Панель управления."""
        control_frame = Frame(self.tab, bg='#f8f9fa')
        control_frame.pack(fill='x', padx=20, pady=20)

        Button(control_frame, text="🔄 ОБНОВИТЬ",
               command=self.load_data,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📥 ИМПОРТ ИЗ EXCEL",
               command=self.import_from_excel,
               bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📤 ЭКСПОРТ В EXCEL",
               command=self.export_to_excel,
               bg='#f39c12', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        self.import_file_var = StringVar()
        Entry(control_frame, textvariable=self.import_file_var,
              font=('Arial', 10), state='readonly', bg='white', width=40).pack(side='left', padx=10)

    def create_main_content(self):
        """Основная область: дерево готовой продукции и спецификаций."""
        content_frame = Frame(self.tab, bg='white')
        content_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # Дерево
        tree_frame = Frame(content_frame, bg='white')
        tree_frame.pack(side='left', fill='both', expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=('value', 'unit'), show='tree headings', height=20)
        self.tree.heading('#0', text='Готовая продукция / Спецификация')
        self.tree.heading('value', text='Количество')
        self.tree.heading('unit', text='Ед. изм.')
        self.tree.column('#0', width=500, minwidth=250)
        self.tree.column('value', width=120, anchor='center')
        self.tree.column('unit', width=100, anchor='center')

        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Правая панель деталей
        details_frame = Frame(content_frame, bg='#f8f9fa', relief='solid', bd=1, width=350)
        details_frame.pack(side='right', fill='y', padx=(20, 0))
        details_frame.pack_propagate(False)

        Label(details_frame, text="ДЕТАЛИ ПОЗИЦИИ",
              font=('Arial', 12, 'bold'), bg='#f8f9fa', fg='#2c3e50').pack(pady=15)

        self.details_text = tk.Text(details_frame, wrap='word', font=('Arial', 10),
                                    bg='white', height=20, padx=10, pady=10)
        self.details_text.pack(fill='both', expand=True, padx=10, pady=10)
        self.details_text.config(state='disabled')

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

    def create_status_bar(self):
        """Строка статуса."""
        self.status_frame = Frame(self.tab, bg='#ecf0f1', height=40)
        self.status_frame.pack(fill='x', padx=20, pady=(0, 20))
        self.status_frame.pack_propagate(False)

        self.status_label = Label(self.status_frame,
                                  text="Готовая продукция: 0 | Спецификаций: 0",
                                  font=('Arial', 9), bg='#ecf0f1', fg='#2c3e50')
        self.status_label.pack(pady=10)

    @log_operation("Загрузка готовой продукции", LogLevel.INFO)
    def load_data(self):
        """Загрузка готовой продукции и спецификаций из БД."""
        try:
            # Очистка дерева
            for item in self.tree.get_children():
                self.tree.delete(item)

            products = db_manager.get_finished_products()
            total_specs = 0

            if not products:
                self.tree.insert('', 'end', text='Нет готовой продукции в базе данных', open=True)
                self.status_label.config(text="Готовая продукция: 0 | Спецификаций: 0")
                self.show_details("Готовая продукция не найдена.\n\n"
                                  "Используйте кнопку «Импорт из Excel» для загрузки спецификаций.")
                return

            for product in products:
                product_code = product['product_code']
                product_name = product.get('product_name', '')
                spec_count = product.get('spec_count', 0)
                total_specs += spec_count

                parent = self.tree.insert('', 'end',
                                          text=f"{product_code} | {product_name}",
                                          values=('', '', f'{spec_count} поз.'),
                                          open=False)

                specs = db_manager.get_finished_product_specifications(product_code)
                for spec in specs:
                    self.tree.insert(parent, 'end',
                                     text=f"  {spec['component_code']} | {spec['component_name']}",
                                     values=(spec['quantity'], spec.get('unit', 'шт')),
                                     tags=('spec',))

            self.status_label.config(text=f"Готовая продукция: {len(products)} | Спецификаций: {total_specs}")
            self.logger.info(f"Загружена готовая продукция: {len(products)} позиций, {total_specs} спецификаций")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки готовой продукции: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные:\n{str(e)}")

    def on_tree_select(self, event=None):
        """Обработчик выбора элемента в дереве."""
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        item = self.tree.item(item_id)
        text = item['text'].strip()

        # Если выбрана спецификация (не корневой элемент)
        if self.tree.parent(item_id):
            parent_id = self.tree.parent(item_id)
            parent_text = self.tree.item(parent_id, 'text')
            details = (f"Готовая продукция:\n{parent_text}\n\n"
                       f"Спецификация:\n{text}\n\n"
                       f"Количество: {item['values'][0]} {item['values'][1]}")
        else:
            details = (f"Готовая продукция:\n{text}\n\n"
                       f"Количество спецификаций: {item['values'][2] if len(item['values']) > 2 else ''}")

        self.show_details(details)

    def show_details(self, text: str):
        """Отображение текста в панели деталей."""
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)
        self.details_text.insert('1.0', text)
        self.details_text.config(state='disabled')

    def import_from_excel(self):
        """Импорт спецификаций готовой продукции из Excel."""
        filetypes = [
            ("Файлы Excel", "*.xlsx *.xls"),
            ("Все файлы", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Выберите файл Excel со спецификациями готовой продукции",
            initialdir=".",
            filetypes=filetypes
        )

        if not filename:
            return

        self.import_file_var.set(filename)

        try:
            db_manager.import_finished_product_specifications_from_excel(filename, replace_existing=True)
            self.load_data()
            messagebox.showinfo("Успех",
                                f"Спецификации готовой продукции успешно импортированы из:\n{filename}")
            self.logger.info(f"Импорт спецификаций готовой продукции из {filename}")
        except Exception as e:
            self.logger.error(f"Ошибка импорта спецификаций готовой продукции: {e}")
            messagebox.showerror("Ошибка", f"Ошибка импорта:\n{str(e)}")

    def export_to_excel(self):
        """Экспорт спецификаций готовой продукции в Excel."""
        default_name = f"готовая_продукция_спецификации_{datetime.now().strftime('%Y%m%d')}.xlsx"
        filetypes = [
            ("Файлы Excel", "*.xlsx"),
            ("Все файлы", "*.*")
        ]

        filename = filedialog.asksaveasfilename(
            title="Выберите путь для экспорта спецификаций готовой продукции",
            initialdir=".",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=filetypes
        )

        if not filename:
            return

        try:
            db_manager.export_finished_product_specifications_to_excel(filename)
            messagebox.showinfo("Успех",
                                f"Спецификации готовой продукции успешно экспортированы в:\n{filename}")
            self.logger.info(f"Экспорт спецификаций готовой продукции в {filename}")
        except Exception as e:
            self.logger.error(f"Ошибка экспорта спецификаций готовой продукции: {e}")
            messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{str(e)}")
