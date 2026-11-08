# src/ui/visualization.py
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.cell import AMBOS, DESPACHO, PASILLO, PUERTA, RACK, E, N, O, S
from src.ui.estilos import (
    BLANCO,
    FUENTE,
    FUENTE_NEGRITA,
    FUENTE_TITULO,
    ROJO,
    crear_boton,
)

COLOR_VOLVER_TERMINADA = "#10b981"
COLORES_PICKERS = [
    "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#ef4444"
]

class Ventana(tk.Frame):
    """Vista de la simulación con escalado automático del mapa (Zoom to Fit)."""

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
        self.simulacion = None
        self.on_volver = on_volver
        self.on_cerrar = on_cerrar
        self.en_ejecucion = False
        self.root = self.winfo_toplevel()

        self.offset_x = 0
        self.offset_y = 0
        self._geometria_dibujada = None
        self._stock_por_celda = {}
        self._productos_recogidos_stock = None
        self._rutas_dibujadas = {}
        self._items_pickers = {}

        if master is None:
            self.root.title("Wave Picking - Simulador")
            self.root.state('zoomed')
            self.pack(fill=tk.BOTH, expand=True)

        # ==========================================
        # 1. BARRA SUPERIOR (Controles y Velocidad)
        # ==========================================
        self.top_bar = tk.Frame(self, bg="#ffffff", padx=12, pady=10, highlightthickness=1, highlightbackground="#cbd5e1")
        self.top_bar.pack(side=tk.TOP, fill=tk.X)

        crear_boton(
            self.top_bar,
            "✕ Cerrar",
            self.btn_cerrar_aplicacion,
            primario=False,
            font=FUENTE_NEGRITA,
            bg=ROJO,
            fg=BLANCO,
            activebackground="#9F3939",
            activeforeground=BLANCO,
            padx=12,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        # Botón Volver (Izquierda)
        self.btn_volver = crear_boton(
            self.top_bar,
            "← Volver al menú",
            self.btn_volver_menu,
            primario=False,
            font=FUENTE_NEGRITA,
            padx=12,
            pady=6,
        )
        self.btn_volver.pack(side=tk.LEFT, padx=(0, 20))
        self._estilo_volver_original = {
            "bg": self.btn_volver.cget("bg"), "fg": self.btn_volver.cget("fg"),
            "activebackground": self.btn_volver.cget("activebackground"),
        }

        # Controles de Simulación (Centro-Izquierda)
        frame_btn = tk.Frame(self.top_bar, bg="#ffffff")
        frame_btn.pack(side=tk.LEFT)

        self.btn_play_pause = crear_boton(
            frame_btn,
            "▶ Iniciar",
            self.btn_toggle_play_pause,
            font=FUENTE_NEGRITA,
            padx=12,
            pady=6,
        )
        self.btn_play_pause.pack(side=tk.LEFT, padx=2)

        for texto, comando in (
            ("🔄 Reiniciar", self.btn_reset),
            ("⏮ Atrás", self.btn_paso_atras),
            ("⏭ Adelante", self.btn_paso),
            ("💾 Guardar Partida", self.btn_guardar_partida),
        ):
            crear_boton(
                frame_btn,
                texto,
                comando,
                primario=False,
                padx=12,
                pady=6,
            ).pack(side=tk.LEFT, padx=2)
        crear_boton(
            frame_btn,
            "📊 Comparar Estrategias",
            self.btn_comparar_estrategias,
            padx=12,
            pady=6,
        ).pack(side=tk.LEFT, padx=2)
        # --- NUEVO: Toggle para mostrar/ocultar etiquetas ---
        frame_etiquetas = tk.Frame(self.top_bar, bg="#ffffff")
        frame_etiquetas.pack(side=tk.RIGHT, padx=15)

        self.mostrar_etiquetas = tk.BooleanVar(value=True)
        chk_etiquetas = tk.Checkbutton(
            frame_etiquetas,
            text="Mostrar etiquetas",
            variable=self.mostrar_etiquetas,
            command=self.toggle_etiquetas,
            bg="#ffffff",
            font=FUENTE_NEGRITA,
            activebackground="#ffffff"
        )
        chk_etiquetas.pack()
        # -----------------------------------------------------

        # Selector de Velocidad (Derecha)
        frame_velocidad = tk.Frame(self.top_bar, bg="#ffffff")
        frame_velocidad.pack(side=tk.RIGHT)

        tk.Label(frame_velocidad, text="Velocidad:", bg="#ffffff", font=FUENTE_NEGRITA).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_velocidad = ttk.Combobox(
            frame_velocidad,
            values=["Lento (500ms)", "Normal (250ms)", "Rápido (100ms)", "Turbo (20ms)", "Hipervelocidad (5ms)", "Máxima Velocidad (0ms)"],
            state="readonly",
            width=20
        )
        self.combo_velocidad.current(1)
        self.combo_velocidad.pack(side=tk.LEFT)
        self.combo_velocidad.bind("<<ComboboxSelected>>", self.cambiar_velocidad)

        # ==========================================
        # 2. ÁREA PRINCIPAL (Panel Izquierdo y Mapa)
        # ==========================================
        self.main_area = tk.Frame(self, bg="#e2e8f0")
        self.main_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Panel Izquierdo (Métricas y Pedidos)
        self.panel = tk.Frame(self.main_area, width=370, bg="#f8fafc", padx=15, pady=10)
        self.panel.pack(side=tk.LEFT, fill=tk.Y)
        self.panel.pack_propagate(False)

        # 1. Métricas Globales
        tk.Label(self.panel, text="Métricas Globales", font=FUENTE_TITULO, bg="#f8fafc", fg="#1e293b").pack(anchor="w", pady=(5, 5))
        self.lbl_wave = tk.Label(self.panel, text="Wave: 0 / 0", font=FUENTE, bg="#f8fafc")
        self.lbl_wave.pack(anchor="w")
        self.lbl_paso = tk.Label(self.panel, text="Paso actual: 0", font=FUENTE, bg="#f8fafc")
        self.lbl_paso.pack(anchor="w")
        self.lbl_productos = tk.Label(self.panel, text="Productos Recogidos: 0 / 0", font=FUENTE, bg="#f8fafc")
        self.lbl_productos.pack(anchor="w")
        self.lbl_productos_wave = tk.Label(self.panel, text="Recogidos Wave Actual: 0", font=FUENTE, bg="#f8fafc")
        self.lbl_productos_wave.pack(anchor="w")
        self.lbl_distancia = tk.Label(self.panel, text="Distancia Total: 0 m", font=FUENTE, bg="#f8fafc")
        self.lbl_distancia.pack(anchor="w")
        self.lbl_altura = tk.Label(self.panel, text="Última altura recogida: Nivel 0", font=FUENTE, bg="#f8fafc")
        self.lbl_altura.pack(anchor="w")

        # 2. Panel de Pickers
        tk.Label(self.panel, text="Estado Pickers", font=FUENTE_TITULO, bg="#f8fafc", fg="#1e293b").pack(anchor="w", pady=(20, 5))
        frame_lista_pickers = tk.Frame(self.panel, bg="#f8fafc")
        frame_lista_pickers.pack(fill=tk.X)
        self.canvas_pickers = tk.Canvas(
            frame_lista_pickers,
            height=180,
            bg="#f8fafc",
            highlightthickness=0,
        )
        scrollbar_pickers = ttk.Scrollbar(
            frame_lista_pickers,
            orient=tk.VERTICAL,
            command=self.canvas_pickers.yview,
        )
        self.canvas_pickers.configure(yscrollcommand=scrollbar_pickers.set)
        self.canvas_pickers.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar_pickers.pack(side=tk.RIGHT, fill=tk.Y)
        self.frame_carga_pickers = tk.Frame(self.canvas_pickers, bg="#f8fafc")
        self._ventana_pickers = self.canvas_pickers.create_window(
            (0, 0), window=self.frame_carga_pickers, anchor="nw"
        )
        self.frame_carga_pickers.bind(
            "<Configure>",
            lambda _event: self.canvas_pickers.configure(
                scrollregion=self.canvas_pickers.bbox("all")
            ),
        )
        self.canvas_pickers.bind(
            "<Configure>",
            lambda event: self.canvas_pickers.itemconfigure(
                self._ventana_pickers, width=event.width
            ),
        )
        self.canvas_pickers.bind("<MouseWheel>", self._scroll_pickers)
        self.canvas_pickers.bind("<Button-4>", self._scroll_pickers)
        self.canvas_pickers.bind("<Button-5>", self._scroll_pickers)
        self.frame_carga_pickers.bind("<MouseWheel>", self._scroll_pickers)
        self.frame_carga_pickers.bind("<Button-4>", self._scroll_pickers)
        self.frame_carga_pickers.bind("<Button-5>", self._scroll_pickers)
        self.lbl_carga_pickers = {}

        # 3. Pedidos de la Wave
        tk.Label(self.panel, text="Pedidos en Wave", font=FUENTE_TITULO, bg="#f8fafc", fg="#1e293b").pack(anchor="w", pady=(20, 5))
        frame_pedidos = tk.Frame(self.panel, bg="#f8fafc")
        frame_pedidos.pack(fill=tk.BOTH, expand=True)
        self.txt_pedidos = tk.Text(frame_pedidos, height=8, width=38, font=("Segoe UI", 9), bg="#ffffff", state=tk.DISABLED, relief=tk.FLAT, padx=8, pady=8, highlightthickness=1, highlightbackground="#cbd5e1")
        scrollbar_pedidos = ttk.Scrollbar(
            frame_pedidos,
            orient=tk.VERTICAL,
            command=self.txt_pedidos.yview,
        )
        self.txt_pedidos.configure(yscrollcommand=scrollbar_pedidos.set)
        self.txt_pedidos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_pedidos.pack(side=tk.RIGHT, fill=tk.Y)

        # Área del Mapa (Derecha)
        self.frame_mapa = tk.Frame(self.main_area, bg="#e2e8f0")
        self.frame_mapa.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.frame_mapa, bg="#e2e8f0", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _recalcular_dimensiones(self):
        """Calcula el tamaño de celda ideal para que el mapa ocupe toda la pantalla."""
        ancho_disp = self.canvas.winfo_width()
        alto_disp = self.canvas.winfo_height()

        if ancho_disp <= 1: ancho_disp = self.root.winfo_screenwidth() * 0.7
        if alto_disp <= 1: alto_disp = self.root.winfo_screenheight() * 0.8

        escala_x = ancho_disp / self.warehouse.ancho_x
        escala_y = alto_disp / self.warehouse.largo_y

        self.tamano_celda = min(escala_x, escala_y)

        ancho_real_mapa = self.warehouse.ancho_x * self.tamano_celda
        alto_real_mapa = self.warehouse.largo_y * self.tamano_celda

        self.offset_x = (ancho_disp - ancho_real_mapa) / 2
        self.offset_y = (alto_disp - alto_real_mapa) / 2

    def _scroll_pickers(self, event):
        if getattr(event, "num", None) == 4:
            unidades = -1
        elif getattr(event, "num", None) == 5:
            unidades = 1
        else:
            unidades = int(-event.delta / 120)
        if unidades:
            self.canvas_pickers.yview_scroll(unidades, "units")

    def btn_cerrar_aplicacion(self):
        if self.on_cerrar:
            self.on_cerrar()
            return
        pausar = getattr(self.simulacion, "pausar", None)
        if pausar is not None:
            pausar()
        self.root.destroy()

    def _on_canvas_resize(self, event):
        self._recalcular_dimensiones()
        if self.simulacion:
            self.actualizar_desde_simulacion()
        elif self._geometria_canvas() != self._geometria_dibujada:
            self._dibujar_fondo()

    def _geometria_canvas(self):
        return (
            self.canvas.winfo_width(),
            self.canvas.winfo_height(),
            self.tamano_celda,
            self.offset_x,
            self.offset_y,
        )

    def _dibujar_fondo(self):
        self.canvas.delete("all")
        self._rutas_dibujadas.clear()
        self._items_pickers.clear()
        self.dibujar_warehouse(self._stock_por_celda)
        self._geometria_dibujada = self._geometria_canvas()

    def _actualizar_iconos_stock(self, stock_map):
        self.canvas.delete("stock")
        for (x, y), cantidad in stock_map.items():
            if cantidad > 0:
                self._dibujar_icono_paquete(*self._obtener_centro(x, y), tag="stock")
        if any(datos["items"] for datos in self._rutas_dibujadas.values()):
            self.canvas.tag_lower("stock", "rutas")
        self._stock_por_celda = stock_map

    def set_simulacion(self, sim):
        self.simulacion = sim

    def btn_toggle_play_pause(self):
        if not self.simulacion: return
        if self.en_ejecucion:
            self.simulacion.pausar()
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Reanudar")
        else:
            self.simulacion.iniciar()
            self.en_ejecucion = True
            self.btn_play_pause.config(text="⏸ Pausar")

    def cambiar_velocidad(self, event=None):
        if not self.simulacion:
            return

        seleccion = self.combo_velocidad.get()
        velocidades = {
            "Lento (500ms)": 500,
            "Normal (250ms)": 250,
            "Rápido (100ms)": 100,
            "Turbo (20ms)": 20,
            "Hipervelocidad (5ms)": 5,
            "Instántaneo (0ms)": 0
        }

        nuevo_intervalo = velocidades.get(seleccion, 250)

        # Llamamos al método que creamos en main.py
        if hasattr(self.simulacion, "actualizar_velocidad"):
            self.simulacion.actualizar_velocidad(nuevo_intervalo)

    def toggle_etiquetas(self):
        if self.simulacion:
            self.actualizar_desde_simulacion()

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
        if self.simulacion and self.simulacion.retroceder_paso():
            self.actualizar_desde_simulacion()

    def btn_comparar_estrategias(self):
        if not self.simulacion: return
        comparar = getattr(self.simulacion, "comparar_estrategias", None)
        if comparar is None: return
        try:
            resultado = comparar()
            self._mostrar_comparacion(resultado)
        except Exception as exc:
            messagebox.showerror("Error al comparar", str(exc), parent=self.root)

    def _mostrar_comparacion(self, comparacion):
        if not comparacion.get("totales"):
            messagebox.showinfo("Sin datos", "No hay waves para comparar.", parent=self.root)
            return

        ventana = tk.Toplevel(self.root)
        ventana.title("Comparación de Estrategias")
        ventana.geometry("700x500")
        ventana.transient(self.root)
        ventana.configure(bg="#f8fafc")

        style = ttk.Style(ventana)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=FUENTE)
        style.configure("Treeview.Heading", font=FUENTE_NEGRITA)

        notebook = ttk.Notebook(ventana)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_global = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
        tab_detalle = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
        notebook.add(tab_global, text="Resumen Global")
        notebook.add(tab_detalle, text="Detalle por Wave")

        nombres_ui = {"A": "A (Orden)", "B": "B (Cercanía)"}
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

        frame_ganadores = tk.Frame(tab_global, bg="#f8fafc")
        frame_ganadores.pack(fill=tk.X, pady=10)

        tk.Label(frame_ganadores, text=f"🏆 Mejor Distancia: {nombres_ui.get(ganador_dist, ganador_dist)}", font=FUENTE_TITULO, fg="#0ea5e9", bg="#f8fafc").pack(anchor="w")
        tk.Label(frame_ganadores, text=f"⏱️ Mejor Tiempo: {nombres_ui.get(ganador_tiempo, ganador_tiempo)}", font=FUENTE_TITULO, fg="#0ea5e9", bg="#f8fafc").pack(anchor="w")

        columnas_detalle = ["Wave", "Distancia A", "Distancia B", "Ganador"]
        tabla_detalle = ttk.Treeview(tab_detalle, columns=columnas_detalle, show="headings", height=10)

        for col in columnas_detalle:
            tabla_detalle.heading(col, text=col)
            tabla_detalle.column(col, anchor="center", width=130)

        for fila in comparacion["por_wave"]:
            wave_id = fila["wave_id"]
            est = fila["estrategias"]
            if "error" in est.get("A", {}) or "error" in est.get("B", {}):
                tabla_detalle.insert("", tk.END, values=[wave_id, "Error", "Error", "-"])
                continue
            d_a = est["A"]["distancia"]
            d_b = est["B"]["distancia"]
            ganador = "A" if d_a < d_b else "B" if d_b < d_a else "Empate"
            tabla_detalle.insert("", tk.END, values=[wave_id, d_a, d_b, ganador])

        tabla_detalle.pack(fill=tk.BOTH, expand=True)
        crear_boton(
            ventana, "Cerrar", ventana.destroy, primario=False, width=15
        ).pack(pady=(0, 12))

    def btn_guardar_partida(self):
        if not self.simulacion: return
        ruta = filedialog.asksaveasfilename(title="Guardar Partida", defaultextension=".json", filetypes=[("Archivos JSON", "*.json")])
        if not ruta: return
        try:
            from main import guardar_partida
            guardar_partida(Path(ruta), self.simulacion)
            messagebox.showinfo("Guardado", f"Partida guardada en:\n{ruta}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}", parent=self.root)

    def _simulacion_terminada(self, estado=None):
        if not self.simulacion: return True
        if estado is None: estado = self.simulacion.get_estado()
        if 'terminada' in estado: return bool(estado['terminada'])
        return False

    def _actualizar_boton_volver(self, estado):
        if self._simulacion_terminada(estado):
            self.btn_volver.config(
                text="✔ Simulación terminada: Volver",
                bg=COLOR_VOLVER_TERMINADA,
                fg="white",
                activebackground="#059669",
            )
            self.btn_volver._hover_normal_background = COLOR_VOLVER_TERMINADA
        else:
            self.btn_volver.config(text="← Volver al menú", **self._estilo_volver_original)
            self.btn_volver._hover_normal_background = self._estilo_volver_original["bg"]

    def btn_volver_menu(self):
        if not self._simulacion_terminada():
            self.simulacion.pausar()
            if not messagebox.askyesno("Volver al menú", "La simulación aún no terminó. ¿Desea volver al menú de todas formas?", parent=self.root):
                return
        if self.on_volver: self.on_volver()

    def _obtener_centro(self, x, y):
        cx = self.offset_x + (x * self.tamano_celda) + (self.tamano_celda / 2)
        cy = self.offset_y + ((self.warehouse.largo_y - 1 - y) * self.tamano_celda) + (self.tamano_celda / 2)
        return cx, cy

    def _obtener_stock_por_celda(self):
        stock_map = {}
        if not self.simulacion: return stock_map
        inventario = getattr(self.simulacion, "inventario", None)
        if not inventario: return stock_map
        try:
            for prod in inventario.todos_los_productos():
                x, y = prod.ubicacion[0], prod.ubicacion[1]
                stock_map[(x, y)] = stock_map.get((x, y), 0) + prod.cantidad_disponible
        except AttributeError:
            pass
        return stock_map

    def dibujar_warehouse(self, stock_map=None):
        if stock_map is None: stock_map = {}
        for y in range(self.warehouse.largo_y):
            for x in range(self.warehouse.ancho_x):
                cell = self.warehouse.grid[y][x]

                x1 = self.offset_x + x * self.tamano_celda
                y1 = self.offset_y + (self.warehouse.largo_y - 1 - y) * self.tamano_celda
                x2 = x1 + self.tamano_celda
                y2 = y1 + self.tamano_celda

                color = "#f1f5f9"
                if cell.tipo == RACK: color = "#1e3a8a"
                elif cell.tipo == DESPACHO: color = "#10b981"
                elif cell.tipo == PUERTA: color = "#f59e0b"
                elif cell.tipo == "VACIA": color = "#cbd5e1"

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline="#e2e8f0",
                    tags=("warehouse",),
                )

                if cell.tipo == RACK:
                    stock = stock_map.get((x, y), 0)
                    if stock > 0:
                        cx, cy = self._obtener_centro(x, y)
                        self._dibujar_icono_paquete(cx, cy, tag="stock")

                if cell.tipo == PASILLO and cell.sentido != AMBOS:
                    cx, cy = self._obtener_centro(x, y)
                    flecha = ""
                    if cell.sentido == N: flecha = "↑"
                    elif cell.sentido == S: flecha = "↓"
                    elif cell.sentido == E: flecha = "→"
                    elif cell.sentido == O: flecha = "←"
                    font_size = max(6, int(self.tamano_celda * 0.6))
                    self.canvas.create_text(
                        cx, cy, text=flecha, fill="#64748b",
                        font=("Arial", font_size, "bold"), tags=("warehouse",),
                    )

    def _dibujar_icono_paquete(self, cx, cy, tag="stock"):
        tam = self.tamano_celda * 0.45
        x1, y1 = cx - tam, cy - tam
        x2, y2 = cx + tam, cy + tam
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill="#d97706", outline="#190b03", width=1,
            tags=(tag,),
        )
        self.canvas.create_line(
            x1, cy, x2, cy, fill="#fde68a", width=1, tags=(tag,)
        )
        self.canvas.create_line(
            cx, y1, cx, y2, fill="#fde68a", width=1, tags=(tag,)
        )

    def _crear_segmento_ruta(self, picker_id, origen, destino, color, grosor):
        x1, y1 = self._obtener_centro(*origen)
        x2, y2 = self._obtener_centro(*destino)
        return self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=grosor,
            dash=(4, 2),
            arrow=tk.LAST,
            tags=("rutas", f"ruta:{picker_id}"),
        )

    def dibujar_recorrido(self, picker_id, ruta, color="#0ea5e9"):
        nueva_ruta = tuple(tuple(punto) for punto in ruta)
        datos = self._rutas_dibujadas.get(picker_id)
        if datos is None:
            datos = {"ruta": (), "items": [], "color": color}
            self._rutas_dibujadas[picker_id] = datos

        ruta_anterior = datos["ruta"]
        items = datos["items"]
        if nueva_ruta == ruta_anterior:
            return

        prefijo = 0
        while (
            prefijo < min(len(ruta_anterior), len(nueva_ruta))
            and ruta_anterior[prefijo] == nueva_ruta[prefijo]
        ):
            prefijo += 1
        sufijo = 0
        while (
            sufijo < min(len(ruta_anterior), len(nueva_ruta)) - prefijo
            and ruta_anterior[-(sufijo + 1)] == nueva_ruta[-(sufijo + 1)]
        ):
            sufijo += 1

        aristas_comunes_inicio = max(0, prefijo - 1)
        aristas_comunes_final = min(
            max(0, sufijo - 1),
            max(
                0,
                min(len(ruta_anterior), len(nueva_ruta))
                - 1
                - aristas_comunes_inicio,
            ),
        )
        aristas_nuevas = max(0, len(nueva_ruta) - 1)
        aristas_comunes_final = min(
            aristas_comunes_final,
            max(0, aristas_nuevas - aristas_comunes_inicio),
        )

        conservar_inicio = items[:aristas_comunes_inicio]
        conservar_final = (
            items[-aristas_comunes_final:]
            if aristas_comunes_final
            else []
        )
        conservar = set(conservar_inicio + conservar_final)
        for item in items:
            if item not in conservar:
                self.canvas.delete(item)

        grosor = max(1, int(self.tamano_celda * 0.1))
        nuevos_items = []
        fin_nuevas_aristas = aristas_nuevas - aristas_comunes_final
        for indice in range(aristas_comunes_inicio, fin_nuevas_aristas):
            nuevos_items.append(
                self._crear_segmento_ruta(
                    picker_id,
                    nueva_ruta[indice],
                    nueva_ruta[indice + 1],
                    color,
                    grosor,
                )
            )
        for item in nuevos_items:
            self.canvas.itemconfigure(item, arrow=tk.NONE)

        items = conservar_inicio + nuevos_items + conservar_final
        if items:
            ultimo_anterior = datos["items"][-1] if datos["items"] else None
            if (
                ultimo_anterior in conservar
                and ultimo_anterior != items[-1]
            ):
                self.canvas.itemconfigure(ultimo_anterior, arrow=tk.NONE)
            self.canvas.itemconfigure(items[-1], arrow=tk.LAST)

        datos["ruta"] = nueva_ruta
        datos["items"] = items
        datos["color"] = color

    def dibujar_picker(self, x, y, p_data, color="#ef4444"):
        cx, cy = self._obtener_centro(x, y)
        radio = self.tamano_celda * 0.35

        if p_data.get("recolectando", False):
            color = "#10b981"

        inicial = str(p_data['id'])[-1]
        font_size = max(6, int(self.tamano_celda * 0.4))
        items = self._items_pickers.get(p_data["id"])
        if items is None:
            circulo = self.canvas.create_oval(
                0, 0, 0, 0, fill=color, outline="#1e293b", width=1
            )
            numero = self.canvas.create_text(
                cx, cy, text=inicial, fill="white",
                font=("Arial", font_size, "bold"),
            )
            etiqueta_id = self.canvas.create_text(0, 0, anchor=tk.S)
            etiqueta_detalle = self.canvas.create_text(
                0, 0, justify=tk.CENTER, anchor=tk.N
            )
            items = (circulo, numero, etiqueta_id, etiqueta_detalle)
            self._items_pickers[p_data["id"]] = items

        circulo, numero, etiqueta_id, etiqueta_detalle = items
        self.canvas.coords(circulo, cx - radio, cy - radio, cx + radio, cy + radio)
        self.canvas.itemconfigure(circulo, fill=color)
        self.canvas.coords(numero, cx, cy)
        self.canvas.itemconfigure(numero, text=inicial, font=("Arial", font_size, "bold"))

        wave_str = p_data.get("wave_actual", "-")
        if wave_str == "-":
            wave_str = "Sin wave"
        carga = p_data.get("carga_actual_kg", 0)
        cap = p_data.get("capacidad_carga_kg", 0)
        font_id = max(9, int(self.tamano_celda * 0.45))
        self.canvas.coords(etiqueta_id, cx, cy - radio - 2)
        self.canvas.itemconfigure(
            etiqueta_id,
            text=p_data["id"],
            fill=color,
            font=("Arial", font_id, "bold"),
            state=tk.NORMAL if self.mostrar_etiquetas.get() else tk.HIDDEN,
        )
        font_detalle = max(9, int(self.tamano_celda * 0.42))
        self.canvas.coords(etiqueta_detalle, cx, cy + radio + 2)
        self.canvas.itemconfigure(
            etiqueta_detalle,
            text=f"{carga:.0f}/{cap:.0f}kg\n{wave_str}",
            fill=color,
            font=("Arial", font_detalle, "bold"),
            state=tk.NORMAL if self.mostrar_etiquetas.get() else tk.HIDDEN,
        )
        for item in items:
            self.canvas.tag_raise(item)

    def actualizar_desde_simulacion(self):
        if not self.simulacion: return
        self._recalcular_dimensiones()

        estado = self.simulacion.get_estado()
        productos_recogidos = estado.get("productos_recogidos")
        actualizar_stock = False
        if (
            self._productos_recogidos_stock is None
            or productos_recogidos != self._productos_recogidos_stock
        ):
            stock_map = self._obtener_stock_por_celda()
            self._productos_recogidos_stock = productos_recogidos
            if stock_map != self._stock_por_celda:
                self._stock_por_celda = stock_map
                actualizar_stock = True

        if self._geometria_canvas() != self._geometria_dibujada:
            self._dibujar_fondo()
        elif actualizar_stock:
            self._actualizar_iconos_stock(self._stock_por_celda)

        rutas = estado.get('rutas', [])
        pickers_estado = estado.get('pickers', [])

        for i, p in enumerate(pickers_estado):
            color = COLORES_PICKERS[i % len(COLORES_PICKERS)]
            self.dibujar_recorrido(
                p["id"], rutas[i] if i < len(rutas) else [], color=color
            )

            # --- RESOLUCIÓN: Tu lógica de gris, eliminando la duplicación ---
            color_picker = color if p.get("activo", True) else "#94a3b8"
            self.dibujar_picker(p['x'], p['y'], p, color=color_picker)

        # Métricas Globales
        self.lbl_wave.config(text=f"Wave: {estado.get('wave_actual', 0)} / {estado.get('waves_totales', 0)}")
        self.lbl_paso.config(text=f"Paso actual: {estado.get('paso_actual', 0)}")
        self.lbl_productos.config(text=f"Productos Recogidos: {estado.get('productos_recogidos', 0)} / {estado.get('total_productos', 0)}")
        rec_wave = estado.get('productos_recogidos_wave_actual', 0)
        tot_wave = estado.get('total_productos_wave_actual', 0)
        self.lbl_productos_wave.config(text=f"Recogidos Wave Actual: {rec_wave} / {tot_wave}")
        self.lbl_distancia.config(text=f"Distancia Total: {estado.get('distancia', 0)} m")
        self.lbl_altura.config(text=f"Última altura recogida: Nivel {estado.get('ultima_altura', 0)}")

        ids_pickers = {picker["id"] for picker in pickers_estado}
        for picker_id in list(self.lbl_carga_pickers):
            if picker_id not in ids_pickers:
                for widget in self.lbl_carga_pickers[picker_id]:
                    widget.destroy()
                del self.lbl_carga_pickers[picker_id]

        # --- ESTADO INDIVIDUAL DE LOS PICKERS ---
        for picker in pickers_estado:
            picker_id = picker["id"]
            if picker_id not in self.lbl_carga_pickers:
                lbl = tk.Label(self.frame_carga_pickers, text="", bg="#f8fafc", font=("Segoe UI", 9), justify=tk.LEFT, anchor="w", wraplength=340)
                lbl.pack(fill=tk.X, pady=2)
                lbl.bind("<MouseWheel>", self._scroll_pickers)
                lbl.bind("<Button-4>", self._scroll_pickers)
                lbl.bind("<Button-5>", self._scroll_pickers)
                self.lbl_carga_pickers[picker_id] = [lbl]

            cantidad_actual = picker.get("productos_transportados", 0)
            cantidad_objetivo = picker.get("productos_objetivo", 0)
            items = picker.get("items_transportados", [])
            detalle = ", ".join(f"{i['producto_id']}({i['cantidad']})" for i in items) or "Vacío"

            # --- RESOLUCIÓN: Mantenemos tu texto de Terminado ---
            if not picker.get("activo", True):
                estado_texto = "✅ Terminado (en espera)"
            elif picker.get("recolectando", False):
                estado_texto = "📦 ¡RECOLECTANDO!"
            else:
                estado_texto = "🚶 En movimiento"

            # --- RESOLUCIÓN: Combinamos la wave de tu compañero con tu progreso ---
            wave_str = picker.get("wave_actual", "-")
            if wave_str == "-":
                wave_str = "Sin wave"

            texto = f"• {picker_id} | {wave_str}  ({cantidad_actual}/{cantidad_objetivo} items)\n  {estado_texto}\n  {detalle}"
            self.lbl_carga_pickers[picker_id][0].config(text=texto)

        self.txt_pedidos.config(state=tk.NORMAL)
        self.txt_pedidos.delete(1.0, tk.END)
        pedidos = estado.get('pedidos_actuales', {})

        if not pedidos:
            self.txt_pedidos.insert(tk.END, "No hay pedidos pendientes.\n¡Wave completada!")
        else:
            es_anidado = bool(pedidos) and isinstance(list(pedidos.values())[0], dict)
            def obtener_altura(pid):
                try:
                    inv = getattr(self.simulacion, "inventario", None)
                    if inv:
                        prod = inv.obtener_producto(pid)
                        return int(prod.ubicacion[2]) if len(prod.ubicacion) > 2 else 0
                except Exception: pass
                return 0

            if es_anidado:
                for picker_id, demanda in pedidos.items():
                    if demanda:
                        self.txt_pedidos.insert(tk.END, f"Picker {picker_id}:\n")
                        for prod_id, cant in demanda.items():
                            self.txt_pedidos.insert(tk.END, f"  - {prod_id}: {cant} u, alt ({obtener_altura(prod_id)})\n")
            else:
                for prod_id, cant in pedidos.items():
                    self.txt_pedidos.insert(tk.END, f"- {prod_id}: {cant} u, alt ({obtener_altura(prod_id)})\n")

        self.txt_pedidos.config(state=tk.DISABLED)
        self._actualizar_boton_volver(estado)

        if estado.get('terminada', False):
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Iniciar")

    def iniciar(self):
        self.mainloop()
