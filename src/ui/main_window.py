import customtkinter as ctk
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.pos_view import POSView
from src.models.backup_manager import BackupManager

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("THE GARAGE AUTO ACCESORIOS SV - POS & Inventario")
        self.geometry("1280x768")
        self.minsize(1024, 600)
        
        # Tema Visual
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#121218")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        
        # Contenedor de Vistas
        self.container = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=12)
        self.container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.views = {}
        self._load_views()
        self.show_view("dashboard")
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, fg_color="#181824", corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_rowconfigure(8, weight=1)

        title = ctk.CTkLabel(
            sidebar, 
            text="THE GARAGE\nAUTO ACCESORIOS", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#8A2BE2"
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 30))

        buttons = [
            ("Inicio / Dashboard", "dashboard"),
            ("Punto de Venta (POS)", "pos"),
            ("Catálogo de Productos", "inventory"),
            ("Corte de Caja", "cash"),
            ("Reportes y Utilidad", "reports")
        ]

        for idx, (label, tag) in enumerate(buttons, start=1):
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                fg_color="transparent",
                hover_color="#7B1FA2",
                anchor="w",
                font=ctk.CTkFont(size=13),
                command=lambda t=tag: self.show_view(t)
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=10, pady=4)

    def _load_views(self):
        self.views["dashboard"] = DashboardView(self.container)
        self.views["pos"] = POSView(self.container)
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def show_view(self, name: str):
        view = self.views.get(name)
        if view:
            view.tkraise()
            if hasattr(view, "refresh_data"):
                view.refresh_data()

    def _on_close(self):
        try:
            BackupManager.create_automatic_backup()
        except Exception as e:
            print(f"Error generando backup automático: {e}")
        self.destroy()
