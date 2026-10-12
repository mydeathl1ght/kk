"""
Работа с PostgreSQL.
Каждая функция открывает новое подключение и закрывает его автоматически.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG


# ============================================================
# Подключение
# ============================================================
def get_connection():
    """Возвращает новое подключение к БД."""
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# Чтение (SELECT)
# ============================================================
def fetch_all(query, params=None):
    """Возвращает все строки как список словарей."""
    return _run_read(query, params, fetch_all=True)


def fetch_one(query, params=None):
    """Возвращает одну строку как словарь."""
    return _run_read(query, params, fetch_all=False)


# ============================================================
# Запись (INSERT / UPDATE / DELETE)
# ============================================================
def execute(query, params=None):
    """Выполняет INSERT/UPDATE/DELETE. Возвращает число затронутых строк."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount


def execute_returning(query, params=None):
    """Выполняет INSERT с RETURNING. Возвращает значение первой колонки."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            row = cur.fetchone()
            return row[0] if row else None


# ============================================================
# Вспомогательные
# ============================================================
def _run_read(query, params, fetch_all: bool):
    """Общий метод для SELECT-запросов с курсором-словарём."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall() if fetch_all else cur.fetchone()