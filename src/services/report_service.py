"""
Servicio de reportes y análisis de negocio.
Centraliza la lógica para generar reportes de ventas, ganancias e inventario.
"""

from datetime import datetime, timedelta
from src.database.connection import get_connection


class ReportService:
    """Genera reportes y análisis de negocio."""

    @staticmethod
    def get_profit_and_loss(fecha_inicio: str = None, fecha_fin: str = None) -> dict:
        """Obtiene estado de resultados de un intervalo de fechas."""
        if not fecha_inicio or not fecha_fin:
            hoy = datetime.now()
            fecha_fin = hoy.strftime('%Y-%m-%d')
            fecha_inicio = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')

        with get_connection() as conn:
            ventas = conn.execute(
                "SELECT SUM(total) as tot FROM ventas WHERE DATE(fecha) >= ? AND DATE(fecha) <= ?",
                (fecha_inicio, fecha_fin)
            ).fetchone()['tot'] or 0.0

            cogs = conn.execute(
                """SELECT SUM(costo_unitario * cantidad) as cogs
                   FROM ventas_detalle vd
                   JOIN ventas v ON vd.venta_id = v.id
                   WHERE DATE(v.fecha) >= ? AND DATE(v.fecha) <= ?""",
                (fecha_inicio, fecha_fin)
            ).fetchone()['cogs'] or 0.0

            gastos = conn.execute(
                "SELECT SUM(monto) as tot FROM gastos WHERE DATE(fecha) >= ? AND DATE(fecha) <= ?",
                (fecha_inicio, fecha_fin)
            ).fetchone()['tot'] or 0.0

            margen_bruto = float(ventas) - float(cogs)
            utilidad_neta = margen_bruto - float(gastos)

            return {
                'periodo': f"{fecha_inicio} a {fecha_fin}",
                'ventas_brutas': float(ventas),
                'costo_mercancia_vendida': float(cogs),
                'margen_bruto': margen_bruto,
                'gastos_operativos': float(gastos),
                'utilidad_neta': utilidad_neta,
                'margen_bruto_pct': (margen_bruto / float(ventas) * 100) if ventas > 0 else 0,
                'utilidad_neta_pct': (utilidad_neta / float(ventas) * 100) if ventas > 0 else 0,
            }

    @staticmethod
    def get_low_stock_alert() -> list:
        """Obtiene productos con stock bajo."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT id, sku, nombre, stock_actual, stock_minimo, precio
                   FROM productos
                   WHERE activo = 1 AND tipo = 'FISICO' AND stock_actual <= stock_minimo
                   ORDER BY stock_actual ASC"""
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_inventory_value() -> dict:
        """Calcula valor total del inventario."""
        with get_connection() as conn:
            inv = conn.execute(
                """SELECT COUNT(id) as total_items,
                          SUM(stock_actual) as total_units,
                          SUM(stock_actual * costo) as valor_costo,
                          SUM(stock_actual * precio) as valor_venta
                   FROM productos WHERE activo = 1 AND tipo = 'FISICO'"""
            ).fetchone()
            return {
                'total_items': inv['total_items'] or 0,
                'total_units': inv['total_units'] or 0,
                'valor_costo': float(inv['valor_costo'] or 0.0),
                'valor_venta': float(inv['valor_venta'] or 0.0),
                'margen_inventario': float(inv['valor_venta'] or 0.0) - float(inv['valor_costo'] or 0.0),
            }

    @staticmethod
    def get_best_sellers(limit: int = 10, fecha_inicio: str = None, fecha_fin: str = None) -> list:
        """Obtiene los productos más vendidos."""
        if not fecha_inicio or not fecha_fin:
            hoy = datetime.now()
            fecha_fin = hoy.strftime('%Y-%m-%d')
            fecha_inicio = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')

        with get_connection() as conn:
            rows = conn.execute(
                """SELECT p.id, p.sku, p.nombre, SUM(vd.cantidad) as cantidad_vendida,
                          SUM(vd.subtotal) as monto_vendido
                   FROM ventas_detalle vd
                   JOIN productos p ON vd.producto_id = p.id
                   JOIN ventas v ON vd.venta_id = v.id
                   WHERE DATE(v.fecha) >= ? AND DATE(v.fecha) <= ?
                   GROUP BY p.id
                   ORDER BY cantidad_vendida DESC
                   LIMIT ?""",
                (fecha_inicio, fecha_fin, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_sales_trend(days: int = 30) -> list:
        """Obtiene la tendencia de ventas de los últimos días."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT DATE(fecha) as fecha, COUNT(*) as cantidad, SUM(total) as monto
                   FROM ventas
                   WHERE fecha >= datetime('now', '-' || ? || ' days')
                   GROUP BY DATE(fecha)
                   ORDER BY fecha DESC""",
                (days,)
            ).fetchall()
            return [{'fecha': row['fecha'], 'cantidad': row['cantidad'], 'monto': float(row['monto'] or 0.0)} for row in rows]


__all__ = ['ReportService']
