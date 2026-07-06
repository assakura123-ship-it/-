import tkinter as tk
from tkinter import Frame, Label, Button
from modules.database import db_manager
from modules.logger import system_logger


class HomeTab:
    def __init__(self, master, notebook, start_window):
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('HomeTab')
        self.create_tab()

    def create_tab(self):
        """Создание главной вкладки"""
        try:
            self.tab = Frame(self.notebook, bg='#2c3e50')
            self.notebook.add(self.tab, text="🏠 ГЛАВНАЯ")

            # Контейнер для содержимого
            content_frame = Frame(self.tab, bg='#2c3e50', padx=40, pady=40)
            content_frame.pack(fill='both', expand=True)

            self.create_header(content_frame)
            self.create_quick_access(content_frame)
            self.create_stats(content_frame)
            self.create_info(content_frame)

            self.logger.debug("Главная вкладка создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания главной вкладки: {e}")
            raise

    def create_header(self, parent):
        """Создание заголовка"""
        header_frame = Frame(parent, bg='#2c3e50')
        header_frame.pack(fill='x', pady=(0, 40))

        Label(header_frame, text="📋", font=('Arial', 48),
              bg='#2c3e50', fg='white').pack()
        Label(header_frame, text="СИСТЕМА СОЗДАНИЯ КАРТ ЗАГРУЗОК (SQLite)",
              font=('Arial', 24, 'bold'), bg='#2c3e50', fg='white').pack(pady=(10, 5))
        Label(header_frame, text="Профессиональный инструмент для работы с рецептурами",
              font=('Arial', 12), bg='#2c3e50', fg='#bdc3c7').pack()

    def create_quick_access(self, parent):
        """Создание блока быстрого доступа"""
        quick_access_frame = Frame(parent, bg='#2c3e50')
        quick_access_frame.pack(fill='x', pady=(0, 40))

        Label(quick_access_frame, text="БЫСТРЫЙ ДОСТУП",
              font=('Arial', 14, 'bold'), bg='#2c3e50', fg='white').pack(anchor='w', pady=(0, 20))

        # Кнопки быстрого доступа в ряд
        button_row = Frame(quick_access_frame, bg='#2c3e50')
        button_row.pack(fill='x')

        # Кнопка создания карты загрузки
        create_btn = Button(button_row, text="📄 СОЗДАТЬ КАРТУ ЗАГРУЗКИ",
                            command=self.start_window.open_editor_tab,
                            bg='#3498db', fg='white',
                            font=('Arial', 12, 'bold'),
                            padx=20, pady=15,
                            cursor="hand2",
                            relief="flat",
                            bd=0)
        create_btn.pack(side='left', padx=5, fill='x', expand=True)
        create_btn.bind("<Enter>", lambda e: create_btn.config(bg='#2980b9'))
        create_btn.bind("<Leave>", lambda e: create_btn.config(bg='#3498db'))

        # Кнопка просмотра сохраненных карт
        view_btn = Button(button_row, text="📋 ПРОСМОТР КАРТ",
                          command=lambda: self.notebook.select(1),
                          bg='#9b59b6', fg='white',
                          font=('Arial', 12, 'bold'),
                          padx=20, pady=15,
                          cursor="hand2",
                          relief="flat",
                          bd=0)
        view_btn.pack(side='left', padx=5, fill='x', expand=True)
        view_btn.bind("<Enter>", lambda e: view_btn.config(bg='#8e44ad'))
        view_btn.bind("<Leave>", lambda e: view_btn.config(bg='#9b59b6'))

        # Кнопка склада
        warehouse_btn = Button(button_row, text="🏭 СКЛАД",
                               command=lambda: self.notebook.select(2),
                               bg='#e67e22', fg='white',
                               font=('Arial', 12, 'bold'),
                               padx=20, pady=15,
                               cursor="hand2",
                               relief="flat",
                               bd=0)
        warehouse_btn.pack(side='left', padx=5, fill='x', expand=True)
        warehouse_btn.bind("<Enter>", lambda e: warehouse_btn.config(bg='#d35400'))
        warehouse_btn.bind("<Leave>", lambda e: warehouse_btn.config(bg='#e67e22'))

        # Кнопка продуктов
        products_btn = Button(button_row, text="📦 ПРОДУКТЫ",
                              command=lambda: self.notebook.select(3),
                              bg='#27ae60', fg='white',
                              font=('Arial', 12, 'bold'),
                              padx=20, pady=15,
                              cursor="hand2",
                              relief="flat",
                              bd=0)
        products_btn.pack(side='left', padx=5, fill='x', expand=True)
        products_btn.bind("<Enter>", lambda e: products_btn.config(bg='#229954'))
        products_btn.bind("<Leave>", lambda e: products_btn.config(bg='#27ae60'))

        # Кнопка импорта/экспорта
        import_btn = Button(button_row, text="📤 ИМПОРТ/ЭКСПОРТ",
                            command=lambda: self.notebook.select(5),
                            bg='#1abc9c', fg='white',
                            font=('Arial', 12, 'bold'),
                            padx=20, pady=15,
                            cursor="hand2",
                            relief="flat",
                            bd=0)
        import_btn.pack(side='left', padx=5, fill='x', expand=True)
        import_btn.bind("<Enter>", lambda e: import_btn.config(bg='#16a085'))
        import_btn.bind("<Leave>", lambda e: import_btn.config(bg='#1abc9c'))

        # Кнопка логирования
        logs_btn = Button(button_row, text="📊 ЛОГИ",
                          command=lambda: self.notebook.select(4),
                          bg='#34495e', fg='white',
                          font=('Arial', 12, 'bold'),
                          padx=20, pady=15,
                          cursor="hand2",
                          relief="flat",
                          bd=0)
        logs_btn.pack(side='left', padx=5, fill='x', expand=True)
        logs_btn.bind("<Enter>", lambda e: logs_btn.config(bg='#2c3e50'))
        logs_btn.bind("<Leave>", lambda e: logs_btn.config(bg='#34495e'))

    def create_stats(self, parent):
        """Создание блока статистики"""
        stats_frame = Frame(parent, bg='#34495e', relief='solid', bd=1)
        stats_frame.pack(fill='x', pady=(0, 20))

        stats_inner = Frame(stats_frame, bg='#34495e', padx=20, pady=15)
        stats_inner.pack(fill='x')

        Label(stats_inner, text="📊 СТАТИСТИКА СИСТЕМЫ",
              font=('Arial', 14, 'bold'), bg='#34495e', fg='white').pack(anchor='w', pady=(0, 10))

        # Получаем статистику из базы данных
        try:
            products = db_manager.get_products()
            cards = db_manager.get_loading_cards()
            warehouse_items = db_manager.get_warehouse_items()

            # Статистика в ряд
            stats_row = Frame(stats_inner, bg='#34495e')
            stats_row.pack(fill='x')

            stats_data = [
                ("Продуктов в базе", str(len(products)), "#3498db"),
                ("Создано карт", str(len(cards)), "#9b59b6"),
                ("Позиций на складе", str(len(warehouse_items)), "#e67e22"),
                ("Рецептур", str(sum(p.get('recipe_count', 0) for p in products)), "#27ae60")
            ]

            for stat_text, stat_value, stat_color in stats_data:
                stat_frame = Frame(stats_row, bg='#2c3e50', relief='solid', bd=1)
                stat_frame.pack(side='left', padx=5, fill='both', expand=True)

                Label(stat_frame, text=stat_text,
                      font=('Arial', 9), bg='#2c3e50', fg='#bdc3c7').pack(pady=(10, 5))
                Label(stat_frame, text=stat_value,
                      font=('Arial', 18, 'bold'), bg='#2c3e50', fg=stat_color).pack(pady=(0, 10))

        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")

    def create_info(self, parent):
        """Создание блока информации"""
        info_frame = Frame(parent, bg='#ecf0f1', relief='solid', bd=1)
        info_frame.pack(fill='x')

        info_inner = Frame(info_frame, bg='#ecf0f1', padx=20, pady=15)
        info_inner.pack(fill='x')

        Label(info_inner, text="ℹ️ ИНФОРМАЦИЯ О СИСТЕМЕ",
              font=('Arial', 12, 'bold'), bg='#ecf0f1', fg='#2c3e50').pack(anchor='w', pady=(0, 10))

        info_text = f"""• Версия системы: 2.0 (SQLite)
• База данных: {db_manager.db_path}
• Дата сборки: Январь 2024
• Поддерживаемые форматы импорта: Excel (.xlsx, .xls)
• Поддерживаемые форматы экспорта: Excel (.xlsx)
• Максимальный размер файла: 50 МБ
• Автоматическое резервное копирование
• Поддержка Unicode
• Встроенная система логирования
• SQLite для надежного хранения данных"""

        Label(info_inner, text=info_text,
              font=('Arial', 10), bg='#ecf0f1', fg='#2c3e50', justify='left').pack(anchor='w')