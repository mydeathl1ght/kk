"""
Просмотр состава заказа + редактирование.
Администратор может менять дату заказа и удалять позиции.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
)
from PyQt6.QtCore import Qt, QDate

from config import STYLESHEET
from db import fetch_one, fetch_all, execute
from utils.messages import show_error, show_info, confirm


# ---------- Константы ----------
ADMIN_ROLE = 'Администратор'
TITLE_STYLE = "font-size: 18px; font-weight: bold; color: #70B2AF;"
TOTAL_STYLE = "font-size: 16px; font-weight: bold;"
CLIENT_STYLE = "font-size: 14px;"

TABLE_HEADERS = ['№', 'Модель', 'Производитель', 'Размер', 'Кол-во', 'Сумма (руб.)']

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

STYLE_DANGER = """
    QPushButton {
        background-color: #d9534f;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #c9302c; }
"""

SQL_FIND_ORDER = "SELECT * FROM orders WHERE id = %s"

SQL_LOAD_ITEMS = """
    SELECT
        oi.id,
        p.name AS product_name,
        p.manufacturer,
        s.value AS size_value,
        oi.quantity,
        oi.price_at_moment,
        (oi.quantity * oi.price_at_moment) AS subtotal
    FROM order_items oi
    JOIN products p ON p.id = oi.product_id
    JOIN sizes s ON s.id = oi.size_id
    WHERE oi.order_id = %s
    ORDER BY oi.id
"""

SQL_UPDATE_DATE = "UPDATE orders SET order_date = %s WHERE id = %s"

SQL_DELETE_ITEM = "DELETE FROM order_items WHERE id = %s"


class OrderViewWindow(QDialog):
    """Состав заказа. Админ может менять дату и удалять позиции."""

    def __init__(self, order_id: int, user: dict, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.user = user
        self.is_admin = user.get('role_name') == ADMIN_ROLE

        self.setWindowTitle(f'Чудо Обувь — Заказ №{order_id}')
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_order()

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(self._make_title())
        root.addLayout(self._make_date_row())

        self.client_label = self._make_client_label()
        root.addWidget(self.client_label)

        root.addWidget(self._make_table())
        root.addWidget(self._make_total())
        root.addLayout(self._make_buttons())

    def _make_title(self) -> QLabel:
        label = QLabel(f'Заказ №{self.order_id}')
        label.setStyleSheet(TITLE_STYLE)
        return label

    def _make_date_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel('Дата заказа:'))

        field = QDateEdit()
        field.setCalendarPopup(True)
        field.setEnabled(self.is_admin)
        self.date_edit = field
        row.addWidget(field)

        row.addStretch()
        return row

    def _make_client_label(self) -> QLabel:
        label = QLabel('')
        label.setStyleSheet(CLIENT_STYLE)
        return label

    def _make_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(TABLE_HEADERS))
        table.setHorizontalHeaderLabels(TABLE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table = table
        return table

    def _make_total(self) -> QLabel:
        label = QLabel('Итого: 0.00 руб.')
        label.setStyleSheet(TOTAL_STYLE)
        label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label = label
        return label

    def _make_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        if self.is_admin:
            row.addWidget(self._make_save_button())
            row.addWidget(self._make_delete_button())

        row.addStretch()
        row.addWidget(self._make_back_button())

        return row

    def _make_save_button(self) -> QPushButton:
        button = QPushButton('Сохранить изменения')
        button.setMinimumHeight(40)
        button.clicked.connect(self._save_changes)
        return button

    def _make_delete_button(self) -> QPushButton:
        button = QPushButton('Удалить позицию')
        button.setMinimumHeight(40)
        button.setStyleSheet(STYLE_DANGER)
        button.clicked.connect(self._delete_item)
        return button

    def _make_back_button(self) -> QPushButton:
        button = QPushButton('Назад')
        button.setMinimumHeight(40)
        button.setStyleSheet(STYLE_SECONDARY)
        button.clicked.connect(self.accept)
        return button

    # ============================================================
    # Загрузка данных
    # ============================================================
    def _load_order(self):
        order = fetch_one(SQL_FIND_ORDER, (self.order_id,))
        if not order:
            show_error(self, 'Заказ не найден')
            self.reject()
            return

        self._set_date(order['order_date'])
        self._set_client(order['client_name'])
        items = self._load_items()
        self._fill_table(items)
        self._update_total(items)

    def _set_date(self, d):
        self.date_edit.setDate(QDate(d.year, d.month, d.day))

    def _set_client(self, client_name: str):
        self.client_label.setText(f"Клиент: <b>{client_name}</b>")

    def _load_items(self) -> list:
        items = fetch_all(SQL_LOAD_ITEMS, (self.order_id,))
        self.items = [dict(r) for r in items]
        return self.items

    def _fill_table(self, items: list):
        self.table.setRowCount(0)
        for idx, item in enumerate(items):
            self.table.insertRow(idx)
            self._fill_row(idx, item)

    def _fill_row(self, row: int, item: dict):
        cells = [
            str(item['id']),
            item['product_name'],
            item['manufacturer'] or '',
            str(item['size_value']),
            str(item['quantity']),
            f"{float(item['subtotal']):,.2f}".replace(',', ' '),
        ]
        for col, text in enumerate(cells):
            self.table.setItem(row, col, QTableWidgetItem(text))

    def _update_total(self, items: list):
        total = sum(float(item['subtotal']) for item in items)
        self.total_label.setText(
            f"Итого: {total:,.2f} руб.".replace(',', ' ')
        )

    # ============================================================
    # Действия администратора
    # ============================================================
    def _save_changes(self):
        if not self.is_admin:
            return
        new_date = self.date_edit.date().toPyDate()
        try:
            execute(SQL_UPDATE_DATE, (new_date, self.order_id))
            show_info(self, 'Изменения сохранены')
        except Exception as err:
            show_error(self, f'Ошибка сохранения: {err}')

    def _delete_item(self):
        if not self.is_admin:
            return

        row = self.table.currentRow()
        if row < 0:
            show_error(self, 'Выберите позицию для удаления')
            return

        item_id = self.items[row]['id']
        if not confirm(self, 'Удалить эту позицию из заказа?'):
            return

        try:
            execute(SQL_DELETE_ITEM, (item_id,))
            show_info(self, 'Позиция удалена')
            self._load_order()
        except Exception as err:
            show_error(self, f'Не удалось удалить позицию: {err}')