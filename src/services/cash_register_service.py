"""
Servicio de gestión de caja y turnos.
Centraliza toda la lógica de negocio relacionada con arqueos y cierres de turno.
"""

from src.database.connection import get_connection
from src.core.validators import CashRegisterValidator, ValidationError


class CashRegisterService:
    """Gestiona todas las operaciones de caja y turnos."""

    @staticmethod
    def open_turn(fondo_inicial: float = 100.0) -> dict:
        """Abre un nuevo turno."""
        fondo_inicial = CashRegisterValidator.validate_initial_fund(fondo_inicial)
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO turnos_caja (fondo_inicial, estado) VALUES (?, 'ABIERTO')",
                (fondo_inicial,)
            )
            conn.commit()
            turno = conn.execute(
                "SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(turno) if turno else None

    @staticmethod
    def get_open_turn() -> dict:
        """Obtiene el turno abierto actual."""
        with get_connection() as conn:
            turno = conn.execute(
                "SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(turno) if turno else None

    @staticmethod
    def get_turn_summary(turno_id: int) -> dict:
        """Obtiene resumen de un turno."""
        with get_connection() as conn:
            turno = conn.execute("SELECT * FROM turnos_caja WHERE id = ?", (turno_id,)).fetchone()
            if not turno:
                raise ValidationError(f"Turno {turno_id} no existe.")

            ventas = conn.execute(
                """SELECT metodo_pago, COUNT(*) as cantidad, SUM(total) as monto
                   FROM ventas WHERE turno_id = ? GROUP BY metodo_pago""",
                (turno_id,)
            ).fetchall()

            resumen_pagos = {}
            total_vendido = 0.0
            for row in ventas:
                resumen_pagos[row['metodo_pago']] = {
                    'cantidad': row['cantidad'],
                    'monto': float(row['monto'] or 0.0),
                }
                total_vendido += float(row['monto'] or 0.0)

            efectivo_ventas = float(resumen_pagos.get('EFECTIVO', {}).get('monto', 0.0))
            esperado_efectivo = float(turno['fondo_inicial'] or 0.0) + efectivo_ventas
            return {
                'turno': dict(turno),
                'resumen_pagos': resumen_pagos,
                'total_vendido': total_vendido,
                'efectivo_esperado': esperado_efectivo,
                'efectivo_ventas': efectivo_ventas,
            }

    @staticmethod
    def close_turn(turno_id: int, efectivo_contado: float) -> dict:
        """Cierra un turno y registra la diferencia de caja."""
        efectivo_contado = CashRegisterValidator.validate_cash_amount(efectivo_contado)

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                turno = cursor.execute("SELECT * FROM turnos_caja WHERE id = ?", (turno_id,)).fetchone()
                if not turno:
                    raise ValidationError(f"Turno {turno_id} no existe.")
                if turno['estado'] != 'ABIERTO':
                    raise ValidationError("El turno ya está cerrado.")

                ventas_ef = cursor.execute(
                    "SELECT SUM(total) as tot FROM ventas WHERE turno_id = ? AND metodo_pago = 'EFECTIVO'",
                    (turno_id,)
                ).fetchone()['tot'] or 0.0

                esperado = float(turno['fondo_inicial'] or 0.0) + float(ventas_ef or 0.0)
                diferencia = efectivo_contado - esperado

                cursor.execute(
                    """UPDATE turnos_caja
                       SET fecha_cierre = CURRENT_TIMESTAMP, efectivo_declarado = ?, diferencia = ?, estado = 'CERRADO'
                       WHERE id = ?""",
                    (efectivo_contado, diferencia, turno_id)
                )
                cursor.execute(
                    "INSERT INTO turnos_caja (fondo_inicial, estado) VALUES (100.0, 'ABIERTO')"
                )
                conn.commit()

                return {
                    'turno_id': turno_id,
                    'fondo_inicial': float(turno['fondo_inicial'] or 0.0),
                    'efectivo_ventas': float(ventas_ef or 0.0),
                    'esperado': esperado,
                    'contado': efectivo_contado,
                    'diferencia': diferencia,
                    'status': 'CERRADO',
                }
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_turn_history(limit: int = 10) -> list:
        """Obtiene los últimos turnos cerrados."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM turnos_caja WHERE estado = 'CERRADO'
                   ORDER BY fecha_cierre DESC LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_cash_summary_by_date(fecha: str) -> dict:
        """Obtiene resumen de caja para una fecha."""
        with get_connection() as conn:
            turnos = conn.execute(
                """SELECT * FROM turnos_caja
                   WHERE DATE(fecha_apertura) = ? OR DATE(fecha_cierre) = ?
                   ORDER BY id DESC""",
                (fecha, fecha)
            ).fetchall()

            total_esperado = 0.0
            total_contado = 0.0
            total_diferencia = 0.0
            for turno in turnos:
                if turno['fondo_inicial']:
                    total_esperado += float(turno['fondo_inicial'])
                if turno['efectivo_declarado']:
                    total_contado += float(turno['efectivo_declarado'])
                if turno['diferencia']:
                    total_diferencia += float(turno['diferencia'])

            return {
                'fecha': fecha,
                'turnos_count': len(turnos),
                'total_esperado': total_esperado,
                'total_contado': total_contado,
                'total_diferencia': total_diferencia,
                'turnos': [dict(t) for t in turnos],
            }


__all__ = ['CashRegisterService']
