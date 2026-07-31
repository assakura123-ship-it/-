# modules/finished_product_requirement.py
"""
Расчёт потребности компонентов на готовую продукцию.

Источники:
- файл спецификаций (рецептур) готовой продукции (Excel) с компонентами/процентами;
- файл склада (Excel) с остатками компонентов (полуфабрикаты, картон, крышки и т.д.).

Результат:
- дерево потребности по каждому компоненту,
- детализация по готовой продукции,
- сравнение со складом и дефицит,
- экспорт в Excel.
"""

import math
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import pandas as pd


def load_recipes_from_excel(file_path: str) -> List[Dict]:
    """Загрузить рецептуры готовой продукции из Excel."""
    df = pd.read_excel(file_path)

    rename_map = {}
    for col in df.columns:
        clean = col.strip().lower()
        if 'код продукта' in clean or 'код готовой продукции' in clean:
            rename_map[col] = 'code_product'
        elif 'наименование' in clean and 'компонент' not in clean and 'норма' not in clean:
            rename_map[col] = 'name_product'
        elif 'номер рц' in clean or 'номер рц' in clean:
            rename_map[col] = 'rc_number'
        elif 'код компонента' in clean or 'код п/ф' in clean or 'код полуфабриката' in clean:
            rename_map[col] = 'code_component'
        elif 'компонент' in clean and 'код' not in clean:
            rename_map[col] = 'name_component'
        elif 'процент' in clean:
            rename_map[col] = 'percent'

    df.rename(columns=rename_map, inplace=True)

    required = ['code_product', 'name_product', 'code_component', 'percent']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"В файле спецификаций не найден обязательный столбец: {col}")

    recipes = []
    grouped = df.groupby(['code_product', 'name_product'])
    for (code, name), group in grouped:
        components = {}
        rc_number = ''
        for _, row in group.iterrows():
            if not rc_number and 'rc_number' in row and not pd.isna(row['rc_number']):
                rc_number = str(row['rc_number']).strip()
            percent_val = row['percent']
            if pd.isna(percent_val):
                continue
            try:
                percent = float(percent_val)
            except (ValueError, TypeError):
                continue
            if percent <= 0:
                continue
            comp_code = str(row['code_component']).strip() if not pd.isna(row['code_component']) else ''
            if not comp_code:
                continue
            components[comp_code] = percent / 100.0

        if not components:
            continue

        total = sum(components.values())
        if abs(total - 1.0) > 0.01:
            print(f"ВНИМАНИЕ: Сумма долей для {code} ({name}) = {total:.3f}")

        recipes.append({
            'code': str(code).strip(),
            'name': str(name).strip(),
            'rc_number': rc_number,
            'components': components
        })

    return recipes


def load_inventory_from_excel(file_path: str) -> Tuple[Dict[str, float], List[Dict], pd.DataFrame]:
    """Загрузить остатки склада из Excel."""
    df = pd.read_excel(file_path)
    original_df = df.copy()

    rename_map = {}
    for col in df.columns:
        clean = col.strip().lower()
        if 'код компонента' in clean or 'код п/ф' in clean or 'код полуфабриката' in clean:
            rename_map[col] = 'code_component'
        elif 'конечный остаток' in clean:
            rename_map[col] = 'ending_stock'
        elif 'начальный остаток' in clean:
            rename_map[col] = 'start_stock'
        elif 'приход' in clean:
            rename_map[col] = 'income'
        elif 'расход' in clean:
            rename_map[col] = 'expense'
        elif 'место хранения' in clean:
            rename_map[col] = 'location'
        elif 'компонент' in clean and 'код' not in clean:
            rename_map[col] = 'name_component'

    df.rename(columns=rename_map, inplace=True)

    if 'code_component' not in df.columns or 'ending_stock' not in df.columns:
        raise ValueError("В файле склада не найдены столбцы 'Код компонента' и 'Конечный остаток'")

    summary = {}
    details = []
    for _, row in df.iterrows():
        code = str(row['code_component']).strip() if not pd.isna(row['code_component']) else ''
        if not code:
            continue

        name = str(row.get('name_component', '')).strip() if not pd.isna(row.get('name_component')) else ''
        location = str(row.get('location', '')).strip() if 'location' in df.columns and not pd.isna(row.get('location')) else ''
        start = float(row.get('start_stock', 0)) if not pd.isna(row.get('start_stock')) else 0.0
        income = float(row.get('income', 0)) if not pd.isna(row.get('income')) else 0.0
        expense = float(row.get('expense', 0)) if not pd.isna(row.get('expense')) else 0.0
        ending = float(row['ending_stock']) if not pd.isna(row['ending_stock']) else 0.0

        details.append({
            'code': code,
            'name': name,
            'location': location,
            'start': start,
            'income': income,
            'expense': expense,
            'ending': ending
        })
        summary[code] = summary.get(code, 0.0) + ending

    return summary, details, original_df


def calculate_max_units(recipe: Dict, inventory_summary: Dict[str, float]) -> int:
    """Сколько единиц готовой продукции можно произвести по текущему складу."""
    possible = []
    for comp, need_per_unit in recipe['components'].items():
        if need_per_unit <= 0 or math.isnan(need_per_unit):
            continue
        stock = inventory_summary.get(comp, 0.0)
        possible.append(int(stock // need_per_unit))
    return min(possible) if possible else 0


def enrich_recipes_with_availability(recipes: List[Dict], inventory_summary: Dict[str, float]) -> List[Dict]:
    """Дополнить рецепты полем max_units."""
    result = []
    for r in recipes:
        r_copy = r.copy()
        r_copy['max_units'] = calculate_max_units(r, inventory_summary) if inventory_summary else 0
        result.append(r_copy)
    return result


def calculate_requirements(cart: List[Dict], inventory_summary: Dict[str, float],
                           inventory_details: List[Dict]) -> Dict[str, Dict]:
    """
    Рассчитать потребность компонентов по корзине готовой продукции.

    cart: список {'recipe': {...}, 'qty': int}
    Возвращает словарь {code_component: {'name': ..., 'total': ..., 'details': [...]}}
    """
    req = defaultdict(lambda: {'name': '', 'total': 0.0, 'details': []})

    for item in cart:
        rec = item['recipe']
        qty = item['qty']
        for comp_code, need_per_unit in rec['components'].items():
            need = need_per_unit * qty
            data = req[comp_code]
            data['total'] += need
            data['details'].append({
                'recipe_code': rec['code'],
                'recipe_name': rec['name'],
                'recipe_rc': rec.get('rc_number', ''),
                'qty_recipe': qty,
                'need': need
            })

    for comp_code in req:
        for det in inventory_details:
            if det['code'] == comp_code:
                req[comp_code]['name'] = det['name']
                break

    return dict(req)


def export_requirements_to_excel(req: Dict[str, Dict], inventory_summary: Dict[str, float],
                                 output_path: str) -> None:
    """Экспортировать потребность в Excel."""
    rows = []
    for comp_code, data in req.items():
        stock = inventory_summary.get(comp_code, 0.0) if inventory_summary else 0.0
        deficit = data['total'] - stock
        rows.append([
            comp_code,
            data['name'],
            'Сумма',
            round(data['total'], 2),
            round(stock, 2),
            round(deficit, 2) if deficit > 0 else 0.0
        ])
        for det in data['details']:
            rows.append([
                comp_code,
                data['name'],
                f"{det['recipe_code']} {det['recipe_name']} (x{det['qty_recipe']})",
                round(det['need'], 2),
                '',
                ''
            ])

    df = pd.DataFrame(
        rows,
        columns=['Код компонента', 'Наименование', 'Готовая продукция', 'Требуется', 'На складе', 'Дефицит']
    )
    df.to_excel(output_path, index=False)


def produce(recipe: Dict, units: int, inventory_summary: Dict[str, float],
            inventory_details: List[Dict]) -> Tuple[Dict[str, float], List[Dict]]:
    """
    Списать компоненты со склада по рецепту и количеству.
    Возвращает (new_summary, new_details).
    """
    new_summary = inventory_summary.copy()
    for comp, need in recipe['components'].items():
        if comp in new_summary:
            new_summary[comp] -= need * units

    old_ending_by_code = {}
    for det in inventory_details:
        code = det['code']
        old_ending_by_code[code] = old_ending_by_code.get(code, 0.0) + det['ending']

    new_details = []
    for det in inventory_details:
        new_det = det.copy()
        code = new_det['code']
        if code in new_summary:
            old_total = old_ending_by_code.get(code, 0.0)
            if old_total > 0:
                ratio = new_det['ending'] / old_total
                new_det['ending'] = new_summary[code] * ratio
            else:
                new_det['ending'] = 0.0
        new_details.append(new_det)

    return new_summary, new_details
