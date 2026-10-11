CREATE TABLE roles (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    last_name   VARCHAR(50) NOT NULL,
    first_name  VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    login       VARCHAR(50) NOT NULL UNIQUE,
    role_id     INTEGER NOT NULL REFERENCES roles(id)
);

CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    category     VARCHAR(50) NOT NULL,
    subcategory  VARCHAR(50),
    name         VARCHAR(200) NOT NULL,
    manufacturer VARCHAR(100),
    image_path   VARCHAR(200),
    description  TEXT,
    composition  TEXT,
    price        NUMERIC(10,2) NOT NULL CHECK (price >= 0)
);

CREATE TABLE sizes (
    id    SERIAL PRIMARY KEY,
    value NUMERIC(4,1) NOT NULL UNIQUE
);

CREATE TABLE stock_items (
    id                 SERIAL PRIMARY KEY,
    product_id         INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    size_id            INTEGER NOT NULL REFERENCES sizes(id) ON DELETE CASCADE,
    quantity_available INTEGER NOT NULL DEFAULT 0 CHECK (quantity_available >= 0),
    UNIQUE (product_id, size_id)
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    order_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    client_name VARCHAR(150) NOT NULL
);

CREATE TABLE order_items (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    size_id         INTEGER NOT NULL REFERENCES sizes(id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    price_at_moment NUMERIC(10,2) NOT NULL CHECK (price_at_moment >= 0)
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_stock_product ON stock_items(product_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);

INSERT INTO roles (name) VALUES
    ('Администратор'),
    ('Менеджер'),
    ('Авторизованный пользователь');
