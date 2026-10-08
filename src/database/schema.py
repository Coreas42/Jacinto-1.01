SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    correo TEXT,
    direccion TEXT,
    ciudad TEXT,
    notas TEXT,
    activo INTEGER DEFAULT 1,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    marca_vehiculo TEXT DEFAULT 'Universal',
    anio_vehiculo TEXT DEFAULT 'Todos',
    tipo TEXT CHECK(tipo IN ('FISICO', 'SERVICIO')) NOT NULL DEFAULT 'FISICO',
    costo REAL NOT NULL DEFAULT 0.0,
    precio REAL NOT NULL DEFAULT 0.0,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 3,
    imagen_path TEXT DEFAULT '',
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS turnos_caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_apertura DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre DATETIME,
    fondo_inicial REAL NOT NULL,
    efectivo_declarado REAL,
    diferencia REAL,
    estado TEXT CHECK(estado IN ('ABIERTO', 'CERRADO')) DEFAULT 'ABIERTO'
);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER REFERENCES clientes(id),
    turno_id INTEGER REFERENCES turnos_caja(id),
    subtotal REAL NOT NULL,
    descuento REAL DEFAULT 0.0,
    total REAL NOT NULL,
    metodo_pago TEXT CHECK(metodo_pago IN ('EFECTIVO', 'TARJETA', 'TRANSFERENCIA')) NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ventas_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    costo_unitario REAL NOT NULL,
    subtotal REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    numero_pedido TEXT UNIQUE NOT NULL,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega DATETIME,
    tipo_entrega TEXT CHECK(tipo_entrega IN ('ENVIO', 'INSTALACION', 'RECOGIDA', 'LOCAL')) NOT NULL DEFAULT 'ENVIO',
    subtotal REAL NOT NULL DEFAULT 0.0,
    descuento REAL NOT NULL DEFAULT 0.0,
    envio REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    anticipo REAL NOT NULL DEFAULT 0.0,
    saldo_pendiente REAL NOT NULL DEFAULT 0.0,
    estado TEXT CHECK(estado IN ('PENDIENTE', 'CONFIRMADO', 'EN_PREPARACION', 'POR_ENTREGAR', 'EN_INSTALACION', 'COMPLETADO', 'CANCELADO')) NOT NULL DEFAULT 'PENDIENTE',
    metodo_pago TEXT CHECK(metodo_pago IN ('EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'CREDITO')) DEFAULT 'EFECTIVO',
    notas TEXT,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pedido_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES productos(id),
    nombre TEXT NOT NULL,
    descripcion TEXT,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    costo_unitario REAL NOT NULL DEFAULT 0.0,
    subtotal REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pagos_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    monto REAL NOT NULL,
    metodo_pago TEXT CHECK(metodo_pago IN ('EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'CREDITO')) NOT NULL,
    tipo TEXT CHECK(tipo IN ('ANTICIPO', 'PAGO', 'DEVOLUCION')) NOT NULL DEFAULT 'ANTICIPO',
    referencia TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agenda_pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    fecha_programada DATETIME NOT NULL,
    tipo TEXT CHECK(tipo IN ('INSTALACION', 'ENTREGA', 'RECOGIDA', 'OTRO')) NOT NULL DEFAULT 'INSTALACION',
    direccion TEXT,
    observaciones TEXT,
    estado TEXT CHECK(estado IN ('PENDIENTE', 'PROGRAMADA', 'COMPLETADA', 'CANCELADA')) NOT NULL DEFAULT 'PENDIENTE'
);

CREATE TABLE IF NOT EXISTS kardex_movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER REFERENCES productos(id),
    tipo TEXT CHECK(tipo IN ('ENTRADA', 'SALIDA', 'AJUSTE', 'MERMA', 'DEVOLUCION')) NOT NULL,
    cantidad INTEGER NOT NULL,
    motivo TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concepto TEXT NOT NULL,
    categoria TEXT NOT NULL,
    tipo TEXT CHECK(tipo IN ('VARIABLE', 'FIJO', 'DEPRECIACION')) NOT NULL,
    monto REAL NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre);
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id, estado);
CREATE INDEX IF NOT EXISTS idx_pedidos_fecha ON pedidos(fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_pedido_items_pedido ON pedido_items(pedido_id);
CREATE INDEX IF NOT EXISTS idx_agenda_fecha ON agenda_pedidos(fecha_programada);
CREATE INDEX IF NOT EXISTS idx_prod_sku ON productos(sku);
CREATE INDEX IF NOT EXISTS idx_prod_vehiculo ON productos(marca_vehiculo, anio_vehiculo);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
"""

DEFAULT_DATA_SQL = """
INSERT OR IGNORE INTO clientes (id, nombre, telefono, activo) VALUES (1, 'Cliente General', '0000-0000', 1);

INSERT OR IGNORE INTO productos (id, sku, nombre, categoria, marca_vehiculo, anio_vehiculo, tipo, costo, precio, stock_actual, stock_minimo, imagen_path) 
VALUES 
(1, 'ALF-5D-HILUX', 'Alfombras 5D Bandeja', 'Alfombras', 'Toyota Hilux', '2016-2024', 'FISICO', 45.00, 75.00, 12, 3, ''),
(2, 'LON-DMAX-01', 'Lona Maritima Enrollable', 'Lonas', 'Isuzu D-Max', '2018-2024', 'FISICO', 110.00, 185.00, 5, 2, ''),
(3, 'EST-NAVARA', 'Estribos Laterales Negros', 'Estribos', 'Nissan NP300', '2016-2023', 'FISICO', 130.00, 220.00, 4, 2, ''),
(4, 'POL-NANO-CER', 'Polarizado Nano Cerámico Completo', 'Servicios', 'Universal', 'Todos', 'SERVICIO', 35.00, 95.00, 0, 0, ''),
(5, 'INST-ACCESORIO', 'Instalación y Cableado General', 'Servicios', 'Universal', 'Todos', 'SERVICIO', 15.00, 35.00, 0, 0, '');

INSERT OR IGNORE INTO turnos_caja (id, fondo_inicial, estado) VALUES (1, 100.00, 'ABIERTO');
"""
