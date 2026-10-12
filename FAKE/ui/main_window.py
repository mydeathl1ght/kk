"""
Главное окно — каталог товаров.
Отображает карточки, фильтры, поиск, сортировку;
управляет переходами в корзину и заказы.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QLineEdit, QComboBox, QPushButton,
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from config import RESOURCES_DIR, STYLESHEET
from db import fetch_all
from ui.product_card import ProductCard
from utils.discount import get_discount_for_product


# ---------- Константы ----------
WINDOW_TITLE = 'Чудо Обувь — Каталог'
ADMIN_ROLES = ('Администратор', 'Менеджер')

SORT_NONE = 'Без сортировки'
SORT_ASC = 'Цена ↑'
SORT_DESC = 'Цена ↓'
SORT_OPTIONS = [SORT_NONE, SORT_ASC, SORT_DESC]

CATEGORY_ALL = 'Все категории'

SQL_LOAD_PRODUCTS = """
    SELECT p.*, COALESCE(SUM(si.quantity_available), 0) AS total_quantity
    FROM products p
    LEFT JOIN stock_items si ON si.product_id = p.id
    GROUP BY p.id
    ORDER BY p.name
"""


class MainWindow(QMainWindow):
    """Главное окно приложения: каталог товаров."""

    def __init__(self, user: dict = None):
        super().__init__()
        self.user = user
        self.cart = []

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1200, 800)
        self.setStyleSheet(STYLESHEET)
        self._set_icon()

        self._build_ui()
        self._load_products()

    # ============================================================
    # Окно и иконка
    # ============================================================
    def _set_icon(self):
        icon_path = os.path.join(RESOURCES_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._make_header())
        root.addWidget(self._make_filter_panel())
        root.addWidget(self._make_cards_area(), 1)

    # ---------- Шапка ----------
    def _make_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        self._add_logo(row)
        row.addStretch()

        if self.user:
            row.addWidget(self._make_fio_label())

        if self._is_authorized():
            row.addWidget(self._make_cart_button())

        if self._is_staff():
            row.addWidget(self._make_orders_button())

        if self.user:
            row.addWidget(self._make_logout_button())

        return row

    def _add_logo(self, row: QHBoxLayout):
        logo_path = os.path.join(RESOURCES_DIR, 'logo.png')
        if not os.path.exists(logo_path):
            return
        logo = QLabel()
        logo.setPixmap(QPixmap(logo_path).scaledToHeight(
            80, Qt.TransformationMode.SmoothTransformation
        ))
        row.addWidget(logo)

    def _make_fio_label(self) -> QLabel:
        label = QLabel(self.user.get('full_name', ''))
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        return label

    def _make_cart_button(self) -> QPushButton:
        button = QPushButton('Корзина')
        button.setMinimumHeight(40)
        button.clicked.connect(self._open_cart)
        self.cart_btn = button
        return button

    def _make_orders_button(self) -> QPushButton:
        button = QPushButton('Управление заказами')
        button.setMinimumHeight(40)
        button.clicked.connect(self._open_orders)
        return button

    def _make_logout_button(self) -> QPushButton:
        button = QPushButton('Выйти')
        button.setMinimumHeight(40)
        button.clicked.connect(self._logout)
        return button

    # ---------- Панель фильтров ----------
    def _make_filter_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #D2F6E7;
                border-radius: 12px;
            }
            QLineEdit, QComboBox {
                background-color: white;
                border: 1px solid #a0d0c0;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)

        row = QHBoxLayout(panel)
        row.setContentsMargins(15, 12, 15, 12)
        row.setSpacing(12)

        row.addWidget(QLabel('Поиск:'))
        row.addWidget(self._make_search_input(), 2)

        row.addWidget(QLabel('Категория:'))
        row.addWidget(self._make_category_combo(), 1)

        row.addWidget(QLabel('Сортировка:'))
        row.addWidget(self._make_sort_combo(), 1)

        panel.setVisible(self.user is not None)
        return panel

    def _make_search_input(self) -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText('Поиск по наименованию или описанию...')
        field.textChanged.connect(self._apply_filters)
        self.search_input = field
        return field

    def _make_category_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(CATEGORY_ALL, None)
        combo.currentIndexChanged.connect(self._apply_filters)
        self.category_combo = combo
        return combo

    def _make_sort_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItems(SORT_OPTIONS)
        combo.currentIndexChanged.connect(self._apply_filters)
        self.sort_combo = combo
        return combo

    # ---------- Область карточек ----------
    def _make_cards_area(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        cards = QVBoxLayout(container)
        cards.setAlignment(Qt.AlignmentFlag.AlignTop)
        cards.setSpacing(12)
        cards.setContentsMargins(5, 5, 5, 5)
        scroll.setWidget(container)

        self.cards_container = container
        self.cards_layout = cards
        return scroll

    # ============================================================
    # Проверки ролей
    # ============================================================
    def _is_authorized(self) -> bool:
        return bool(self.user and self.user.get('id'))

    def _is_staff(self) -> bool:
        return bool(
            self.user and self.user.get('role_name') in ADMIN_ROLES
        )

    # ============================================================
    # Загрузка и фильтрация товаров
    # ============================================================
    def _load_products(self):
        self.all_products = [dict(r) for r in fetch_all(SQL_LOAD_PRODUCTS)]
        self._fill_categories()
        self._apply_filters()

    def _fill_categories(self):
        categories = sorted({p['category'] for p in self.all_products})
        for cat in categories:
            self.category_combo.addItem(cat, cat)

    def _apply_filters(self):
        products = self._filter_by_category(self.all_products)
        products = self._filter_by_search(products)
        products = self._sort(products)
        self._render_products(products)

    def _filter_by_category(self, products: list) -> list:
        cat = self.category_combo.currentData()
        if not cat:
            return list(products)
        return [p for p in products if p['category'] == cat]

    def _filter_by_search(self, products: list) -> list:
        query = self.search_input.text().strip().lower()
        if not query:
            return list(products)
        return [
            p for p in products
            if query in p['name'].lower()
            or query in (p.get('description') or '').lower()
        ]

    def _sort(self, products: list) -> list:
        mode = self.sort_combo.currentText()
        if mode == SORT_ASC:
            return sorted(products, key=lambda p: float(p['price']))
        if mode == SORT_DESC:
            return sorted(products, key=lambda p: float(p['price']), reverse=True)
        return list(products)

    # ============================================================
    # Отрисовка карточек
    # ============================================================
    def _render_products(self, products: list):
        self._clear_cards()

        if not products:
            self.cards_layout.addWidget(QLabel('Товары не найдены'))
            return

        for product in products:
            self.cards_layout.addWidget(self._make_card(product))

    def _clear_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _make_card(self, product: dict) -> ProductCard:
        discount = get_discount_for_product(product['id'])
        card = ProductCard(product, discount)
        card.clicked.connect(self._open_product)
        return card

    # ============================================================
    # Переходы между окнами
    # ============================================================
    def _open_product(self, product_id: int):
        """Открывает форму просмотра товара."""
        if not self._is_authorized():
            from utils.messages import show_info
            show_info(self, 'Для оформления заказа войдите в систему')
            return

        from ui.product_view import ProductView
        dialog = ProductView(product_id, self.cart, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._update_cart_button()

    def _open_cart(self):
        """Открывает окно корзины."""
        from ui.cart_widget import CartWindow
        dialog = CartWindow(self.user, self.cart, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._load_products()
            self._update_cart_button()

    def _open_orders(self):
        """Открывает окно управления заказами."""
        from ui.orders_window import OrdersWindow
        dialog = OrdersWindow(user=self.user, parent=self)
        dialog.exec()
        self._load_products()

    def _logout(self):
        """Выход и возврат к окну авторизации."""
        from ui.login_window import LoginWindow
        self.close()

        login = LoginWindow()
        if login.exec() != login.DialogCode.Accepted:
            return

        new_window = MainWindow(user=login.get_user())
        new_window.show()
        self._new_window = new_window

    # ============================================================
    # Вспомогательные
    # ============================================================
    def _update_cart_button(self):
        """Обновляет счётчик на кнопке «Корзина»."""
        if not hasattr(self, 'cart_btn'):
            return
        if self.cart:
            total = sum(item['quantity'] for item in self.cart)
            self.cart_btn.setText(f'Корзина ({total})')
        else:
            self.cart_btn.setText('Корзина')