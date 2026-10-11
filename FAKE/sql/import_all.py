"""
Загрузка справочников и заказов в БД «Чудо Обувь».
Читаем xlsx через openpyxl, пишем в PostgreSQL через psycopg2.
Запуск: python3 sql/import_all.py
"""

import os
import sys
import openpyxl
import psycopg2

# Чтобы можно было импортировать config из корня проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, DATA_DIR


# ---------- Константы ----------
# Все «хитрые» пробелы, которые могут встретиться в Excel.
# Неразрывный (\xa0), узкий (\u2009), тонкий (\u202f) и т.п.
SPACE_CHARS = ['\xa0', '\u2009', '\u202f', '\t', '\u200b', '\u2007', '\u2008']

SQL_INSERT_SIZE = """
    INSERT INTO sizes (value)
    VALUES (%s)
    ON CONFLICT (value) DO NOTHING
"""

SQL_INSERT_PRODUCT = """
    INSERT INTO products
        (category, subcategory, name, manufacturer,
         image_path, description, composition, price)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

SQL_FIND_ROLE = "SELECT id FROM roles WHERE name = %s"

SQL_INSERT_USER = """
    INSERT INTO users
        (last_name, first_name, middle_name, login, role_id)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (login) DO NOTHING
"""

SQL_FIND_PRODUCT = "SELECT id, name, manufacturer FROM products"

SQL_FIND_SIZE = "SELECT id FROM sizes WHERE value = %s"

SQL_UPSERT_STOCK = """
    INSERT INTO stock_items
        (product_id, size_id, quantity_available)
    VALUES (%s, %s, %s)
    ON CONFLICT (product_id, size_id)
    DO UPDATE SET quantity_available = EXCLUDED.quantity_available
"""

SQL_FIND_USER_BY_FIO = """
    SELECT id FROM users
    WHERE TRIM(last_name || ' ' || first_name || ' ' || COALESCE(middle_name, '')) = %s
    LIMIT 1
"""

SQL_INSERT_ORDER = """
    INSERT INTO orders (order_date, user_id, client_name)
    VALUES (%s, %s, %s)
    RETURNING id
"""

SQL_INSERT_ORDER_ITEM = """
    INSERT INTO order_items
        (order_id, product_id, size_id, quantity, price_at_moment)
    VALUES (%s, %s, %s, %s, %s)
"""


# ============================================================
# Вспомогательные функции
# ============================================================
def normalize(text):
    """
    Приводит строку к «чистому» виду:
      – все виды пробелов → обычный пробел
      – множественные пробелы → один
      – нижний регистр
    """
    if text is None:
        return ''
    s = str(text)
    for ch in SPACE_CHARS:
        s = s.replace(ch, ' ')
    return ' '.join(s.split()).strip().lower()


def read_xlsx(filename):
    """Читает xlsx из data/, возвращает строки без заголовка."""
    full_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Нет файла: {full_path}")

    wb = openpyxl.load_workbook(full_path, read_only=True, data_only=True)
    ws = wb.active
    data = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()

    # Пустые строки пропускаем
    return [r for r in data if r[0] is not None]


def find_product_id(cur, name, manufacturer):
    """
    Ищет товар по названию (с учётом нормализации).
    Возвращает id или None.

    Пять попыток — от строгого совпадения до подстроки:
      1) name + manufacturer (точно)
      2) name (точно)
      3) products.name начинается с name
      4) name входит в products.name
      5) products.name входит в name
    """
    if name is None:
        return None

    n_name = normalize(name)
    n_manuf = normalize(manufacturer)

    cur.execute(SQL_FIND_PRODUCT)
    products = cur.fetchall()

    # 1) Точное совпадение имени и производителя
    for pid, pname, pmanuf in products:
        if normalize(pname) == n_name and normalize(pmanuf) == n_manuf:
            return pid

    # 2) Точное совпадение только имени
    for pid, pname, _ in products:
        if normalize(pname) == n_name:
            return pid

    # 3) products.name начинается с name
    for pid, pname, _ in products:
        if normalize(pname).startswith(n_name):
            return pid

    # 4) name входит в products.name
    for pid, pname, _ in products:
        if n_name in normalize(pname):
            return pid

    # 5) products.name входит в name
    for pid, pname, _ in products:
        norm_p = normalize(pname)
        if norm_p and norm_p in n_name:
            return pid

    return None


def find_size_id(cur, value):
    """Возвращает id размера или None."""
    if value is None:
        return None
    try:
        raw = str(value).replace(',', '.').strip() if isinstance(value, str) else value
        num = float(raw)
    except (ValueError, TypeError):
        return None

    cur.execute(SQL_FIND_SIZE, (num,))
    row = cur.fetchone()
    return row[0] if row else None


# ============================================================
# 1. Размеры
# ============================================================
def import_sizes(cur):
    rows = read_xlsx('Sizes_import.xlsx')
    added = 0
    processed = set()

    for row in rows:
        raw = row[0]
        try:
            num = float(str(raw).replace(',', '.').strip())
        except (ValueError, TypeError):
            continue

        if num in processed:
            continue
        processed.add(num)

        cur.execute(SQL_INSERT_SIZE, (num,))
        if cur.rowcount > 0:
            added += 1

    print(f"  Sizes: {added}")


# ============================================================
# 2. Товары
# ============================================================
def import_products(cur):
    rows = read_xlsx('Products_import.xlsx')
    added = 0

    for row in rows:
        if row[3] is None:
            continue

        cur.execute(SQL_INSERT_PRODUCT, (
            _clean(row[0]),
            _clean(row[1]),
            _clean(row[3]),
            _clean(row[4]),
            _clean(row[2]),   # image_path
            _clean(row[5]),
            _clean(row[6]),
            float(row[7]) if row[7] is not None else 0,
        ))
        added += 1

    print(f"  Products: {added}")


def _clean(value):
    """Приводит ячейку xlsx к строке или None."""
    if value is None:
        return None
    return str(value).strip()


# ============================================================
# 3. Пользователи
# ============================================================
def import_users(cur):
    rows = read_xlsx('Users_import.xlsx')
    added = 0
    skipped = 0

    for row in rows:
        if row[3] is None:
            continue

        cur.execute(SQL_FIND_ROLE, (str(row[4]).strip(),))
        role = cur.fetchone()
        if not role:
            skipped += 1
            print(f"    ⚠️  Роль не найдена: {row[4]!r}")
            continue

        cur.execute(SQL_INSERT_USER, (
            _clean(row[0]),
            _clean(row[1]),
            _clean(row[2]),
            _clean(row[3]),
            role[0],
        ))
        if cur.rowcount > 0:
            added += 1

    print(f"  Users: {added} (пропущено: {skipped})")


# ============================================================
# 4. Остатки
# ============================================================
def import_stock_items(cur):
    rows = read_xlsx('Stock_Items_import.xlsx')
    added = 0
    skipped = 0

    for row in rows:
        if row[0] is None:
            continue

        pid = find_product_id(cur, row[0], row[1])
        if not pid:
            skipped += 1
            print(f"    ⚠️  Товар не найден: {row[0]!r} / {row[1]!r}")
            continue

        sid = find_size_id(cur, row[2])
        if not sid:
            skipped += 1
            print(f"    ⚠️  Размер не найден: {row[2]!r}")
            continue

        cur.execute(SQL_UPSERT_STOCK, (pid, sid, int(row[3])))
        added += 1

    print(f"  Stock_Items: {added} (пропущено: {skipped})")


# ============================================================
# 5. Заказы и позиции
# ============================================================
def import_orders(cur):
    rows = read_xlsx('Orders_import.xlsx')

    # Группируем строки по номеру заказа
    grouped = {}
    for r in rows:
        num = r[0]
        grouped.setdefault(num, {'header': r, 'items': []})
        grouped[num]['items'].append(r)

    orders_added = 0
    items_added = 0
    skipped = 0

    for _, data in grouped.items():
        header = data['header']
        order_date = header[1]
        fio = str(header[2]).strip()

        # 1) Ищем пользователя по ФИО
        cur.execute(SQL_FIND_USER_BY_FIO, (fio,))
        user = cur.fetchone()
        uid = user[0] if user else 1

        # 2) Создаём заказ
        cur.execute(SQL_INSERT_ORDER, (order_date, uid, fio))
        order_id = cur.fetchone()[0]
        orders_added += 1

        # 3) Позиции заказа
        for it in data['items']:
            pid = find_product_id(cur, it[4], it[5])
            if not pid:
                skipped += 1
                print(f"    ⚠️  Товар не найден: {it[4]!r} / {it[5]!r}")
                continue

            sid = find_size_id(cur, it[6])
            if not sid:
                skipped += 1
                print(f"    ⚠️  Размер не найден: {it[6]!r}")
                continue

            cur.execute(SQL_INSERT_ORDER_ITEM, (
                order_id, pid, sid, int(it[7]), float(it[8]),
            ))
            items_added += 1

    print(f"  Orders: {orders_added}")
    print(f"  Order_Items: {items_added} (пропущено: {skipped})")


# ============================================================
# MAIN
# ============================================================
def main():
    line = "=" * 60
    print(line)
    print("Импорт данных в БД Чудо Обувь")
    print(line)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        print("\n[1/5] Размеры...")
        import_sizes(cur)

        print("\n[2/5] Товары...")
        import_products(cur)

        print("\n[3/5] Пользователи...")
        import_users(cur)

        print("\n[4/5] Остатки...")
        import_stock_items(cur)

        print("\n[5/5] Заказы...")
        import_orders(cur)

        conn.commit()
        print("\n" + line)
        print("🎉 Готово!")
        print(line)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()