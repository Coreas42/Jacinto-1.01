"""
Servicio de gestión de productos.
Centraliza toda la lógica de negocio relacionada con productos.
"""

from src.database.connection import get_connection
from src.core.validators import ProductValidator, ValidationError


class ProductService:
    """Gestiona todas las operaciones de productos."""

    @staticmethod
    def create_product(sku: str, nombre: str, categoria: str, marca_vehiculo: str, 
                      anio_vehiculo: str, tipo: str, costo: float, precio: float, 
                      stock_actual: int = 0, stock_minimo: int = 3, imagen_path: str = "") -> int:
        """Crea un nuevo producto con validaciones."""
        validated = ProductValidator.validate_product_data(
            sku, nombre, tipo, costo, precio, stock_actual, stock_minimo
        )

        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Verifica duplicados
            existing = cursor.execute(
                "SELECT id FROM productos WHERE sku = ? AND activo = 1",
                (validated['sku'],)
            ).fetchone()
            if existing:
                raise ValidationError(f"El SKU '{validated['sku']}' ya existe.")

            cursor.execute(
                """INSERT INTO productos 
                   (sku, nombre, categoria, marca_vehiculo, anio_vehiculo, tipo, costo, precio, stock_actual, stock_minimo, imagen_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (validated['sku'], validated['nombre'], categoria or "General", 
                 marca_vehiculo or "Universal", anio_vehiculo or "Todos",
                 validated['tipo'], validated['costo'], validated['precio'],
                 validated['stock_actual'], validated['stock_minimo'], imagen_path)
            )
            product_id = cursor.lastrowid
            conn.commit()

        return product_id

    @staticmethod
    def update_product(product_id: int, sku: str, nombre: str, categoria: str, 
                      marca_vehiculo: str, anio_vehiculo: str, tipo: str, costo: float, 
                      precio: float, stock_actual: int = 0, stock_minimo: int = 3, 
                      imagen_path: str = "") -> None:
        """Actualiza un producto existente."""
        validated = ProductValidator.validate_product_data(
            sku, nombre, tipo, costo, precio, stock_actual, stock_minimo
        )

        with get_connection() as conn:
            cursor = conn.cursor()

            existing = cursor.execute(
                "SELECT id FROM productos WHERE sku = ? AND id != ? AND activo = 1",
                (validated['sku'], product_id)
            ).fetchone()
            if existing:
                raise ValidationError(f"El SKU '{validated['sku']}' ya existe en otro producto.")

            cursor.execute(
                """UPDATE productos 
                   SET sku = ?, nombre = ?, categoria = ?, marca_vehiculo = ?, anio_vehiculo = ?,
                       tipo = ?, costo = ?, precio = ?, stock_actual = ?, stock_minimo = ?, imagen_path = ?
                   WHERE id = ?""",
                (validated['sku'], validated['nombre'], categoria or "General",
                 marca_vehiculo or "Universal", anio_vehiculo or "Todos",
                 validated['tipo'], validated['costo'], validated['precio'],
                 validated['stock_actual'], validated['stock_minimo'], imagen_path, product_id)
            )
            conn.commit()

    @staticmethod
    def get_product(product_id: int) -> dict:
        """Obtiene un producto por ID."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM productos WHERE id = ?",
                (product_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_all_active_products() -> list:
        """Obtiene todos los productos activos."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM productos WHERE activo = 1 ORDER BY nombre ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def search_products(query: str) -> list:
        """Busca productos por SKU, nombre o marca de vehículo."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM productos WHERE activo = 1 AND 
                   (sku LIKE ? OR nombre LIKE ? OR marca_vehiculo LIKE ?)
                   ORDER BY nombre ASC LIMIT 100""",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def deactivate_product(product_id: int) -> None:
        """Desactiva un producto (soft delete)."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE productos SET activo = 0 WHERE id = ?",
                (product_id,)
            )
            conn.commit()

    @staticmethod
    def get_low_stock_products(limit: int = 50) -> list:
        """Obtiene productos con stock bajo (menor al mínimo)."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM productos 
                   WHERE activo = 1 AND tipo = 'FISICO' AND stock_actual <= stock_minimo
                   ORDER BY stock_actual ASC LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def adjust_stock(product_id: int, quantity: int, reason: str) -> None:
        """Ajusta el stock de un producto y registra el movimiento en kardex."""
        from src.core.validators import SaleValidator
        quantity = SaleValidator.validate_quantity(abs(quantity))

        with get_connection() as conn:
            cursor = conn.cursor()
            
            product = cursor.execute(
                "SELECT id, stock_actual FROM productos WHERE id = ?",
                (product_id,)
            ).fetchone()
            
            if not product:
                raise ValidationError(f"Producto con ID {product_id} no encontrado.")

            new_stock = product['stock_actual'] + quantity
            if new_stock < 0:
                raise ValidationError(f"No se puede reducir stock por debajo de 0.")

            cursor.execute(
                "UPDATE productos SET stock_actual = ? WHERE id = ?",
                (new_stock, product_id)
            )
            cursor.execute(
                """INSERT INTO kardex_movimientos (producto_id, tipo, cantidad, motivo)
                   VALUES (?, 'AJUSTE', ?, ?)""",
                (product_id, quantity, reason)
            )
            conn.commit()

    @staticmethod
    def get_products_by_category(category: str) -> list:
        """Obtiene productos por categoría."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM productos 
                   WHERE activo = 1 AND categoria = ?
                   ORDER BY nombre ASC""",
                (category,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_categories() -> list:
        """Obtiene todas las categorías únicas."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT DISTINCT categoria FROM productos WHERE activo = 1
                   ORDER BY categoria ASC"""
            ).fetchall()
            return [row[0] for row in rows]

    @staticmethod
    def calculate_margin(cost: float, price: float) -> dict:
        """Calcula margen bruto y porcentaje."""
        margin = price - cost
        margin_pct = (margin / price * 100) if price > 0 else 0
        return {
            'margin_amount': round(margin, 2),
            'margin_percentage': round(margin_pct, 2)
        }
