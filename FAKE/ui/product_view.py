"""
Просмотр товара + добавление в корзину.
Показывает картинку, характеристики, цену со скидкой,
даёт выбрать размер и количество.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QPushButton, QTextEdit,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from config import PRODUCTS_IMG_DIR, RESOURCES_DIR, STYLESHEET
from db import fetch_one, fetch_all
from utils.discount import get_discount_for_product, calculate_price_with_discount
from utils.messages import show_error, show_info


# ---------- Константы ----------
WINDOW_TITLE = 'Чудо Обувь — Просмотр товара'
IMAGE_SIZE = 300
DESC_HEIGHT = 80

STYLE_SECONDARY = """
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

SQL_FIND_PRODUCT = "SELECT * FROM products WHERE id = %s"

SQL_SIZES_BY_PRODUCT = """
    SELECT s.id AS size_id, s.value, si.quantity_available
    FROM stock_items si
    JOIN sizes s ON s.id = si.size_id
    WHERE si.product_id = %s AND si.quantity_available > 0
    ORDER BY s.value
"""


class ProductView(QDialog):
    """Форма просмотра товара + добавление в корзину."""

    def __init__(self, product_id: int, cart: list, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.cart = cart

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(700, 700)
        self.setStyleSheet(STYLESHEET)

        self._load_data()
        self._build_ui()

    # ============================================================
    # Загрузка данных
    # ============================================================
    def _load_data(self):
        self.product = dict(fetch_one(SQL_FIND_PRODUCT, (self.product_id,)))
        self.sizes = fetch_all(SQL_SIZES_BY_PRODUCT, (self.product_id,))
        self.discount = get_discount_for_product(self.product_id)

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(self._make_image())
        layout.addWidget(self._make_title())
        layout.addWidget(QLabel(f"Категория: {self.product.get('category', '')}"))
        layout.addWidget(QLabel(f"Состав: {self.product.get('composition', '')}"))
        layout.addWidget(self._make_description())
        layout.addWidget(self._make_price_label())
        layout.addLayout(self._make_size_row())
        layout.addLayout(self._make_buttons())

    def _make_image(self) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = self._load_pixmap()
        label.setPixmap(pixmap.scaled(
            IMAGE_SIZE, IMAGE_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        return label

    def _load_pixmap(self) -> QPixmap:
        """Загружает картинку товара или заглушку."""
        name = self.product.get('image_path')
        if name:
            path = os.path.join(PRODUCTS_IMG_DIR, name)
            if os.path.exists(path):
                return QPixmap(path)
        return QPixmap(os.path.join(RESOURCES_DIR, 'picture.png'))

    def _make_title(self) -> QLabel:
        text = (
            f"<b>{self.product.get('manufacturer', '')}"
            f" | {self.product.get('name', '')}</b>"
        )
        return QLabel(text)

    def _make_description(self) -> QTextEdit:
        field = QTextEdit(self.product.get('description') or '')
        field.setReadOnly(True)
        field.setMaximumHeight(DESC_HEIGHT)
        return field

    def _make_price_label(self) -> QLabel:
        base = float(self.product['price'])
        final = calculate_price_with_discount(base, self.discount)

        text = f"<b>Цена со скидкой: {final:.2f} ₽</b>"
        if self.discount > 0:
            text += (
                f" <span style='color:#999;text-decoration:line-through;'>"
                f"{base:.2f} ₽</span>"
            )
        return QLabel(text)

    def _make_size_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        row.addWidget(QLabel('Размер:'))
        self.size_combo = self._make_size_combo()
        row.addWidget(self.size_combo)

        row.addWidget(QLabel('Кол-во:'))
        self.qty_spin = self._make_qty_spin()
        row.addWidget(self.qty_spin)

        self.size_combo.currentIndexChanged.connect(self._update_max_qty)
        self._update_max_qty()

        return row

    def _make_size_combo(self) -> QComboBox:
        combo = QComboBox()
        if not self.sizes:
            combo.addItem('Нет в наличии', None)
            combo.setEnabled(False)
            return combo

        for size in self.sizes:
            combo.addItem(
                f"{size['value']} (доступно: {size['quantity_available']})",
                (size['size_id'], size['quantity_available']),
            )
        return combo

    def _make_qty_spin(self) -> QSpinBox:
        spin = QSpinBox()
        spin.setMinimum(1)
        spin.setMaximum(1)
        return spin

    def _make_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.add_btn = QPushButton('Добавить в заказ')
        self.add_btn.clicked.connect(self._add_to_cart)
        if not self.sizes:
            self.add_btn.setEnabled(False)
        row.addWidget(self.add_btn)

        back_btn = QPushButton('Назад')
        back_btn.setStyleSheet(STYLE_SECONDARY)
        back_btn.clicked.connect(self.reject)
        row.addWidget(back_btn)

        return row

    # ============================================================
    # Работа с размером
    # ============================================================
    def _update_max_qty(self):
        data = self.size_combo.currentData()
        max_qty = data[1] if data else 0
        self.qty_spin.setMaximum(max_qty)

    # ============================================================
    # Добавление в корзину
    # ============================================================
    def _add_to_cart(self):
        data = self.size_combo.currentData()
        if not data:
            show_error(self, 'Выберите доступный размер')
            return

        size_id, available = data
        qty = self.qty_spin.value()

        if qty <= 0 or qty > available:
            show_error(self, f'Количество должно быть от 1 до {available}')
            return

        final_price = calculate_price_with_discount(
            float(self.product['price']), self.discount
        )

        if self._merge_into_existing(size_id, qty):
            show_info(self, 'Количество в заказе увеличено')
        else:
            self._append_new_item(size_id, qty, final_price)
            show_info(self, 'Товар добавлен в заказ')

        self.accept()

    def _merge_into_existing(self, size_id: int, qty: int) -> bool:
        """Если товар с таким размером уже в корзине — увеличивает кол-во."""
        for item in self.cart:
            if item['product_id'] == self.product_id and item['size_id'] == size_id:
                item['quantity'] += qty
                return True
        return False

    def _append_new_item(self, size_id: int, qty: int, price: float):
        size_text = self.size_combo.currentText().split(' ')[0]
        self.cart.append({
            'product_id': self.product_id,
            'name': self.product['name'],
            'manufacturer': self.product.get('manufacturer', ''),
            'size_id': size_id,
            'size_value': size_text,
            'quantity': qty,
            'price': price,
        })