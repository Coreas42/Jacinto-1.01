import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from src.database.connection import get_connection

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._init_ui()

    def _init_ui(self):
        # Tarjetas KPI superiores
        self.kpi_ventas = self._create_card("Ventas Hoy ($)", "$0.00", 0)
        self.kpi_ganancia = self._create_card("Ganancia Neta ($)", "$0.00", 1)
        self.kpi_articulos = self._create_card("Prod. Vendidos (#)", "0", 2)
        self.kpi_stock = self._create_card("Stock Total Almacén", "0 u", 3)

        # Gráfico Embebido Matplotlib
        self.graph_frame = ctk.CTkFrame(self, fg_color="#181824", corner_radius=10)
        self.graph_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        self._draw_chart([100, 250, 400, 320, 580, 420, 690], [40, 110, 160, 120, 240, 180, 310])

    def _create_card(self, title: str, value: str, col: int) -> ctk.CTkLabel:
        card = ctk.CTkFrame(self, fg_color="#252538", corner_radius=8, border_color="#7B1FA2", border_width=1)
        card.grid(row=0, column=col, padx=8, pady=8, sticky="ew")
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#A0A0B0")
        lbl_title.pack(anchor="w", padx=10, pady=(8, 2))
        
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=20, weight="bold"), text_color="#FFFFFF")
        lbl_val.pack(anchor="w", padx=10, pady=(0, 8))
        return lbl_val

    def _draw_chart(self, sales: list, profits: list):
        fig, ax = plt.subplots(figsize=(7, 3), facecolor="#181824")
        ax.set_facecolor("#181824")
        
        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        ax.plot(days, sales, color="#8A2BE2", marker="o", linewidth=2.5, label="Ventas ($)")
        ax.plot(days, profits, color="#00E5FF", marker="s", linewidth=2.0, linestyle="--", label="Ganancia ($)")

        ax.tick_params(colors="#A0A0B0", labelsize=9)
        ax.spines['bottom'].set_color('#3A3A4C')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#3A3A4C')
        ax.grid(axis='y', color='#252538', linestyle=':')
        ax.legend(facecolor="#1E1E2E", edgecolor="none", labelcolor="#FFFFFF")

        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
