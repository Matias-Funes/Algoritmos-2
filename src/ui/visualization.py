# src/ui/visualization.py
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.cell import AMBOS, DESPACHO, PASILLO, PUERTA, RACK, E, N, O, S

COLOR_VOLVER_TERMINADA = "#10b981"
COLOR_BOTON_PRIMARIO = "#24577a"
COLOR_BOTON_PRIMARIO_HOVER = "#34769a"
COLOR_BOTON_SECUNDARIO = "#dce7ef"
COLOR_BOTON_SECUNDARIO_HOVER = "#c5d6e3"
COLOR_BOTON_PELIGRO = "#b94747"
COLOR_BOTON_PELIGRO_HOVER = "#9e3737"
COLOR_BOTON_TERMINADO_HOVER = "#0c8b60"
COLOR_PANEL = "#f8fafc"
COLOR_TEXTO = "#193b59"
COLORES_PICKERS = [
    "#0ea5e9", # Celeste
    "#10b981", # Verde
    "#f59e0b", # Naranja
    "#8b5cf6", # Violeta
    "#ec4899", # Rosa
    "#ef4444", # Rojo (el original)
]

class Ventana(tk.Frame):
    """Vista de la simulación (colores y diseño originales)."""

    def __init__(
        self,
        warehouse,
        tamano_celda=30,
        master=None,
        on_volver=None,
        on_cerrar=None,
    ):
        super().__init__(master)
        self.warehouse = warehouse
        self.tamano_celda = tamano_celda
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._fondo_mapa_dibujado = False
        self._redibujar_mapa_id = None
        self._rutas_dibujadas = {}
        self._stock_dibujado = None
        self.simulacion = None
        self.on_volver = on_volver
        self.on_cerrar = on_cerrar
        self.en_ejecucion = False
        self.root = self.winfo_toplevel()
        self._configurar_estilo_scrollbars()

        if master is None:
            self.root.title("Wave Picking - Simulador")
            self.pack(fill=tk.BOTH, expand=True)

        # --- Configuración del Panel Lateral (Izquierda) ---
        self.panel = tk.Frame(self, width=280, bg=COLOR_PANEL, padx=10, pady=10)
        self.panel.pack(side=tk.LEFT, fill=tk.Y)
        self.panel.pack_propagate(False)  # Evita que el frame se achique

        # 1. Controles
        tk.Label(self.panel, text="Controles", font=("Arial", 12, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(anchor="w", pady=(0, 5))

        frame_btn = tk.Frame(self.panel, bg=COLOR_PANEL)
        frame_btn.pack(fill=tk.X)

        # Fila 0: Play/Pausar (Izquierda) y Reiniciar (Derecha)
        self.btn_play_pause = self._crear_boton_simulacion(
            frame_btn,
            "▶ Iniciar",
            self.btn_toggle_play_pause,
            variante="primario",
        )
        self.btn_play_pause.grid(
            row=0, column=0, sticky="ew", pady=3, padx=(2, 1)
        )

        self._crear_boton_simulacion(
            frame_btn,
            "🔄 Reiniciar",
            self.btn_reset,
            variante="secundario",
        ).grid(row=0, column=1, sticky="ew", pady=3, padx=(1, 2))

        # Fila 1: Atrás y Adelante
        frame_pasos = tk.Frame(frame_btn, bg=COLOR_PANEL)
        frame_pasos.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

        self._crear_boton_simulacion(
            frame_pasos,
            "⏮ Atrás",
            self.btn_paso_atras,
            variante="secundario",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 1), pady=2)
        self._crear_boton_simulacion(
            frame_pasos,
            "⏭ Adelante",
            self.btn_paso,
            variante="secundario",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1, 2), pady=2)

        # Fila 2: Guardar y Comparar
        self._crear_boton_simulacion(
            frame_btn,
            "💾 Guardar Partida",
            self.btn_guardar_partida,
            variante="secundario",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=3, padx=2)

        self._crear_boton_simulacion(
            frame_btn,
            "📊 Comparar Estrategias",
            self.btn_comparar_estrategias,
            variante="acento",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 3), padx=2)

        self.btn_cerrar = self._crear_boton_simulacion(
            frame_btn,
            "✕ Cerrar juego",
            self.on_cerrar or self.root.destroy,
            variante="peligro",
        )
        self.btn_cerrar.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(6, 2),
            padx=2,
        )

        frame_btn.columnconfigure(0, weight=1)
        frame_btn.columnconfigure(1, weight=1)

        # 2. Métricas Globales
        tk.Label(self.panel, text="Métricas Globales", font=("Arial", 12, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(anchor="w", pady=(15, 5))

        self.lbl_wave = tk.Label(self.panel, text="Wave: 0 / 0", font=("Arial", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO)
        self.lbl_wave.pack(anchor="w")

        self.lbl_paso = tk.Label(self.panel, text="Paso actual: 0", font=("Arial", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO)
        self.lbl_paso.pack(anchor="w")

        self.lbl_productos = tk.Label(self.panel, text="Productos Recogidos: 0 / 0", font=("Arial", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO)
        self.lbl_productos.pack(anchor="w")

        self.lbl_distancia = tk.Label(self.panel, text="Distancia Total: 0 m", font=("Arial", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO)
        self.lbl_distancia.pack(anchor="w")

        # --- NUEVA MÉTRICA DE ALTURA ---
        self.lbl_altura = tk.Label(self.panel, text="Última altura recogida: Nivel 0", font=("Arial", 10), bg=COLOR_PANEL, fg=COLOR_TEXTO)
        self.lbl_altura.pack(anchor="w")

        # 3. Panel de Pickers
        tk.Label(self.panel, text="Estado Pickers", font=("Arial", 12, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(anchor="w", pady=(15, 5))
        contenedor_pickers = tk.Frame(self.panel, bg=COLOR_PANEL)
        contenedor_pickers.pack(fill=tk.BOTH, expand=True)
        self.canvas_pickers = tk.Canvas(
            contenedor_pickers,
            bg=COLOR_PANEL,
            highlightthickness=0,
            height=100,
            yscrollincrement=24,
        )
        self.scrollbar_pickers = ttk.Scrollbar(
            contenedor_pickers,
            orient=tk.VERTICAL,
            command=self.canvas_pickers.yview,
            style="Simulation.Vertical.TScrollbar",
        )
        self.canvas_pickers.configure(
            yscrollcommand=self.scrollbar_pickers.set,
        )
        self.scrollbar_pickers.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_pickers.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.frame_carga_pickers = tk.Frame(self.canvas_pickers, bg="#f8fafc")
        self._ventana_pickers = self.canvas_pickers.create_window(
            (0, 0),
            window=self.frame_carga_pickers,
            anchor="nw",
        )
        self.frame_carga_pickers.bind(
            "<Configure>",
            self._actualizar_region_scroll_pickers,
        )
        self.canvas_pickers.bind(
            "<Configure>",
            self._ajustar_ancho_lista_pickers,
        )
        self._habilitar_scroll_pickers(self.canvas_pickers)
        self._habilitar_scroll_pickers(self.frame_carga_pickers)
        self.lbl_carga_pickers = {}

        # 4. Pedidos de la Wave
        tk.Label(self.panel, text="Pedidos en Wave", font=("Arial", 12, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(anchor="w", pady=(15, 5))
        contenedor_pedidos = tk.Frame(self.panel, bg=COLOR_PANEL)
        contenedor_pedidos.pack(fill=tk.X)
        self.txt_pedidos = tk.Text(
            contenedor_pedidos,
            height=6,
            width=35,
            font=("Arial", 9),
            bg="#ffffff",
            fg=COLOR_TEXTO,
            insertbackground=COLOR_TEXTO,
            selectbackground=COLOR_BOTON_PRIMARIO,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#d5e0e8",
            highlightcolor=COLOR_BOTON_PRIMARIO,
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        self.scrollbar_pedidos = ttk.Scrollbar(
            contenedor_pedidos,
            orient=tk.VERTICAL,
            command=self.txt_pedidos.yview,
            style="Simulation.Vertical.TScrollbar",
        )
        self.txt_pedidos.configure(
            yscrollcommand=self.scrollbar_pedidos.set,
        )
        self.txt_pedidos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_pedidos.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_pedidos.bind("<MouseWheel>", self._desplazar_pedidos, add="+")
        self.txt_pedidos.bind("<Button-4>", self._desplazar_pedidos, add="+")
        self.txt_pedidos.bind("<Button-5>", self._desplazar_pedidos, add="+")
        self.scrollbar_pedidos.bind("<MouseWheel>", self._desplazar_pedidos, add="+")
        self._wave_pedidos_mostrada = None

        # 5. Volver al menú
        self.btn_volver = self._crear_boton_simulacion(
            self.panel,
            "← Volver al menú",
            self.btn_volver_menu,
            variante="secundario",
        )
        self.btn_volver.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        self._estilo_volver_original = {
            "bg": self.btn_volver.cget("bg"),
            "fg": self.btn_volver.cget("fg"),
            "activebackground": self.btn_volver.cget("activebackground"),
        }

        # --- Configuración del Canvas (Derecha) ---
        self.canvas = tk.Canvas(self, width=1, height=1, bg="#e2e8f0")
        self.canvas.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10,
        )
        self.canvas.bind("<Configure>", self._ajustar_mapa_a_ventana)

    def set_simulacion(self, sim):
        self.simulacion = sim

    def _crear_boton_simulacion(
        self,
        parent,
        texto,
        comando,
        variante="secundario",
    ):
        estilos = {
            "primario": (
                COLOR_BOTON_PRIMARIO,
                COLOR_BOTON_PRIMARIO_HOVER,
                "white",
            ),
            "secundario": (
                COLOR_BOTON_SECUNDARIO,
                COLOR_BOTON_SECUNDARIO_HOVER,
                COLOR_TEXTO,
            ),
            "acento": ("#dceef8", "#c5e2f1", COLOR_TEXTO),
            "peligro": (
                COLOR_BOTON_PELIGRO,
                COLOR_BOTON_PELIGRO_HOVER,
                "white",
            ),
        }
        fondo, hover, texto_color = estilos[variante]
        boton = tk.Button(
            parent,
            text=texto,
            command=comando,
            bg=fondo,
            fg=texto_color,
            activebackground=hover,
            activeforeground=texto_color,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=6,
            font=("Arial", 9, "bold"),
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=COLOR_PANEL,
            highlightcolor=hover,
        )
        boton._color_fondo_normal = fondo
        boton._color_fondo_hover = hover
        boton.bind(
            "<Enter>",
            lambda _evento: boton.configure(bg=boton._color_fondo_hover),
            add="+",
        )
        boton.bind(
            "<Leave>",
            lambda _evento: boton.configure(bg=boton._color_fondo_normal),
            add="+",
        )
        return boton

    def _configurar_estilo_scrollbars(self):
        estilo = ttk.Style(self)
        estilo.configure(
            "Simulation.Vertical.TScrollbar",
            background=COLOR_BOTON_SECUNDARIO,
            darkcolor=COLOR_BOTON_SECUNDARIO,
            lightcolor=COLOR_BOTON_SECUNDARIO,
            troughcolor="#e8eef3",
            bordercolor="#e8eef3",
            arrowcolor=COLOR_TEXTO,
            relief=tk.FLAT,
            borderwidth=0,
            arrowsize=10,
            width=13,
        )
        estilo.map(
            "Simulation.Vertical.TScrollbar",
            background=[("active", COLOR_BOTON_PRIMARIO_HOVER)],
            arrowcolor=[("active", COLOR_BOTON_PRIMARIO)],
        )

    def _ajustar_mapa_a_ventana(self, evento):
        ancho_mapa = self.warehouse.ancho_x
        alto_mapa = self.warehouse.largo_y
        ancho_disponible = max(1, evento.width - 24)
        alto_disponible = max(1, evento.height - 24)

        self.tamano_celda = min(
            ancho_disponible / max(1, ancho_mapa),
            alto_disponible / max(1, alto_mapa),
        )
        self._offset_x = (evento.width - ancho_mapa * self.tamano_celda) / 2
        self._offset_y = (evento.height - alto_mapa * self.tamano_celda) / 2

        if self._redibujar_mapa_id is not None:
            self.after_cancel(self._redibujar_mapa_id)
        self._redibujar_mapa_id = self.after(
            40,
            self._redibujar_mapa_redimensionado,
        )

    def _redibujar_mapa_redimensionado(self):
        self._redibujar_mapa_id = None
        self.canvas.delete("all")
        self._fondo_mapa_dibujado = False
        self._rutas_dibujadas.clear()
        self._stock_dibujado = None
        if self.simulacion is not None:
            self.actualizar_desde_simulacion()
        else:
            self.dibujar_warehouse()

    def _actualizar_region_scroll_pickers(self, _evento=None):
        region = self.canvas_pickers.bbox("all")
        if region is not None:
            self.canvas_pickers.configure(scrollregion=region)

    def _ajustar_ancho_lista_pickers(self, evento):
        self.canvas_pickers.itemconfigure(
            self._ventana_pickers,
            width=evento.width,
        )

    def _habilitar_scroll_pickers(self, widget):
        widget.bind("<MouseWheel>", self._desplazar_pickers, add="+")
        widget.bind("<Button-4>", self._desplazar_pickers, add="+")
        widget.bind("<Button-5>", self._desplazar_pickers, add="+")

    def _desplazar_pickers(self, evento):
        if getattr(evento, "num", None) == 4:
            unidades = -1
        elif getattr(evento, "num", None) == 5:
            unidades = 1
        else:
            delta = getattr(evento, "delta", 0)
            if not delta:
                return
            unidades = -1 if delta > 0 else 1

        self.canvas_pickers.yview_scroll(unidades, "units")
        return "break"

    def _desplazar_pedidos(self, evento):
        if getattr(evento, "num", None) == 4:
            unidades = -1
        elif getattr(evento, "num", None) == 5:
            unidades = 1
        else:
            delta = getattr(evento, "delta", 0)
            if not delta:
                return
            unidades = -1 if delta > 0 else 1

        self.txt_pedidos.yview_scroll(unidades, "units")
        return "break"

    # --- Callbacks ---
    def btn_toggle_play_pause(self):
        if not self.simulacion:
            return

        if self.en_ejecucion:
            self.simulacion.pausar()
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Reanudar")
        else:
            self.simulacion.iniciar()
            self.en_ejecucion = True
            self.btn_play_pause.config(text="⏸ Pausar")

    def btn_paso(self):
        if self.simulacion:
            self.simulacion.pausar() 
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Iniciar")
            self.simulacion.avanzar_paso()
            self.actualizar_desde_simulacion()

    def btn_reset(self):
        if self.simulacion:
            self.simulacion.resetear()
            self.actualizar_desde_simulacion()
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Iniciar")

    def btn_paso_atras(self):
        if self.simulacion:
            if self.simulacion.retroceder_paso():
                self.actualizar_desde_simulacion()

    def btn_comparar_estrategias(self):
        if not self.simulacion:
            return
        comparar = getattr(self.simulacion, "comparar_estrategias", None)
        if comparar is None:
            messagebox.showinfo("No disponible", "Esta simulación no expone la comparación.")
            return

        try:
            resultado = comparar()
        except Exception as exc:
            messagebox.showerror("Error al comparar", str(exc), parent=self.root)
            return

        self._mostrar_comparacion(resultado)

    def _mostrar_comparacion(self, comparacion):
        if not comparacion.get("totales"):
            messagebox.showinfo("Sin datos", "No hay waves para comparar.", parent=self.root)
            return

        ventana = tk.Toplevel(self.root)
        ventana.title("Comparación de Estrategias")
        ventana.geometry("700x500")
        ventana.minsize(600, 400)
        ventana.transient(self.root)
        ventana.configure(bg="#f8fafc")

        style = ttk.Style(ventana)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=25, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        notebook = ttk.Notebook(ventana)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_global = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
        tab_detalle = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)

        notebook.add(tab_global, text="Resumen Global")
        notebook.add(tab_detalle, text="Detalle por Wave")

        # PESTAÑA 1
        nombres_ui = {"A": "A (Orden de pedidos)", "B": "B (Vecino más cercano)"}
        totales = comparacion["totales"]
        nombres = list(totales)

        columnas_global = ["Métrica"] + [nombres_ui.get(n, n) for n in nombres]
        tabla_global = ttk.Treeview(tab_global, columns=columnas_global, show="headings", height=5)

        for col in columnas_global:
            tabla_global.heading(col, text=col)
            tabla_global.column(col, anchor="center", width=180)
            if col == "Métrica":
                tabla_global.column(col, anchor="w", width=150)

        filas_global = [
            ("Tiempo total (ms)", "tiempo_ms", "{:.3f}"),
            ("Distancia total", "distancia", "{}"),
            ("Nodos visitados", "nodos", "{}"),
            ("Aristas recorridas", "aristas", "{}"),
        ]

        for etiqueta, clave, fmt in filas_global:
            valores = [etiqueta] + [fmt.format(totales[n].get(clave, 0)) for n in nombres]
            tabla_global.insert("", tk.END, values=valores)

        tabla_global.pack(fill=tk.X, pady=10)

        ganador_dist = comparacion.get('ganador_distancia', '-')
        ganador_tiempo = comparacion.get('ganador_tiempo', '-')

        eficiencia = ""
        if len(nombres) == 2:
            d_a = totales["A"].get("distancia", 0)
            d_b = totales["B"].get("distancia", 0)
            if d_a > 0:
                if d_b < d_a:
                    ahorro = ((d_a - d_b) / d_a) * 100
                    eficiencia = f"La Estrategia B ahorró un {ahorro:.1f}% de distancia respecto a A."
                else:
                    ahorro = ((d_b - d_a) / d_b) * 100
                    eficiencia = f"La Estrategia A ahorró un {ahorro:.1f}% de distancia respecto a B."

        frame_ganadores = tk.Frame(tab_global, bg="#f8fafc")
        frame_ganadores.pack(fill=tk.X, pady=10)

        tk.Label(frame_ganadores, text=f"🏆 Mejor Distancia: {nombres_ui.get(ganador_dist, ganador_dist)}",
                 font=("Arial", 12, "bold"), fg="#0ea5e9", bg="#f8fafc").pack(anchor="w")
        tk.Label(frame_ganadores, text=f"⏱️ Mejor Tiempo: {nombres_ui.get(ganador_tiempo, ganador_tiempo)}",
                 font=("Arial", 12, "bold"), fg="#0ea5e9", bg="#f8fafc").pack(anchor="w")
        if eficiencia:
            tk.Label(frame_ganadores, text=f"💡 {eficiencia}",
                     font=("Arial", 11, "italic"), fg="#10b981", bg="#f8fafc").pack(anchor="w", pady=(5,0))

        # PESTAÑA 2
        tk.Label(tab_detalle, text="Distancia recorrida por la flota en cada Wave",
                 font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(0, 10))

        columnas_detalle = ["Wave", "Distancia A", "Distancia B", "Ganador"]
        tabla_detalle = ttk.Treeview(tab_detalle, columns=columnas_detalle, show="headings", height=10)

        for col in columnas_detalle:
            tabla_detalle.heading(col, text=col)
            tabla_detalle.column(col, anchor="center", width=130)

        victorias = {"A": 0, "B": 0, "Empate": 0}

        for fila in comparacion["por_wave"]:
            wave_id = fila["wave_id"]
            est = fila["estrategias"]

            if "error" in est.get("A", {}) or "error" in est.get("B", {}):
                tabla_detalle.insert("", tk.END, values=[wave_id, "Error", "Error", "-"])
                continue

            d_a = est["A"]["distancia"]
            d_b = est["B"]["distancia"]

            if d_a < d_b:
                ganador = "A"
                victorias["A"] += 1
            elif d_b < d_a:
                ganador = "B"
                victorias["B"] += 1
            else:
                ganador = "Empate"
                victorias["Empate"] += 1

            tabla_detalle.insert("", tk.END, values=[wave_id, d_a, d_b, ganador])

        tabla_detalle.pack(fill=tk.BOTH, expand=True)

        texto_victorias = f"Victorias: A ({victorias['A']}) | B ({victorias['B']}) | Empates ({victorias['Empate']})"
        tk.Label(tab_detalle, text=texto_victorias, font=("Arial", 11, "bold"),
                 bg="#f8fafc", fg="#64748b").pack(anchor="e", pady=10)

        tk.Button(ventana, text="Cerrar", command=ventana.destroy, width=15).pack(pady=(0, 10))

    def btn_guardar_partida(self):
        if not self.simulacion: return
        ruta = filedialog.asksaveasfilename(
            title="Guardar Partida",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json")]
        )
        if not ruta: return

        try:
            from main import guardar_partida
            guardar_partida(Path(ruta), self.simulacion)
            messagebox.showinfo("Guardado", f"Partida guardada en:\n{ruta}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}", parent=self.root)

    def _simulacion_terminada(self, estado=None):
        if not self.simulacion:
            return True
        if estado is None:
            estado = self.simulacion.get_estado()
        if 'terminada' in estado:
            return bool(estado['terminada'])
        waves_totales = estado.get('waves_totales', 0)
        return (waves_totales > 0
                and estado.get('wave_actual', 0) >= waves_totales
                and not estado.get('pedidos_actuales'))

    def _actualizar_boton_volver(self, estado):
        if self._simulacion_terminada(estado):
            self.btn_volver._color_fondo_normal = COLOR_VOLVER_TERMINADA
            self.btn_volver._color_fondo_hover = COLOR_BOTON_TERMINADO_HOVER
            self.btn_volver.config(text="✔ Simulación terminada: Volver al menú",
                                   bg=COLOR_VOLVER_TERMINADA, fg="white",
                                   activebackground=COLOR_BOTON_TERMINADO_HOVER,
                                   activeforeground="white")
        else:
            self.btn_volver._color_fondo_normal = self._estilo_volver_original["bg"]
            self.btn_volver._color_fondo_hover = COLOR_BOTON_SECUNDARIO_HOVER
            self.btn_volver.config(text="← Volver al menú", **self._estilo_volver_original)

    def btn_volver_menu(self):
        if not self._simulacion_terminada():
            self.simulacion.pausar()
            if not messagebox.askyesno(
                "Volver al menú",
                "La simulación aún no terminó. ¿Desea volver al menú de todas formas?",
                parent=self.root
            ):
                return
        if self.on_volver:
            self.on_volver()

    def _obtener_centro(self, x, y):
        cx = self._offset_x + (x * self.tamano_celda) + (self.tamano_celda / 2)
        cy = (
            self._offset_y
            + ((self.warehouse.largo_y - 1 - y) * self.tamano_celda)
            + (self.tamano_celda / 2)
        )
        return cx, cy

    # --- Lee el stock en tiempo real del inventario ---
    def _obtener_stock_por_celda(self):
        """Devuelve un diccionario {(x,y): cantidad_total} con el stock actual."""
        stock_map = {}
        if not self.simulacion:
            return stock_map
        
        inventario = getattr(self.simulacion, "inventario", None)
        if not inventario:
            return stock_map
            
        try:
            for prod in inventario.todos_los_productos():
                x, y = prod.ubicacion[0], prod.ubicacion[1]
                stock_map[(x, y)] = stock_map.get((x, y), 0) + prod.cantidad_disponible
        except AttributeError:
            pass
            
        return stock_map

    def dibujar_warehouse(self, stock_map=None):
        for y in range(self.warehouse.largo_y):
            for x in range(self.warehouse.ancho_x):
                cell = self.warehouse.grid[y][x]
                x1 = self._offset_x + x * self.tamano_celda
                y1 = (
                    self._offset_y
                    + (self.warehouse.largo_y - 1 - y) * self.tamano_celda
                )
                x2 = x1 + self.tamano_celda
                y2 = y1 + self.tamano_celda

                color = "#f1f5f9"
                if cell.tipo == RACK:
                    color = "#1e3a8a"
                elif cell.tipo == DESPACHO:
                    color = "#10b981"
                elif cell.tipo == PUERTA:
                    color = "#f59e0b"
                elif cell.tipo == "VACIA":
                    color = "#cbd5e1"

                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline="#e2e8f0",
                    tags=("warehouse",),
                )

                if cell.tipo == PASILLO and cell.sentido != AMBOS:
                    cx, cy = self._obtener_centro(x, y)
                    flecha = ""
                    if cell.sentido == N:
                        flecha = "↑"
                    elif cell.sentido == S:
                        flecha = "↓"
                    elif cell.sentido == E:
                        flecha = "→"
                    elif cell.sentido == O:
                        flecha = "←"
                    self.canvas.create_text(
                        cx,
                        cy,
                        text=flecha,
                        fill="#64748b",
                        font=("Arial", 10, "bold"),
                        tags=("warehouse",),
                    )

        self._fondo_mapa_dibujado = True
        if stock_map is not None:
            self._dibujar_stock(stock_map)

    def _dibujar_stock(self, stock_map):
        for (x, y), cantidad in stock_map.items():
            if (
                cantidad <= 0
                or not (0 <= x < self.warehouse.ancho_x)
                or not (0 <= y < self.warehouse.largo_y)
                or self.warehouse.grid[y][x].tipo != RACK
            ):
                continue
            cx, cy = self._obtener_centro(x, y)
            self._dibujar_icono_paquete(cx, cy)

    def _dibujar_icono_paquete(self, cx, cy):
        """Dibuja una caja de cartón pequeña en el centro de la celda."""
        tam = self.tamano_celda * 0.45
        x1, y1 = cx - tam, cy - tam
        x2, y2 = cx + tam, cy + tam
        
        self.canvas.create_rectangle(
            x1, y1, x2, y2, 
            fill="#d97706", outline="#190b03", width=1, tags=("stock",)
        )
        self.canvas.create_line(
            x1, cy, x2, cy, fill="#fde68a", width=1, tags=("stock",)
        )
        self.canvas.create_line(
            cx, y1, cx, y2, fill="#fde68a", width=1, tags=("stock",)
        )
        self.canvas.create_polygon(
            x1, y1, x1 + tam * 0.5, y1, x1, y1 + tam * 0.5,
            fill="#fef08a", outline="", tags=("stock",)
        )

    def dibujar_recorrido(self, ruta, color="#0ea5e9", tag="route"):
        if not ruta or len(ruta) < 2:
            return
        puntos_px = []
        for (x, y) in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])
        self.canvas.create_line(
            puntos_px,
            fill=color,
            width=2,
            dash=(4, 2),
            arrow=tk.LAST,
            tags=("routes", tag),
        )

    def dibujar_picker(self, x, y, p_data, color="#ef4444"):
        cx, cy = self._obtener_centro(x, y)
        radio = self.tamano_celda * 0.35

        esta_recolectando = p_data.get("recolectando", False)

        # --- CAMBIO DE COLOR SI ESTÁ RECOLECTANDO ---
        if esta_recolectando:
            color = "#10b981" # Verde brillante
        # --------------------------------------------

        self.canvas.create_oval(
            cx - radio,
            cy - radio,
            cx + radio,
            cy + radio,
            fill=color,
            outline="#1e293b",
            width=2,
            tags=("picker",),
        )

        inicial = str(p_data['id'])[-1]
        self.canvas.create_text(
            cx,
            cy,
            text=inicial,
            fill="white",
            font=("Arial", 8, "bold"),
            tags=("picker",),
        )

        wave = p_data.get('wave_actual', '?')
        carga = p_data.get('carga_actual_kg', 0)
        cap = p_data.get('capacidad_carga_kg', 0)
        detalle = f"{p_data['id']} | W{wave} | {carga:.0f}/{cap:.0f}kg"

        self.canvas.create_text(
            cx,
            cy + radio + 10,
            text=detalle,
            fill=color,
            font=("Arial", 7, "bold"),
            tags=("picker",),
        )

    def actualizar_desde_simulacion(self):
        if not self.simulacion:
            return

        estado = self.simulacion.get_estado()
        if not self._fondo_mapa_dibujado:
            self.dibujar_warehouse()

        self.canvas.delete("picker")
        stock_map = self._obtener_stock_por_celda()
        if stock_map != self._stock_dibujado:
            self.canvas.delete("stock")
            self._dibujar_stock(stock_map)
            self._stock_dibujado = stock_map

        rutas = estado.get('rutas', [])
        pickers_estado = estado.get('pickers', [])

        for i, p in enumerate(pickers_estado):
            color = COLORES_PICKERS[i % len(COLORES_PICKERS)]

            if i < len(rutas):
                firma_ruta = tuple(tuple(punto) for punto in rutas[i])
                tag_ruta = f"route_{i}"
                if self._rutas_dibujadas.get(i) != firma_ruta:
                    self.canvas.delete(tag_ruta)
                    self.dibujar_recorrido(
                        rutas[i],
                        color=color,
                        tag=tag_ruta,
                    )
                    self._rutas_dibujadas[i] = firma_ruta

            if p.get("activo", True):
                self.dibujar_picker(p['x'], p['y'], p, color=color)

        self.lbl_wave.config(text=f"Wave: {estado.get('wave_actual', 0)} / {estado.get('waves_totales', 0)}")
        self.lbl_paso.config(text=f"Paso actual: {estado.get('paso_actual', 0)}")
        self.lbl_productos.config(text=f"Productos Recogidos: {estado.get('productos_recogidos', 0)} / {estado.get('total_productos', 0)}")
        self.lbl_distancia.config(text=f"Distancia Total: {estado.get('distancia', 0)} m")
        
        # --- ACTUALIZAR MÉTRICA DE ALTURA ---
        self.lbl_altura.config(text=f"Última altura recogida: Nivel {estado.get('ultima_altura', 0)}")

        pickers_estado = estado.get("pickers", [])
        ids_pickers = {picker["id"] for picker in pickers_estado}

        for picker_id in list(self.lbl_carga_pickers):
            if picker_id not in ids_pickers:
                for widget in self.lbl_carga_pickers[picker_id]:
                    widget.destroy()
                del self.lbl_carga_pickers[picker_id]

        for picker in pickers_estado:
            picker_id = picker["id"]
            if picker_id not in self.lbl_carga_pickers:
                lbl = tk.Label(
                    self.frame_carga_pickers,
                    text="",
                    bg="white",
                    fg=COLOR_TEXTO,
                    font=("Arial", 9),
                    justify=tk.LEFT,
                    anchor="w",
                    padx=7,
                    pady=5,
                    relief=tk.FLAT,
                    highlightthickness=1,
                    highlightbackground="#e1e8ee",
                )
                lbl.pack(fill=tk.X, pady=3, padx=(2, 4))
                self._habilitar_scroll_pickers(lbl)
                self.lbl_carga_pickers[picker_id] = [lbl]

            cantidad_actual = picker.get("productos_transportados", 0)
            cantidad_objetivo = picker.get("productos_objetivo", 0)
            items = picker.get("items_transportados", [])
            detalle = ", ".join(f"{i['producto_id']}({i['cantidad']})" for i in items) or "Vacío"

            esta_recolectando = picker.get("recolectando", False)
            
            if esta_recolectando:
                estado_texto = "📦 ¡RECOLECTANDO!"
            else:
                estado_texto = "🚶 En movimiento"

            texto = f"• {picker_id}: {cantidad_actual}/{cantidad_objetivo} items\n  {estado_texto}\n  {detalle}"
            self.lbl_carga_pickers[picker_id][0].config(text=texto)

        wave_actual = estado.get("wave_actual")
        cambio_wave = wave_actual != self._wave_pedidos_mostrada
        scroll_anterior = self.txt_pedidos.yview()[0]

        self.txt_pedidos.config(state=tk.NORMAL)
        self.txt_pedidos.delete(1.0, tk.END)

        pedidos = estado.get('pedidos_actuales', {})
        if not pedidos:
            self.txt_pedidos.insert(tk.END, "No hay pedidos pendientes.\n¡Wave completada!")
        else:
            es_anidado = False
            if pedidos:
                primer_valor = list(pedidos.values())[0]
                if isinstance(primer_valor, dict):
                    es_anidado = True
            
            # --- NUEVO: Helper para buscar la altura ---
            def obtener_altura(pid):
                try:
                    inv = getattr(self.simulacion, "inventario", None)
                    if inv:
                        prod = inv.obtener_producto(pid)
                        return int(prod.ubicacion[2]) if len(prod.ubicacion) > 2 else 0
                except Exception:
                    pass
                return 0
            # ---------------------------------------------

            if es_anidado:
                for picker_id, demanda in pedidos.items():
                    if demanda:
                        self.txt_pedidos.insert(tk.END, f"Picker {picker_id}:\n")
                        for prod_id, cant in demanda.items():
                            altura = obtener_altura(prod_id)
                            # --- FORMATO CON COMA Y ALTURA ---
                            self.txt_pedidos.insert(tk.END, f"  - {prod_id}: {cant} unidades, altura ({altura})\n")
            else:
                for prod_id, cant in pedidos.items():
                    altura = obtener_altura(prod_id)
                    # --- FORMATO CON COMA Y ALTURA ---
                    self.txt_pedidos.insert(tk.END, f"- {prod_id}: {cant} unidades, altura ({altura})\n")

        self.txt_pedidos.config(state=tk.DISABLED)
        if cambio_wave:
            self.txt_pedidos.yview_moveto(0)
            self._wave_pedidos_mostrada = wave_actual
        else:
            self.txt_pedidos.yview_moveto(scroll_anterior)
        self._actualizar_boton_volver(estado)

        if estado.get('terminada', False):
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Iniciar")

    def iniciar(self):
        self.mainloop()