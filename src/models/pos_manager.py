from src.database.connection import get_connection
from src.core.validators import ProductValidator, SaleValidator, ValidationError


class POSManager:
    @staticmethod
    def _get_or_create_open_turn(conn):
        """Devuelve el turno activo o crea uno nuevo si no existe."""
        turno = conn.execute(
            "SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if turno:
            return turno['id']

        conn.execute(
            "INSERT INTO turnos_caja (fondo_inicial, estado) VALUES (?, 'ABIERTO')",
            (100.0,)
        )
        return conn.execute("SELECT last_insert_rowid() AS id").fetchone()['id']

    @staticmethod
    def process_sale(cliente_id: int, turno_id: int, items: list, metodo_pago: str, descuento: float = 0.0) -> int:
        """
        Procesa una venta con validaciones robustas.
        items: lista de dicts [{'producto_id', 'cantidad', 'precio_unitario', 'costo_unitario', 'tipo'}]
        """
        if not items or not isinstance(items, list):
            raise ValidationError("Debe incluir al menos un producto en la venta.")

        metodo_pago = SaleValidator.validate_payment_method(metodo_pago)

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                if turno_id is None:
                    turno_id = POSManager._get_or_create_open_turn(conn)

                # Verifica que el turno exista y esté abierto antes de vender
                turno = cursor.execute(
                    "SELECT id, estado FROM turnos_caja WHERE id = ?",
                    (turno_id,)
                ).fetchone()
                if not turno or turno['estado'] != 'ABIERTO':
                    raise ValidationError("No existe un turno abierto válido para registrar esta venta.")

                if cliente_id is None:
                    cliente_id = 1

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

                    row = cursor.execute(
                        "SELECT id, nombre, stock_actual, tipo, activo FROM productos WHERE id = ?",
                        (producto_id,)
                    ).fetchone()
                    if not row:
                        raise ValidationError(f"Producto no encontrado con ID {producto_id}.")
                    if row['activo'] != 1:
                        raise ValidationError(f"El producto '{row['nombre']}' está inactivo y no puede venderse.")
                    if row['tipo'] == 'FISICO' and row['stock_actual'] < cantidad:
                        raise ValueError(f"Stock insuficiente para: {row['nombre']}")

                    item_total = cantidad * precio_unitario
                    subtotal += item_total
                    validated_items.append({
                        'producto_id': producto_id,
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario,
                        'costo_unitario': costo_unitario,
                        'tipo': tipo,
                        'subtotal': item_total,
                        'nombre': row['nombre']
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
                return venta_id
            except Exception:
                conn.rollback()
                raise
