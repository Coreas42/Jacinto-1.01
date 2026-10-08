import customtkinter as ctk
from tkinter import messagebox

from src.services.product_service import ProductService
from src.services.sale_service import SaleService
from src.utils.image_helper import load_ctk_image


class POSView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.cart = []
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        left_panel = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        search_bar = ctk.CTkFrame(left_panel, fg_color="transparent")
        search_bar.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Buscar SKU, accesorio o vehículo...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self._search_product())

        btn_ver_todos = ctk.CTkButton(search_bar, text="Ver Todos", width=90, fg_color="#3A3A54", hover_color="#7B1FA2", command=self.refresh_data)
        btn_ver_todos.pack(side="right")

        self.results_box = ctk.CTkScrollableFrame(left_panel, fg_color="#1E1E2E")
        self.results_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        right_panel = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        ctk.CTkLabel(right_panel, text="Detalle de Ticket", font=ctk.CTkFont(size=16, weight="bold"), text_color="#8A2BE2").pack(pady=10)

        self.cart_box = ctk.CTkScrollableFrame(right_panel, fg_color="#1E1E2E")
        self.cart_box.pack(fill="both", expand=True, padx=10, pady=5)

        self.lbl_total = ctk.CTkLabel(right_panel, text="TOTAL: $0.00", font=ctk.CTkFont(size=22, weight="bold"), text_color="#00E5FF")
        self.lbl_total.pack(pady=8)

        self.payment_method = ctk.CTkOptionMenu(
            right_panel,
            values=["EFECTIVO", "TARJETA", "TRANSFERENCIA"],
            fg_color="#252538", button_color="#7B1FA2"
        )
        self.payment_method.pack(fill="x", padx=15, pady=5)

        btn_checkout = ctk.CTkButton(
            right_panel,
            text="COBRAR E IMPRIMIR",
            fg_color="#8A2BE2",
            hover_color="#7B1FA2",
            height=40,
            command=self._finalize_sale
        )
        btn_checkout.pack(fill="x", padx=15, pady=(10, 15))

    def refresh_data(self):
        self.search_entry.delete(0, 'end')
        self._search_product()

    def _search_product(self):
        q = self.search_entry.get().strip()
        for w in self.results_box.winfo_children():
            w.destroy()

        rows = ProductService.search_products(q)

        if not rows:
            ctk.CTkLabel(self.results_box, text="No se encontraron productos coincidentes.", text_color="#808090").pack(pady=20)
            return

        for prod in rows:
            p_dict = dict(prod)
            item_frame = ctk.CTkFrame(self.results_box, fg_color="#252538", corner_radius=6)
            item_frame.pack(fill="x", pady=3, padx=4)

            thumb = load_ctk_image(p_dict['imagen_path'], (50, 50))
            lbl_img = ctk.CTkLabel(item_frame, text="", image=thumb)
            lbl_img.pack(side="left", padx=8, pady=4)

            tipo_tag = "[SERVICIO]" if p_dict['tipo'] == 'SERVICIO' else f"Stock: {p_dict['stock_actual']}"
            txt = f"{p_dict['sku']} | {p_dict['nombre']}\nAuto: {p_dict['marca_vehiculo']} | ${p_dict['precio']:.2f} ({tipo_tag})"
            lbl_desc = ctk.CTkLabel(item_frame, text=txt, justify="left", font=ctk.CTkFont(size=12))
            lbl_desc.pack(side="left", padx=6, fill="x", expand=True)

            btn_add = ctk.CTkButton(
                item_frame, text="+ Añadir", width=75, fg_color="#8A2BE2", hover_color="#7B1FA2",
                command=lambda p=p_dict: self._add_to_cart(p)
            )
            btn_add.pack(side="right", padx=8)

    def _add_to_cart(self, prod: dict):
        for item in self.cart:
            if item['producto_id'] == prod['id']:
                if prod['tipo'] == 'FISICO' and (item['cantidad'] + 1) > prod['stock_actual']:
                    messagebox.showwarning("Existencias", f"Stock insuficiente para {prod['nombre']}.")
                    return
                item['cantidad'] += 1
                self._render_cart()
                return

        if prod['tipo'] == 'FISICO' and prod['stock_actual'] <= 0:
            messagebox.showwarning("Sin Stock", f"{prod['nombre']} no tiene existencias disponibles.")
            return

        self.cart.append({
            'producto_id': prod['id'],
            'nombre': prod['nombre'],
            'cantidad': 1,
            'precio_unitario': prod['precio'],
            'costo_unitario': prod['costo'],
            'tipo': prod['tipo']
        })
        self._render_cart()

    def _render_cart(self):
        for w in self.cart_box.winfo_children():
            w.destroy()

        total = 0.0
        for idx, item in enumerate(self.cart):
            sub = item['cantidad'] * item['precio_unitario']
            total += sub

            fila = ctk.CTkFrame(self.cart_box, fg_color="#252538")
            fila.pack(fill="x", pady=2, padx=2)

            lbl = ctk.CTkLabel(fila, text=f"{item['cantidad']}x {item['nombre']}\n${sub:.2f}", anchor="w", justify="left")
            lbl.pack(side="left", padx=8, pady=4, expand=True, fill="x")

            btn_del = ctk.CTkButton(
                fila, text="X", width=28, height=28, fg_color="#C62828", hover_color="#8E0000",
                command=lambda i=idx: self._remove_item(i)
            )
            btn_del.pack(side="right", padx=6)

        self.lbl_total.configure(text=f"TOTAL: ${total:.2f}")

    def _remove_item(self, index: int):
        self.cart.pop(index)
        self._render_cart()

    def _finalize_sale(self):
        if not self.cart:
            messagebox.showwarning("Aviso", "No hay artículos en el ticket.")
            return

        try:
            result = SaleService.process_sale(
                items=self.cart,
                metodo_pago=self.payment_method.get(),
                cliente_id=1,
                descuento=0.0
            )
            messagebox.showinfo("Éxito", f"Venta #{result['venta_id']} procesada exitosamente.")
            self.cart.clear()
            self._render_cart()
            self.refresh_data()
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al procesar la venta: {e}")
