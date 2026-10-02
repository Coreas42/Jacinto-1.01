from src.database.connection import get_connection

class POSManager:
    @staticmethod
    def process_sale(cliente_id: int, turno_id: int, items: list, metodo_pago: str, descuento: float = 0.0) -> int:
        """
        items: lista de dicts [{'producto_id', 'cantidad', 'precio_unitario', 'costo_unitario', 'tipo'}]
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Validar existencias previas
                for item in items:
                    if item['tipo'] == 'FISICO':
                        cursor.execute("SELECT stock_actual, nombre FROM productos WHERE id = ?", (item['producto_id'],))
                        row = cursor.fetchone()
                        if not row or row['stock_actual'] < item['cantidad']:
                            raise ValueError(f"Stock insuficiente para: {row['nombre'] if row else 'ID '+str(item['producto_id'])}")

                # Iniciar Cabecera
                subtotal = sum(i['cantidad'] * i['precio_unitario'] for i in items)
                total = max(0.0, subtotal - descuento)
                
                cursor.execute(
                    """INSERT INTO ventas (cliente_id, turno_id, subtotal, descuento, total, metodo_pago)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (cliente_id, turno_id, subtotal, descuento, total, metodo_pago)
                )
                venta_id = cursor.lastrowid

                # Detalle y Kardex
                for item in items:
                    item_subtotal = item['cantidad'] * item['precio_unitario']
                    cursor.execute(
                        """INSERT INTO ventas_detalle (venta_id, producto_id, cantidad, precio_unitario, costo_unitario, subtotal)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (venta_id, item['producto_id'], item['cantidad'], item['precio_unitario'], item['costo_unitario'], item_subtotal)
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
            except Exception as e:
                conn.rollback()
                raise e
