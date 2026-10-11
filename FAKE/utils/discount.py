"""
Расчёт скидки 25% для товаров без заказов за прошлый календарный месяц.
"""

from datetime import date, timedelta
from db import fetch_one


# ---------- Константы ----------
DISCOUNT_PERCENT = 25   # размер скидки в процентах
DEFAULT_DISCOUNT = 0    # если товар заказывали в прошлом месяце

SQL_COUNT_ORDERS_IN_PERIOD = """
    SELECT COUNT(*) AS cnt
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    WHERE oi.product_id = %s
      AND o.order_date BETWEEN %s AND %s
"""


# ============================================================
# Публичные функции
# ============================================================
def get_discount_for_product(product_id: int, reference_date: date = None) -> int:
    """
    Возвращает размер скидки в процентах:
      – 25, если за прошлый календарный месяц заказов не было
      – 0, если заказы были
    """
    period_start, period_end = _get_last_month_range(reference_date)
    orders_count = _count_orders(product_id, period_start, period_end)

    if orders_count == 0:
        return DISCOUNT_PERCENT
    return DEFAULT_DISCOUNT


def calculate_price_with_discount(price: float, discount: int) -> float:
    """Возвращает цену со скидкой, округлённую до копеек."""
    return round(price * (1 - discount / 100.0), 2)


# ============================================================
# Вспомогательные функции
# ============================================================
def _get_last_month_range(reference_date: date = None) -> tuple:
    """
    Возвращает (начало, конец) прошлого календарного месяца
    относительно reference_date (по умолчанию — сегодня).
    """
    if reference_date is None:
        reference_date = date.today()

    first_of_current = reference_date.replace(day=1)
    last_day_of_previous = first_of_current - timedelta(days=1)
    first_day_of_previous = last_day_of_previous.replace(day=1)

    return first_day_of_previous, last_day_of_previous


def _count_orders(product_id: int, period_start: date, period_end: date) -> int:
    """Считает количество заказов товара за период."""
    row = fetch_one(
        SQL_COUNT_ORDERS_IN_PERIOD,
        (product_id, period_start, period_end),
    )
    return row['cnt']