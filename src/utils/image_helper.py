import os
import shutil
from PIL import Image
import customtkinter as ctk
from src.utils.path_helper import get_storage_path

def get_images_dir() -> str:
    img_dir = get_storage_path("product_images")
    os.makedirs(img_dir, exist_ok=True)
    return img_dir

def save_product_image(source_file_path: str, sku: str) -> str:
    """Copia la foto seleccionada a product_images/{sku}.ext y retorna su ruta relativa."""
    if not source_file_path or not os.path.exists(source_file_path):
        return ""
    
    img_dir = get_images_dir()
    _, ext = os.path.splitext(source_file_path)
    clean_sku = "".join(c for c in sku if c.isalnum() or c in ('-', '_')).strip()
    dest_filename = f"{clean_sku}{ext.lower()}"
    dest_path = os.path.join(img_dir, dest_filename)

    shutil.copy2(source_file_path, dest_path)
    return os.path.join("product_images", dest_filename)

def load_ctk_image(relative_path: str, size: tuple = (100, 100)) -> ctk.CTkImage:
    """Carga y redimensiona la foto. Si no existe o falla, retorna un placeholder oscuro."""
    if relative_path:
        full_path = get_storage_path(relative_path)
        if os.path.exists(full_path):
            try:
                pil_img = Image.open(full_path)
                return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            except Exception:
                pass
    
    blank = Image.new("RGBA", size, "#252538")
    return ctk.CTkImage(light_image=blank, dark_image=blank, size=size)
