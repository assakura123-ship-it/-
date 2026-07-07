import sqlite3
import pandas as pd
import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from modules.logger import system_logger, log_operation, LogLevel


# ===================== SQLite ДАТАБЕЙЗ ХЭНДЛЕР =====================
class DatabaseManager:
    """Класс для управления базой данных SQLite"""

    def __init__(self, db_path: str = "loading_cards.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.logger = system_logger.get_logger('DatabaseManager')
        self.initialize_database()

    def initialize_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Создание таблицы продуктов
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_code TEXT UNIQUE NOT NULL,
                    product_name TEXT NOT NULL,
                    description TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создание таблицы рецептур
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_number TEXT NOT NULL,
                    product_code TEXT NOT NULL,
                    recipe_name TEXT,
                    version INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_code) REFERENCES products(product_code),
                    UNIQUE(recipe_number, product_code)
                )
            ''')

            # Создание таблицы компонентов рецептур
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipe_components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER NOT NULL,
                    component_code TEXT NOT NULL,
                    component_name TEXT NOT NULL,
                    percentage REAL NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
                    unit TEXT DEFAULT 'kg',
                    sort_order INTEGER DEFAULT 0,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id),
                    UNIQUE(recipe_id, component_code)
                )
            ''')

            # Создание таблицы карт загрузок
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS loading_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_name TEXT NOT NULL,
                    product_code TEXT NOT NULL,
                    recipe_id INTEGER NOT NULL,
                    reactor TEXT,
                    batch_quantity REAL DEFAULT 1000.0,
                    total_mass REAL,
                    status TEXT DEFAULT 'draft',
                    created_by TEXT DEFAULT 'system',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_code) REFERENCES products(product_code),
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                )
            ''')

            # Создание таблицы компонентов карты загрузки
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS card_components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL,
                    component_code TEXT NOT NULL,
                    component_name TEXT NOT NULL,
                    percentage REAL NOT NULL,
                    calculated_mass REAL NOT NULL,
                    actual_mass REAL,
                    unit TEXT DEFAULT 'kg',
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (card_id) REFERENCES loading_cards(id)
                )
            ''')

            # Создание таблицы склада
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS warehouse (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_code TEXT UNIQUE NOT NULL,
                    component_name TEXT NOT NULL,
                    current_stock REAL DEFAULT 0.0,
                    min_stock REAL DEFAULT 0.0,
                    max_stock REAL DEFAULT 1000.0,
                    unit TEXT DEFAULT 'kg',
                    location TEXT,
                    supplier TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # СОЗДАНИЕ ТАБЛИЦЫ norms ВМЕСТО product_norms
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS norms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_code TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    norm_code TEXT NOT NULL,
                    norm_name TEXT NOT NULL,
                    lower_limit REAL,
                    upper_limit REAL,
                    string_value TEXT,
                    analysis_method TEXT,
                    norm_type TEXT DEFAULT 'phys_chem',
                    is_active INTEGER DEFAULT 1,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_code) REFERENCES products(product_code),
                    UNIQUE(product_code, norm_code)
                )
            ''')

            # Создание индексов для ускорения поиска
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_code ON products(product_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_product ON recipes(product_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_components_recipe ON recipe_components(recipe_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_product ON loading_cards(product_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_recipe ON loading_cards(recipe_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_code ON warehouse(component_code)')
            # ДОБАВЛЕН ИНДЕКС ДЛЯ ТАБЛИЦЫ norms
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_norms_product ON norms(product_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_norms_code ON norms(norm_code)')

            self.conn.commit()
            self.logger.info(f"База данных инициализирована: {self.db_path}")

            # Чиним записи, повреждённые старой версией import_from_excel()
            # (до исправления numpy.int64 записывался в БД напрямую и
            # сохранялся sqlite3 как BLOB вместо текста)
            self._repair_corrupted_codes()

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            raise

    def _repair_corrupted_codes(self):
        """Восстановить текстовые коды, повреждённые старым багом импорта.

        До исправления в import_from_excel() значения numpy.int64/float64
        (коды продуктов, компонентов, номера рецептур), полученные из
        pandas, передавались в sqlite3 напрямую. sqlite3 не умеет
        сериализовать numpy-скаляры как текст и сохранял их как 8-байтный
        BLOB (little-endian представление числа), а не как строку с
        цифрами. Из-за этого в существующих базах пользователей могли
        остаться "битые" строки вида b'\\xdb\\xb1\\xa9\\x00\\x00\\x00\\x00\\x00'
        вместо '11121115' — это ломает импорт/экспорт и вывод в интерфейсе
        (TypeError: unsupported format string passed to bytes.__format__).

        Эта функция при каждом запуске сканирует все текстовые колонки,
        которые могли пострадать, находит значения типа BLOB длиной 8 байт
        и преобразует их обратно в строку с числом.
        """
        import struct

        columns_to_check = [
            ('products', 'product_code'),
            ('recipes', 'product_code'),
            ('recipes', 'recipe_number'),
            ('recipe_components', 'component_code'),
            ('loading_cards', 'product_code'),
            ('card_components', 'component_code'),
            ('warehouse', 'component_code'),
            ('norms', 'product_code'),
            ('norms', 'norm_code'),
        ]

        total_repaired = 0

        for table, column in columns_to_check:
            try:
                self.cursor.execute(
                    f'SELECT rowid, "{column}" FROM {table} WHERE typeof("{column}") = "blob"'
                )
                broken_rows = self.cursor.fetchall()
            except sqlite3.Error:
                # Таблицы/колонки может не быть в старой версии схемы - пропускаем
                continue

            for rowid, blob_value in broken_rows:
                fixed_value = self._decode_corrupted_blob(blob_value)
                if fixed_value is None:
                    self.logger.warning(
                        f"Не удалось восстановить повреждённое значение в {table}.{column} "
                        f"(rowid={rowid}): {blob_value!r}"
                    )
                    continue

                try:
                    self.cursor.execute(
                        f'UPDATE {table} SET "{column}" = ? WHERE rowid = ?',
                        (fixed_value, rowid)
                    )
                    total_repaired += 1
                    self.logger.info(
                        f"Восстановлено значение {table}.{column} (rowid={rowid}): "
                        f"{blob_value!r} -> '{fixed_value}'"
                    )
                except sqlite3.IntegrityError as e:
                    # Если восстановленное значение конфликтует с уже существующей
                    # корректной строкой (UNIQUE constraint) - удаляем дубликат-мусор,
                    # оставляя корректную запись
                    self.logger.warning(
                        f"Конфликт при восстановлении {table}.{column} (rowid={rowid}) "
                        f"-> '{fixed_value}': {e}. Удаляю повреждённую дублирующую запись."
                    )
                    try:
                        self.cursor.execute(f'DELETE FROM {table} WHERE rowid = ?', (rowid,))
                    except sqlite3.Error:
                        pass

        if total_repaired:
            self.conn.commit()
            self.logger.info(f"Автовосстановление БД: исправлено {total_repaired} повреждённых значений")

    @staticmethod
    def _decode_corrupted_blob(blob_value) -> Optional[str]:
        """Попытаться декодировать повреждённый BLOB обратно в строку с числом.

        Поддерживает 8-байтное little-endian представление numpy.int64 -
        единственный тип, из-за которого старый баг импорта Excel мог
        записать BLOB вместо текста в sqlite3.

        Примечание: numpy.float64 НЕ вызывает эту проблему, т.к. является
        подклассом обычного Python float и sqlite3 умеет адаптировать его
        в текст самостоятельно (проверено эмпирически). Битые BLOB'ы
        возникают только из numpy.int64 (не являющегося подклассом int),
        поэтому декодируем именно как 8-байтное целое со знаком.
        """
        import struct

        if not isinstance(blob_value, (bytes, bytearray)) or len(blob_value) != 8:
            return None

        try:
            as_int = struct.unpack('<q', blob_value)[0]
            return str(as_int)
        except struct.error:
            pass

        # На всякий случай - если целочисленная интерпретация не сработала,
        # пробуем как float64
        try:
            as_float = struct.unpack('<d', blob_value)[0]
            if as_float == as_float and abs(as_float) < 1e15:
                if as_float.is_integer():
                    return str(int(as_float))
                return str(as_float)
        except struct.error:
            pass

        return None

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            self.logger.info("Соединение с базой данных закрыто")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Выполнение запроса и возврат результатов в виде словарей"""
        try:
            self.cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in self.cursor.description]
                return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            self.conn.commit()
            return []
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка выполнения запроса: {query} - {e}")
            raise

    def _fetch_one(self, query: str, params: tuple = ()):
        """Выполнить запрос и вернуть одну строку"""
        try:
            self.cursor.execute(query, params)
            columns = [column[0] for column in self.cursor.description]
            row = self.cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса: {query}, {params}: {e}")
            return None

    # ===================== МЕТОДЫ ДЛЯ НОРМ =====================

    def get_product_norms(self, product_code: str) -> list:
        """Получить нормы для конкретного продукта по его коду"""
        try:
            query = """
            SELECT 
                n.norm_code,
                n.norm_name,
                n.lower_limit,
                n.upper_limit,
                n.string_value,
                n.analysis_method
            FROM norms n
            WHERE n.product_code = ? AND n.is_active = 1
            ORDER BY n.norm_code
            """
            self.cursor.execute(query, (product_code,))
            columns = [column[0] for column in self.cursor.description]
            norms = []

            for row in self.cursor.fetchall():
                norms.append(dict(zip(columns, row)))

            self.logger.debug(f"Получено {len(norms)} норм для продукта {product_code}")
            return norms

        except Exception as e:
            self.logger.error(f"Ошибка получения норм для продукта {product_code}: {e}")
            return []

    def get_product_name_by_code(self, product_code: str) -> str:
        """Получить название продукта по коду"""
        try:
            query = "SELECT product_name FROM products WHERE product_code = ?"
            self.cursor.execute(query, (product_code,))
            result = self.cursor.fetchone()
            return result[0] if result else product_code
        except Exception as e:
            self.logger.error(f"Ошибка получения названия продукта {product_code}: {e}")
            return product_code

    @log_operation("Импорт норм из Excel", LogLevel.INFO)
    def import_norms_from_excel(self, file_path: str, replace_existing: bool = False) -> bool:
        """Импорт норм физико-химических показателей из Excel файла"""
        try:
            self.logger.info(f"Начало импорта норм из файла: {file_path}")

            # Читаем Excel файл
            df = pd.read_excel(file_path)

            # Проверяем наличие необходимых колонок
            required_columns = ['Код полуфабриката', 'Наименование полуфабриката',
                                'Код нормы', 'Наименование нормы',
                                'Нижняя граница', 'Верхняя граница',
                                'Строка', 'Метод анализа']

            for col in required_columns:
                if col not in df.columns:
                    self.logger.error(f"Отсутствует обязательная колонка: {col}")
                    return False

            # Начинаем транзакцию
            self.cursor.execute('BEGIN TRANSACTION')

            if replace_existing:
                # Удаляем существующие нормы для продуктов из файла
                product_codes = df['Код полуфабриката'].unique()
                for code in product_codes:
                    self.cursor.execute('DELETE FROM norms WHERE product_code = ?', (str(code).strip(),))
                self.logger.info(f"Удалены старые нормы для {len(product_codes)} продуктов")

            # Импортируем данные
            imported_count = 0
            skipped_count = 0

            for _, row in df.iterrows():
                try:
                    # Подготовка данных
                    product_code = str(row['Код полуфабриката']).strip()
                    product_name = str(row['Наименование полуфабриката']).strip()
                    norm_code = str(row['Код нормы']).strip()
                    norm_name = str(row['Наименование нормы']).strip()

                    # Обработка числовых значений (может быть NaN)
                    lower_limit = row['Нижняя граница']
                    if pd.isna(lower_limit):
                        lower_limit = None
                    else:
                        try:
                            lower_limit = float(lower_limit)
                        except:
                            lower_limit = None

                    upper_limit = row['Верхняя граница']
                    if pd.isna(upper_limit):
                        upper_limit = None
                    else:
                        try:
                            upper_limit = float(upper_limit)
                        except:
                            upper_limit = None

                    string_value = str(row['Строка']).strip() if not pd.isna(row['Строка']) else ''
                    analysis_method = str(row['Метод анализа']).strip() if not pd.isna(row['Метод анализа']) else ''

                    # Проверяем, существует ли уже такая норма
                    self.cursor.execute(
                        'SELECT id FROM norms WHERE product_code = ? AND norm_code = ?',
                        (product_code, norm_code)
                    )

                    existing = self.cursor.fetchone()

                    if existing:
                        # Обновляем существующую запись
                        self.cursor.execute('''
                            UPDATE norms SET
                                product_name = ?,
                                norm_name = ?,
                                lower_limit = ?,
                                upper_limit = ?,
                                string_value = ?,
                                analysis_method = ?,
                                updated_date = CURRENT_TIMESTAMP
                            WHERE product_code = ? AND norm_code = ?
                        ''', (product_name, norm_name, lower_limit, upper_limit,
                              string_value, analysis_method, product_code, norm_code))
                        self.logger.debug(f"Обновлена норма: {norm_code} для продукта {product_code}")
                    else:
                        # Добавляем новую запись
                        self.cursor.execute('''
                            INSERT INTO norms 
                            (product_code, product_name, norm_code, norm_name,
                             lower_limit, upper_limit, string_value, analysis_method)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (product_code, product_name, norm_code, norm_name,
                              lower_limit, upper_limit, string_value, analysis_method))
                        self.logger.debug(f"Добавлена новая норма: {norm_code} для продукта {product_code}")

                    imported_count += 1

                except Exception as e:
                    self.logger.warning(f"Ошибка обработки строки {_ + 2}: {e}")
                    skipped_count += 1
                    continue

            # Фиксируем транзакцию
            self.conn.commit()

            self.logger.info(f"Импорт норм завершен. Импортировано: {imported_count}, Пропущено: {skipped_count}")
            return True

        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка импорта норм из Excel: {e}")
            return False

    @log_operation("Получение норм для продукта", LogLevel.INFO)
    def get_norms_for_product(self, product_code: str) -> List[Dict[str, Any]]:
        """Получить нормы физико-химических показателей для продукта"""
        try:
            result = self.execute_query('''
                SELECT 
                    norm_code,
                    norm_name,
                    lower_limit,
                    upper_limit,
                    string_value,
                    analysis_method,
                    norm_type,
                    is_active,
                    created_date,
                    updated_date
                FROM norms 
                WHERE product_code = ? AND is_active = 1
                ORDER BY norm_code
            ''', (product_code,))
            return result if result is not None else []

        except Exception as e:
            self.logger.error(f"Ошибка получения норм для продукта {product_code}: {e}")
            return []

    @log_operation("Получение всех продуктов с нормами", LogLevel.INFO)
    def get_products_with_norms(self) -> List[Dict[str, Any]]:
        """Получить список всех продуктов, для которых есть нормы"""
        try:
            result = self.execute_query('''
                SELECT DISTINCT 
                    p.product_code,
                    p.product_name,
                    COUNT(n.id) as norm_count,
                    MAX(n.updated_date) as last_updated
                FROM products p
                LEFT JOIN norms n ON p.product_code = n.product_code
                GROUP BY p.product_code, p.product_name
                HAVING COUNT(n.id) > 0
                ORDER BY p.product_name
            ''')
            return result if result is not None else []

        except Exception as e:
            self.logger.error(f"Ошибка получения продуктов с нормами: {e}")
            return []

    @log_operation("Удаление норм для продукта", LogLevel.WARNING)
    def delete_norms_for_product(self, product_code: str) -> bool:
        """Удалить все нормы для указанного продукта"""
        try:
            self.execute_query('DELETE FROM norms WHERE product_code = ?', (product_code,))
            self.logger.warning(f"Удалены нормы для продукта {product_code}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления норм для продукта {product_code}: {e}")
            return False

    @log_operation("Экспорт норм в Excel", LogLevel.INFO)
    def export_norms_to_excel(self, output_path: str, product_code: str = None) -> bool:
        """Экспорт норм в Excel файл"""
        try:
            if product_code:
                # Экспорт норм для конкретного продукта
                norms = self.get_norms_for_product(product_code)

                if not norms:
                    self.logger.warning(f"Нет норм для продукта {product_code}")
                    return False

                # Получаем информацию о продукте
                product_info = self.get_product_by_code(product_code)
                product_name = product_info['product_name'] if product_info else product_code

                # Создаем DataFrame
                data = []
                for norm in norms:
                    data.append({
                        'Код полуфабриката': product_code,
                        'Наименование полуфабриката': product_name,
                        'Код нормы': norm['norm_code'],
                        'Наименование нормы': norm['norm_name'],
                        'Нижняя граница': norm['lower_limit'],
                        'Верхняя граница': norm['upper_limit'],
                        'Строка': norm['string_value'],
                        'Метод анализа': norm['analysis_method']
                    })

                df = pd.DataFrame(data)

            else:
                # Экспорт всех норм
                result = self.execute_query('''
                    SELECT 
                        product_code,
                        product_name,
                        norm_code,
                        norm_name,
                        lower_limit,
                        upper_limit,
                        string_value,
                        analysis_method
                    FROM norms
                    ORDER BY product_code, norm_code
                ''')

                if not result:
                    return False

                data = []
                for row in result:
                    data.append({
                        'Код полуфабриката': row['product_code'],
                        'Наименование полуфабриката': row['product_name'],
                        'Код нормы': row['norm_code'],
                        'Наименование нормы': row['norm_name'],
                        'Нижняя граница': row['lower_limit'],
                        'Верхняя граница': row['upper_limit'],
                        'Строка': row['string_value'],
                        'Метод анализа': row['analysis_method']
                    })

                df = pd.DataFrame(data)

            # Экспорт в Excel
            df.to_excel(output_path, index=False)

            self.logger.info(f"Нормы успешно экспортированы в {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка экспорта норм в Excel: {e}")
            return False

    @log_operation("Проверка наличия норм для продукта", LogLevel.INFO)
    def has_norms_for_product(self, product_code: str) -> bool:
        """Проверить, есть ли нормы для указанного продукта"""
        try:
            result = self.execute_query(
                'SELECT COUNT(*) as count FROM norms WHERE product_code = ?',
                (product_code,)
            )

            if result and len(result) > 0:
                has_norms = result[0]['count'] > 0
                self.logger.debug(f"Продукт {product_code} имеет нормы: {has_norms}")
                return has_norms
            return False

        except Exception as e:
            self.logger.error(f"Ошибка проверки наличия норм для продукта {product_code}: {e}")
            return False

    def get_total_norms_count(self) -> int:
        """Получить общее количество норм в базе"""
        try:
            result = self.execute_query('SELECT COUNT(*) as count FROM norms')
            return result[0]['count'] if result and len(result) > 0 else 0
        except Exception as e:
            self.logger.error(f"Ошибка получения количества норм: {e}")
            return 0

    def get_products_with_norms_count(self) -> int:
        """Получить количество продуктов с нормами"""
        try:
            result = self.execute_query('SELECT COUNT(DISTINCT product_code) as count FROM norms')
            return result[0]['count'] if result and len(result) > 0 else 0
        except Exception as e:
            self.logger.error(f"Ошибка получения количества продуктов с нормами: {e}")
            return 0

    # ===================== ОСТАЛЬНЫЕ МЕТОДЫ БАЗЫ ДАННЫХ =====================

    def get_products(self) -> List[Dict[str, Any]]:
        """Получение списка всех продуктов"""
        try:
            result = self.execute_query('''
                SELECT p.*, 
                       (SELECT COUNT(*) FROM recipes r WHERE r.product_code = p.product_code) as recipe_count
                FROM products p
                ORDER BY p.product_name
            ''')
            return result if result is not None else []
        except Exception as e:
            self.logger.error(f"Ошибка получения продуктов: {e}")
            return []

    def get_product_by_code(self, product_code: str) -> Optional[Dict[str, Any]]:
        """Получение продукта по коду"""
        result = self.execute_query('SELECT * FROM products WHERE product_code = ?', (product_code,))
        return result[0] if result else None

    def get_recipes_for_product(self, product_code: str) -> List[Dict[str, Any]]:
        """Получение рецептур для продукта"""
        return self.execute_query('''
            SELECT r.*,
                   (SELECT COUNT(*) FROM recipe_components rc WHERE rc.recipe_id = r.id) as component_count
            FROM recipes r
            WHERE r.product_code = ?
            ORDER BY r.recipe_number
        ''', (product_code,))

    def get_recipe_components(self, recipe_id: int) -> List[Dict[str, Any]]:
        """Получение компонентов рецептуры"""
        return self.execute_query('''
            SELECT * FROM recipe_components
            WHERE recipe_id = ?
            ORDER BY sort_order, id
        ''', (recipe_id,))

    def get_recipe_by_number(self, product_code: str, recipe_number: str) -> Optional[Dict[str, Any]]:
        """Получение рецептуры по номеру"""
        result = self.execute_query('''
            SELECT * FROM recipes
            WHERE product_code = ? AND recipe_number = ?
        ''', (product_code, recipe_number))
        return result[0] if result else None

    def create_product(self, product_code: str, product_name: str, description: str = "") -> int:
        """Создание нового продукта"""
        self.execute_query('''
            INSERT INTO products (product_code, product_name, description)
            VALUES (?, ?, ?)
        ''', (product_code, product_name, description))
        return self.cursor.lastrowid

    def create_recipe(self, product_code: str, recipe_number: str, recipe_name: str = "") -> int:
        """Создание новой рецептуры"""
        self.execute_query('''
            INSERT INTO recipes (product_code, recipe_number, recipe_name)
            VALUES (?, ?, ?)
        ''', (product_code, recipe_number, recipe_name))
        return self.cursor.lastrowid

    def add_recipe_component(self, recipe_id: int, component_code: str,
                             component_name: str, percentage: float) -> int:
        """Добавление компонента в рецептуру"""
        self.execute_query('''
            INSERT INTO recipe_components (recipe_id, component_code, component_name, percentage)
            VALUES (?, ?, ?, ?)
        ''', (recipe_id, component_code, component_name, percentage))
        return self.cursor.lastrowid

    def update_recipe_component(self, component_id: int, component_code: str = None,
                                component_name: str = None, percentage: float = None):
        """Обновление компонента рецептуры"""
        updates = []
        params = []

        if component_code is not None:
            updates.append("component_code = ?")
            params.append(component_code)
        if component_name is not None:
            updates.append("component_name = ?")
            params.append(component_name)
        if percentage is not None:
            updates.append("percentage = ?")
            params.append(percentage)

        if updates:
            params.append(component_id)
            query = f"UPDATE recipe_components SET {', '.join(updates)} WHERE id = ?"
            self.execute_query(query, tuple(params))

    def delete_recipe_component(self, component_id: int):
        """Удаление компонента из рецептуры"""
        self.execute_query('DELETE FROM recipe_components WHERE id = ?', (component_id,))

    def create_loading_card(self, card_name: str, product_code: str, recipe_id: int,
                            reactor: str = "Р-1", batch_quantity: float = 1000.0) -> int:
        """Создание новой карты загрузки"""
        self.execute_query('''
            INSERT INTO loading_cards (card_name, product_code, recipe_id, reactor, batch_quantity)
            VALUES (?, ?, ?, ?, ?)
        ''', (card_name, product_code, recipe_id, reactor, batch_quantity))
        return self.cursor.lastrowid

    def add_card_component(self, card_id: int, component_code: str, component_name: str,
                           percentage: float, calculated_mass: float) -> int:
        """Добавление компонента в карту загрузки"""
        self.execute_query('''
            INSERT INTO card_components (card_id, component_code, component_name, 
                                        percentage, calculated_mass)
            VALUES (?, ?, ?, ?, ?)
        ''', (card_id, component_code, component_name, percentage, calculated_mass))
        return self.cursor.lastrowid

    def get_loading_cards(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение списка карт загрузок"""
        return self.execute_query('''
            SELECT lc.*, p.product_name, r.recipe_number,
                   (SELECT COUNT(*) FROM card_components cc WHERE cc.card_id = lc.id) as component_count
            FROM loading_cards lc
            LEFT JOIN products p ON lc.product_code = p.product_code
            LEFT JOIN recipes r ON lc.recipe_id = r.id
            ORDER BY lc.created_date DESC
            LIMIT ?
        ''', (limit,))

    def get_loading_card_details(self, card_id: int) -> Optional[Dict[str, Any]]:
        """Получение деталей карты загрузки"""
        result = self.execute_query('''
            SELECT lc.*, p.product_name, r.recipe_number, r.recipe_name
            FROM loading_cards lc
            LEFT JOIN products p ON lc.product_code = p.product_code
            LEFT JOIN recipes r ON lc.recipe_id = r.id
            WHERE lc.id = ?
        ''', (card_id,))
        return result[0] if result else None

    def get_card_components(self, card_id: int) -> List[Dict[str, Any]]:
        """Получение компонентов карта загрузки"""
        return self.execute_query('''
            SELECT * FROM card_components
            WHERE card_id = ?
            ORDER BY sort_order, id
        ''', (card_id,))

    def update_card_total_mass(self, card_id: int, total_mass: float):
        """Обновление общей массы карты загрузки"""
        self.execute_query('''
            UPDATE loading_cards SET total_mass = ?, updated_date = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (total_mass, card_id))

    def delete_loading_card(self, card_id: int):
        """Удаление карты загрузки и её компонентов"""
        # Сначала удаляем компоненты
        self.execute_query('DELETE FROM card_components WHERE card_id = ?', (card_id,))
        # Затем удаляем саму карту
        self.execute_query('DELETE FROM loading_cards WHERE id = ?', (card_id,))

    @staticmethod
    def _normalize_excel_value(value) -> str:
        """Привести значение ячейки Excel (в т.ч. numpy.int64/float64/Timestamp)
        к нативной Python-строке.

        pandas при чтении Excel возвращает числовые колонки как numpy-типы
        (numpy.int64, numpy.float64). sqlite3 не умеет корректно
        сериализовать numpy-типы через параметризованные запросы — вместо
        текста получается повреждённый BLOB (см. баг с product_code).
        Поэтому все значения, которые идут в TEXT-колонки, нормализуем
        в обычный Python str.
        """
        if value is None:
            return ''
        if pd.isna(value):
            return ''
        # numpy числовые типы имеют метод .item(), который возвращает
        # эквивалентный нативный Python-тип (int/float)
        if hasattr(value, 'item'):
            value = value.item()
        # Целые float вида 11121115.0 приводим к виду "11121115" (без .0),
        # т.к. коды продуктов/компонентов в Excel часто хранятся как float
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    def import_from_excel(self, filepath: str, replace_existing: bool = False):
        """Импорт данных из Excel файла в базу данных

        Args:
            filepath (str): Путь к Excel файлу
            replace_existing (bool): Если True, существующие рецептуры (по коду продукта
                и номеру РЦ) будут удалены перед импортом новых данных
        """
        try:
            self.logger.info(f"Импорт данных из Excel файла: {filepath} (replace_existing={replace_existing})")

            # Чтение Excel файла
            df = pd.read_excel(filepath)

            # Автоматическое определение колонок
            column_mapping = {}
            for col in df.columns:
                col_lower = str(col).lower().strip()
                if any(x in col_lower for x in ['код продукт', 'артикул', 'product code']):
                    column_mapping[col] = 'Код продукта'
                elif any(x in col_lower for x in ['наимен', 'назван', 'product name']):
                    column_mapping[col] = 'Наименование'
                elif any(x in col_lower for x in ['номер рц', 'рц', 'рецептура', 'recipe']):
                    column_mapping[col] = 'Номер РЦ'
                elif any(x in col_lower for x in ['код компонент', 'component code']):
                    column_mapping[col] = 'Код компонента'
                elif any(x in col_lower for x in ['компонент', 'ингредиент', 'component']):
                    if 'код' not in col_lower:
                        column_mapping[col] = 'Компонент'
                elif any(x in col_lower for x in ['процент', '%', 'percentage']):
                    column_mapping[col] = 'Процент'

            if column_mapping:
                df = df.rename(columns=column_mapping)

            # Группировка по продуктам и рецептурам
            if 'Код продукта' in df.columns and 'Номер РЦ' in df.columns:
                grouped = df.groupby(['Код продукта', 'Номер РЦ'])

                for (product_code, recipe_number), group in grouped:
                    # Приводим ключи группировки к нативным Python-типам (str),
                    # иначе pandas/numpy может вернуть numpy.int64, который
                    # sqlite3 сохраняет как повреждённый BLOB вместо текста
                    product_code = self._normalize_excel_value(product_code)
                    recipe_number = self._normalize_excel_value(recipe_number)

                    # Добавляем продукт
                    product_name = self._normalize_excel_value(
                        group.iloc[0].get('Наименование', product_code))
                    self.execute_query('''
                        INSERT OR IGNORE INTO products (product_code, product_name)
                        VALUES (?, ?)
                    ''', (product_code, product_name))

                    # Если требуется замена существующих данных - удаляем старую рецептуру
                    if replace_existing:
                        existing_recipe = self.get_recipe_by_number(product_code, recipe_number)
                        if existing_recipe:
                            self.execute_query(
                                'DELETE FROM recipe_components WHERE recipe_id = ?',
                                (existing_recipe['id'],)
                            )
                            self.logger.debug(
                                f"Удалены старые компоненты рецептуры {recipe_number} продукта {product_code}")

                    # Добавляем рецептуру
                    self.execute_query('''
                        INSERT OR IGNORE INTO recipes (product_code, recipe_number, recipe_name)
                        VALUES (?, ?, ?)
                    ''', (product_code, recipe_number, f"Рецептура {recipe_number}"))

                    # Получаем ID рецептуры
                    recipe = self.get_recipe_by_number(product_code, recipe_number)
                    if recipe:
                        recipe_id = recipe['id']

                        # Добавляем компоненты
                        for _, row in group.iterrows():
                            component_code = self._normalize_excel_value(row.get('Код компонента', ''))
                            component_name = self._normalize_excel_value(row.get('Компонент', ''))
                            percentage_value = row.get('Процент', 0.0)

                            # Преобразуем процент в число
                            try:
                                if isinstance(percentage_value, str):
                                    percentage_value = percentage_value.replace(',', '.').strip()
                                    percentage_value = percentage_value.replace('%', '')
                                    percentage = float(percentage_value)
                                else:
                                    percentage = float(percentage_value)
                            except (ValueError, TypeError):
                                percentage = 0.0

                            self.logger.debug(
                                f"Обработка компонента: код='{component_code}', имя='{component_name}', процент='{percentage_value}' -> {percentage}")
                            if component_code and component_name and percentage > 0:
                                self.execute_query('''
                                    INSERT OR IGNORE INTO recipe_components 
                                    (recipe_id, component_code, component_name, percentage)
                                    VALUES (?, ?, ?, ?)
                                ''', (recipe_id, component_code, component_name, percentage))

                self.conn.commit()
                self.logger.info(f"Импортировано {len(grouped)} рецептур из файла {filepath}")
                return True
            else:
                self.logger.error("Не найдены необходимые колонки в Excel файле")
                return False

        except Exception as e:
            self.logger.error(f"Ошибка импорта из Excel: {e}")
            return False

    def export_to_excel(self, card_id: int, output_path: str) -> bool:
        """Экспорт карты загрузки в Excel файл"""
        try:
            # Получаем данные карты
            card = self.get_loading_card_details(card_id)
            if not card:
                return False

            components = self.get_card_components(card_id)

            # Создаем DataFrame для основной информации
            info_data = {
                'Параметр': [
                    'Дата создания', 'Название карты', 'Продукт', 'Код продукта',
                    'Рецептура', 'Реактор', 'Количество, кг', 'Количество компонентов',
                    'Общая масса, кг', 'Статус'
                ],
                'Значение': [
                    card['created_date'],
                    card['card_name'],
                    card.get('product_name', ''),
                    card['product_code'],
                    card.get('recipe_number', ''),
                    card.get('reactor', 'Р-1'),
                    card.get('batch_quantity', 1000.0),
                    len(components),
                    card.get('total_mass', 0.0),
                    card.get('status', 'draft')
                ]
            }
            info_df = pd.DataFrame(info_data)

            # Создаем DataFrame для компонентов
            comp_data = []
            for i, comp in enumerate(components, 1):
                comp_data.append({
                    '№': i,
                    'Код компонента': comp['component_code'],
                    'Наименование компонента': comp['component_name'],
                    'Процент, %': comp['percentage'],
                    'Масса, кг': comp['calculated_mass']
                })

            # Добавляем итоговую строку
            if components:
                total_percent = sum(comp['percentage'] for comp in components)
                total_mass = sum(comp['calculated_mass'] for comp in components)
                comp_data.append({
                    '№': '',
                    'Код компонента': 'ВСЕГО:',
                    'Наименование компонента': f"{len(components)} компонентов",
                    'Процент, %': total_percent,
                    'Масса, кг': total_mass
                })

            comp_df = pd.DataFrame(comp_data)

            # Сохраняем в Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                info_df.to_excel(writer, sheet_name='Информация', index=False)
                comp_df.to_excel(writer, sheet_name='Рецептура', index=False)

            self.logger.info(f"Карта загрузки экспортирована в {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка экспорта в Excel: {e}")
            return False

    def get_warehouse_items(self) -> List[Dict[str, Any]]:
        """Получение списка всех позиций на складе"""
        return self.execute_query('''
            SELECT * FROM warehouse
            ORDER BY component_name
        ''')

    def update_warehouse_stock(self, component_code: str, quantity_change: float):
        """Обновление остатков на складе"""
        self.execute_query('''
            UPDATE warehouse 
            SET current_stock = current_stock + ?, last_updated = CURRENT_TIMESTAMP
            WHERE component_code = ?
        ''', (quantity_change, component_code))

    def add_warehouse_item(self, component_code: str, component_name: str,
                           current_stock: float = 0.0, unit: str = "кг",
                           location: str = "", min_stock: float = 0.0,
                           max_stock: float = 1000.0):
        """Добавление новой позиции на склад"""
        self.execute_query('''
            INSERT OR REPLACE INTO warehouse 
            (component_code, component_name, current_stock, unit, location, min_stock, max_stock)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (component_code, component_name, current_stock, unit, location, min_stock, max_stock))

    def import_warehouse_from_excel(self, filepath: str) -> bool:
        """Импорт данных склада из Excel файла"""
        try:
            self.logger.info(f"Импорт данных склада из Excel файла: {filepath}")

            # Чтение Excel файла
            df = pd.read_excel(filepath)

            # Автоматическое определение колонок для склада
            column_mapping = {}
            for col in df.columns:
                col_lower = str(col).lower().strip()
                if any(x in col_lower for x in ['код компонент', 'артикул', 'component code', 'код']):
                    column_mapping[col] = 'Код компонента'
                elif any(x in col_lower for x in ['наимен', 'назван', 'component name', 'компонент']):
                    column_mapping[col] = 'Наименование'
                elif any(x in col_lower for x in ['начальн', 'initial', 'начальный остаток']):
                    column_mapping[col] = 'Начальный остаток'
                elif any(x in col_lower for x in ['приход', 'поступление', 'income']):
                    column_mapping[col] = 'Приход'
                elif any(x in col_lower for x in ['расход', 'выдача', 'consumption', 'выбытие']):
                    column_mapping[col] = 'Расход'
                elif any(x in col_lower for x in
                         ['конечн', 'final', 'текущий', 'остаток', 'current', 'конечный остаток']):
                    column_mapping[col] = 'Конечный остаток'
                elif any(x in col_lower for x in ['единиц', 'unit', 'ед. изм.', 'measurement']):
                    column_mapping[col] = 'Единица измерения'
                elif any(x in col_lower for x in ['местоположение', 'location', 'ячейка', 'стеллаж']):
                    column_mapping[col] = 'Местоположение'
                elif any(x in col_lower for x in ['поставщик', 'supplier', 'производитель']):
                    column_mapping[col] = 'Поставщик'

            if column_mapping:
                df = df.rename(columns=column_mapping)

            # Проверяем обязательные колонки
            if 'Код компонента' not in df.columns or 'Наименование' not in df.columns:
                self.logger.error("Не найдены необходимые колонки для склада: Код компонента и Наименование")
                return False

            # Обрабатываем каждую строку
            imported_count = 0
            for _, row in df.iterrows():
                try:
                    # Получаем значения из строки
                    component_code = str(row.get('Код компонента', '')).strip()
                    component_name = str(row.get('Наименование', '')).strip()

                    # Если код или имя пустые, пропускаем
                    if not component_code or not component_name:
                        continue

                    # Получаем остатки (пытаемся из разных колонок)
                    current_stock = 0.0

                    # Сначала пробуем получить конечный остаток
                    if 'Конечный остаток' in df.columns:
                        try:
                            val = row.get('Конечный остаток')
                            if pd.notna(val):
                                current_stock = float(str(val).replace(',', '.'))
                        except:
                            pass

                    # Если нет конечного остатка, пробуем начальный
                    if current_stock == 0 and 'Начальный остаток' in df.columns:
                        try:
                            val = row.get('Начальный остаток')
                            if pd.notna(val):
                                current_stock = float(str(val).replace(',', '.'))
                        except:
                            pass

                    # Если все еще 0, вычисляем из начальный + приход - расход
                    if current_stock == 0:
                        try:
                            initial = 0.0
                            income = 0.0
                            consumption = 0.0

                            if 'Начальный остаток' in df.columns:
                                val = row.get('Начальный остаток')
                                if pd.notna(val):
                                    initial = float(str(val).replace(',', '.'))

                            if 'Приход' in df.columns:
                                val = row.get('Приход')
                                if pd.notna(val):
                                    income = float(str(val).replace(',', '.'))

                            if 'Расход' in df.columns:
                                val = row.get('Расход')
                                if pd.notna(val):
                                    consumption = float(str(val).replace(',', '.'))

                            current_stock = initial + income - consumption
                        except:
                            current_stock = 0.0

                    # Получаем дополнительные поля
                    location = str(row.get('Местоположение', '')).strip() if pd.notna(
                        row.get('Местоположение', '')) else ''
                    supplier = str(row.get('Поставщик', '')).strip() if pd.notna(row.get('Поставщик', '')) else ''
                    unit = str(row.get('Единица измерения', 'кг')).strip() if pd.notna(
                        row.get('Единица измерения', '')) else 'кг'

                    # Добавляем или обновляем позицию на складе
                    self.add_warehouse_item(
                        component_code=component_code,
                        component_name=component_name,
                        current_stock=current_stock,
                        unit=unit,
                        location=location
                    )

                    # Если есть поставщик, обновляем запись
                    if supplier:
                        self.execute_query('''
                            UPDATE warehouse SET supplier = ? 
                            WHERE component_code = ?
                        ''', (supplier, component_code))

                    imported_count += 1

                except Exception as e:
                    self.logger.warning(f"Ошибка обработки строки склада: {e}")
                    continue

            self.conn.commit()
            self.logger.info(f"Импортировано {imported_count} позиций склада из файла {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка импорта склада из Excel: {e}")
            return False

    def get_norms_count(self) -> int:
        """Получить общее количество норм в базе (алиас для get_total_norms_count)"""
        return self.get_total_norms_count()

    def get_product_by_id(self, product_id):
        """
        Получить продукт по ID

        Args:
            product_id (int): ID продукта

        Returns:
            dict: Данные продукта или None если не найден
        """
        try:
            result = self.execute_query('SELECT * FROM products WHERE id = ?', (product_id,))
            return result[0] if result else None

        except Exception as e:
            self.logger.error(f"Ошибка получения продукта по ID {product_id}: {e}")
            return None

    def get_product_recipes(self, product_id):
        """
        Получить рецептуры для продукта по его ID

        Args:
            product_id (int): ID продукта

        Returns:
            list: Список рецептур в виде словарей
        """
        try:
            self.logger.debug(f"Вызов get_product_recipes с product_id={product_id}")

            # Получаем продукт по ID, чтобы узнать его код
            product = self.get_product_by_id(product_id)
            if not product:
                self.logger.warning(f"Продукт с ID={product_id} не найден")
                return []

            product_code = product.get('product_code')
            if not product_code:
                self.logger.warning(f"У продукта с ID={product_id} нет кода")
                return []

            # Используем существующий метод get_recipes_for_product
            return self.get_recipes_for_product(product_code)

        except Exception as e:
            self.logger.error(f"Ошибка в get_product_recipes для product_id={product_id}: {e}")
            return []

    def get_recipe_components_by_codes(self, product_code: str, recipe_number: str) -> List[Dict[str, Any]]:
        """
        Получить компоненты рецептуры по коду продукта и номеру рецептуры

        Args:
            product_code (str): Код продукта
            recipe_number (str): Номер рецептуры

        Returns:
            list: Список компонентов рецептуры
        """
        try:
            # Сначала находим рецептуру
            recipe = self.get_recipe_by_number(product_code, recipe_number)
            if not recipe:
                self.logger.warning(f"Рецептура {recipe_number} для продукта {product_code} не найдена")
                return []

            # Получаем компоненты этой рецептуры
            recipe_id = recipe['id']
            return self.get_recipe_components(recipe_id)

        except Exception as e:
            self.logger.error(f"Ошибка получения компонентов рецептуры {recipe_number} для продукта {product_code}: {e}")
            return []


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()