import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Frame
from modules.logger import system_logger, log_operation, LogLevel
from modules.database import db_manager
from modules.loading_card_tab import LoadingCardTab
from modules.widgets.status_bar import StatusBar
from modules.tabs.home_tab import HomeTab
from modules.tabs.cards_tab import CardsTab
from modules.tabs.warehouse_tab import WarehouseTab
from modules.tabs.products_tab import ProductsTab
from modules.tabs.logs_tab import LogsTab
from modules.tabs.import_export_tab import ImportExportTab
import os
import pandas as pd
from datetime import datetime


class StartWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("📋 СИСТЕМА СОЗДАНИЯ КАРТ ЗАГРУЗОК (SQLite)")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f5f5f5')

        # Логгер для этого класса
        self.logger = system_logger.get_logger('StartWindow')
        self.logger.info("Инициализация стартового окна")

        # Словарь для хранения открытых редакторов {tab_id: editor_instance}
        self.open_editors = {}

        # Центрируем окно
        self.center_window()

        self.create_widgets()

        self.logger.info("Стартовое окно успешно инициализирован")

    def center_window(self):
        """Центрировать окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.logger.debug(f"Окно центрировано: {width}x{height} at ({x}, {y})")

    def create_widgets(self):
        """Создание виджетов стартового окна"""
        try:
            self.logger.info("Создание виджетов стартового окна")

            # Главный контейнер с вкладками
            self.notebook = ttk.Notebook(self.root)
            self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

            # Стилизация вкладок
            self.setup_notebook_style()

            # Создаем вкладки через отдельные классы
            self.tabs = {}
            self.tabs['home'] = HomeTab(self.root, self.notebook, self)
            self.tabs['cards'] = CardsTab(self.root, self.notebook, self)
            self.tabs['warehouse'] = WarehouseTab(self.root, self.notebook, self)
            self.tabs['products'] = ProductsTab(self.root, self.notebook, self)
            self.tabs['logs'] = LogsTab(self.root, self.notebook, self)
            self.tabs['import_export'] = ImportExportTab(self.root, self.notebook, self)

            # Обработчик закрытия вкладки
            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

            # Панель статуса
            self.status_bar = StatusBar(self.root)

            self.logger.info("Виджеты стартового окна успешно созданы")

        except Exception as e:
            self.logger.error(f"Ошибка создания виджетов: {e}")
            system_logger.log_error_with_traceback("Ошибка создания виджетов", e)
            raise

    def setup_notebook_style(self):
        """Настройка стиля вкладок"""
        style = ttk.Style()
        style.configure("TNotebook", background='#2c3e50')
        style.configure("TNotebook.Tab",
                        background='#95a5a6',
                        foreground='white',
                        padding=[20, 10])
        style.map("TNotebook.Tab",
                  background=[('selected', '#3498db')],
                  foreground=[('selected', 'white')])

    @log_operation("Открытие редактора", LogLevel.INFO)
    def open_editor_tab(self):
        """Открыть новую вкладку с редактором"""
        try:
            # Создаем уникальный ID для вкладки
            tab_id = f"editor_{len(self.open_editors) + 1}"

            # Создаем фрейм для вкладки
            tab_frame = Frame(self.notebook, bg='#f5f5f5')

            # Создаем редактор во вкладке
            editor = LoadingCardTab(tab_frame, self)
            editor.pack(fill='both', expand=True)

            # Добавляем вкладку
            tab_title = f"📝 РЕДАКТОР {len(self.open_editors) + 1}"
            self.notebook.add(tab_frame, text=tab_title)

            # Переключаемся на новую вкладку
            self.notebook.select(tab_frame)

            # Сохраняем редактор
            self.open_editors[tab_id] = editor

            self.status_bar.set_status(f"Открыт редактор {len(self.open_editors)}")
            self.logger.info(f"Открыта новая вкладка редактора: {tab_title}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть редактор:\n{str(e)}")
            self.logger.error(f"Ошибка открытия редактора: {e}")
            system_logger.log_error_with_traceback("Ошибка открытия редактора", e)

    @log_operation("Закрытие редактора", LogLevel.INFO)
    def close_editor_tab(self, tab_frame):
        """Закрыть вкладку редактора"""
        try:
            # Находим ID вкладки
            tab_id = None
            for tab_id_key, editor in list(self.open_editors.items()):
                if editor.master == tab_frame:
                    tab_id = tab_id_key
                    break

            if tab_id:
                # Проверяем, есть ли несохраненные изменения
                editor = self.open_editors[tab_id]
                if hasattr(editor, 'has_unsaved_changes') and editor.has_unsaved_changes:
                    if not messagebox.askyesno("Подтверждение",
                                               "Есть несохраненные изменения. Закрыть вкладку?"):
                        self.logger.info("Пользователь отменил закрытие вкладки с несохраненными изменениями")
                        return

                # Удаляем вкладку из notebook
                self.notebook.forget(tab_frame)

                # Удаляем из словаря
                del self.open_editors[tab_id]

                self.status_bar.set_status(f"Закрыт редактор. Осталось: {len(self.open_editors)}")
                self.logger.info(f"Закрыта вкладка редактора {tab_id}. Осталось вкладок: {len(self.open_editors)}")

        except Exception as e:
            self.logger.error(f"Ошибка закрытия вкладки редактора: {e}")
            system_logger.log_error_with_traceback("Ошибка закрытия вкладки редактора", e)

    def on_tab_changed(self, event):
        """Обработчик изменения вкладки"""
        try:
            # Получаем текущую вкладку
            current_tab = self.notebook.select()
            if current_tab:
                tab_index = self.notebook.index(current_tab)
                tab_text = self.notebook.tab(tab_index, "text")

                # Обновляем статус
                if tab_text.startswith("📝"):
                    self.status_bar.set_status(f"Активен: {tab_text}")
                elif tab_text == "🏠 ГЛАВНАЯ":
                    self.status_bar.set_status("Главная страница")
                elif tab_text == "📋 КАРТЫ ЗАГРРУЗОК":
                    self.status_bar.set_status("Просмотр сохраненных карт")
                elif tab_text == "📊 ЛОГИ":
                    self.status_bar.set_status("Просмотр системных логов")

                self.logger.debug(f"Переключена вкладка: {tab_text}")

        except Exception as e:
            self.logger.error(f"Ошибка обработки переключения вкладки: {e}")

    def export_card_to_excel(self, card_id: int):
        """Экспорт карты в Excel файл"""
        try:
            # Выбираем путь для сохранения
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
                # Экспортируем в Excel
                if db_manager.export_to_excel(card_id, filename):
                    messagebox.showinfo("Успех", f"Карта экспортирована в файл:\n{filename}")
                    self.logger.info(f"Карта ID:{card_id} экспортирована в {filename}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось экспортировать карту")
                    self.logger.error(f"Ошибка экспорта карты ID:{card_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать карту:\n{str(e)}")
            self.logger.error(f"Ошибка экспорта карты {card_id}: {e}")