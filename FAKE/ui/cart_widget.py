"""
Окно корзины и оформления заказа.
Показывает текущие позиции, позволяет удалять/очищать
и сохраняет заказ в БД (с проверкой остатков).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

from config import STYLESHEET
from db import execute, execute_returning
from utils.messages import show_error, show_info, confirm, show_warning


# ---------- Константы ----------
TITLE_TEXT = 'Корзина и оформление заказа'
TABLE_HEADERS = ['ID', 'Наименование', 'Производитель', 'Размер', 'Кол-во', 'Сумма (руб.)']

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


# ---------- Стили кнопок ----------
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


class CartWindow(QDialog):
    """Окно корзины. Оформляет заказ в БД."""

    def __init__(self, user: dict, cart: list, parent=None):
        super().__init__(parent)
        self.user = user
        self.cart = cart

        self.setWindowTitle('Чудо Обувь — Корзина')
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._refresh_table()

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(self._make_title())
        root.addWidget(self._make_table())
        root.addWidget(self._make_total())
        root.addLayout(self._make_buttons())

    def _make_title(self) -> QLabel:
        label = QLabel(TITLE_TEXT)
        label.setStyleSheet("font-size: 18px; font-weight: bold; color: #70B2AF;")
        return label

    def _make_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(TABLE_HEADERS))
        table.setHorizontalHeaderLabels(TABLE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table = table
        return table

    def _make_total(self) -> QLabel:
        label = QLabel('Итого к оплате: 0.00 руб.')
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label = label
        return label

    def _make_buttons(self) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)  # ← добавь
    # ... остальное как было

        remove_btn = QPushButton('Удалить позицию')
        remove_btn.clicked.connect(self._remove_selected)
        row.addWidget(remove_btn)

        clear_btn = QPushButton('Очистить')
        clear_btn.setStyleSheet(STYLE_SECONDARY)
        clear_btn.clicked.connect(self._clear_cart)
        row.addWidget(clear_btn)

        checkout_btn = QPushButton('Оформить заказ')
        checkout_btn.clicked.connect(self._checkout)
        row.addWidget(checkout_btn)

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet(STYLE_SECONDARY)
        back_btn.clicked.connect(self.reject)
        row.addWidget(back_btn)

        return row

    # ============================================================
    # Работа с таблицей
    # ============================================================
    def _refresh_table(self):
        """Перерисовывает таблицу и пересчитывает итог."""
        self.table.setRowCount(0)
        total = 0.0

        for idx, item in enumerate(self.cart):
            subtotal = item['price'] * item['quantity']
            total += subtotal

            self.table.insertRow(idx)
            self._fill_row(idx, item, subtotal)

        self.total_label.setText(
            f"Итого к оплате: {total:,.2f} руб.".replace(',', ' ')
        )

    def _fill_row(self, row: int, item: dict, subtotal: float):
        """Заполняет одну строку таблицы."""
        cells = [
            str(item['product_id']),
            item['name'],
            item.get('manufacturer', ''),
            str(item['size_value']),
            str(item['quantity']),
            f"{subtotal:.2f}",
        ]
        for col, text in enumerate(cells):
            self.table.setItem(row, col, QTableWidgetItem(text))

    # ============================================================
    # Действия с корзиной
    # ============================================================
    def _remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            show_warning(self, 'Выберите строку для удаления')
            return
        self.cart.pop(row)
        self._refresh_table()

    def _clear_cart(self):
        if not self.cart:
            return
        if not confirm(self, 'Очистить всю корзину?'):
            return
        self.cart.clear()
        self._refresh_table()

    # ============================================================
    # Оформление заказа
    # ============================================================
    def _checkout(self):
        if not self._can_checkout():
            return
        if not confirm(self, 'Оформить заказ?'):
            return

        try:
            order_id = self._save_order()
            show_info(self, f'Заказ №{order_id} успешно оформлен!')
            self.cart.clear()
            self.accept()
        except Exception as err:
            show_error(self, f'Не удалось оформить заказ:\n{err}')

    def _can_checkout(self) -> bool:
        """Проверки перед оформлением."""
        if not self.cart:
            show_error(self, 'Корзина пуста')
            return False
        if not self.user or not self.user.get('id'):
            show_error(self, 'Для оформления заказа нужна авторизация')
            return False
        return True

    def _save_order(self) -> int:
        """Создаёт заказ и позиции, возвращает order_id."""
        # 1) Заказ
        order_id = execute_returning(
            SQL_INSERT_ORDER,
            (self.user['id'], self.user['full_name']),
        )

        # 2) Позиции + уменьшение остатков
        for item in self.cart:
            self._decrease_stock(item)
            self._insert_item(order_id, item)

        return order_id

    def _decrease_stock(self, item: dict):
        """Уменьшает остаток. Бросает исключение, если не хватает."""
        affected = execute(
            SQL_DECREASE_STOCK,
            (item['quantity'], item['product_id'],
             item['size_id'], item['quantity']),
        )
        if affected == 0:
            raise Exception(
                f"Недостаточно товара: {item['name']} (размер {item['size_value']})"
            )

    def _insert_item(self, order_id: int, item: dict):
        """Сохраняет одну позицию заказа."""
        execute(
            SQL_INSERT_ITEM,
            (order_id, item['product_id'], item['size_id'],
             item['quantity'], item['price']),
        )