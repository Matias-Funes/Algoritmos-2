from tkinter import filedialog, messagebox

import customtkinter as ctk

from warehouse.generacion.generador import ConfigGeneracion, generar_escenario
from warehouse.generacion.validador import validar_escenario
from warehouse.generacion.validador_cobertura import validar_cobertura_waves
from warehouse.io.cargador_json import cargar_escenario
from warehouse.simulacion.dinamica import SimulacionDinamica
from warehouse.waves.generador_waves import (EstrategiaWaves, generar_waves,
                                             generar_waves_con_split)


class MenuConfig(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wave Picking Simulator - Launcher")
        self.geometry("550x750")
        self.resizable(False, False)

        self.escenario = None
        self.simulacion = None
        self.estrategia_recorrido = "vecino_mas_cercano"
        self.posiciones_aleatorias = False

        self.frame_actual = None
        self.mostrar_menu_principal()

    def _limpiar_pantalla(self):
        if self.frame_actual:
            self.frame_actual.destroy()

    def mostrar_menu_principal(self):
        self._limpiar_pantalla()
        self.frame_actual = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actual.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(
            self.frame_actual,
            text="Warehouse Wave Picking",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#64b5f6",
        ).pack(pady=(20, 10))
        ctk.CTkLabel(
            self.frame_actual,
            text="Algoritmos y Estructuras de Datos II",
            font=ctk.CTkFont(size=14),
        ).pack(pady=(0, 40))

        ctk.CTkButton(
            self.frame_actual,
            text="➕ Generar Nuevo Escenario",
            height=40,
            font=ctk.CTkFont(weight="bold"),
            command=self.mostrar_generar,
        ).pack(fill="x", pady=10)
        ctk.CTkButton(
            self.frame_actual,
            text="📂 Cargar Escenario Existente",
            height=40,
            command=self.mostrar_cargar,
        ).pack(fill="x", pady=10)
        ctk.CTkButton(
            self.frame_actual,
            text="ℹ️ Créditos / Info",
            height=40,
            fg_color="#444444",
            command=self.mostrar_creditos,
        ).pack(fill="x", pady=10)
        ctk.CTkButton(
            self.frame_actual,
            text="✕ Salir",
            height=40,
            fg_color="#a83232",
            hover_color="#7a2020",
            command=self.destroy,
        ).pack(fill="x", pady=(30, 10))

    def mostrar_creditos(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Créditos")
        ventana.geometry("420x360")
        ventana.resizable(False, False)
        ventana.transient(self)
        ventana.grab_set()

        ctk.CTkLabel(
            ventana,
            text="Simulador de Wave Picking",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        ).pack(pady=(25, 12))

        ctk.CTkLabel(
            ventana,
            text="Desarrollado para la cátedra de\nAlgoritmos y Estructuras de Datos II",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            justify="center",
        ).pack(pady=8)

        ctk.CTkLabel(
            ventana,
            text="Versión 1.0.0",
            font=ctk.CTkFont(family="Segoe UI", size=14),
        ).pack(pady=8)

        ctk.CTkLabel(
            ventana,
            text="Integrantes\nJulieta Forconesi\nJonathan Cornejo\nMatías Funes\nCésar Flores",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            justify="center",
        ).pack(pady=8)

        ctk.CTkButton(
            ventana,
            text="Cerrar",
            command=ventana.destroy,
        ).pack(pady=(12, 20))

    def mostrar_generar(self):
        self._limpiar_pantalla()
        self.frame_actual = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actual.pack(fill="both", expand=True, padx=20, pady=20)

        # 1. BOTONES FIJOS ABAJO (se empaquetan primero para que se queden ahí)
        frame_botones = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        frame_botones.pack(side="bottom", fill="x", pady=(10, 0))

        ctk.CTkButton(frame_botones, text="▶ Comenzar Simulación", height=40, command=self.ejecutar_generacion).pack(fill="x", pady=(0, 5))
        ctk.CTkButton(frame_botones, text="← Volver al Menú", fg_color="#444444", command=self.mostrar_menu_principal).pack(fill="x")

        # 2. TÍTULO ARRIBA
        ctk.CTkLabel(self.frame_actual, text="Configurar Escenario", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(0, 10))

        # 3. FORMULARIO CON SCROLL EN EL MEDIO
        frame_inputs = ctk.CTkScrollableFrame(self.frame_actual, fg_color="transparent")
        frame_inputs.pack(fill="both", expand=True, padx=10)

        def add_input(label, default):
            ctk.CTkLabel(frame_inputs, text=label, anchor="w").pack(fill="x", padx=10, pady=(5, 0))
            entry = ctk.CTkEntry(frame_inputs)
            entry.insert(0, default)
            entry.pack(fill="x", padx=10)
            return entry

        def add_dropdown(label, values, default):
            ctk.CTkLabel(frame_inputs, text=label, anchor="w").pack(fill="x", padx=10, pady=(5, 0))
            menu = ctk.CTkOptionMenu(frame_inputs, values=values)
            menu.set(default)
            menu.pack(fill="x", padx=10)
            return menu

        self.entry_bloques = add_input("Bloques de Racks (Ancho):", "3")
        self.entry_alto = add_dropdown("Altura del Warehouse:", ["16", "20", "24", "28", "32"], "16")
        self.entry_pedidos = add_input("Cantidad de Pedidos:", "30")
        self.entry_seed = add_input("Semilla (Seed):", "42")
        self.entry_zonas = add_dropdown("Cantidad de Zonas de Despacho:", ["1", "2", "3", "4"], "1")
        self.entry_rack_alto = add_dropdown("Alto del Rack:", ["4", "5", "6", "7", "8"], "6")
        self.entry_pickers = add_input("Cantidad de Pickers:", "2")

        self.var_split = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame_inputs, text="Permitir Split (pedidos en varias waves)", variable=self.var_split).pack(anchor="w", padx=10, pady=5)

        self.var_random = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame_inputs, text="Inicio aleatorio de pickers", variable=self.var_random).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(frame_inputs, text="Estrategia de Recorrido:").pack(anchor="w", padx=10, pady=(10, 0))
        self.combo_estrategia_gen = ctk.CTkOptionMenu(frame_inputs, values=["vecino_mas_cercano", "orden_pedidos"])
        self.combo_estrategia_gen.pack(fill="x", padx=10, pady=(0, 10))

    def mostrar_cargar(self):
        self._limpiar_pantalla()
        self.frame_actual = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actual.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            self.frame_actual,
            text="Cargar Escenario o Partida",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(0, 10))

        # Opciones de simulación
        self.frame_opts = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        self.frame_opts.pack(fill="x", pady=5)

        self.var_random_load = ctk.BooleanVar(value=False)
        self.chk_random = ctk.CTkCheckBox(
            self.frame_opts, text="Inicio aleatorio", variable=self.var_random_load
        )
        self.chk_random.pack(side="left", padx=10)

        ctk.CTkLabel(self.frame_opts, text="Estrategia:").pack(
            side="left", padx=(10, 5)
        )
        self.combo_estrategia_load = ctk.CTkOptionMenu(
            self.frame_opts, values=["vecino_mas_cercano", "orden_pedidos"], width=150
        )
        self.combo_estrategia_load.pack(side="left")

        # Tabview con comando para detectar cambio de pestaña
        self.tabview = ctk.CTkTabview(
            self.frame_actual, height=350, command=self._on_tab_changed
        )
        self.tabview.pack(fill="both", expand=True, pady=10)

        self.tab_partidas = self.tabview.add("Partidas Guardadas")
        self.tab_escenarios = self.tabview.add("Escenarios Base")

        ctk.CTkButton(
            self.frame_actual,
            text="🔄 Refrescar Listas",
            width=120,
            fg_color="#444444",
            command=self._cargar_listas_archivos,
        ).pack(pady=(0, 10))

        # Botón para ejecutar la carga del archivo seleccionado
        self.btn_cargar_seleccionado = ctk.CTkButton(
            self.frame_actual,
            text="▶ Cargar Seleccionado",
            height=40,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#1b5e20",
            hover_color="#2e7d32",
            state="disabled",  # Empieza deshabilitado
            command=self._ejecutar_carga_seleccionada,
        )
        self.btn_cargar_seleccionado.pack(fill="x", pady=(10, 5))

        self._cargar_listas_archivos()

        # Forzamos la validación inicial de la pestaña activa
        self._on_tab_changed()

        # Botón estilo "Ghost" (fantasma)
        ctk.CTkButton(
            self.frame_actual,
            text="← Volver al Menú",
            height=30,
            fg_color="transparent",  # Fondo transparente (se mezcla con el fondo oscuro)
            text_color="#aaaaaa",  # Texto gris claro para que no llame tanto la atención
            hover_color="#2b2b2b",  # Un gris oscuro al pasar el mouse (feedback visual)
            border_width=1,  # Un borde fino
            border_color="#555555",  # Color del borde gris
            command=self.mostrar_menu_principal,
        ).pack(fill="x", pady=(5, 0))

    def _on_tab_changed(self):
        # Limpiamos la selección al cambiar de pestaña
        self.archivo_seleccionado = None
        if hasattr(self, "boton_seleccionado"):
            self.boton_seleccionado = None

        # Verificamos que el botón exista antes de tocarlo
        if hasattr(self, "btn_cargar_seleccionado"):
            self.btn_cargar_seleccionado.configure(state="disabled")

        tab_actual = self.tabview.get()
        if tab_actual == "Partidas Guardadas":
            self.chk_random.configure(state="disabled")
            self.combo_estrategia_load.configure(state="disabled")
        else:
            self.chk_random.configure(state="normal")
            self.combo_estrategia_load.configure(state="normal")

    def _seleccionar_archivo(self, ruta: str, boton: ctk.CTkButton):
        # Si había un botón seleccionado antes, lo despintamos
        if hasattr(self, "boton_seleccionado") and self.boton_seleccionado:
            try:
                self.boton_seleccionado.configure(fg_color="#2b2b2b")
            except Exception:
                pass  # Por si el botón ya no existe (se borró el archivo)

        # Guardamos el nuevo seleccionado y lo pintamos de azul
        self.archivo_seleccionado = ruta
        self.boton_seleccionado = boton
        boton.configure(fg_color="#1f538d")

        # Habilitamos el botón de "Cargar Seleccionado"
        self.btn_cargar_seleccionado.configure(state="normal")

    def _ejecutar_carga_seleccionada(self):
        if hasattr(self, "archivo_seleccionado") and self.archivo_seleccionado:
            self._cargar_desde_path(self.archivo_seleccionado)

    def _eliminar_archivo(self, path: str, nombre: str, tab_actual):
        import os
        from tkinter import messagebox

        # 4. El sistema pregunta si está seguro
        respuesta = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Estás seguro que querés eliminar permanentemente la partida:\n\n'{nombre}'?",
        )

        if respuesta:
            try:
                os.remove(path)
                messagebox.showinfo(
                    "Eliminado", f"El archivo '{nombre}' fue eliminado."
                )

                # Limpiamos selección por si borraron el que estaba seleccionado
                self.archivo_seleccionado = None
                self.btn_cargar_seleccionado.configure(state="disabled")
                self.boton_seleccionado = None

                self._cargar_listas_archivos()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el archivo:\n{e}")

    def _cargar_listas_archivos(self):
        import os
        from pathlib import Path
        from tkinter import messagebox

        # Limpiar pestañas
        for widget in self.tab_partidas.winfo_children():
            widget.destroy()
        for widget in self.tab_escenarios.winfo_children():
            widget.destroy()

        def poblar_tab(tab, directorio):
            path_dir = Path(directorio)
            if not path_dir.exists():
                ctk.CTkLabel(
                    tab, text="No se encontró la carpeta.", text_color="#ff5252"
                ).pack(pady=20)
                return

            archivos = sorted([f for f in os.listdir(path_dir) if f.endswith(".json")])
            if not archivos:
                ctk.CTkLabel(tab, text="No hay archivos disponibles.").pack(pady=20)
                return

            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True)

            for archivo in archivos:
                nombre_limpio = archivo.replace(".json", "")
                ruta_completa = str(path_dir / archivo)

                fila = ctk.CTkFrame(scroll, fg_color="transparent")
                fila.pack(fill="x", pady=2)

                # Botón principal (ahora solo selecciona)
                btn_cargar = ctk.CTkButton(
                    fila,
                    text=f"📄 {nombre_limpio}",
                    anchor="w",
                    fg_color="#2b2b2b",
                    hover_color="#3a3a3a",
                    command=lambda r=ruta_completa, b=None: None,  # Se asigna abajo para pasar el botón
                )
                btn_cargar.pack(side="left", fill="x", expand=True, padx=(0, 5))

                # Le pasamos el propio botón para poder cambiarle el color
                btn_cargar.configure(
                    command=lambda r=ruta_completa, b=btn_cargar: self._seleccionar_archivo(
                        r, b
                    )
                )

                # Botón de eliminar (rojo pequeño)
                btn_borrar = ctk.CTkButton(
                    fila,
                    text="🗑️",
                    width=30,
                    fg_color="#a83232",
                    hover_color="#7a2020",
                    command=lambda r=ruta_completa, n=nombre_limpio: self._eliminar_archivo(
                        r, n, tab
                    ),
                )
                btn_borrar.pack(side="right")

        poblar_tab(self.tab_partidas, "data/sesiones")
        poblar_tab(self.tab_escenarios, "data/escenarios")

    def ejecutar_generacion(self):
        try:
            rack_alto = int(self.entry_rack_alto.get())

            cfg = ConfigGeneracion(
                n_bloques_racks=int(self.entry_bloques.get()),
                alto=int(self.entry_alto.get()),
                margen_inferior=5,
                margen_superior=5,
                n_pedidos=int(self.entry_pedidos.get()),
                seed=int(self.entry_seed.get()),
                n_zonas=int(self.entry_zonas.get()),
                n_pickers=int(self.entry_pickers.get()),
                # Auto-calculamos el pasillo horizontal para que el rack tenga el alto elegido
                cada_cuantas_filas_pasillo_horizontal=(rack_alto + 1)
            )

            self.escenario = generar_escenario(cfg)
            validar_escenario(self.escenario)
            self.estrategia_recorrido = self.combo_estrategia_gen.get()

            max_peso = max([p.capacidad_carga_kg for p in self.escenario.pickers]) if self.escenario.pickers else 500.0

            if self.var_split.get():
                waves, items_por_wave = generar_waves_con_split(
                    self.escenario.pedidos, self.escenario.warehouse, 3, 20, max_peso, EstrategiaWaves.PRIORIDAD_Y_CERCANIA
                )
                validar_cobertura_waves(self.escenario.pedidos, items_por_wave)
            else:
                waves = generar_waves(self.escenario.pedidos, self.escenario.warehouse, 3, 20, max_peso, EstrategiaWaves.PRIORIDAD_Y_CERCANIA)
                items_por_wave = None

            self.escenario.waves = waves
            self.simulacion = SimulacionDinamica.desde_waves(
                waves=waves, pickers=self.escenario.pickers, warehouse=self.escenario.warehouse,
                posiciones_aleatorias=self.var_random.get(), items_por_wave=items_por_wave
            )

            self.posiciones_aleatorias = self.var_random.get()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el escenario:\n{e}")

    def _cargar_desde_path(self, path: str):
        try:
            self.escenario = cargar_escenario(path)

            # Si es una partida guardada (tiene sesion), usamos SUS datos.
            # Si es un escenario base, usamos los de la UI.
            if self.escenario.sesion:
                self.estrategia_recorrido = self.escenario.sesion.estrategia_recorrido
                self.posiciones_aleatorias = self.escenario.sesion.posiciones_aleatorias
            else:
                self.estrategia_recorrido = self.combo_estrategia_load.get()
                self.posiciones_aleatorias = self.var_random_load.get()

            if not self.escenario.waves:
                max_peso = (
                    max([p.capacidad_carga_kg for p in self.escenario.pickers])
                    if self.escenario.pickers
                    else 500.0
                )
                self.escenario.waves = generar_waves(
                    self.escenario.pedidos,
                    self.escenario.warehouse,
                    self.escenario.wave_config.max_pedidos,
                    self.escenario.wave_config.max_productos,
                    max_peso,
                    EstrategiaWaves.PRIORIDAD_Y_CERCANIA,
                )

            # Determinar si usamos inicio aleatorio (prioriza lo guardado en el JSON)
            self.posiciones_aleatorias = self.var_random_load.get()
            if self.escenario.sesion:
                self.posiciones_aleatorias = self.escenario.sesion.posiciones_aleatorias

            self.simulacion = SimulacionDinamica.desde_waves(
                waves=self.escenario.waves,
                pickers=self.escenario.pickers,
                warehouse=self.escenario.warehouse,
                posiciones_aleatorias=self.posiciones_aleatorias,
                items_por_wave=None,
            )

            # FAST-FORWARD: Avanzar hasta el paso guardado
            if self.escenario.sesion and self.escenario.sesion.indice_actual > 0:
                for _ in range(self.escenario.sesion.indice_actual):
                    if not self.simulacion.avanzar():
                        break  # Si se completó antes, cortamos

            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")
