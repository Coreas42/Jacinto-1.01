import customtkinter as ctk
from tkinter import messagebox
from src.database.connection import get_connection
from src.models.pos_manager import POSManager

class POSView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.cart = []
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        # Panel Izquierdo: Catálogo y Búsqueda
        left_panel = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        self.search_entry = ctk.CTkEntry(left_panel, placeholder_text="Buscar SKU o nombre de accesorio...")
        self.search_entry.pack(fill="x", padx=12, pady=12)
        self.search_entry.bind("<Return>", self._search_product)

        self.results_box = ctk.CTkScrollableFrame(left_panel, fg_color="#1E1E2E")
        self.results_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Panel Derecho: Ticket de Venta
        right_panel = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        
        ctk.CTkLabel(right_panel, text="Detalle de Ticket", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.cart_box = ctk.CTkScrollableFrame(right_panel, fg_color="#1E1E2E", height=300)
        self.cart_box.pack(fill="both", expand=True, padx=10, pady=5)

        self.lbl_total = ctk.CTkLabel(right_panel, text="TOTAL: $0.00", font=ctk.CTkFont(size=22, weight="bold"), text_color="#00E5FF")
        self.lbl_total.pack(pady=10)

        self.payment_method = ctk.CTkOptionMenu(right_panel, values=["EFECTIVO", "TARJETA", "TRANSFERENCIA"])
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

    def _search_product(self, event=None):
        query = self.search_entry.get().strip()
        for w in self.results_box.winfo_children():
            w.destroy()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM productos WHERE (sku LIKE ? OR nombre LIKE ?) AND activo = 1 LIMIT 20",
                (f"%{query}%", f"%{query}%")
            )
            rows = cursor.fetchall()

        for prod in rows:
            btn = ctk.CTkButton(
                self.results_box,
                text=f"{prod['sku']} - {prod['nombre']} | ${prod['precio']:.2f} (Stock: {prod['stock_actual']})",
                anchor="w",
                fg_color="#252538",
                hover_color="#3A3A54",
                command=lambda p=dict(prod): self._add_to_cart(p)
            )
            btn.pack(fill="x", pady=2)

    def _add_to_cart(self, prod: dict):
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
        for item in self.cart:
            sub = item['cantidad'] * item['precio_unitario']
            total += sub
            lbl = ctk.CTkLabel(self.cart_box, text=f"{item['cantidad']}x {item['nombre']} - ${sub:.2f}", anchor="w")
            lbl.pack(fill="x", pady=2)

        self.lbl_total.configure(text=f"TOTAL: ${total:.2f}")

    def _finalize_sale(self):
        if not self.cart:
            messagebox.showwarning("Aviso", "No hay artículos en la canasta.")
            return

        try:
            venta_id = POSManager.process_sale(
                cliente_id=1,
                turno_id=1,
                items=self.cart,
                metodo_pago=self.payment_method.get(),
                descuento=0.0
            )
            messagebox.showinfo("Éxito", f"Venta #{venta_id} registrada con éxito.")
            self.cart.clear()
            self._render_cart()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo completar la venta: {str(e)}")
