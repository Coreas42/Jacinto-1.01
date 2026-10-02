import os
import shutil
import sqlite3
from datetime import datetime
from src.utils.path_helper import get_storage_path
from src.database.connection import DB_PATH

class BackupManager:
    @staticmethod
    def get_backup_dir() -> str:
        backup_dir = get_storage_path("backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @classmethod
    def create_automatic_backup(cls) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_garage_{timestamp}.db"
        dest_path = os.path.join(cls.get_backup_dir(), backup_filename)

        with sqlite3.connect(DB_PATH) as src_conn:
            with sqlite3.connect(dest_path) as dest_conn:
                src_conn.backup(dest_conn)
        return dest_path

    @classmethod
    def restore_backup(cls, source_file_path: str):
        if not os.path.exists(source_file_path):
            raise FileNotFoundError("El archivo de respaldo seleccionado no existe.")
        cls.create_automatic_backup()  # Respaldo de seguridad previo
        shutil.copy2(source_file_path, DB_PATH)
