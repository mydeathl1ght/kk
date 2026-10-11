"""
Карточка товара в каталоге (по макету из КИМ).
Клик по карточке — сигнал `clicked(product_id)`.
"""

import os
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

from config import PRODUCTS_IMG_DIR, RESOURCES_DIR, COLOR_LOW_STOCK


# ---------- Константы ----------
IMAGE_SIZE = 150       # было 140
LOW_STOCK_LIMIT = 3
COMPOSITION_CUT = 80

TITLE_STYLE = "font-size: 15px; font-weight: bold; color: #333;"
PRICE_STYLE = "font-size: 18px; font-weight: bold; color: #70B2AF;"
OLD_PRICE_STYLE = "text-decoration: line-through; color: #999; font-size: 12px;"

STYLE_LOW_STOCK = """
    ProductCard {
        border: 1px solid #ff8080;
        border-radius: 12px;
        background-color: rgba(255, 128, 128, 40);
    }
    ProductCard:hover {
        border: 2px solid #ff8080;
        background-color: rgba(255, 128, 128, 60);
    }
"""

STYLE_NORMAL = """
    ProductCard {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        background-color: white;
    }
    ProductCard:hover {
        border: 2px solid #70B2AF;
        background-color: #FAFFFD;
    }
"""

class ProductCard(QFrame):
    """Карточка одной модели обуви."""

    clicked = pyqtSignal(int)

    def __init__(self, product: dict, discount: int, parent=None):
        super().__init__(parent)
        self.product_id = product['id']
        self.setFrameShape(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(product, discount)

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _build_ui(self, product: dict, discount: int):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)   # было 10, 10, 10, 10
        layout.setSpacing(20)  

        layout.addWidget(self._make_image(product))
        layout.addLayout(self._make_info(product), 1)
        layout.addLayout(self._make_price(product, discount))

        self._apply_style(int(product.get('total_quantity', 0)))

    def _make_image(self, product: dict) -> QLabel:
        label = QLabel()
        label.setFixedSize(IMAGE_SIZE, IMAGE_SIZE)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = self._load_pixmap(product.get('image_path'))
        label.setPixmap(pixmap.scaled(
            IMAGE_SIZE, IMAGE_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        return label

    def _make_info(self, product: dict) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(4)

        col.addWidget(self._make_title(product))
        col.addWidget(QLabel(f"Категория: {product.get('category', '')}"))
        col.addWidget(self._make_qty_label(product))
        col.addWidget(self._make_composition_label(product))
        col.addStretch()
        return col

    def _make_title(self, product: dict) -> QLabel:
        text = f"{product.get('manufacturer', '')} | {product.get('name', '')}"
        label = QLabel(text)
        label.setStyleSheet(TITLE_STYLE)
        return label

    def _make_qty_label(self, product: dict) -> QLabel:
        total = int(product.get('total_quantity', 0))
        label = QLabel(f"Количество: {total}")
        if total <= LOW_STOCK_LIMIT:
            label.setStyleSheet(f"color: {COLOR_LOW_STOCK}; font-weight: bold;")
        return label

    def _make_composition_label(self, product: dict) -> QLabel:
        text = (product.get('composition') or '')[:COMPOSITION_CUT]
        return QLabel(f"Состав: {text}...")

    def _make_price(self, product: dict, discount: int) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        base_price = float(product['price'])
        final_price = base_price * (1 - discount / 100.0)

        col.addWidget(self._make_final_price_label(final_price))
        if discount > 0:
            col.addWidget(self._make_old_price_label(base_price))

        return col

    def _make_final_price_label(self, price: float) -> QLabel:
        label = QLabel(f"{price:,.2f} ₽".replace(',', ' '))
        label.setStyleSheet(PRICE_STYLE)
        return label

    def _make_old_price_label(self, price: float) -> QLabel:
        label = QLabel(f"{price:,.2f} ₽".replace(',', ' '))
        label.setStyleSheet(OLD_PRICE_STYLE)
        return label

    # ============================================================
    # Стиль карточки
    # ============================================================
    def _apply_style(self, total_qty: int):
        if total_qty <= LOW_STOCK_LIMIT:
            self.setStyleSheet(STYLE_LOW_STOCK)
        else:
            self.setStyleSheet(STYLE_NORMAL)

    # ============================================================
    # Загрузка картинки
    # ============================================================
    def _load_pixmap(self, image_name: str) -> QPixmap:
        """Возвращает картинку товара или заглушку."""
        if image_name:
            path = os.path.join(PRODUCTS_IMG_DIR, image_name)
            if os.path.exists(path):
                return QPixmap(path)

        stub = os.path.join(RESOURCES_DIR, 'picture.png')
        return QPixmap(stub) if os.path.exists(stub) else QPixmap()

    # ============================================================
    # Клик
    # ============================================================
    def mousePressEvent(self, event):
        self.clicked.emit(self.product_id)