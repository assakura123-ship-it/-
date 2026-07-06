import logging
import sys
import os
import traceback
import json
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# ===================== НАСТРОЙКА ЛОГИРОВАНИЯ =====================
class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SystemLogger:
    """Класс для управления системой логирования"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.log_dir = Path("logs")
            self.config_file = Path("logging_config.json")
            self.loggers = {}
            self.default_config = {
                "log_level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5,
                "enable_console": True,
                "enable_file": True,
                "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S"
            }
            self._setup_logging()
            self._initialized = True

    def _setup_logging(self):
        """Настройка системы логирования"""
        try:
            # Создаем директорию для логов
            self.log_dir.mkdir(exist_ok=True)

            # Загружаем конфигурацию
            config = self._load_config()

            # Настраиваем корневой логгер
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, config["log_level"]))

            # Форматтер
            formatter = logging.Formatter(
                config["log_format"],
                datefmt=config["date_format"]
            )

            # Очищаем существующие обработчики
            root_logger.handlers.clear()

            # Файловый обработчик с ротацией по размеру
            if config["enable_file"]:
                file_handler = RotatingFileHandler(
                    self.log_dir / "system.log",
                    maxBytes=config["max_file_size_mb"] * 1024 * 1024,
                    backupCount=config["backup_count"],
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(getattr(logging, config["log_level"]))
                root_logger.addHandler(file_handler)

            # Обработчик для консоли
            if config["enable_console"]:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                console_handler.setLevel(getattr(logging, config["log_level"]))
                root_logger.addHandler(console_handler)

            # Логгер ошибок
            error_handler = RotatingFileHandler(
                self.log_dir / "errors.log",
                maxBytes=config["max_file_size_mb"] * 1024 * 1024,
                backupCount=config["backup_count"],
                encoding='utf-8'
            )
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            root_logger.addHandler(error_handler)

            # Логгер операций пользователя
            operations_handler = TimedRotatingFileHandler(
                self.log_dir / "operations.log",
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            operations_handler.setFormatter(formatter)
            operations_handler.setLevel(logging.INFO)
            operations_handler.addFilter(self._operations_filter)
            root_logger.addHandler(operations_handler)

            self._log_system_start()

        except Exception as e:
            print(f"Ошибка настройки логирования: {e}")
            self._setup_fallback_logging()

    def _setup_fallback_logging(self):
        """Резервная настройка логирования при ошибках"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("system_fallback.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def _load_config(self):
        """Загрузка конфигурации логирования"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Объединяем с дефолтной конфигурацией
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"Ошибка загрузки конфигурации логирования: {e}")

        # Сохраняем дефолтную конфигурацию
        self._save_config(self.default_config)
        return self.default_config

    def _save_config(self, config):
        """Сохранение конфигурации логирования"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")

    def _operations_filter(self, record):
        """Фильтр для логов операций"""
        return hasattr(record, 'operation_type') or 'operation' in record.getMessage().lower()

    def _log_system_start(self):
        """Логирование запуска системы"""
        logger = logging.getLogger('System')
        logger.info("=" * 60)
        logger.info("СИСТЕМА СОЗДАНИЯ КАРТ ЗАГРУЗОК - ЗАПУСК (SQLite версия)")
        logger.info(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Версия Python: {sys.version}")
        logger.info(f"Платформа: {sys.platform}")
        logger.info(f"Рабочая директория: {os.getcwd()}")
        logger.info("=" * 60)

    def get_logger(self, name):
        """Получение логгера с указанным именем"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]

    def log_operation(self, operation_type, details, user="system", level=LogLevel.INFO):
        """Логирование операции пользователя"""
        logger = logging.getLogger('Operations')
        log_msg = f"[{operation_type}] [{user}] {details}"

        if level == LogLevel.DEBUG:
            logger.debug(log_msg)
        elif level == LogLevel.INFO:
            logger.info(log_msg)
        elif level == LogLevel.WARNING:
            logger.warning(log_msg)
        elif level == LogLevel.ERROR:
            logger.error(log_msg)
        elif level == LogLevel.CRITICAL:
            logger.critical(log_msg)

    def log_error_with_traceback(self, error_msg, exception=None):
        """Логирование ошибки с трассировкой стека"""
        logger = logging.getLogger('Errors')
        logger.error(f"ОШИБКА: {error_msg}")

        if exception:
            logger.error(f"Тип исключения: {type(exception).__name__}")
            logger.error(f"Сообщение исключения: {str(exception)}")
            logger.error("Трассировка стека:")
            for line in traceback.format_exception(type(exception), exception, exception.__traceback__):
                for subline in line.strip().split('\n'):
                    if subline:
                        logger.error(f"  {subline}")

    def log_performance(self, operation_name, start_time, end_time=None):
        """Логирование производительности операции"""
        if end_time is None:
            end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()
        logger = logging.getLogger('Performance')

        if duration > 1.0:
            level = logging.WARNING
        elif duration > 5.0:
            level = logging.ERROR
        else:
            level = logging.INFO

        logger.log(level, f"Операция '{operation_name}' выполнена за {duration:.3f} секунд")

    def get_log_files(self):
        """Получение списка файлов логов"""
        log_files = []
        for log_file in self.log_dir.glob("*.log"):
            stat = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime)
            })
        return log_files

    def clear_old_logs(self, days_to_keep=30):
        """Очистка старых логов"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0

            for log_file in self.log_dir.glob("*.log.*"):  # Ротационные файлы
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    deleted_count += 1

            logger = logging.getLogger('System')
            logger.info(f"Очищено {deleted_count} старых файлов логов")
            return deleted_count
        except Exception as e:
            logger = logging.getLogger('System')
            logger.error(f"Ошибка очистки логов: {e}")
            return 0


# Декоратор для логирования функций
def log_operation(operation_name, level=LogLevel.INFO):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = system_logger.get_logger(func.__module__)
            start_time = datetime.now()

            try:
                logger.log(
                    getattr(logging, level.value),
                    f"Начало операции: {operation_name}"
                )

                result = func(*args, **kwargs)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                logger.log(
                    getattr(logging, level.value),
                    f"Завершение операции: {operation_name} (длительность: {duration:.3f} сек)"
                )

                return result

            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                logger.error(
                    f"Ошибка в операции '{operation_name}' (длительность: {duration:.3f} сек): {e}"
                )
                system_logger.log_error_with_traceback(
                    f"Ошибка в операции '{operation_name}'",
                    e
                )
                raise

        return wrapper

    return decorator


# Глобальный экземпляр логгера
system_logger = SystemLogger()