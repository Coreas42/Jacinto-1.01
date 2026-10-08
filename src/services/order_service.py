"""
Módulo de órdenes y pedidos.

Gestiona pedidos, clientes, productos, instalación, anticipo, saldo pendiente y agenda.
"""

from datetime import datetime
from src.database.connection import get_connection
from src.core.validators import ProductValidator, SaleValidator, ValidationError


class OrderService:
    """Gestiona pedidos y agenda para ventas con instalación y envío."""

    ESTADOS = ['PENDIENTE', 'CONFIRMADA', 'EN_INSTALACION', 'INSTALADA', 'ENVIADA', 'COMPLETADA', 'CANCELADA']
    TIPOS_SERVICIO = ['INSTALACION_SITIO', 'ENVIO', 'SOLO_VENTA']

    @staticmethod
    def create_order(cliente_id: int, tipo_servicio: str, items: list, total_orden: float,
                    anticipo: float = 0.0, costo_envio: float = 0.0,
                    fecha_instalacion: str = None, notas: str = "", direccion: str = "") -> int:
        """Crea una nueva orden con productos y datos de servicio."""
        tipo_servicio = (tipo_servicio or '').upper()
        if tipo_servicio not in OrderService.TIPOS_SERVICIO:
            raise ValidationError(f"Tipo de servicio no válido: {tipo_servicio}")

        total_orden = ProductValidator.validate_price(total_orden, "Total de la orden")
        anticipo = ProductValidator.validate_price(anticipo, "Anticipo")
        costo_envio = ProductValidator.validate_price(costo_envio, "Costo de envío")

        if not items:
            raise ValidationError("La orden debe incluir al menos un producto o servicio.")

        total_con_envio = total_orden + costo_envio
        saldo_pendiente = total_con_envio - anticipo
        if saldo_pendiente < 0:
            raise ValidationError("El anticipo no puede exceder el total de la orden.")

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO ordenes (
                        cliente_id, tipo_servicio, total_orden, costo_envio, total_con_envio,
                        anticipo, saldo_pendiente, fecha_instalacion, notas, direccion, estado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')""",
                    (cliente_id, tipo_servicio, total_orden, costo_envio, total_con_envio,
                     anticipo, saldo_pendiente, fecha_instalacion, notas or '', direccion or '')
                )
                orden_id = cursor.lastrowid

                for item in items:
                    if not isinstance(item, dict):
                        raise ValidationError("Cada item de la orden debe ser un diccionario.")

                    producto_id = item.get('producto_id')
                    cantidad = SaleValidator.validate_quantity(item.get('cantidad', 0))
                    precio_unitario = ProductValidator.validate_price(item.get('precio_unitario', 0), "Precio unitario")

                    cursor.execute(
                        """INSERT INTO ordenes_detalle (orden_id, producto_id, cantidad, precio_unitario, subtotal)
                           VALUES (?, ?, ?, ?, ?)""",
                        (orden_id, producto_id, cantidad, precio_unitario, cantidad * precio_unitario)
                    )

                conn.commit()
                return orden_id
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_order(orden_id: int) -> dict:
        """Obtiene una orden con detalles."""
        with get_connection() as conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                return None
            detalles = conn.execute("SELECT * FROM ordenes_detalle WHERE orden_id = ?", (orden_id,)).fetchall()
            return {
                'orden': dict(orden),
                'detalles': [dict(d) for d in detalles],
            }

    @staticmethod
    def update_order_status(orden_id: int, nuevo_estado: str) -> None:
        """Actualiza el estado de una orden."""
        nuevo_estado = (nuevo_estado or '').upper()
        if nuevo_estado not in OrderService.ESTADOS:
            raise ValidationError(f"Estado no válido: {nuevo_estado}")

        with get_connection() as conn:
            conn.execute(
                "UPDATE ordenes SET estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?",
                (nuevo_estado, orden_id)
            )
            conn.commit()

    @staticmethod
    def registrar_anticipo(orden_id: int, monto: float) -> dict:
        """Registra anticipo para una orden y actualiza saldo pendiente."""
        monto = ProductValidator.validate_price(monto, "Monto del anticipo")

        with get_connection() as conn:
            cursor = conn.cursor()
            orden = cursor.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                raise ValidationError(f"La orden {orden_id} no existe.")

            nuevo_anticipo = float(orden['anticipo'] or 0.0) + monto
            nuevo_saldo = float(orden['total_con_envio'] or 0.0) - nuevo_anticipo
            if nuevo_saldo < 0:
                raise ValidationError("El anticipo ingresado excede el total de la orden.")

            cursor.execute(
                "UPDATE ordenes SET anticipo = ?, saldo_pendiente = ? WHERE id = ?",
                (nuevo_anticipo, nuevo_saldo, orden_id)
            )
            cursor.execute(
                "INSERT INTO pagos_orden (orden_id, monto, tipo_pago, concepto) VALUES (?, ?, 'ANTICIPO', ?)",
                (orden_id, monto, f"Anticipo registrado {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            )
            conn.commit()

            return {
                'orden_id': orden_id,
                'anticipo_total': nuevo_anticipo,
                'saldo_pendiente': nuevo_saldo
            }

    @staticmethod
    def registrar_pago_saldo(orden_id: int, monto: float) -> dict:
        """Registra un pago del saldo pendiente."""
        monto = ProductValidator.validate_price(monto, "Monto del saldo pagado")

        with get_connection() as conn:
            cursor = conn.cursor()
            orden = cursor.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                raise ValidationError(f"La orden {orden_id} no existe.")

            saldo_actual = float(orden['saldo_pendiente'] or 0.0)
            if monto > saldo_actual:
                raise ValidationError(f"El monto pagado excede el saldo pendiente ({saldo_actual}).")

            nuevo_saldo = saldo_actual - monto
            nuevo_estado = 'COMPLETADA' if nuevo_saldo == 0 else orden['estado']

            cursor.execute(
                "UPDATE ordenes SET saldo_pendiente = ?, estado = ? WHERE id = ?",
                (nuevo_saldo, nuevo_estado, orden_id)
            )
            cursor.execute(
                "INSERT INTO pagos_orden (orden_id, monto, tipo_pago, concepto) VALUES (?, ?, 'PAGO_SALDO', ?)",
                (orden_id, monto, f"Pago de saldo {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            )
            conn.commit()

            return {
                'orden_id': orden_id,
                'saldo_pendiente': nuevo_saldo,
                'estado': nuevo_estado
            }

    @staticmethod
    def get_orders_by_state(estado: str) -> list:
        """Obtiene órdenes por estado."""
        estado = (estado or '').upper()
        if estado not in OrderService.ESTADOS:
            raise ValidationError(f"Estado no válido: {estado}")

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ordenes WHERE estado = ? ORDER BY fecha_creacion DESC",
                (estado,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_agenda(fecha: str = None) -> list:
        """Obtiene la agenda de instalación o entrega para una fecha."""
        if not fecha:
            fecha = datetime.now().strftime('%Y-%m-%d')

        with get_connection() as conn:
            rows = conn.execute(
                """SELECT o.id, c.nombre as cliente, c.telefono, o.direccion, o.tipo_servicio,
                          o.fecha_instalacion, o.estado, o.saldo_pendiente, o.notas
                   FROM ordenes o
                   JOIN clientes c ON c.id = o.cliente_id
                   WHERE DATE(o.fecha_instalacion) = ?
                   ORDER BY o.fecha_instalacion ASC""",
                (fecha,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_resumen_pendientes() -> dict:
        """Obtiene resumen del total de pendientes por cobrar."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as total_ordenes, SUM(saldo_pendiente) as saldo_total FROM ordenes WHERE estado NOT IN ('COMPLETADA', 'CANCELADA')"
            ).fetchone()
            return {
                'total_ordenes': row['total_ordenes'] or 0,
                'saldo_total': float(row['saldo_total'] or 0.0)
            }


__all__ = ['OrderService']
