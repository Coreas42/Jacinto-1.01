import os
import sys

def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta a recursos internos (empaquetados o en desarrollo)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_storage_path(filename: str = "") -> str:
    """Obtiene una ruta persistente en la carpeta de ejecución del usuario."""
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    if filename:
        return os.path.join(base_dir, filename)
    return base_dir
