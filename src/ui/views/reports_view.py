import customtkinter as ctk
from src.database.connection import get_connection

class ReportsView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        panel = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        panel.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            panel, 
            text="Estado de Resultados Simplificado", 
            font=ctk.CTkFont(size=18, weight="bold"), 
            text_color="#8A2BE2"
        ).pack(pady=15)

        self.report_card = ctk.CTkFrame(panel, fg_color="#1E1E2E", corner_radius=8)
        self.report_card.pack(fill="both", expand=True, padx=25, pady=15)

        self.lbl_reporte = ctk.CTkLabel(
            self.report_card, 
            text="Calculando resultados...", 
            font=ctk.CTkFont(size=15), 
            justify="left"
        )
        self.lbl_reporte.pack(padx=20, pady=20, anchor="w")

    def refresh_data(self):
        with get_connection() as conn:
            v_row = conn.execute("SELECT SUM(total) as tot FROM ventas").fetchone()
            v = v_row['tot'] if v_row and v_row['tot'] else 0.0

            c_row = conn.execute("SELECT SUM(costo_unitario * cantidad) as cogs FROM ventas_detalle").fetchone()
            c = c_row['cogs'] if c_row and c_row['cogs'] else 0.0

            g_row = conn.execute("SELECT SUM(monto) as gastos FROM gastos").fetchone()
            g = g_row['gastos'] if g_row and g_row['gastos'] else 0.0

            margen_bruto = v - c
            utilidad_neta = margen_bruto - g

            texto = (
                f"(+) Ventas Brutas Totales      : ${v:.2f}\n"
                f"(-) Costo de Mercancía Vendida : ${c:.2f}\n"
                f"-------------------------------------------------\n"
                f"(=) Margen Bruto               : ${margen_bruto:.2f}\n"
                f"(-) Gastos Operativos          : ${g:.2f}\n"
                f"=================================================\n"
                f"(=) UTILIDAD NETA REAL         : ${utilidad_neta:.2f}"
            )
            self.lbl_reporte.configure(text=texto)
