"""
Servicio de gestión de ventas.
Centraliza toda la lógica de negocio relacionada con ventas y tickets.
"""

from src.database.connection import get_connection
from src.core.validators import SaleValidator, ProductValidator, ValidationError


class SaleService:
    """Gestiona todas las operaciones de ventas."""

    @staticmethod
    def get_open_turn():
        """Obtiene o crea el turno abierto actual."""
        with get_connection() as conn:
            turno = conn.execute(
                "SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if turno:
                return dict(turno)

            conn.execute(
                "INSERT INTO turnos_caja (fondo_inicial, estado) VALUES (100.0, 'ABIERTO')"
            )
            conn.commit()
            turno = conn.execute(
                "SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(turno) if turno else None

    @staticmethod
    def process_sale(items: list, metodo_pago: str, cliente_id: int = 1, descuento: float = 0.0, turno_id: int = None) -> dict:
        """Procesa una venta completa con validaciones."""
        if not items or not isinstance(items, list):
            raise ValidationError("Debe incluir al menos un producto en la venta.")

        metodo_pago = SaleValidator.validate_payment_method(metodo_pago)

        if turno_id is None:
            turno = SaleService.get_open_turn()
            if not turno:
                raise ValidationError("No existe un turno abierto.")
            turno_id = turno['id']

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                turno = cursor.execute(
                    "SELECT id, estado FROM turnos_caja WHERE id = ?",
                    (turno_id,)
                ).fetchone()
                if not turno or turno['estado'] != 'ABIERTO':
                    raise ValidationError("No existe un turno abierto válido para registrar esta venta.")

                validated_items = []
                subtotal = 0.0

                for item in items:
                    if not isinstance(item, dict):
                        raise ValidationError("Cada item de la venta debe ser un diccionario.")

                    producto_id = item.get('producto_id')
                    cantidad = SaleValidator.validate_quantity(item.get('cantidad', 0))
                    precio_unitario = ProductValidator.validate_price(item.get('precio_unitario', 0), "Precio unitario")
                    costo_unitario = ProductValidator.validate_price(item.get('costo_unitario', 0), "Costo unitario")
                    tipo = item.get('tipo', 'FISICO')
                    ProductValidator.validate_product_type(tipo)

                    prod = cursor.execute(
                        "SELECT id, nombre, stock_actual, tipo, activo FROM productos WHERE id = ?",
                        (producto_id,)
                    ).fetchone()
                    if not prod:
                        raise ValidationError(f"Producto {producto_id} no existe.")
                    if prod['activo'] != 1:
                        raise ValidationError(f"Producto '{prod['nombre']}' está inactivo.")
                    if prod['tipo'] == 'FISICO' and prod['stock_actual'] < cantidad:
                        raise ValidationError(f"Stock insuficiente para {prod['nombre']}. Disponible: {prod['stock_actual']}")

                    item_total = cantidad * precio_unitario
                    subtotal += item_total
                    validated_items.append({
                        'producto_id': producto_id,
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario,
                        'costo_unitario': costo_unitario,
                        'tipo': tipo,
                        'subtotal': item_total,
                        'nombre': prod['nombre']
                    })

                descuento = SaleValidator.validate_discount(descuento, subtotal)
                total = max(0.0, subtotal - descuento)

                cursor.execute(
                    """INSERT INTO ventas (cliente_id, turno_id, subtotal, descuento, total, metodo_pago)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (cliente_id, turno_id, subtotal, descuento, total, metodo_pago)
                )
                venta_id = cursor.lastrowid

                for item in validated_items:
                    cursor.execute(
                        """INSERT INTO ventas_detalle (venta_id, producto_id, cantidad, precio_unitario, costo_unitario, subtotal)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (venta_id, item['producto_id'], item['cantidad'], item['precio_unitario'], item['costo_unitario'], item['subtotal'])
                    )

                    if item['tipo'] == 'FISICO':
                        cursor.execute(
                            "UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?",
                            (item['cantidad'], item['producto_id'])
                        )
                        cursor.execute(
                            """INSERT INTO kardex_movimientos (producto_id, tipo, cantidad, motivo)
                               VALUES (?, 'SALIDA', ?, ?)""",
                            (item['producto_id'], item['cantidad'], f"Venta #{venta_id}")
                        )

                conn.commit()
                return {
                    'venta_id': venta_id,
                    'turno_id': turno_id,
                    'subtotal': subtotal,
                    'descuento': descuento,
                    'total': total,
                    'metodo_pago': metodo_pago,
                    'items_count': len(validated_items),
                }
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_sale(venta_id: int) -> dict:
        """Obtiene detalle de una venta."""
        with get_connection() as conn:
            venta = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
            if not venta:
                return None
            detalles = conn.execute("SELECT * FROM ventas_detalle WHERE venta_id = ?", (venta_id,)).fetchall()
            return {
                'venta': dict(venta),
                'detalles': [dict(item) for item in detalles],
            }

    @staticmethod
    def get_sales_by_turn(turno_id: int) -> list:
        """Obtiene las ventas de un turno."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ventas WHERE turno_id = ? ORDER BY fecha DESC",
                (turno_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_sales_summary(turno_id: int = None) -> dict:
        """Obtiene resumen de ventas por método de pago."""
        with get_connection() as conn:
            if turno_id:
                rows = conn.execute(
                    """SELECT metodo_pago, COUNT(*) as cantidad, SUM(total) as monto
                       FROM ventas WHERE turno_id = ? GROUP BY metodo_pago""",
                    (turno_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT metodo_pago, COUNT(*) as cantidad, SUM(total) as monto
                       FROM ventas GROUP BY metodo_pago"""
                ).fetchall()
            return {row['metodo_pago']: {'cantidad': row['cantidad'], 'monto': float(row['monto'] or 0.0)} for row in rows}

    @staticmethod
    def calculate_sale_profit(venta_id: int) -> float:
        """Calcula la ganancia bruta de una venta."""
        with get_connection() as conn:
            row = conn.execute(
                """SELECT SUM((precio_unitario - costo_unitario) * cantidad) as ganancia
                   FROM ventas_detalle WHERE venta_id = ?""",
                (venta_id,)
            ).fetchone()
            return float(row['ganancia'] or 0.0)


__all__ = ['SaleService']
