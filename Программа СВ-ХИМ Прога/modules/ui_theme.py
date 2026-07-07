# modules/ui_theme.py
"""
Единая тема оформления приложения — "современный минимализм".

Централизует палитру цветов и шрифты, чтобы все модули (главное окно,
редактор карт загрузки и т.д.) выглядели визуально согласованно.
Палитра построена в духе современных минималистичных интерфейсов:
приглушённые нейтральные (slate) тона + один яркий акцент (индиго).
"""

COLORS = {
    # Акцентный цвет (кнопки, активные вкладки, выделения)
    'primary': '#4F46E5',        # indigo-600
    'primary_hover': '#4338CA',  # indigo-700
    'primary_pressed': '#3730A3',  # indigo-800
    'primary_light': '#EEF2FF',  # indigo-50 (подложка выбранной вкладки/строки)

    # Нейтральный / вторичный
    'secondary': '#64748B',      # slate-500
    'secondary_hover': '#475569',  # slate-600
    'secondary_pressed': '#334155',  # slate-700

    # Статусные цвета
    'success': '#16A34A',        # green-600
    'success_hover': '#15803D',
    'success_pressed': '#166534',
    'warning': '#D97706',        # amber-600
    'warning_hover': '#B45309',
    'warning_pressed': '#92400E',
    'danger': '#DC2626',         # red-600
    'danger_hover': '#B91C1C',
    'danger_pressed': '#991B1B',
    'accent': '#7C3AED',         # violet-600 (доп. акцент для второстепенных блоков)
    'accent_hover': '#6D28D9',

    # Фон / поверхности
    'background': '#F8FAFC',     # slate-50 — фон приложения
    'surface': '#FFFFFF',        # белые "карточки"
    'surface_alt': '#F1F5F9',    # slate-100 — подложки, readonly-поля, шапки таблиц
    'dark_surface': '#0F172A',   # slate-900 — тёмная полоса (статус-бар, шапки)
    'dark_surface_alt': '#1E293B',  # slate-800

    # Текст
    'on_surface': '#0F172A',     # slate-900 — основной текст
    'on_background': '#0F172A',
    'text_muted': '#64748B',     # slate-500 — второстепенный текст
    'text_on_accent': '#FFFFFF',

    # Границы / состояния
    'border': '#E2E8F0',         # slate-200
    'border_strong': '#CBD5E1',  # slate-300
    'hover': '#F1F5F9',          # slate-100 — лёгкая подсветка при наведении
    'selected_row': '#EEF2FF',   # выделенная строка таблицы (= primary_light)
    'row_alt': '#F8FAFC',        # чередующийся фон строк (зебра)

    # Вкладки
    'tab_selected': '#4F46E5',
    'tab_unselected': '#94A3B8',  # slate-400
}

FONTS = {
    'h1': ('Segoe UI', 22, 'bold'),
    'h2': ('Segoe UI', 18, 'bold'),
    'h3': ('Segoe UI', 14, 'bold'),
    'body': ('Segoe UI', 10),
    'body_semibold': ('Segoe UI', 10, 'bold'),
    'caption': ('Segoe UI', 9),
    'small': ('Segoe UI', 8),
}

# Единый шрифт для legacy-виджетов на чистом tkinter (Label/Entry/Button),
# которые задают шрифт строкой вида ('Arial', 10, 'bold') — теперь используем
# то же семейство, что и во всём приложении.
LEGACY_FONT_FAMILY = 'Segoe UI'


def shade_color(hex_color: str, percent: float) -> str:
    """
    Осветлить/затемнить hex-цвет на percent (например, -12 — темнее на 12%,
    +12 — светлее на 12%). Используется для автоматических hover-эффектов
    у "сырых" tk-виджетов (не ttk), где нет style.map().
    """
    try:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return f'#{hex_color}' if hex_color else hex_color
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        factor = 1 + percent / 100.0
        r, g, b = (max(0, min(255, int(round(c * factor)))) for c in (r, g, b))
        return f'#{r:02x}{g:02x}{b:02x}'
    except Exception:
        return f'#{hex_color}' if not hex_color.startswith('#') else hex_color
