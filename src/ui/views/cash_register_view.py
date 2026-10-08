import customtkinter as ctk

from src.services.cash_register_service import CashRegisterService


class CashRegisterView(ctk.CTkFrame):
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
            text="Arqueo y Cierre de Turno (Caja Z)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#8A2BE2"
        ).pack(pady=15)

        self.info_box = ctk.CTkFrame(panel, fg_color="#1E1E2E", corner_radius=8)
        self.info_box.pack(fill="x", padx=25, pady=10)

        self.lbl_resumen = ctk.CTkLabel(self.info_box, text="Cargando resumen de turno...", font=ctk.CTkFont(size=14), justify="left")
        self.lbl_resumen.pack(padx=15, pady=15, anchor="w")

        action_frame = ctk.CTkFrame(panel, fg_color="transparent")
        action_frame.pack(fill="x", padx=25, pady=15)

        self.ent_efectivo_real = ctk.CTkEntry(action_frame, placeholder_text="Monto en Efectivo Físico Contado ($)")
        self.ent_efectivo_real.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_cerrar = ctk.CTkButton(
            action_frame,
            text="FINALIZAR TURNO",
            fg_color="#C62828",
            hover_color="#8E0000",
            command=self._close_turn
        )
        self.btn_cerrar.pack(side="right", padx=(10, 0))

    def refresh_data(self):
        turno = CashRegisterService.get_open_turn()
        if not turno:
            self.lbl_resumen.configure(text="No hay turnos abiertos actualmente.")
            return

        resumen = CashRegisterService.get_turn_summary(turno['id'])
        ventas = resumen['resumen_pagos']
        efectivo = float(ventas.get('EFECTIVO', {}).get('monto', 0.0) or 0.0)
        tarjeta = float(ventas.get('TARJETA', {}).get('monto', 0.0) or 0.0)
        transfer = float(ventas.get('TRANSFERENCIA', {}).get('monto', 0.0) or 0.0)
        total_turno = efectivo + tarjeta + transfer
        esperado_efectivo = float(turno['fondo_inicial'] or 0.0) + efectivo

        texto = (
            f"Turno Activo ID: #{turno['id']} (Iniciado: {turno['fecha_apertura']})\n"
            f"------------------------------------------------------------\n"
            f"Fondo de Caja Inicial : ${float(turno['fondo_inicial'] or 0.0):.2f}\n"
            f"Ventas en Efectivo    : ${efectivo:.2f}\n"
            f"Ventas con Tarjeta    : ${tarjeta:.2f}\n"
            f"Transferencias        : ${transfer:.2f}\n"
            f"------------------------------------------------------------\n"
            f"Total Vendido         : ${total_turno:.2f}\n"
            f"Efectivo Esperado en Gaveta: ${esperado_efectivo:.2f}"
        )
        self.lbl_resumen.configure(text=texto)

    def _close_turn(self):
        from tkinter import messagebox
        try:
            turno = CashRegisterService.get_open_turn()
            if not turno:
                messagebox.showinfo("Aviso", "No hay un turno abierto.")
                return

            monto = float(self.ent_efectivo_real.get() or 0.0)
            result = CashRegisterService.close_turn(turno['id'], monto)
            messagebox.showinfo("Corte Completo", f"Turno cerrado.\nDiferencia registrada: ${result['diferencia']:.2f}")
            self.ent_efectivo_real.delete(0, 'end')
            self.refresh_data()
        except Exception as e:
            messagebox.showerror("Error", f"Error cerrando turno: {e}")
