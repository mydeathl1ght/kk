"""
Форма создания нового заказа (Менеджер / Администратор).
Слева — каталог с поиском, справа — позиции заказа.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QSpinBox, QListWidget, QListWidgetItem,
    QFormLayout, QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from config import STYLESHEET
from db import fetch_all, execute, execute_returning
from utils.discount import get_discount_for_product, calculate_price_with_discount
from utils.messages import show_error, show_info, confirm


# ---------- Константы ----------
WINDOW_TITLE = 'Чудо Обувь — Новый заказ'
TITLE_TEXT = 'Создание нового заказа'
TITLE_STYLE = "font-size: 18px; font-weight: bold; color: #70B2AF;"

CART_HEADERS = ['Наименование', 'Размер', 'Кол-во', 'Цена', 'Сумма']

STYLE_SECONDARY = """
    QPushButton {
        background-color: #D2F6E7;
        color: #333;
        border: 2px solid #70B2AF;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #BBEBD7; }
"""

SQL_PRODUCTS = "SELECT id, name, manufacturer, price FROM products ORDER BY name"

SQL_SIZES_BY_PRODUCT = """
    SELECT s.id AS size_id, s.value, si.quantity_available
    FROM stock_items si
    JOIN sizes s ON s.id = si.size_id
    WHERE si.product_id = %s AND si.quantity_available > 0
    ORDER BY s.value
"""

SQL_INSERT_ORDER = """
    INSERT INTO orders (order_date, user_id, client_name)
    VALUES (CURRENT_DATE, %s, %s)
    RETURNING id
"""

SQL_DECREASE_STOCK = """
    UPDATE stock_items
    SET quantity_available = quantity_available - %s
    WHERE product_id = %s
      AND size_id = %s
      AND quantity_available >= %s
"""

SQL_INSERT_ITEM = """
    INSERT INTO order_items
        (order_id, product_id, size_id, quantity, price_at_moment)
    VALUES (%s, %s, %s, %s, %s)
"""


class NewOrderWindow(QDialog):
    """Создание нового заказа из каталога."""

    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.user = user
        self.cart = []

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_products()

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(self._make_title())
        root.addLayout(self._make_client_row())
        root.addLayout(self._make_search_row())
        root.addLayout(self._make_main_row())
        root.addLayout(self._make_bottom_buttons())

    def _make_title(self) -> QLabel:
        label = QLabel(TITLE_TEXT)
        label.setStyleSheet(TITLE_STYLE)
        return label

    def _make_client_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel('Клиент (ФИО):'))
        field = QLineEdit()
        field.setPlaceholderText('Иванов Иван Иванович')
        self.client_input = field
        row.addWidget(field, 2)
        return row

    def _make_search_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel('Поиск:'))
        field = QLineEdit()
        field.setPlaceholderText('Введите название...')
        field.textChanged.connect(self._filter_products)
        self.search_input = field
        row.addWidget(field, 1)
        return row

    def _make_main_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addLayout(self._make_products_column(), 1)
        row.addLayout(self._make_center_buttons())
        row.addLayout(self._make_cart_column(), 1)
        return row

    def _make_products_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel('Каталог:'))

        lst = QListWidget()
        lst.itemDoubleClicked.connect(self._add_product)
        self.products_list = lst
        col.addWidget(lst)
        return col

    def _make_center_buttons(self) -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(15)
    col.addStretch()

    add_btn = QPushButton('→')
    add_btn.setFixedSize(60, 60)
    add_btn.setStyleSheet("""
        QPushButton {
            background-color: #70B2AF;
            color: white;
            border: none;
            border-radius: 30px;
            font-size: 20px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #5a9a97; }
    """)
    add_btn.clicked.connect(self._add_product)
    col.addWidget(add_btn)

    remove_btn = QPushButton('←')
    remove_btn.setFixedSize(60, 60)
    remove_btn.setStyleSheet("""
        QPushButton {
            background-color: #D2F6E7;
            color: #333;
            border: 2px solid #70B2AF;
            border-radius: 30px;
            font-size: 20px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #BBEBD7; }
    """)
    remove_btn.clicked.connect(self._remove_item)
    col.addWidget(remove_btn)

    col.addStretch()
    return col

    def _make_cart_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel('Позиции заказа:'))

        table = QTableWidget()
        table.setColumnCount(len(CART_HEADERS))
        table.setHorizontalHeaderLabels(CART_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cart_table = table
        col.addWidget(table)

        total = QLabel('Итого: 0.00 руб.')
        total.setStyleSheet("font-size: 14px; font-weight: bold;")
        total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label = total
        col.addWidget(total)
        return col

    def _make_bottom_buttons(self) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)

    save_btn = QPushButton('Сохранить заказ')
    save_btn.setMinimumHeight(45)
    save_btn.clicked.connect(self._save_order)
    row.addWidget(save_btn)

    cancel_btn = QPushButton('Отмена')
    cancel_btn.setMinimumHeight(45)
    cancel_btn.setStyleSheet(STYLE_SECONDARY)
    cancel_btn.clicked.connect(self.reject)
    row.addWidget(cancel_btn)

    return row
    # ============================================================
    # Загрузка и фильтрация товаров
    # ============================================================
    def _load_products(self):
        self.all_products = [dict(r) for r in fetch_all(SQL_PRODUCTS)]
        self._filter_products()

    def _filter_products(self):
        query = self.search_input.text().strip().lower()
        self.products_list.clear()

        for product in self.all_products:
            if query and query not in product['name'].lower():
                continue
            self._add_to_list(product)

    def _add_to_list(self, product: dict):
        item = QListWidgetItem(
            f"{product['manufacturer']} | {product['name']}"
        )
        item.setData(Qt.ItemDataRole.UserRole, product)
        self.products_list.addItem(item)

    # ============================================================
    # Добавление позиции в заказ
    # ============================================================
    def _add_product(self):
        current = self.products_list.currentItem()
        if not current:
            show_error(self, 'Выберите товар из каталога')
            return

        product = current.data(Qt.ItemDataRole.UserRole)
        sizes = fetch_all(SQL_SIZES_BY_PRODUCT, (product['id'],))

        if not sizes:
            show_error(self, f"Товар «{product['name']}» нет в наличии")
            return

        chosen = self._ask_size_and_qty(sizes)
        if chosen is None:
            return

        size_id, size_value, qty = chosen
        price = self._final_price(product)

        self.cart.append({
            'product_id': product['id'],
            'name': product['name'],
            'size_id': size_id,
            'size_value': size_value,
            'quantity': qty,
            'price': price,
        })
        self._refresh_cart()

    def _ask_size_and_qty(self, sizes: list):
        """
        Показывает диалог выбора размера и количества.
        Возвращает (size_id, size_value, qty) или None.
        """
        dlg = self._make_size_dialog(sizes)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None

        size_id, available, size_value = dlg.size_combo.currentData()
        qty = dlg.qty_spin.value()

        if qty <= 0 or qty > available:
            show_error(self, f'Количество должно быть от 1 до {available}')
            return None

        return size_id, size_value, qty

    def _make_size_dialog(self, sizes: list) -> QDialog:
        """Создаёт диалог выбора размера и количества."""
        dlg = QDialog(self)
        dlg.setWindowTitle('Выбор размера и количества')
        dlg.setStyleSheet(STYLESHEET)

        form = QFormLayout(dlg)

        size_combo = QComboBox()
        for s in sizes:
            size_combo.addItem(
                f"{s['value']} (доступно: {s['quantity_available']})",
                (s['size_id'], s['quantity_available'], s['value']),
            )
        form.addRow('Размер:', size_combo)

        qty_spin = QSpinBox()
        qty_spin.setMinimum(1)
        qty_spin.setMaximum(sizes[0]['quantity_available'])
        form.addRow('Количество:', qty_spin)

        size_combo.currentIndexChanged.connect(
            lambda: self._update_qty_max(size_combo, qty_spin)
        )

        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        bbox.accepted.connect(dlg.accept)
        bbox.rejected.connect(dlg.reject)
        form.addRow(bbox)

        dlg.size_combo = size_combo
        dlg.qty_spin = qty_spin
        return dlg

    def _update_qty_max(self, combo: QComboBox, spin: QSpinBox):
        data = combo.currentData()
        if data:
            spin.setMaximum(data[1])

    def _final_price(self, product: dict) -> float:
        discount = get_discount_for_product(product['id'])
        return calculate_price_with_discount(float(product['price']), discount)

    # ============================================================
    # Работа с корзиной
    # ============================================================
    def _remove_item(self):
        row = self.cart_table.currentRow()
        if row < 0:
            show_error(self, 'Выберите позицию в заказе')
            return
        self.cart.pop(row)
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_table.setRowCount(0)
        total = 0.0

        for idx, item in enumerate(self.cart):
            subtotal = item['price'] * item['quantity']
            total += subtotal
            self.cart_table.insertRow(idx)
            self._fill_cart_row(idx, item, subtotal)

        self.total_label.setText(
            f"Итого: {total:,.2f} руб.".replace(',', ' ')
        )

    def _fill_cart_row(self, row: int, item: dict, subtotal: float):
        cells = [
            item['name'],
            str(item['size_value']),
            str(item['quantity']),
            f"{item['price']:.2f}",
            f"{subtotal:.2f}",
        ]
        for col, text in enumerate(cells):
            self.cart_table.setItem(row, col, QTableWidgetItem(text))

    # ============================================================
    # Сохранение заказа
    # ============================================================
    def _save_order(self):
        if not self._validate():
            return
        if not confirm(self, 'Сохранить заказ?'):
            return

        try:
            order_id = self._save_to_db()
            show_info(self, f'Заказ №{order_id} создан')
            self.accept()
        except Exception as err:
            show_error(self, f'Не удалось создать заказ:\n{err}')

    def _validate(self) -> bool:
        if not self.client_input.text().strip():
            show_error(self, 'Введите ФИО клиента')
            return False
        if not self.cart:
            show_error(self, 'Добавьте товары в заказ')
            return False
        return True

    def _save_to_db(self) -> int:
        """Создаёт заказ и позиции, возвращает order_id."""
        client = self.client_input.text().strip()

        order_id = execute_returning(
            SQL_INSERT_ORDER, (self.user['id'], client)
        )

        for item in self.cart:
            self._decrease_stock(item)
            self._insert_item(order_id, item)

        return order_id

    def _decrease_stock(self, item: dict):
        affected = execute(SQL_DECREASE_STOCK, (
            item['quantity'], item['product_id'],
            item['size_id'], item['quantity'],
        ))
        if affected == 0:
            raise Exception(
                f"Недостаточно товара: {item['name']} (размер {item['size_value']})"
            )

    def _insert_item(self, order_id: int, item: dict):
        execute(SQL_INSERT_ITEM, (
            order_id, item['product_id'], item['size_id'],
            item['quantity'], item['price'],
        ))