import tkinter as tk
from modules.logger import system_logger
from modules.database import db_manager
from modules.modern_start_window import ModernStartWindow  # Измененный импорт
import sys
import os

def main():
    """Запуск программы"""
    try:
        # Логгер уже инициализирован при импорте
        logger = system_logger.get_logger('Main')
        logger.info("=" * 60)
        logger.info("ЗАПУСК ПРОГРАММЫ 'СИСТЕМА СОЗДАНИЯ КАРТ ЗАГРУЗОК' (SQLite версия)")
        logger.info("=" * 60)

        # Создаем стартовое окно
        root = tk.Tk()
        app = ModernStartWindow(root)  # Используем ModernStartWindow вместо StartWindow

        # Обработчик закрытия окна
        def on_closing():
            logger.info("Закрытие приложения")
            system_logger.log_operation("application_shutdown",
                                        "Завершение работы приложения",
                                        user="system")

            # Закрываем соединение с базой данных
            db_manager.close()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()

        logger.info("=" * 60)
        logger.info("ПРОГРАММА ЗАВЕРШИЛА РАБОТУ")
        logger.info("=" * 60)

    except ImportError as e:
        error_msg = "ОШИБКА: Не установлены необходимые библиотеки!"
        print(error_msg)
        print(f"Детали: {e}")
        print("Установите их с помощью команд:")
        print("pip install pandas")
        print("pip install openpyxl")

        # Логируем ошибку даже без инициализированной системы логирования
        try:
            import logging
            logging.basicConfig(level=logging.ERROR)
            logging.error(error_msg)
            logging.error(f"ImportError: {e}")
        except:
            pass

        input("Нажмите Enter для выхода...")
    except Exception as e:
        error_msg = f"Критическая ошибка при запуске программы: {e}"
        print(error_msg)

        # Пытаемся записать в лог
        try:
            import logging
            logging.basicConfig(level=logging.ERROR)
            logging.critical(error_msg, exc_info=True)
        except:
            pass

        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()