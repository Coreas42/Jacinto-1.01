"""
Módulo de clientes para registrar información de clientes y posibles compradores.
"""

from src.database.connection import get_connection
from src.core.validators import ValidationError


class ClientService:
    """Gestiona clientes y su información. """

    @staticmethod
    def create_client(nombre: str, telefono: str, ubicacion: str = "", direccion: str = "", notas: str = "") -> int:
        """Crea un cliente con información básica."""
        nombre = (nombre or '').strip()
        telefono = (telefono or '').strip()
        if not nombre:
            raise ValidationError("El nombre del cliente es obligatorio.")
        if not telefono:
            raise ValidationError("El teléfono del cliente es obligatorio.")

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO clientes (nombre, telefono, ubicacion, direccion, notas)
                   VALUES (?, ?, ?, ?, ?)""",
                (nombre, telefono, ubicacion or '', direccion or '', notas or '')
            )
            cliente_id = cursor.lastrowid
            conn.commit()
            return cliente_id

    @staticmethod
    def get_client(cliente_id: int) -> dict:
        """Obtiene un cliente por ID."""
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def search_clients(query: str) -> list:
        """Busca clientes por nombre, teléfono o ubicación."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM clientes
                   WHERE nombre LIKE ? OR telefono LIKE ? OR ubicacion LIKE ?
                   ORDER BY nombre ASC LIMIT 100""",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def update_client(cliente_id: int, nombre: str, telefono: str, ubicacion: str = "", direccion: str = "", notas: str = "") -> None:
        """Actualiza un cliente."""
        nombre = (nombre or '').strip()
        telefono = (telefono or '').strip()
        if not nombre:
            raise ValidationError("El nombre del cliente es obligatorio.")
        if not telefono:
            raise ValidationError("El teléfono del cliente es obligatorio.")

        with get_connection() as conn:
            conn.execute(
                """UPDATE clientes
                   SET nombre = ?, telefono = ?, ubicacion = ?, direccion = ?, notas = ?
                   WHERE id = ?""",
                (nombre, telefono, ubicacion or '', direccion or '', notas or '', cliente_id)
            )
            conn.commit()

    @staticmethod
    def get_all_clients() -> list:
        """Obtiene todos los clientes."""
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM clientes ORDER BY nombre ASC").fetchall()
            return [dict(r) for r in rows]


__all__ = ['ClientService']
