import customtkinter as ctk
from tkinter import messagebox
from src.database.connection import get_connection

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

        ctk.CTkLabel(panel, text="Arqueo y Cierre de Turno (Caja Z)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#8A2BE2").pack(pady=15)

        self.info_box = ctk.CTkFrame(panel, fg_color="#1E1E2E", corner_radius=8)
        self.info_box.pack(fill="x", padx=25, pady=10)

        self.lbl_resumen = ctk.CTkLabel(self.info_box, text="Cargando resumen de turno...", font=ctk.CTkFont(size=14), justify="left")
        self.lbl_resumen.pack(padx=15, pady=15, anchor="w")

        action_frame = ctk.CTkFrame(panel, fg_color="transparent")
        action_frame.pack(fill="x", padx=25, pady=15)

        self.ent_efectivo_real = ctk.CTkEntry(action_frame, placeholder_text="Monto en Efectivo Físico Contado ($)")
        self.ent_efectivo_real.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_cerrar = ctk.CTkButton(
            action_frame, text="FINALIZAR TURNO", fg_color="#C62828", hover_color="#8E0000",
            command=self._close_turn
        )
        btn_cerrar.pack(side="right", padx=(10, 0))

    def refresh_data(self):
        with get_connection() as conn:
            turno = conn.execute("SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1").fetchone()
            if not turno:
                self.lbl_resumen.configure(text="No hay turnos abiertos actualmente.")
                return

            ventas = conn.execute(
                """SELECT metodo_pago, SUM(total) as subtotal FROM ventas 
                   WHERE turno_id = ? GROUP BY metodo_pago""", (turno['id'],)
            ).fetchall()

            resumen_pagos = {row['metodo_pago']: row['subtotal'] for row in ventas}
            efectivo = resumen_pagos.get('EFECTIVO', 0.0)
            tarjeta = resumen_pagos.get('TARJETA', 0.0)
            transfer = resumen_pagos.get('TRANSFERENCIA', 0.0)
            total_turno = efectivo + tarjeta + transfer

            esperado_efectivo = turno['fondo_inicial'] + efectivo

            texto = (
                f"Turno Activo ID: #{turno['id']} (Iniciado: {turno['fecha_apertura']})\n"
                f"------------------------------------------------------------\n"
                f"Fondo de Caja Inicial : ${turno['fondo_inicial']:.2f}\n"
                f"Ventas en Efectivo    : ${efectivo:.2f}\n"
                f"Ventas con Tarjeta    : ${tarjeta:.2f}\n"
                f"Transferencias        : ${transfer:.2f}\n"
                f"------------------------------------------------------------\n"
                f"Total Vendido         : ${total_turno:.2f}\n"
                f"Efectivo Esperado en Gaveta: ${esperado_efectivo:.2f}"
            )
            self.lbl_resumen.configure(text=texto)

    def _close_turn(self):
        try:
            conteo = float(self.ent_efectivo_real.get() or 0.0)
            with get_connection() as conn:
                turno = conn.execute("SELECT * FROM turnos_caja WHERE estado = 'ABIERTO' ORDER BY id DESC LIMIT 1").fetchone()
                if not turno:
                    messagebox.showinfo("Aviso", "No hay un turno abierto.")
                    return

                ventas_ef = conn.execute(
                    "SELECT SUM(total) as tot FROM ventas WHERE turno_id = ? AND metodo_pago = 'EFECTIVO'",
                    (turno['id'],)
                ).fetchone()['tot'] or 0.0

                esperado = turno['fondo_inicial'] + ventas_ef
                diferencia = conteo - esperado

                conn.execute(
                    """UPDATE turnos_caja 
                       SET fecha_cierre = CURRENT_TIMESTAMP, efectivo_declarado = ?, diferencia = ?, estado = 'CERRADO'
                       WHERE id = ?""",
                    (conteo, diferencia, turno['id'])
                )
                conn.execute("INSERT INTO turnos_caja (fondo_inicial, estado) VALUES (100.00, 'ABIERTO')")
                conn.commit()

            messagebox.showinfo("Corte Completo", f"Turno cerrado.\nDiferencia registrada: ${diferencia:.2f}")
            self.ent_efectivo_real.delete(0, 'end')
            self.refresh_data()
        except Exception as e:
            messagebox.showerror("Error", f"Error cerrando turno: {e}")
