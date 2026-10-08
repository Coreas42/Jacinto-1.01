"""
Servicio de gestión de órdenes y pedidos.
Centraliza la lógica de negocio para órdenes con anticipos, saldo pendiente y seguimiento.
"""

from datetime import datetime
from src.database.connection import get_connection
from src.core.validators import SaleValidator, ProductValidator, ValidationError


class OrderService:
    """Gestiona todas las operaciones de órdenes y pedidos."""

    # Estados posibles de una orden
    ESTADOS = ['PENDIENTE', 'CONFIRMADA', 'EN_INSTALACION', 'INSTALADA', 'ENVIADA', 'COMPLETADA', 'CANCELADA']
    TIPOS_SERVICIO = ['INSTALACION_SITIO', 'ENVIO', 'SOLO_VENTA']

    @staticmethod
    def create_order(cliente_nombre: str, cliente_telefono: str, cliente_ubicacion: str,
                     tipo_servicio: str, items: list, total_orden: float, anticipo: float = 0.0,
                     costo_envio: float = 0.0, fecha_instalacion: str = None, notas: str = "") -> int:
        """Crea una nueva orden con anticipos y saldo pendiente."""
        
        tipo_servicio = tipo_servicio.upper()
        if tipo_servicio not in OrderService.TIPOS_SERVICIO:
            raise ValidationError(f"Tipo de servicio debe ser uno de: {', '.join(OrderService.TIPOS_SERVICIO)}")

        anticipo = SaleValidator.validate_discount(anticipo, total_orden)
        costo_envio = ProductValidator.validate_price(costo_envio, "Costo de envío")
        
        total_con_envio = total_orden + costo_envio
        saldo_pendiente = total_con_envio - anticipo

        if saldo_pendiente < 0:
            raise ValidationError("El anticipo no puede ser mayor que el total de la orden.")

        if not cliente_nombre or not cliente_telefono:
            raise ValidationError("Nombre y teléfono del cliente son obligatorios.")

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO ordenes 
                       (cliente_nombre, cliente_telefono, cliente_ubicacion, tipo_servicio,
                        total_orden, costo_envio, total_con_envio, anticipo, saldo_pendiente,
                        fecha_instalacion, notas, estado)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')""",
                    (cliente_nombre, cliente_telefono, cliente_ubicacion, tipo_servicio,
                     total_orden, costo_envio, total_con_envio, anticipo, saldo_pendiente,
                     fecha_instalacion, notas)
                )
                orden_id = cursor.lastrowid

                # Inserta detalles de items
                for item in items:
                    if not isinstance(item, dict):
                        raise ValidationError("Formato inválido en items.")

                    producto_id = item.get('producto_id')
                    cantidad = SaleValidator.validate_quantity(item.get('cantidad', 0))
                    precio_unitario = ProductValidator.validate_price(item.get('precio_unitario', 0))

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
        """Obtiene una orden completa con detalles."""
        with get_connection() as conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                return None

            detalles = conn.execute(
                "SELECT * FROM ordenes_detalle WHERE orden_id = ?",
                (orden_id,)
            ).fetchall()

            return {
                'orden': dict(orden),
                'detalles': [dict(d) for d in detalles]
            }

    @staticmethod
    def get_ordenes_by_estado(estado: str) -> list:
        """Obtiene órdenes por estado."""
        if estado.upper() not in OrderService.ESTADOS:
            raise ValidationError(f"Estado debe ser uno de: {', '.join(OrderService.ESTADOS)}")

        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ordenes WHERE estado = ? ORDER BY fecha_creacion DESC",
                (estado.upper(),)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_agenda_instalaciones(fecha: str = None) -> list:
        """Obtiene la agenda de instalaciones para una fecha (YYYY-MM-DD)."""
        if not fecha:
            fecha = datetime.now().strftime('%Y-%m-%d')

        with get_connection() as conn:
            rows = conn.execute(
                """SELECT id, cliente_nombre, cliente_telefono, cliente_ubicacion,
                          tipo_servicio, total_con_envio, anticipo, saldo_pendiente,
                          fecha_instalacion, notas, estado
                   FROM ordenes
                   WHERE (tipo_servicio IN ('INSTALACION_SITIO', 'ENVIO') 
                          AND DATE(fecha_instalacion) = ?)
                   OR (estado IN ('PENDIENTE', 'CONFIRMADA', 'EN_INSTALACION'))
                   ORDER BY fecha_instalacion ASC, cliente_nombre ASC""",
                (fecha,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def registrar_pago_anticipo(orden_id: int, monto_anticipo: float) -> dict:
        """Registra un anticipo para una orden y calcula saldo pendiente."""
        monto_anticipo = SaleValidator.validate_discount(monto_anticipo, 999999.99)

        with get_connection() as conn:
            cursor = conn.cursor()
            orden = cursor.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()

            if not orden:
                raise ValidationError(f"Orden {orden_id} no existe.")

            nuevo_anticipo = float(orden['anticipo'] or 0.0) + monto_anticipo
            nuevo_saldo = float(orden['total_con_envio'] or 0.0) - nuevo_anticipo

            if nuevo_saldo < 0:
                raise ValidationError("El anticipo acumulado no puede exceder el total de la orden.")

            cursor.execute(
                "UPDATE ordenes SET anticipo = ?, saldo_pendiente = ? WHERE id = ?",
                (nuevo_anticipo, nuevo_saldo, orden_id)
            )
            cursor.execute(
                """INSERT INTO pagos_orden (orden_id, monto, tipo_pago, concepto)
                   VALUES (?, ?, 'ANTICIPO', ?)""",
                (orden_id, monto_anticipo, f"Anticipo registrado {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            )
            conn.commit()

            return {
                'orden_id': orden_id,
                'anticipo_anterior': float(orden['anticipo'] or 0.0),
                'anticipo_nuevo': nuevo_anticipo,
                'saldo_pendiente': nuevo_saldo
            }

    @staticmethod
    def registrar_pago_saldo(orden_id: int, monto_pagado: float) -> dict:
        """Registra el pago del saldo pendiente y marca orden como completada."""
        monto_pagado = ProductValidator.validate_price(monto_pagado, "Monto pagado")

        with get_connection() as conn:
            cursor = conn.cursor()
            orden = cursor.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()

            if not orden:
                raise ValidationError(f"Orden {orden_id} no existe.")

            saldo_actual = float(orden['saldo_pendiente'] or 0.0)
            if monto_pagado > saldo_actual:
                raise ValidationError(f"El monto pagado ({monto_pagado}) excede el saldo pendiente ({saldo_actual}).")

            nuevo_saldo = saldo_actual - monto_pagado
            nuevo_estado = 'COMPLETADA' if nuevo_saldo == 0.0 else orden['estado']

            cursor.execute(
                "UPDATE ordenes SET saldo_pendiente = ?, estado = ? WHERE id = ?",
                (nuevo_saldo, nuevo_estado, orden_id)
            )
            cursor.execute(
                """INSERT INTO pagos_orden (orden_id, monto, tipo_pago, concepto)
                   VALUES (?, ?, 'PAGO_SALDO', ?)""",
                (orden_id, monto_pagado, f"Pago de saldo {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            )
            conn.commit()

            return {
                'orden_id': orden_id,
                'monto_pagado': monto_pagado,
                'saldo_anterior': saldo_actual,
                'saldo_nuevo': nuevo_saldo,
                'estado': nuevo_estado
            }

    @staticmethod
    def cambiar_estado_orden(orden_id: int, nuevo_estado: str) -> None:
        """Cambia el estado de una orden."""
        nuevo_estado = nuevo_estado.upper()
        if nuevo_estado not in OrderService.ESTADOS:
            raise ValidationError(f"Estado debe ser uno de: {', '.join(OrderService.ESTADOS)}")

        with get_connection() as conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                raise ValidationError(f"Orden {orden_id} no existe.")

            conn.execute(
                "UPDATE ordenes SET estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?",
                (nuevo_estado, orden_id)
            )
            conn.commit()

    @staticmethod
    def get_resumen_ordenes_pendientes() -> dict:
        """Obtiene resumen de órdenes pendientes de pago."""
        with get_connection() as conn:
            ordenes = conn.execute(
                """SELECT COUNT(*) as total_ordenes, SUM(saldo_pendiente) as saldo_total
                   FROM ordenes WHERE estado != 'COMPLETADA' AND estado != 'CANCELADA'"""
            ).fetchone()

            return {
                'total_ordenes': ordenes['total_ordenes'] or 0,
                'saldo_total_pendiente': float(ordenes['saldo_total'] or 0.0)
            }

    @staticmethod
    def get_ordenes_por_rango_fechas(fecha_inicio: str, fecha_fin: str) -> list:
        """Obtiene órdenes en un rango de fechas."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM ordenes
                   WHERE DATE(fecha_creacion) >= ? AND DATE(fecha_creacion) <= ?
                   ORDER BY fecha_creacion DESC""",
                (fecha_inicio, fecha_fin)
            ).fetchall()
            return [dict(row) for row in rows]


__all__ = ['OrderService']
