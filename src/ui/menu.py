# src/ui/menu.py
# Vista del menú de bienvenida (solo tkinter).
import tkinter as tk
from tkinter import messagebox, ttk

from src.ui.estilos import (
    AZUL_MARINO_OSCURO,
    BEIGE_DORADO,
    BLANCO,
    CREMA_PRINCIPAL,
    FUENTE,
    GRIS_VERDOSO,
    NEGRO_AZULADO,
    VERDE_OSCURO,
    crear_boton,
    px,
)

TEXTO_SIN_JSON = "Ningún archivo JSON cargado"
TEXTO_SIN_MANUAL = "Sin configuración manual"
TEXTO_MANUAL_OK = "✔ Configuración manual cargada"


class VistaMenu(tk.Frame):
    """Menú principal: cargar JSON, configuración manual e iniciar simulación."""

    def __init__(
        self, master, on_cargar_json, on_config_manual, on_iniciar, on_cargar_partida
    ):
        super().__init__(master, bg=CREMA_PRINCIPAL)

        contenedor = tk.Frame(self, bg=CREMA_PRINCIPAL)
        contenedor.place(relx=0.5, rely=0.5, anchor="center")

        # --- Banner de bienvenida (Fila 0) ---
        banner = tk.Frame(contenedor, bg=AZUL_MARINO_OSCURO, padx=70, pady=28)
        banner.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 40))
        tk.Label(
            banner,
            text="Bienvenido",
            font=("Arial", 32, "bold"),
            fg=BLANCO,
            bg=AZUL_MARINO_OSCURO,
        ).pack()
        tk.Label(
            banner,
            text="Simulador de Wave Picking",
            font=("Arial", 12),
            fg=GRIS_VERDOSO,
            bg=AZUL_MARINO_OSCURO,
        ).pack(pady=(4, 0))

        # --- Fila 1: cargar JSON ---
        self.lbl_json = tk.Label(
            contenedor,
            text=TEXTO_SIN_JSON,
            font=FUENTE,
            bg=CREMA_PRINCIPAL,
            fg=NEGRO_AZULADO,
            anchor="e",
            width=34,
        )
        self.lbl_json.grid(row=1, column=0, sticky="e", padx=(0, 15), pady=8)
        crear_boton(contenedor, "Cargar JSON", on_cargar_json, width=24).grid(
            row=1, column=1, sticky="ew", pady=8
        )

        # --- Fila 2: configuración manual ---
        self.lbl_manual = tk.Label(
            contenedor,
            text=TEXTO_SIN_MANUAL,
            font=FUENTE,
            bg=CREMA_PRINCIPAL,
            fg=NEGRO_AZULADO,
            anchor="e",
            width=34,
        )
        self.lbl_manual.grid(row=2, column=0, sticky="e", padx=(0, 15), pady=8)
        crear_boton(
            contenedor, "Configuración manual", on_config_manual, width=24
        ).grid(row=2, column=1, sticky="ew", pady=8)

        # --- Fila 3: iniciar simulación ---
        crear_boton(
            contenedor,
            "Iniciar simulación",
            on_iniciar,
            width=24,
            font=("Arial", 10, "bold"),
        ).grid(row=3, column=1, sticky="ew", pady=(24, 8))

        # --- Fila 4: Selector de Modo de Waves ---
        frame_modo = tk.Frame(contenedor, bg=CREMA_PRINCIPAL)
        frame_modo.grid(row=4, column=1, sticky="ew", pady=(0, 10))

        tk.Label(
            frame_modo, text="Modo de waves:", bg=CREMA_PRINCIPAL, font=FUENTE
        ).pack(side=tk.LEFT)

        self.combo_modo_waves = ttk.Combobox(
            frame_modo,
            state="readonly",
            values=["Wave Global (Flota)", "Wave por Picker"],
            width=20,
        )
        self.combo_modo_waves.current(0)  # 0 = Wave Global por defecto
        self.combo_modo_waves.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        # --- Fila 4.5: Selector de Estrategia ---
        frame_estrategia = tk.Frame(contenedor, bg=CREMA_PRINCIPAL)
        frame_estrategia.grid(row=5, column=1, sticky="ew", pady=(0, 10))

        tk.Label(
            frame_estrategia,
            text="Estrategia de recorrido:",
            bg=CREMA_PRINCIPAL,
            font=FUENTE,
        ).pack(side=tk.LEFT)

        self.combo_estrategia = ttk.Combobox(
            frame_estrategia,
            state="readonly",
            values=["Vecino más cercano (B)", "Orden de pedidos (A)"],
            width=20,
        )
        self.combo_estrategia.current(0)
        self.combo_estrategia.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        # --- Fila 5: Cargar Partida ---
        crear_boton(
            contenedor,
            "📂 Cargar Partida Guardada",
            on_cargar_partida,
            width=24,
            primario=False,
        ).grid(row=6, column=1, sticky="ew", pady=(0, 8))

        # --- Fila 6: Aviso en línea ---
        self.lbl_aviso = tk.Label(
            contenedor,
            text="",
            font=FUENTE,
            bg=CREMA_PRINCIPAL,
            fg=BEIGE_DORADO,
            wraplength=px(520),
            justify=tk.CENTER,
        )
        self.lbl_aviso.grid(row=6, column=0, columnspan=2, pady=(10, 0))

    # --- API para el controlador ---
    def set_archivo_json(self, nombre=None):
        if nombre:
            self.lbl_json.config(text=f"✔ {nombre}", fg=VERDE_OSCURO)
        else:
            self.lbl_json.config(text=TEXTO_SIN_JSON, fg=NEGRO_AZULADO)

    def set_config_manual(self, cargada):
        if cargada:
            self.lbl_manual.config(text=TEXTO_MANUAL_OK, fg=VERDE_OSCURO)
        else:
            self.lbl_manual.config(text=TEXTO_SIN_MANUAL, fg=NEGRO_AZULADO)

    def mostrar_aviso(self, texto):
        self.lbl_aviso.config(text=texto)
        messagebox.showwarning("Faltan datos", texto, parent=self)

    def limpiar_aviso(self):
        self.lbl_aviso.config(text="")
