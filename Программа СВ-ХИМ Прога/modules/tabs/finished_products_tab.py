import tkinter as tk
from tkinter import Frame, Label, Button, Entry, StringVar, messagebox, filedialog, END, Toplevel
from tkinter import ttk
import os
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd

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

        Button(control_frame, text="📉 ДЕФИЦИТ ПО ГОТОВОЙ ПРОДУКЦИИ",
               command=self.calculate_deficit,
               bg='#e74c3c', fg='white', font=('Arial', 10, 'bold'),
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

    @log_operation("Расчет дефицита готовой продукции", LogLevel.INFO)
    def calculate_deficit(self):
        """Расчет дефицита по готовой продукции из Excel-файла.

        Структура файла: КОД ГП, Наименование ГП, Бренд, Нач. остаток, Расход, Кон. Остаток.
        Дефицитом считаются только отрицательные значения в колонке 'Кон. Остаток'.
        """
        filetypes = [
            ("Файлы Excel", "*.xlsx *.xls"),
            ("Все файлы", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Выберите файл Excel 'Дефицит по готовой продукции'",
            initialdir=".",
            filetypes=filetypes
        )

        if not filename:
            return

        try:
            df = pd.read_excel(filename)
            if df.empty:
                raise ValueError("Файл Excel пуст")

            # Нормализация заголовков
            rename_map = {}
            for col in df.columns:
                clean = col.strip().lower()
                if 'код гп' in clean or 'код готовой продукции' in clean or 'артикул' in clean:
                    rename_map[col] = 'product_code'
                elif 'наименование гп' in clean or ('наименование' in clean and 'бренд' not in clean):
                    rename_map[col] = 'product_name'
                elif 'бренд' in clean:
                    rename_map[col] = 'brand'
                elif 'нач' in clean and 'остаток' in clean:
                    rename_map[col] = 'start_stock'
                elif 'расход' in clean:
                    rename_map[col] = 'consumption'
                elif 'кон' in clean and 'остаток' in clean:
                    rename_map[col] = 'ending_stock'

            df.rename(columns=rename_map, inplace=True)

            required = ['product_code', 'product_name', 'ending_stock']
            for col in required:
                if col not in df.columns:
                    raise ValueError(f"В файле не найден обязательный столбец: {col}")

            # Отбираем только строки с отрицательным конечным остатком
            deficits = []
            for _, row in df.iterrows():
                ending = row['ending_stock']
                if pd.isna(ending):
                    continue
                try:
                    ending_val = float(ending)
                except (ValueError, TypeError):
                    continue
                if ending_val >= 0:
                    continue

                product_code = str(row['product_code']).strip() if not pd.isna(row['product_code']) else ''
                product_name = str(row['product_name']).strip() if not pd.isna(row['product_name']) else ''
                brand = str(row['brand']).strip() if 'brand' in df.columns and not pd.isna(row['brand']) else ''
                start_stock = float(row['start_stock']) if 'start_stock' in df.columns and not pd.isna(row['start_stock']) else 0.0
                consumption = float(row['consumption']) if 'consumption' in df.columns and not pd.isna(row['consumption']) else 0.0

                deficits.append({
                    'product_code': product_code,
                    'product_name': product_name,
                    'brand': brand,
                    'start_stock': start_stock,
                    'consumption': consumption,
                    'ending_stock': ending_val,
                    'deficit': abs(ending_val)
                })

            self.show_deficit_window(deficits, filename)
            self.logger.info(f"Расчет дефицита по готовой продукции из {filename}: {len(deficits)} позиций")
        except Exception as e:
            self.logger.error(f"Ошибка расчета дефицита по готовой продукции: {e}")
            messagebox.showerror("Ошибка", f"Ошибка расчета дефицита:\n{str(e)}")

    def show_deficit_window(self, deficits: List[Dict[str, Any]], source_file: str):
        """Отображение окна с результатами расчета дефицита."""
        window = Toplevel(self.master)
        window.title("Дефицит по готовой продукции")
        window.geometry("900x600")
        window.transient(self.master)
        window.grab_set()

        header = Frame(window, bg='#e74c3c', height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        Label(header, text="ДЕФИЦИТ ПО ГОТОВОЙ ПРОДУКЦИИ",
              font=('Arial', 14, 'bold'), bg='#e74c3c', fg='white').pack(pady=12)

        control_frame = Frame(window, bg='white')
        control_frame.pack(fill='x', padx=10, pady=10)

        Button(control_frame, text="📤 Экспорт дефицита в Excel",
               command=lambda: self.export_deficit_to_excel(deficits),
               bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
               padx=10, pady=5, cursor="hand2").pack(side='left', padx=5)

        Label(control_frame,
              text=f"Источник: {os.path.basename(source_file)}  |  Позиций с дефицитом: {len(deficits)}",
              font=('Arial', 10), bg='white', fg='#2c3e50').pack(side='left', padx=20)

        # Дерево результатов
        tree_frame = Frame(window, bg='white')
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        columns = ('product_code', 'product_name', 'brand', 'start_stock', 'consumption', 'ending_stock', 'deficit')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20)

        tree.heading('product_code', text='КОД ГП')
        tree.heading('product_name', text='Наименование ГП')
        tree.heading('brand', text='Бренд')
        tree.heading('start_stock', text='Нач. остаток')
        tree.heading('consumption', text='Расход')
        tree.heading('ending_stock', text='Кон. Остаток')
        tree.heading('deficit', text='Дефицит')

        tree.column('product_code', width=100, anchor='center')
        tree.column('product_name', width=250, anchor='w')
        tree.column('brand', width=120, anchor='w')
        tree.column('start_stock', width=100, anchor='center')
        tree.column('consumption', width=100, anchor='center')
        tree.column('ending_stock', width=100, anchor='center')
        tree.column('deficit', width=100, anchor='center')

        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        for item in deficits:
            tree.insert('', 'end', values=(
                item['product_code'],
                item['product_name'],
                item['brand'],
                f"{item['start_stock']:.2f}",
                f"{item['consumption']:.2f}",
                f"{item['ending_stock']:.2f}",
                f"{item['deficit']:.2f}"
            ))

        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        if not deficits:
            Label(window, text="Дефицит по готовой продукции не выявлен (отрицательных конечных остатков нет).",
                  font=('Arial', 11), bg='white', fg='#2c3e50').pack(pady=20)

    def export_deficit_to_excel(self, deficits: List[Dict[str, Any]]):
        """Экспорт рассчитанного дефицита в Excel."""
        default_name = f"дефицит_готовой_продукции_{datetime.now().strftime('%Y%m%d')}.xlsx"
        filetypes = [
            ("Файлы Excel", "*.xlsx"),
            ("Все файлы", "*.*")
        ]

        filename = filedialog.asksaveasfilename(
            title="Выберите путь для экспорта дефицита",
            initialdir=".",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=filetypes
        )

        if not filename:
            return

        try:
            rows = []
            for item in deficits:
                rows.append({
                    'КОД ГП': item['product_code'],
                    'Наименование ГП': item['product_name'],
                    'Бренд': item['brand'],
                    'Нач. остаток': item['start_stock'],
                    'Расход': item['consumption'],
                    'Кон. Остаток': item['ending_stock'],
                    'Дефицит': item['deficit']
                })

            df = pd.DataFrame(rows)
            df.to_excel(filename, index=False, engine='openpyxl')
            messagebox.showinfo("Успех", f"Дефицит успешно экспортирован в:\n{filename}")
            self.logger.info(f"Экспорт дефицита готовой продукции в {filename}")
        except Exception as e:
            self.logger.error(f"Ошибка экспорта дефицита: {e}")
            messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{str(e)}")
