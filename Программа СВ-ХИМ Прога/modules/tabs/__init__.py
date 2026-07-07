# Инициализация модуля вкладок
from .home_tab import HomeTab
from .cards_tab import CardsTab
from .warehouse_tab import WarehouseTab
from .products_tab import ProductsTab
from .logs_tab import LogsTab
from .import_export_tab import ImportExportTab

__all__ = [
    'HomeTab',
    'CardsTab',
    'WarehouseTab',
    'ProductsTab',
    'LogsTab',
    'ImportExportTab'
]