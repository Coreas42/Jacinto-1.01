SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    correo TEXT,
    vehiculo TEXT,
    placa TEXT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    tipo TEXT CHECK(tipo IN ('FISICO', 'SERVICIO')) NOT NULL DEFAULT 'FISICO',
    costo REAL NOT NULL DEFAULT 0.0,
    precio REAL NOT NULL DEFAULT 0.0,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 5,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razon_social TEXT NOT NULL,
    contacto TEXT,
    telefono TEXT,
    direccion TEXT
);

CREATE TABLE IF NOT EXISTS compras_cabecera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER REFERENCES proveedores(id),
    costo_flete REAL DEFAULT 0.0,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_compra REAL DEFAULT 0.0
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

CREATE INDEX IF NOT EXISTS idx_prod_sku ON productos(sku);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON ventas(cliente_id);
"""

DEFAULT_DATA_SQL = """
INSERT OR IGNORE INTO clientes (id, nombre, telefono) VALUES (1, 'Cliente General', '0000-0000');
"""
