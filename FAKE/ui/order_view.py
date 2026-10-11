"""Просмотр состава заказа + редактирование (Администратор)"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit
)
from PyQt6.QtCore import Qt, QDate

from config import STYLESHEET
from db import fetch_one, fetch_all, execute
from utils.messages import show_error, show_info, confirm


class OrderViewWindow(QDialog):
    """Состав заказа. Админ может менять дату и удалять позиции."""

    def __init__(self, order_id: int, user: dict, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.user = user
        self.is_admin = user.get('role_name') == 'Администратор'

        self.setWindowTitle(f'Чудо Обувь — Заказ №{order_id}')
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_order("""
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

        if self.is_admin:
            row.addWidget(self._make_save_button())
            row.addWidget(self._make_delete_button())

        row.addStretch()
        row.addWidget(self._make_back_button())

        return row

    def _make_save_button(self) -> QPushButton:
        button = QPushButton('Сохранить изменения')
        button.clicked.connect(self._save_changes)
        return button

    def _make_delete_button(self) -> QPushButton:
        button = QPushButton('Удалить позицию')
        button.setStyleSheet(STYLE_DANGER)
        button.clicked.connect(self._delete_item)
        return button

    def _make_back_button(self) -> QPushButton:
        button = QPushButton('Назад')
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
            show_error(self, f'Не удалось удалить позицию: {err}'))

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Заголовок
        self.title_label = QLabel(f'Заказ №{self.order_id}')
        self.title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #70B2AF;"
        )
        layout.addWidget(self.title_label)

        # Дата
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel('Дата заказа:'))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setEnabled(self.is_admin)  # только админ может менять
        date_row.addWidget(self.date_edit)
        date_row.addStretch()
        layout.addLayout(date_row)

        # Клиент
        self.client_label = QLabel('')
        self.client_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.client_label)

        # Таблица позиций
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            '№', 'Модель', 'Производитель',
            'Размер', 'Кол-во', 'Сумма (руб.)'
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.table)

        # Итог
        self.total_label = QLabel('Итого: 0.00 руб.')
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.total_label)

        # Кнопки
        btns = QHBoxLayout()

        if self.is_admin:
            save_btn = QPushButton('Сохранить изменения')
            save_btn.clicked.connect(self._save_changes)
            btns.addWidget(save_btn)

            delete_item_btn = QPushButton('Удалить позицию')
            delete_item_btn.setStyleSheet(self._danger_style())
            delete_item_btn.clicked.connect(self._delete_item)
            btns.addWidget(delete_item_btn)

        btns.addStretch()

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet(self._secondary_style())
        back_btn.clicked.connect(self.accept)
        btns.addWidget(back_btn)

        layout.addLayout(btns)

    def _secondary_style(self) -> str:
        return """
            QPushButton {
                background-color: #D2F6E7;
                color: #333;
                border: 1px solid #70B2AF;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #BBEBD7; }
        """

    def _danger_style(self) -> str:
        return """
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c9302c; }
        """

    def _load_order(self):
        """Загружает данные заказа и его позиции."""
        order = fetch_one(
            "SELECT * FROM orders WHERE id = %s", (self.order_id,)
        )
        if not order:
            show_error(self, 'Заказ не найден')
            self.reject()
            return

        # Дата
        d = order['order_date']
        self.date_edit.setDate(QDate(d.year, d.month, d.day))

        # Клиент
        self.client_label.setText(f"Клиент: <b>{order['client_name']}</b>")

        # Позиции
        items = fetch_all("""
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
        """, (self.order_id,))

        self.items = [dict(r) for r in items]
        self.table.setRowCount(0)
        total = 0.0

        for i, it in enumerate(self.items):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(it['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(it['product_name']))
            self.table.setItem(i, 2, QTableWidgetItem(it['manufacturer'] or ''))
            self.table.setItem(i, 3, QTableWidgetItem(str(it['size_value'])))
            self.table.setItem(i, 4, QTableWidgetItem(str(it['quantity'])))
            self.table.setItem(
                i, 5,
                QTableWidgetItem(f"{float(it['subtotal']):,.2f}".replace(',', ' '))
            )
            total += float(it['subtotal'])

        self.total_label.setText(
            f"Итого: {total:,.2f} руб.".replace(',', ' ')
        )

    def _save_changes(self):
        """Сохраняет новую дату заказа (только Админ)."""
        if not self.is_admin:
            return

        new_date = self.date_edit.date().toPyDate()
        try:
            execute(
                "UPDATE orders SET order_date = %s WHERE id = %s",
                (new_date, self.order_id)
            )
            show_info(self, 'Изменения сохранены')
        except Exception as e:
            show_error(self, f'Ошибка сохранения: {e}')

    def _delete_item(self):
        """Удаляет выбранную позицию заказа (только Админ)."""
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
            execute("DELETE FROM order_items WHERE id = %s", (item_id,))
            show_info(self, 'Позиция удалена')
            self._load_order()  # обновить таблицу
        except Exception as e:
            show_error(self, f'Не удалось удалить позицию: {e}')