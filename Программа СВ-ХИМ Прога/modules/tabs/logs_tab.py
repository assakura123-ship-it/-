import tkinter as tk
from tkinter import ttk, Frame, Label, Button, Listbox, Scrollbar, Text, Entry, StringVar, END, messagebox
from modules.logger import system_logger, log_operation, LogLevel
import os


class LogsTab:
    def __init__(self, master, notebook, start_window):
        self.master = master
        self.notebook = notebook
        self.start_window = start_window
        self.logger = system_logger.get_logger('LogsTab')
        self.create_tab()

    def create_tab(self):
        """Создание вкладки для просмотра логов"""
        try:
            self.tab = Frame(self.notebook, bg='white')
            self.notebook.add(self.tab, text="📊 ЛОГИ")

            self.create_header()
            self.create_controls()
            self.create_logs_panel()
            self.create_stats()

            # Загружаем список файлов логов
            self.load_log_files()

            self.logger.debug("Вкладка 'Логи' создана успешно")

        except Exception as e:
            self.logger.error(f"Ошибка создания вкладки логов: {e}")
            raise

    def create_header(self):
        """Создание заголовка вкладки"""
        header_frame = Frame(self.tab, bg='#34495e', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        Label(header_frame, text="СИСТЕМА ЛОГИРОВАНИЯ",
              font=('Arial', 16, 'bold'), bg='#34495e', fg='white').pack(pady=20)

    def create_controls(self):
        """Создание панели управления"""
        control_frame = Frame(self.tab, bg='#f8f9fa')
        control_frame.pack(fill='x', padx=20, pady=20)

        # Кнопки управления логами
        Button(control_frame, text="🔄 ОБНОВИТЬ",
               command=self.load_logs,
               bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="🗑️ ОЧИСТИТЬ ЛОГИ",
               command=self.clear_logs,
               bg='#e74c3c', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='left', padx=5)

        Button(control_frame, text="📂 ОТКРЫТЬ ПАПКУ ЛОГОВ",
               command=self.open_logs_folder,
               bg='#95a5a6', fg='white', font=('Arial', 10, 'bold'),
               padx=15, pady=8, cursor="hand2").pack(side='right', padx=5)

        # Фильтры логов
        filter_frame = Frame(self.tab, bg='#ecf0f1', padx=10, pady=10)
        filter_frame.pack(fill='x', padx=20, pady=(0, 10))

        Label(filter_frame, text="Уровень логирования:",
              font=('Arial', 10), bg='#ecf0f1').pack(side='left', padx=(0, 10))

        self.log_level_var = StringVar(value="ALL")
        log_level_combo = ttk.Combobox(filter_frame,
                                       textvariable=self.log_level_var,
                                       values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                       state='readonly',
                                       width=15)
        log_level_combo.pack(side='left', padx=(0, 20))
        log_level_combo.bind('<<ComboboxSelected>>', lambda e: self.load_logs())

        Label(filter_frame, text="Поиск:",
              font=('Arial', 10), bg='#ecf0f1').pack(side='left', padx=(0, 10))

        self.log_search_var = StringVar()
        search_entry = Entry(filter_frame,
                             textvariable=self.log_search_var,
                             font=('Arial', 10),
                             width=30)
        search_entry.pack(side='left', padx=(0, 10))
        search_entry.bind('<KeyRelease>', lambda e: self.load_logs())

    def create_logs_panel(self):
        """Создание панели просмотра логов"""
        files_frame = Frame(self.tab)
        files_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        # Левая панель - список файлов логов
        files_list_frame = Frame(files_frame, bg='white', relief='solid', bd=1)
        files_list_frame.pack(side='left', fill='y', padx=(0, 10))

        Label(files_list_frame, text="ФАЙЛЫ ЛОГОВ",
              font=('Arial', 11, 'bold'), bg='#95a5a6', fg='white').pack(fill='x', pady=10)

        files_list_container = Frame(files_list_frame)
        files_list_container.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar_files = Scrollbar(files_list_container)
        scrollbar_files.pack(side='right', fill='y')

        self.log_files_listbox = Listbox(files_list_container,
                                         yscrollcommand=scrollbar_files.set,
                                         font=('Arial', 10),
                                         bg='white',
                                         height=15,
                                         width=25)
        self.log_files_listbox.pack(side='left', fill='both', expand=True)

        scrollbar_files.config(command=self.log_files_listbox.yview)
        self.log_files_listbox.bind('<<ListboxSelect>>', self.on_log_file_selected)

        # Правая панель - содержимое логов
        content_frame = Frame(files_frame, bg='white', relief='solid', bd=1)
        content_frame.pack(side='right', fill='both', expand=True)

        Label(content_frame, text="СОДЕРЖИМОЕ ЛОГА",
              font=('Arial', 11, 'bold'), bg='#95a5a6', fg='white').pack(fill='x', pady=10)

        # Текстовое поле для отображения логов
        text_container = Frame(content_frame)
        text_container.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar_text = Scrollbar(text_container)
        scrollbar_text.pack(side='right', fill='y')

        self.log_text = Text(text_container,
                             yscrollcommand=scrollbar_text.set,
                             font=('Consolas', 10),
                             bg='#2c3e50',
                             fg='#ecf0f1',
                             wrap='word',
                             height=20)
        self.log_text.pack(side='left', fill='both', expand=True)

        scrollbar_text.config(command=self.log_text.yview)

        # Добавляем теги для цветов в зависимости от уровня логирования
        self.log_text.tag_config('DEBUG', foreground='#95a5a6')
        self.log_text.tag_config('INFO', foreground='#27ae60')
        self.log_text.tag_config('WARNING', foreground='#f39c12')
        self.log_text.tag_config('ERROR', foreground='#e74c3c')
        self.log_text.tag_config('CRITICAL', foreground='#c0392b', background='#2c3e50')

    def create_stats(self):
        """Создание статистики логов"""
        stats_frame = Frame(self.tab, bg='#ecf0f1', height=40)
        stats_frame.pack(fill='x', padx=20, pady=(0, 20))
        stats_frame.pack_propagate(False)

        self.log_stats_label = Label(stats_frame,
                                     text="Всего файлов: 0 | Всего записей: 0",
                                     font=('Arial', 9),
                                     bg='#ecf0f1',
                                     fg='#2c3e50')
        self.log_stats_label.pack(pady=10)

    @log_operation("Загрузка списка файлов логов", LogLevel.INFO)
    def load_log_files(self):
        """Загрузка списка файлов логов"""
        try:
            # Получаем список файлов логов
            log_files = system_logger.get_log_files()

            # Очищаем список
            self.log_files_listbox.delete(0, END)

            if not log_files:
                self.log_files_listbox.insert(END, "Файлы логов не найдены")
                self.log_stats_label.config(text="Файлы логов не найдены")
                return

            # Добавляем файлы в список
            for log_file in log_files:
                size_mb = log_file['size'] / (1024 * 1024)
                if size_mb < 1:
                    size_str = f"{log_file['size'] / 1024:.1f} КБ"
                else:
                    size_str = f"{size_mb:.1f} МБ"

                display_text = f"{log_file['name']} ({size_str})"
                self.log_files_listbox.insert(END, display_text)

            # Обновляем статистику
            self.log_stats_label.config(text=f"Всего файлов: {len(log_files)}")

            # Выбираем первый файл
            if log_files:
                self.log_files_listbox.selection_set(0)
                self.on_log_file_selected()

            self.logger.debug(f"Загружено {len(log_files)} файлов логов")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки списка файлов логов: {e}")
            self.log_files_listbox.insert(END, f"Ошибка загрузки: {str(e)}")

    @log_operation("Загрузка содержимого лога", LogLevel.INFO)
    def load_logs(self):
        """Загрузка и фильтрация содержимого логов"""
        try:
            selection = self.log_files_listbox.curselection()
            if not selection:
                return

            # Получаем выбранный файл
            selected_text = self.log_files_listbox.get(selection[0])
            file_name = selected_text.split(' (')[0]

            # Ищем полный путь к файлу
            log_files = system_logger.get_log_files()
            selected_file = None
            for log_file in log_files:
                if log_file['name'] == file_name:
                    selected_file = log_file
                    break

            if not selected_file:
                self.log_text.delete(1.0, END)
                self.log_text.insert(END, "Файл не найден")
                return

            # Читаем содержимое файла
            with open(selected_file['path'], 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Очищаем текстовое поле
            self.log_text.delete(1.0, END)

            # Применяем фильтры
            log_level = self.log_level_var.get()
            search_text = self.log_search_var.get().lower()

            filtered_count = 0
            total_count = 0

            for line in lines:
                total_count += 1

                # Проверяем уровень логирования
                if log_level != "ALL":
                    if not any(level in line for level in [' - ' + log_level + ' - ', ' ' + log_level + ' ']):
                        continue

                # Проверяем поисковый запрос
                if search_text and search_text not in line.lower():
                    continue

                # Добавляем строку с соответствующим тегом
                if ' - DEBUG - ' in line:
                    self.log_text.insert(END, line, 'DEBUG')
                elif ' - INFO - ' in line:
                    self.log_text.insert(END, line, 'INFO')
                elif ' - WARNING - ' in line:
                    self.log_text.insert(END, line, 'WARNING')
                elif ' - ERROR - ' in line:
                    self.log_text.insert(END, line, 'ERROR')
                elif ' - CRITICAL - ' in line:
                    self.log_text.insert(END, line, 'CRITICAL')
                else:
                    self.log_text.insert(END, line)

                filtered_count += 1

            # Обновляем статистику
            self.log_stats_label.config(
                text=f"Файл: {file_name} | Всего строк: {total_count} | Отфильтровано: {filtered_count}"
            )

            # Прокручиваем вниз
            self.log_text.see(END)

            self.logger.debug(f"Загружено {filtered_count}/{total_count} строк из лога {file_name}")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки логов: {e}")
            self.log_text.delete(1.0, END)
            self.log_text.insert(END, f"Ошибка загрузки файла: {str(e)}")

    def on_log_file_selected(self, event=None):
        """Обработчик выбора файла лога"""
        self.load_logs()

    @log_operation("Очистка логов", LogLevel.WARNING)
    def clear_logs(self):
        """Очистка файлов логов"""
        if not messagebox.askyesno("Подтверждение",
                                   "Очистить все файлы логов?\n\n"
                                   "Это действие необратимо!"):
            self.logger.info("Пользователь отменил очистку логов")
            return

        try:
            # Удаляем файлы логов
            deleted_count = 0
            for log_file in system_logger.log_dir.glob("*.log*"):
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Ошибка удаления файла {log_file}: {e}")

            # Обновляем список файлов
            self.load_log_files()

            # Очищаем текстовое поле
            self.log_text.delete(1.0, END)

            messagebox.showinfo("Успех", f"Удалено {deleted_count} файлов логов")
            self.logger.warning(f"Очищено {deleted_count} файлов логов")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить логи:\n{str(e)}")
            self.logger.error(f"Ошибка очистки логов: {e}")

    @log_operation("Открытие папки логов", LogLevel.INFO)
    def open_logs_folder(self):
        """Открыть папку с логами"""
        try:
            import os
            os.startfile(system_logger.log_dir)
            self.logger.info("Открыта папка с логами")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{str(e)}")
            self.logger.error(f"Ошибка открытия папки логов: {e}")