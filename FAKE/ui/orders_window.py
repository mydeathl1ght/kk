"""
Окно списка заказов.
Доступно Менеджеру и Администратору.
Позволяет открыть, создать и удалить заказ.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

from config import STYLESHEET
from db import fetch_all, execute
from utils.messages import show_error, show_info, confirm


# ---------- Константы ----------
WINDOW_TITLE = 'Чудо Обувь — Управление заказами'
TITLE_TEXT = 'Список заказов'
TITLE_STYLE = "font-size: 18px; font-weight: bold; color: #70B2AF;"

TABLE_HEADERS = ['№', 'Дата заказа', 'Клиент', 'Сумма (руб.)']

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

SQL_LOAD_ORDERS = """
    SELECT
        o.id,
        o.order_date,
        o.client_name,
        COALESCE(SUM(oi.quantity * oi.price_at_moment), 0) AS total
    FROM orders o
    LEFT JOIN order_items oi ON oi.order_id = o.id
    GROUP BY o.id
    ORDER BY o.order_date DESC, o.id DESC
"""

SQL_DELETE_ORDER = "DELETE FROM orders WHERE id = %s"


class OrdersWindow(QDialog):
    """Список всех заказов. Менеджер/Админ могут открывать, создавать, удалять."""

    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.user = user

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_orders()

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(self._make_title())
        root.addWidget(self._make_table())
        root.addLayout(self._make_buttons())

    def _make_title(self) -> QLabel:
        label = QLabel(TITLE_TEXT)
        label.setStyleSheet(TITLE_STYLE)
        return label

    def _make_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(TABLE_HEADERS))
        table.setHorizontalHeaderLabels(TABLE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.doubleClicked.connect(self._open_order)
        self.table = table
        return table

    def _make_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()

        open_btn = QPushButton('Открыть заказ')
        open_btn.clicked.connect(self._open_order)
        row.addWidget(open_btn)

        create_btn = QPushButton('Создать заказ')
        create_btn.clicked.connect(self._create_order)
        row.addWidget(create_btn)

        delete_btn = QPushButton('Удалить заказ')
        delete_btn.setStyleSheet(STYLE_DANGER)
        delete_btn.clicked.connect(self._delete_order)
        row.addWidget(delete_btn)

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet(STYLE_SECONDARY)
        back_btn.clicked.connect(self.reject)
        row.addWidget(back_btn)

        return row

    # ============================================================
    # Загрузка и отрисовка списка
    # ============================================================
    def _load_orders(self):
        rows = fetch_all(SQL_LOAD_ORDERS)
        self.orders = [dict(r) for r in rows]
        self.table.setRowCount(0)

        for idx, order in enumerate(self.orders):
            self.table.insertRow(idx)
            self._fill_row(idx, order)

    def _fill_row(self, row: int, order: dict):
        cells = [
            str(order['id']),
            str(order['order_date']),
            order['client_name'],
            f"{float(order['total']):,.2f}".replace(',', ' '),
        ]
        for col, text in enumerate(cells):
            self.table.setItem(row, col, QTableWidgetItem(text))

    # ============================================================
    # Получение выбранного заказа
    # ============================================================
    def _get_selected_order_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.orders[row]['id']

    # ============================================================
    # Действия
    # ============================================================
    def _open_order(self):
        order_id = self._get_selected_order_id()
        if order_id is None:
            show_error(self, 'Выберите заказ')
            return

        from ui.order_view import OrderViewWindow
        dialog = OrderViewWindow(
            order_id=order_id,
            user=self.user,
            parent=self,
        )
        dialog.exec()
        self._load_orders()

    def _create_order(self):
        from ui.new_order_window import NewOrderWindow
        dialog = NewOrderWindow(user=self.user, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._load_orders()

    def _delete_order(self):
        order_id = self._get_selected_order_id()
        if order_id is None:
            show_error(self, 'Выберите заказ для удаления')
            return

        text = f'Удалить заказ №{order_id}?\nЭто действие необратимо.'
        if not confirm(self, text):
            return

        try:
            # ON DELETE CASCADE автоматически удалит позиции заказа
            execute(SQL_DELETE_ORDER, (order_id,))
            show_info(self, f'Заказ №{order_id} удалён')
            self._load_orders()
        except Exception as err:
            show_error(self, f'Не удалось удалить заказ:\n{err}')