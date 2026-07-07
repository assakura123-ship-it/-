import tkinter as tk
from tkinter import ttk, Frame, Label, Button, Listbox, Scrollbar, END, messagebox
from modules.database import db_manager
from modules.logger import system_logger, log_operation, LogLevel


class CardsTab:
    def __init__(self, master, notebook, start_window):
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('CardsTab')
        self.create_tab()

    def create_tab(self):
        """Создание вкладки с картами загрузок"""
        try:
            self.tab = Frame(self.notebook, bg='white')
            self.notebook.add(self.tab, text="📋 КАРТЫ ЗАГРУЗОК")

            self.create_header()
            self.create_controls()
            self.create_cards_list()

            self.logger.debug("Вкладка 'Карты загрузок' создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки карт загрузок: {e}")
            raise

    def create_header(self):
        """Создание заголовка вкладки"""
        header_frame = Frame(self.tab, bg='#3498db', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        Label(header_frame, text="СОХРАНЕННЫЕ КАРТЫ ЗАГРРУЗОК (из базы данных)",
              font=('Arial', 16, 'bold'), bg='#3498db', fg='white').pack(pady=20)

    def create_controls(self):
        """Создание панели управления"""
        control_frame = Frame(self.tab, bg='#f8f9fa')
        control_frame.pack(fill='x', padx=20, pady=20)

        # Кнопки управления
        Button(control_frame, text="🔄 ОБНОВИТЬ СПИСОК",
               command=self.load_saved_cards,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="🗑️ УДАЛИТЬ ВЫБРАННОЕ",
               command=self.delete_selected_card,
               bg='#e74c3c', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📤 ЭКСПОРТ В EXCEL",
               command=self.export_selected_card,
               bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="👁️ ПРОСМОТР",
               command=self.view_card_details,
               bg='#9b59b6', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

    def create_cards_list(self):
        """Создание списка карт"""
        list_frame = Frame(self.tab)
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # Заголовки колонок
        columns_frame = Frame(list_frame, bg='#ecf0f1')
        columns_frame.pack(fill='x')

        columns = ['ID', 'Название карты', 'Продукт', 'Рецептура', 'Реактор', 'Дата создания', 'Статус']
        column_widths = [50, 200, 150, 100, 80, 150, 100]

        for idx, col in enumerate(columns):
            Label(columns_frame, text=col, font=('Arial', 10, 'bold'),
                  bg='#ecf0f1', fg='#2c3e50', width=column_widths[idx] // 10).pack(side='left', padx=2)

        # Список с прокруткой
        list_container = Frame(list_frame)
        list_container.pack(fill='both', expand=True)

        scrollbar = Scrollbar(list_container)
        scrollbar.pack(side='right', fill='y')

        self.cards_listbox = Listbox(list_container,
                                     yscrollcommand=scrollbar.set,
                                     font=('Arial', 10),
                                     selectmode='single',
                                     bg='white',
                                     height=20)
        self.cards_listbox.pack(side='left', fill='both', expand=True)

        scrollbar.config(command=self.cards_listbox.yview)

        # Привязка двойного клика
        self.cards_listbox.bind('<Double-Button-1>', lambda e: self.view_card_details())

    @log_operation("Загрузка сохраненных карт", LogLevel.INFO)
    def load_saved_cards(self):
        """Загрузка списка сохраненных карт загрузок из базы данных"""
        try:
            # Получаем карты из базы данных
            cards = db_manager.get_loading_cards(limit=100)

            # Очищаем список
            self.cards_listbox.delete(0, END)

            if not cards:
                self.cards_listbox.insert(END, "Нет сохраненных карт загрузок")
                self.start_window.status_bar.set_status("Сохраненные карты не найдены")
                self.logger.info("Сохраненные карты не найдены")
                return

            for card in cards:
                try:
                    # Форматируем строку для списка
                    date_str = card['created_date'][:16] if card['created_date'] else "Неизвестно"

                    product_name = (card.get('product_name') or '')[:15]
                    recipe_number = (card.get('recipe_number') or '')[:10]
                    display_text = f"{card['id']:<5} {card['card_name']:<30} {product_name:<15} "
                    display_text += f"{recipe_number:<10} {card.get('reactor', 'Р-1'):<8} "
                    display_text += f"{date_str:<20} {card.get('status', 'draft'):<10}"

                    self.cards_listbox.insert(END, display_text)

                except Exception as e:
                    self.logger.warning(f"Ошибка обработки карты {card.get('id')}: {e}")

            self.start_window.status_bar.set_status(f"Загружено {len(cards)} карт загрузок")
            self.logger.info(f"Загружено {len(cards)} карт загрузок из БД")

        except Exception as e:
            self.cards_listbox.insert(END, f"Ошибка загрузки списка: {str(e)}")
            self.start_window.status_bar.set_status("Ошибка загрузки списка карт")
            self.logger.error(f"Ошибка загрузки списка карт: {e}")
            system_logger.log_error_with_traceback("Ошибка загрузки списка карт", e)

    @log_operation("Просмотр деталей карты", LogLevel.INFO)
    def view_card_details(self):
        """Просмотр деталей выбранной карты загрузки"""
        selection = self.cards_listbox.curselection()
        if not selection:
            self.logger.warning("Попытка просмотра карты без выбора")
            messagebox.showwarning("Внимание", "Выберите карту для просмотра")
            return

        selected_text = self.cards_listbox.get(selection[0])
        card_id = int(selected_text.split()[0])  # Извлекаем ID из первой колонки

        try:
            # Получаем детали карты
            card = db_manager.get_loading_card_details(card_id)
            components = db_manager.get_card_components(card_id)

            if not card:
                messagebox.showerror("Ошибка", "Карта не найдена")
                return

            # Создаем диалоговое окно
            details_window = tk.Toplevel(self.master)
            details_window.title(f"Детали карты загрузки: {card['card_name']}")
            details_window.geometry("900x600")

            # Заголовок
            header_frame = Frame(details_window, bg='#3498db', height=50)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)

            Label(header_frame, text=f"КАРТА ЗАГРУЗКИ: {card['card_name']}",
                  font=('Arial', 14, 'bold'), bg='#3498db', fg='white').pack(pady=15)

            # Основная информация
            info_frame = Frame(details_window, bg='white', padx=20, pady=20)
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

            for i, (label, value) in enumerate(info_data):
                row_frame = Frame(info_frame, bg='white')
                row_frame.pack(fill='x', pady=2)

                Label(row_frame, text=label, font=('Arial', 10, 'bold'),
                      bg='white', width=20, anchor='w').pack(side='left')
                Label(row_frame, text=value, font=('Arial', 10),
                      bg='white', anchor='w').pack(side='left')

            # Компоненты
            comp_frame = Frame(details_window, bg='white')
            comp_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

            Label(comp_frame, text="КОМПОНЕНТЫ:",
                  font=('Arial', 12, 'bold'), bg='white').pack(anchor='w', pady=(0, 10))

            # Создаем таблицу компонентов
            columns = ('№', 'Код компонента', 'Наименование', 'Процент, %', 'Масса, кг')
            tree = ttk.Treeview(comp_frame, columns=columns, show='headings', height=10)

            column_widths = [50, 120, 300, 100, 100]
            for idx, col in enumerate(columns):
                tree.heading(col, text=col)
                tree.column(col, width=column_widths[idx], anchor='center')

            # Заполняем таблицу
            for i, comp in enumerate(components, 1):
                tree.insert('', 'end', values=(
                    str(i),
                    comp['component_code'],
                    comp['component_name'],
                    f"{comp['percentage']:.4f}",
                    f"{comp['calculated_mass']:.3f}"
                ))

            # Добавляем итоговую строку
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

            # Полоса прокрутки
            scrollbar = Scrollbar(comp_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Кнопки
            button_frame = Frame(details_window, bg='white', pady=10)
            button_frame.pack(fill='x')

            Button(button_frame, text="📤 ЭКСПОРТ В EXCEL",
                   command=lambda: self.start_window.export_card_to_excel(card_id),
                   bg='#2ecc71', fg='white', font=('Arial', 10, 'bold'),
                   padx=15, pady=5, cursor="hand2").pack(side='left', padx=20)

            Button(button_frame, text="ЗАКРЫТЬ",
                   command=details_window.destroy,
                   bg='#95a5a6', fg='white', font=('Arial', 10, 'bold'),
                   padx=15, pady=5, cursor="hand2").pack(side='right', padx=20)

            self.logger.info(f"Открыты детали карты загрузки ID: {card_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить детали карты:\n{str(e)}")
            self.logger.error(f"Ошибка просмотра деталей карты {card_id}: {e}")

    @log_operation("Удаление карты загрузки", LogLevel.WARNING)
    def delete_selected_card(self):
        """Удалить выбранную карту загрузки из базы данных"""
        selection = self.cards_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите карту для удаления")
            self.logger.warning("Попытка удаления карты без выбора")
            return

        selected_text = self.cards_listbox.get(selection[0])
        card_id = int(selected_text.split()[0])

        if not messagebox.askyesno("Подтверждение",
                                   f"Удалить карту загрузки ID {card_id}?\n\n"
                                   "Это действие нельзя отменить!"):
            self.logger.info("Пользователь отменил удаление карты")
            return

        try:
            # Удаляем из базы данных
            db_manager.delete_loading_card(card_id)

            # Обновляем список
            self.load_saved_cards()

            self.start_window.status_bar.set_status(f"Удалена карта ID: {card_id}")
            messagebox.showinfo("Успех", "Карта загрузки удалена")
            self.logger.warning(f"Карта загрузки удалена ID: {card_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить карту:\n{str(e)}")
            self.logger.error(f"Ошибка удаления карты {card_id}: {e}")
            system_logger.log_error_with_traceback(f"Ошибка удаления карты {card_id}", e)

    @log_operation("Экспорт выбранной карты", LogLevel.INFO)
    def export_selected_card(self):
        """Экспорт выбранной карты в Excel"""
        selection = self.cards_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите карту для экспорта")
            self.logger.warning("Попытка экспорта карты без выбора")
            return

        selected_text = self.cards_listbox.get(selection[0])
        card_id = int(selected_text.split()[0])

        self.start_window.export_card_to_excel(card_id)