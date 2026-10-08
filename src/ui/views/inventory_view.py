import customtkinter as ctk
from tkinter import messagebox

from src.database.connection import get_connection
from src.services.product_service import ProductService
from src.core.validators import ProductValidator, ValidationError


class InventoryView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.selected_product_id = None
        self.temp_image_file = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        form = ctk.CTkScrollableFrame(self, fg_color="#181824", corner_radius=10)
        form.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.lbl_form_title = ctk.CTkLabel(
            form,
            text="Nuevo Producto / Servicio",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#8A2BE2"
        )
        self.lbl_form_title.pack(pady=10)

        self.img_preview = ctk.CTkLabel(form, text="", image=load_ctk_image("", (110, 110)))
        self.img_preview.pack(pady=4)

        btn_select_img = ctk.CTkButton(
            form, text="Seleccionar Foto", fg_color="#3A3A54", hover_color="#7B1FA2",
            command=self._pick_image
        )
        btn_select_img.pack(fill="x", padx=15, pady=4)

        self.ent_sku = ctk.CTkEntry(form, placeholder_text="SKU / Código Único")
        self.ent_sku.pack(fill="x", padx=15, pady=4)

        self.ent_nombre = ctk.CTkEntry(form, placeholder_text="Nombre del Producto / Servicio")
        self.ent_nombre.pack(fill="x", padx=15, pady=4)

        self.ent_categoria = ctk.CTkEntry(form, placeholder_text="Categoría (Alfombras, Lonas, etc.)")
        self.ent_categoria.pack(fill="x", padx=15, pady=4)

        self.ent_marca = ctk.CTkEntry(form, placeholder_text="Marca Vehículo (ej. Toyota, Universal)")
        self.ent_marca.pack(fill="x", padx=15, pady=4)

        self.ent_anio = ctk.CTkEntry(form, placeholder_text="Año Compatible (ej. 2016-2024, Todos)")
        self.ent_anio.pack(fill="x", padx=15, pady=4)

        self.combo_tipo = ctk.CTkOptionMenu(
            form, values=["FISICO", "SERVICIO"], command=self._toggle_tipo,
            fg_color="#252538", button_color="#7B1FA2"
        )
        self.combo_tipo.pack(fill="x", padx=15, pady=4)

        self.ent_costo = ctk.CTkEntry(form, placeholder_text="Costo Unitario ($)")
        self.ent_costo.pack(fill="x", padx=15, pady=4)
        self.ent_costo.bind("<KeyRelease>", self._calc_margin)

        self.ent_precio = ctk.CTkEntry(form, placeholder_text="Precio de Venta ($)")
        self.ent_precio.pack(fill="x", padx=15, pady=4)
        self.ent_precio.bind("<KeyRelease>", self._calc_margin)

        self.lbl_margin = ctk.CTkLabel(form, text="Margen: $0.00 (0%)", font=ctk.CTkFont(size=12), text_color="#A0A0B0")
        self.lbl_margin.pack(pady=2)

        self.ent_stock = ctk.CTkEntry(form, placeholder_text="Stock Actual")
        self.ent_stock.pack(fill="x", padx=15, pady=4)

        self.ent_min = ctk.CTkEntry(form, placeholder_text="Stock Mínimo de Alerta")
        self.ent_min.pack(fill="x", padx=15, pady=4)

        self.btn_action = ctk.CTkButton(
            form, text="GUARDAR ARTÍCULO", fg_color="#8A2BE2", hover_color="#7B1FA2",
            height=38, command=self._save_or_update
        )
        self.btn_action.pack(fill="x", padx=15, pady=(12, 4))

        self.btn_cancel = ctk.CTkButton(
            form, text="Limpiar Formulario", fg_color="transparent", border_width=1,
            border_color="#555566", command=self._reset_form
        )
        self.btn_cancel.pack(fill="x", padx=15, pady=4)

        self.btn_delete = ctk.CTkButton(
            form, text="Eliminar Producto", fg_color="#C62828", hover_color="#8E0000",
            command=self._delete_product
        )

        right_panel = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        search_bar = ctk.CTkFrame(right_panel, fg_color="transparent")
        search_bar.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Buscar por SKU, Nombre o Vehículo...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_data())

        self.table_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="#1E1E2E")
        self.table_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _toggle_tipo(self, choice):
        if choice == "SERVICIO":
            self.ent_stock.delete(0, 'end')
            self.ent_stock.insert(0, "0")
            self.ent_min.delete(0, 'end')
            self.ent_min.insert(0, "0")
            self.ent_stock.configure(state="disabled")
            self.ent_min.configure(state="disabled")
        else:
            self.ent_stock.configure(state="normal")
            self.ent_min.configure(state="normal")

    def _calc_margin(self, event=None):
        try:
            costo = float(self.ent_costo.get() or 0.0)
            precio = float(self.ent_precio.get() or 0.0)
            gain = precio - costo
            pct = (gain / precio * 100) if precio > 0 else 0
            self.lbl_margin.configure(
                text=f"Margen: ${gain:.2f} ({pct:.1f}%)",
                text_color="#00E5FF" if gain >= 0 else "#FF5252"
            )
        except ValueError:
            self.lbl_margin.configure(text="Margen: $0.00 (0%)")

    def _pick_image(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(
            title="Seleccionar Foto",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp")]
        )
        if f:
            self.temp_image_file = f
            preview = load_ctk_image(f, (110, 110))
            self.img_preview.configure(image=preview)

    def _save_or_update(self):
        sku = self.ent_sku.get().strip()
        nombre = self.ent_nombre.get().strip()

        if not sku or not nombre:
            messagebox.showwarning("Atención", "El SKU y Nombre son obligatorios.")
            return

        try:
            categoria = self.ent_categoria.get().strip() or "General"
            marca = self.ent_marca.get().strip() or "Universal"
            anio = self.ent_anio.get().strip() or "Todos"
            tipo = self.combo_tipo.get()
            costo = float(self.ent_costo.get() or 0.0)
            precio = float(self.ent_precio.get() or 0.0)
            stock = int(self.ent_stock.get() or 0) if tipo == 'FISICO' else 0
            s_min = int(self.ent_min.get() or 3) if tipo == 'FISICO' else 0

            ProductValidator.validate_product_data(sku, nombre, tipo, costo, precio, stock, s_min)
            if precio <= 0:
                raise ValidationError("Precio de venta debe ser mayor que cero.")

            rel_img = save_product_image(self.temp_image_file, sku) if self.temp_image_file else ""

            if self.selected_product_id:
                ProductService.update_product(
                    self.selected_product_id, sku, nombre, categoria, marca, anio, tipo,
                    costo, precio, stock, s_min, rel_img
                )
                msg = "Producto actualizado correctamente."
            else:
                ProductService.create_product(
                    sku, nombre, categoria, marca, anio, tipo, costo, precio,
                    stock, s_min, rel_img
                )
                msg = "Producto registrado con éxito."

            messagebox.showinfo("Éxito", msg)
            self._reset_form()
            self.refresh_data()
        except (ValidationError, ValueError) as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def _select_product_for_edit(self, prod: dict):
        self.selected_product_id = prod['id']
        self.lbl_form_title.configure(text=f"Modificar Art #{prod['id']}")
        self.btn_action.configure(text="ACTUALIZAR PRODUCTO")
        self.btn_delete.pack(fill="x", padx=15, pady=4)

        self._reset_fields_only()
        self.ent_sku.insert(0, prod['sku'])
        self.ent_nombre.insert(0, prod['nombre'])
        self.ent_categoria.insert(0, prod['categoria'])
        self.ent_marca.insert(0, prod['marca_vehiculo'])
        self.ent_anio.insert(0, prod['anio_vehiculo'])
        self.combo_tipo.set(prod['tipo'])
        self._toggle_tipo(prod['tipo'])
        self.ent_costo.insert(0, str(prod['costo']))
        self.ent_precio.insert(0, str(prod['precio']))
        self._calc_margin()

        if prod['tipo'] == 'FISICO':
            self.ent_stock.insert(0, str(prod['stock_actual']))
            self.ent_min.insert(0, str(prod['stock_minimo']))

        self.temp_image_file = ""
        self.img_preview.configure(image=load_ctk_image(prod['imagen_path'], (110, 110)))

    def _delete_product(self):
        if not self.selected_product_id:
            return
        if messagebox.askyesno("Confirmar", "¿Deseas eliminar permanentemente este producto del catálogo?"):
            ProductService.deactivate_product(self.selected_product_id)
            messagebox.showinfo("Eliminado", "El producto ha sido dado de baja.")
            self._reset_form()
            self.refresh_data()

    def _reset_fields_only(self):
        for e in (self.ent_sku, self.ent_nombre, self.ent_categoria, self.ent_marca, self.ent_anio, self.ent_costo, self.ent_precio, self.ent_stock, self.ent_min):
            e.configure(state="normal")
            e.delete(0, 'end')

    def _reset_form(self):
        self.selected_product_id = None
        self.temp_image_file = ""
        self.lbl_form_title.configure(text="Nuevo Producto / Servicio")
        self.btn_action.configure(text="GUARDAR ARTÍCULO")
        self.btn_delete.pack_forget()
        self._reset_fields_only()
        self.combo_tipo.set("FISICO")
        self._toggle_tipo("FISICO")
        self.lbl_margin.configure(text="Margen: $0.00 (0%)")
        self.img_preview.configure(image=load_ctk_image("", (110, 110)))

    def refresh_data(self):
        for w in self.table_scroll.winfo_children():
            w.destroy()

        q = self.search_entry.get().strip()
        rows = ProductService.search_products(q)

        for prod in rows:
            p_dict = prod
            card = ctk.CTkFrame(self.table_scroll, fg_color="#252538", corner_radius=6)
            card.pack(fill="x", pady=3, padx=4)

            thumb = load_ctk_image(p_dict['imagen_path'], (45, 45))
            lbl_pic = ctk.CTkLabel(card, text="", image=thumb)
            lbl_pic.pack(side="left", padx=8, pady=4)

            stock_text = f"Stock: {p_dict['stock_actual']}" if p_dict['tipo'] == 'FISICO' else "[SERVICIO]"
            info = (
                f"{p_dict['sku']} | {p_dict['nombre']}\n"
                f"Auto: {p_dict['marca_vehiculo']} ({p_dict['anio_vehiculo']})  |  "
                f"PVP: ${p_dict['precio']:.2f}  |  {stock_text}"
            )
            lbl_txt = ctk.CTkLabel(card, text=info, justify="left", font=ctk.CTkFont(size=12))
            lbl_txt.pack(side="left", padx=6, pady=4, fill="x", expand=True)

            btn_edit = ctk.CTkButton(
                card, text="Editar", width=65, fg_color="#3A3A54", hover_color="#7B1FA2",
                command=lambda p=p_dict: self._select_product_for_edit(p)
            )
            btn_edit.pack(side="right", padx=8)


from src.utils.image_helper import save_product_image, load_ctk_image
from src.core.validators import ProductValidator, ValidationError
