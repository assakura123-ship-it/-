import tkinter as tk
from tkinter import Frame, Label
from datetime import datetime
from modules.logger import system_logger


class StatusBar:
    def __init__(self, parent):
        self.parent = parent
        self.logger = system_logger.get_logger('StatusBar')
        self.create_widgets()

    def create_widgets(self):
        """Создание виджетов панели статуса"""
        self.status_frame = Frame(self.parent, bg='#34495e', height=30)
        self.status_frame.pack(fill='x', side='bottom')
        self.status_frame.pack_propagate(False)

        # Текущая дата и время
        self.date_label = Label(self.status_frame,
                                text="",
                                font=('Arial', 9),
                                bg='#34495e',
                                fg='white',
                                anchor='w')
        self.date_label.pack(side='left', padx=10)

        # Статус программы
        self.status_label = Label(self.status_frame,
                                  text="Система готова к работе",
                                  font=('Arial', 9),
                                  bg='#34495e',
                                  fg='white',
                                  anchor='e')
        self.status_label.pack(side='right', padx=10)

        # Обновляем дату
        self.update_date_time()

    def update_date_time(self):
        """Обновление даты и времени"""
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y %H:%M:%S")
        self.date_label.config(text=f"📅 {date_str}")
        # Обновляем каждую секунду
        self.parent.after(1000, self.update_date_time)

    def set_status(self, text):
        """Установить текст статуса"""
        self.status_label.config(text=text)