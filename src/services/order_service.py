"""
Servicio para clientes, pedidos y agenda.
Centraliza la gestión operativa de clientes, seguimiento de pedidos y citas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.connection import get_connection
from src.core.validators import (
    CustomerValidator,
    OrderValidator,
    AgendaValidator,
    ValidationError,
)


class CustomerService:
    """Gestión de clientes del negocio."""

    @staticmethod
    def create_customer(nombre: str, telefono: str = "", correo: str = "",
                       direccion: str = "", ciudad: str = "", notas: str = "") -> int:
        data = CustomerValidator.validate_customer_data(nombre, telefono, correo, direccion, ciudad, notas)

        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO clientes (nombre, telefono, correo, direccion, ciudad, notas)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data['nombre'],
                    data['telefono'],
                    data['correo'],
                    data['direccion'],
                    data['ciudad'],
                    data['notas'],
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:
        if not customer_id:
            return None
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM clientes WHERE id = ? AND activo = 1",
                (customer_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_customers(search: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        query = "SELECT * FROM clientes WHERE activo = 1"
        params: list[Any] = []

        if search:
            search = f"%{search.strip()}%"
            query += " AND (nombre LIKE ? OR telefono LIKE ? OR correo LIKE ? OR ciudad LIKE ?)"
            params.extend([search, search, search, search])

        query += " ORDER BY nombre ASC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def update_customer(customer_id: int, **fields):
        if not customer_id:
            raise ValidationError("Debe indicar un cliente válido.")

        current = CustomerService.get_customer(customer_id)
        if not current:
            raise ValidationError("Cliente no encontrado.")

        updates = {}
        for key, value in fields.items():
            if value is None:
                continue
            if key == 'nombre':
                updates['nombre'] = CustomerValidator.validate_name(value)
            elif key == 'telefono':
                updates['telefono'] = CustomerValidator.validate_phone(value)
            elif key == 'correo':
                updates['correo'] = CustomerValidator.validate_email(value)
            elif key == 'direccion':
                updates['direccion'] = (value or '').strip()[:200]
            elif key == 'ciudad':
                updates['ciudad'] = (value or '').strip()[:100]
            elif key == 'notas':
                updates['notas'] = (value or '').strip()[:500]

        if not updates:
            return current

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [customer_id]

        with get_connection() as conn:
            conn.execute(f"UPDATE clientes SET {set_clause} WHERE id = ?", values)
            return CustomerService.get_customer(customer_id)

    @staticmethod
    def delete_customer(customer_id: int):
        if not customer_id:
            raise ValidationError("Debe indicar un cliente válido.")

        with get_connection() as conn:
            conn.execute("UPDATE clientes SET activo = 0 WHERE id = ?", (customer_id,))
            return True


class OrderService:
    """Gestión de pedidos y pagos."""

    @staticmethod
    def _build_order_number() -> str:
        now = datetime.now()
        return f"PED-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

    @staticmethod
    def create_order(cliente_id: int, items: list, tipo_entrega: str = "ENVIO",
                     fecha_entrega=None, descuento: float = 0.0, envio: float = 0.0,
                     metodo_pago: str = "EFECTIVO", notas: str = "") -> int:
        data = OrderValidator.validate_order_data(
            cliente_id=cliente_id,
            items=items,
            tipo_entrega=tipo_entrega,
            descuento=descuento,
            envio=envio,
            anticipo=0.0,
            notas=notas,
        )

        numero_pedido = OrderService._build_order_number()

        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pedidos (
                    cliente_id, numero_pedido, fecha_entrega, tipo_entrega,
                    subtotal, descuento, envio, total, anticipo, saldo_pendiente,
                    estado, metodo_pago, notas
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data['cliente_id'],
                    numero_pedido,
                    fecha_entrega,
                    data['tipo_entrega'],
                    data['subtotal'],
                    data['descuento'],
                    data['envio'],
                    data['total'],
                    data['anticipo'],
                    data['saldo_pendiente'],
                    'PENDIENTE',
                    metodo_pago.upper(),
                    data['notas'],
                ),
            )
            pedido_id = cursor.lastrowid

            for item in items:
                validated = OrderValidator.validate_item(item)
                conn.execute(
                    """
                    INSERT INTO pedido_items (
                        pedido_id, producto_id, nombre, descripcion, cantidad,
                        precio_unitario, costo_unitario, subtotal
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pedido_id,
                        validated.get('producto_id'),
                        validated.get('nombre'),
                        validated.get('descripcion'),
                        validated.get('cantidad'),
                        validated.get('precio_unitario'),
                        validated.get('costo_unitario'),
                        validated.get('subtotal'),
                    ),
                )

            return pedido_id

    @staticmethod
    def get_order(order_id: int) -> Optional[Dict[str, Any]]:
        if not order_id:
            return None

        with get_connection() as conn:
            order = conn.execute(
                "SELECT * FROM pedidos WHERE id = ? AND activo = 1",
                (order_id,),
            ).fetchone()
            if not order:
                return None

            items = conn.execute(
                "SELECT * FROM pedido_items WHERE pedido_id = ? ORDER BY id ASC",
                (order_id,),
            ).fetchall()
            payments = conn.execute(
                "SELECT * FROM pagos_pedido WHERE pedido_id = ? ORDER BY fecha DESC",
                (order_id,),
            ).fetchall()
            customer = conn.execute(
                "SELECT * FROM clientes WHERE id = ?",
                (order['cliente_id'],),
            ).fetchone()

            result = dict(order)
            result['items'] = [dict(item) for item in items]
            result['pagos'] = [dict(payment) for payment in payments]
            result['cliente'] = dict(customer) if customer else None
            return result

    @staticmethod
    def list_orders(estado: str = None, cliente_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = "SELECT * FROM pedidos WHERE activo = 1"
        params: list[Any] = []

        if estado:
            query += " AND estado = ?"
            params.append(estado.upper())
        if cliente_id:
            query += " AND cliente_id = ?"
            params.append(cliente_id)

        query += " ORDER BY fecha_creacion DESC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def update_order_status(order_id: int, estado: str, fecha_entrega=None):
        if not order_id:
            raise ValidationError("Debe indicar un pedido válido.")
        status = OrderValidator.validate_status(estado)

        with get_connection() as conn:
            conn.execute(
                "UPDATE pedidos SET estado = ?, fecha_entrega = COALESCE(?, fecha_entrega) WHERE id = ?",
                (status, fecha_entrega, order_id),
            )
            return OrderService.get_order(order_id)

    @staticmethod
    def add_payment(order_id: int, monto: float, metodo_pago: str = "EFECTIVO",
                    tipo: str = "ANTICIPO", referencia: str = "") -> Dict[str, Any]:
        if not order_id:
            raise ValidationError("Debe indicar un pedido válido.")

        amount = OrderValidator.validate_money(monto, "Monto del pago")
        valid_tipo = ('ANTICIPO', 'PAGO', 'DEVOLUCION')
        tipo = (tipo or 'ANTICIPO').strip().upper()
        if tipo not in valid_tipo:
            raise ValidationError(f"Tipo de pago no válido. Opciones: {', '.join(valid_tipo)}")

        with get_connection() as conn:
            order = conn.execute(
                "SELECT total, anticipo, saldo_pendiente FROM pedidos WHERE id = ? AND activo = 1",
                (order_id,),
            ).fetchone()
            if not order:
                raise ValidationError("Pedido no encontrado.")

            new_anticipo = order['anticipo'] + amount if tipo == 'ANTICIPO' else order['anticipo']
            saldo = round(order['total'] - new_anticipo, 2)

            conn.execute(
                """
                INSERT INTO pagos_pedido (pedido_id, monto, metodo_pago, tipo, referencia)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, amount, metodo_pago.upper(), tipo, referencia),
            )
            conn.execute(
                "UPDATE pedidos SET anticipo = ?, saldo_pendiente = ? WHERE id = ?",
                (new_anticipo, saldo, order_id),
            )

            return OrderService.get_order(order_id)

    @staticmethod
    def get_pending_orders() -> List[Dict[str, Any]]:
        return OrderService.list_orders(estado='PENDIENTE') + OrderService.list_orders(estado='CONFIRMADO')

    @staticmethod
    def cancel_order(order_id: int, motivo: str = ""):
        if not order_id:
            raise ValidationError("Debe indicar un pedido válido.")

        with get_connection() as conn:
            conn.execute(
                "UPDATE pedidos SET estado = 'CANCELADO', notas = COALESCE(?, notas) WHERE id = ?",
                (motivo, order_id),
            )
            return OrderService.get_order(order_id)


class AgendaService:
    """Gestión de agenda y citas de instalación/entrega."""

    @staticmethod
    def schedule_order(pedido_id: int, fecha_programada, tipo: str = "INSTALACION",
                      direccion: str = "", observaciones: str = "", estado: str = "PENDIENTE") -> int:
        data = AgendaValidator.validate_agenda_data(
            pedido_id=pedido_id,
            fecha_programada=fecha_programada,
            tipo=tipo,
            direccion=direccion,
            observaciones=observaciones,
            estado=estado,
        )

        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agenda_pedidos (pedido_id, fecha_programada, tipo, direccion, observaciones, estado)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data['pedido_id'],
                    data['fecha_programada'],
                    data['tipo'],
                    data['direccion'],
                    data['observaciones'],
                    data['estado'],
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def get_agenda(fecha_inicio=None, fecha_fin=None, limit: int = 100) -> List[Dict[str, Any]]:
        query = "SELECT * FROM agenda_pedidos WHERE 1 = 1"
        params: list[Any] = []

        if fecha_inicio:
            query += " AND fecha_programada >= ?"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND fecha_programada <= ?"
            params.append(fecha_fin)

        query += " ORDER BY fecha_programada ASC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def update_agenda(agenda_id: int, **fields):
        if not agenda_id:
            raise ValidationError("Debe indicar una cita válida.")
        updates = {}

        for key, value in fields.items():
            if value is None:
                continue
            if key == 'estado':
                updates['estado'] = AgendaValidator.validate_agenda_status(value)
            elif key == 'tipo':
                updates['tipo'] = AgendaValidator.validate_type(value)
            elif key == 'direccion':
                updates['direccion'] = AgendaValidator.validate_address(value)
            elif key == 'observaciones':
                updates['observaciones'] = AgendaValidator.validate_notes(value)
            elif key == 'fecha_programada':
                updates['fecha_programada'] = value

        if not updates:
            return None

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [agenda_id]

        with get_connection() as conn:
            conn.execute(f"UPDATE agenda_pedidos SET {set_clause} WHERE id = ?", values)
            return conn.execute("SELECT * FROM agenda_pedidos WHERE id = ?", (agenda_id,)).fetchone()


__all__ = ['CustomerService', 'OrderService', 'AgendaService']
