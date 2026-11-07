# src/ui/visualization.py
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.cell import AMBOS, DESPACHO, PASILLO, PUERTA, RACK, E, N, O, S

COLOR_VOLVER_TERMINADA = "#10b981"
COLORES_PICKERS = [
    "#0ea5e9", # Celeste
    "#10b981", # Verde
    "#f59e0b", # Naranja
    "#8b5cf6", # Violeta
    "#ec4899", # Rosa
    "#ef4444", # Rojo (el original)
]

import platform


def _fuente_emoji():
    """Devuelve la fuente de emojis correcta según el sistema operativo."""
    sistema = platform.system()
    if sistema == "Windows":
        return "Segoe UI Emoji"
    elif sistema == "Darwin": # Mac
        return "Apple Color Emoji"
    else: # Linux
        return "Noto Color Emoji"

class Ventana(tk.Frame):
    """Vista de la simulación (colores y diseño originales)."""

    def __init__(self, warehouse, tamano_celda=30, master=None, on_volver=None):
        super().__init__(master)
        self.warehouse = warehouse
        self.tamano_celda = tamano_celda
        self.simulacion = None
        self.on_volver = on_volver
        self.en_ejecucion = False
        self.mostrar_grilla = True
        self.root = self.winfo_toplevel()

        if master is None:
            self.root.title("Wave Picking - Simulador")
            self.pack(fill=tk.BOTH, expand=True)

        # --- Configuración del Panel Lateral (Izquierda) ---
        self.panel = tk.Frame(self, width=280, bg="#f8fafc", padx=10, pady=10)
        self.panel.pack(side=tk.LEFT, fill=tk.Y)
        self.panel.pack_propagate(False)  # Evita que el frame se achique

        # 1. Controles
        tk.Label(self.panel, text="Controles", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(0, 5))

        frame_btn = tk.Frame(self.panel, bg="#f8fafc")
        frame_btn.pack(fill=tk.X)

        # Fila 0: Play/Pausar (Izquierda) y Reiniciar (Derecha)
        self.btn_play_pause = tk.Button(
            frame_btn, text="▶ Iniciar", command=self.btn_toggle_play_pause
        )
        self.btn_play_pause.grid(row=0, column=0, sticky="ew", pady=2, padx=(2, 1))

        tk.Button(
            frame_btn, text="🔄 Reiniciar", command=self.btn_reset
        ).grid(row=0, column=1, sticky="ew", pady=2, padx=(1, 2))

        # Fila 1: Atrás y Adelante
        frame_pasos = tk.Frame(frame_btn, bg="#f8fafc")
        frame_pasos.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

        tk.Button(frame_pasos, text="⏮ Atrás", command=self.btn_paso_atras).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 1))
        tk.Button(frame_pasos, text="⏭ Adelante", command=self.btn_paso).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1, 2))

        # Fila 2: Guardar (Izquierda) y Mostrar Grilla (Derecha)
        tk.Button(
            frame_btn, text="💾 Guardar", command=self.btn_guardar_partida
        ).grid(row=2, column=0, sticky="ew", pady=2, padx=(2, 1))

        self.btn_grilla = tk.Button(
            frame_btn, text="👁 Grilla", command=self.btn_toggle_grilla
        )
        self.btn_grilla.grid(row=2, column=1, sticky="ew", pady=2, padx=(1, 2))

        # Fila 3: Comparar Estrategias
        tk.Button(
            frame_btn, text="📊 Comparar Estrategias", command=self.btn_comparar_estrategias,
            bg="#e0f2fe", font=("Arial", 9, "bold")
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 2), padx=2)

        frame_btn.columnconfigure(0, weight=1)
        frame_btn.columnconfigure(1, weight=1)

        # 2. Métricas Globales
        tk.Label(self.panel, text="Métricas Globales", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))

        self.lbl_wave = tk.Label(self.panel, text="Wave: 0 / 0", font=("Arial", 10), bg="#f8fafc")
        self.lbl_wave.pack(anchor="w")

        self.lbl_paso = tk.Label(self.panel, text="Paso actual: 0", font=("Arial", 10), bg="#f8fafc")
        self.lbl_paso.pack(anchor="w")

        self.lbl_productos = tk.Label(self.panel, text="Productos Recogidos: 0 / 0", font=("Arial", 10), bg="#f8fafc")
        self.lbl_productos.pack(anchor="w")

        self.lbl_distancia = tk.Label(self.panel, text="Distancia Total: 0 m", font=("Arial", 10), bg="#f8fafc")
        self.lbl_distancia.pack(anchor="w")

        # --- NUEVA MÉTRICA DE ALTURA ---
        self.lbl_altura = tk.Label(self.panel, text="Última altura recogida: Nivel 0", font=("Arial", 10), bg="#f8fafc")
        self.lbl_altura.pack(anchor="w")

        # 3. Panel de Pickers
        tk.Label(self.panel, text="Estado Pickers", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))
        self.frame_carga_pickers = tk.Frame(self.panel, bg="#f8fafc")
        self.frame_carga_pickers.pack(fill=tk.X)
        self.lbl_carga_pickers = {}

        # 4. Pedidos de la Wave
        tk.Label(self.panel, text="Pedidos en Wave", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))
        self.txt_pedidos = tk.Text(self.panel, height=6, width=35, font=("Arial", 9), bg="#ffffff", state=tk.DISABLED)
        self.txt_pedidos.pack(fill=tk.X)

        # 5. Volver al menú
        self.btn_volver = tk.Button(self.panel, text="← Volver al menú", command=self.btn_volver_menu)
        self.btn_volver.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        self._estilo_volver_original = {
            "bg": self.btn_volver.cget("bg"),
            "fg": self.btn_volver.cget("fg"),
            "activebackground": self.btn_volver.cget("activebackground"),
        }

        # --- Configuración del Canvas (Derecha) ---
        self.ancho_px = self.warehouse.ancho_x * self.tamano_celda
        self.alto_px = self.warehouse.largo_y * self.tamano_celda
        self.canvas = tk.Canvas(self, width=self.ancho_px, height=self.alto_px, bg="#e2e8f0")
        self.canvas.pack(side=tk.RIGHT, padx=10, pady=10)

    def _obtener_emoji_producto(self, nombre_producto):
        nombre = nombre_producto.lower()

        # --- Hardware y Periféricos ---
        if "monitor" in nombre: return "🖥️"
        if "notebook" in nombre: return "💻"
        if "tablet" in nombre: return "📱"
        if "teclado" in nombre: return "⌨️"
        if "mouse" in nombre: return "🖱️"
        if "impresora" in nombre: return "🖨️"
        if "scanner" in nombre: return "📄"
        if "proyector" in nombre: return "📽️"
        if "webcam" in nombre or "cámara" in nombre: return "📷"
        if "micrófono" in nombre: return "🎤"
        if "parlante" in nombre: return "🔊"
        if "auricular" in nombre: return "🎧"

        # --- Componentes de PC ---
        if "placa" in nombre: return "🎮"
        if "memoria" in nombre or "ram" in nombre: return "🧠"
        if "disco" in nombre: return "💾"
        if "fuente" in nombre: return "⚡"
        if "gabinete" in nombre: return "🗄️"
        if "soporte" in nombre: return "📐"

        # --- Redes y Conectividad ---
        if "router" in nombre: return "📡"
        if "switch" in nombre: return "🔀"
        if "hub" in nombre: return "🔗"
        if "cable" in nombre: return "🔌"
        if "cargador" in nombre: return "🔋"
        if "ups" in nombre: return "🔋" # Batería/UPS

        # --- Muebles y Oficina ---
        if "silla" in nombre or "escritorio" in nombre: return "🪑"
        if "lámpara" in nombre: return "💡"

        # --- Por defecto ---
        return "📦"

    def btn_toggle_grilla(self):
        self.mostrar_grilla = not self.mostrar_grilla

        if self.mostrar_grilla:
            self.btn_grilla.config(text="👁 Ocultar Grilla")
        else:
            self.btn_grilla.config(text="👁 Mostrar Grilla")

        # Forzamos un redibujado para aplicar el cambio
        self.actualizar_desde_simulacion()

    def set_simulacion(self, sim):
        self.simulacion = sim

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
            self.btn_volver.config(text="✔ Simulación terminada: Volver al menú",
                                   bg=COLOR_VOLVER_TERMINADA, fg="white",
                                   activebackground=COLOR_VOLVER_TERMINADA)
        else:
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
        cx = (x * self.tamano_celda) + (self.tamano_celda / 2)
        cy = ((self.warehouse.largo_y - 1 - y) * self.tamano_celda) + (self.tamano_celda / 2)
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
        if stock_map is None:
            stock_map = {}

        # 1. Agrupamos los emojis por celda (x, y)
        productos_por_celda = {}

        if self.simulacion and hasattr(self.simulacion, 'productos'):
            # Ordenamos por altura Z para que el nivel 1 quede abajo de todo
            productos_ordenados = sorted(
                self.simulacion.productos,
                key=lambda p: p.ubicacion[2]
            )

            for prod in productos_ordenados:
                x, y, z = prod.ubicacion
                coords = (x, y)
                emoji = self._obtener_emoji_producto(prod.nombre)

                if coords not in productos_por_celda:
                    productos_por_celda[coords] = []

                # Evitamos duplicados si hay dos productos iguales en la misma celda
                if emoji not in productos_por_celda[coords]:
                    productos_por_celda[coords].append(emoji)

                # Máximo 3 productos por celda (por los niveles Z)
                if len(productos_por_celda[coords]) == 3:
                    pass # Ya tenemos los 3 niveles

        # 2. Dibujamos la grilla
        for y in range(self.warehouse.largo_y):
            for x in range(self.warehouse.ancho_x):
                cell = self.warehouse.grid[y][x]
                x1 = x * self.tamano_celda
                y1 = (self.warehouse.largo_y - 1 - y) * self.tamano_celda
                x2 = x1 + self.tamano_celda
                y2 = y1 + self.tamano_celda

                color = "#f1f5f9"
                if cell.tipo == RACK: color = "#1e3a8a"
                elif cell.tipo == DESPACHO: color = "#10b981"
                elif cell.tipo == PUERTA: color = "#f59e0b"
                elif cell.tipo == "VACIA": color = "#cbd5e1"

                # 1. Dibujamos el fondo de color
                if cell.tipo == RACK:
                    # Si es un rack, forzamos que siempre tenga borde (grilla)
                    outline_color = "#e2e8f0"
                else:
                    # Si es otro tipo de celda, respetamos el botón de ocultar/mostrar
                    outline_color = "#e2e8f0" if self.mostrar_grilla else ""

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=outline_color)

                cx, cy = self._obtener_centro(x, y)

                # 3. Dibujamos los iconos
                if cell.tipo == RACK:
                    if (x, y) in productos_por_celda:
                        emojis = productos_por_celda[(x, y)]
                        cantidad = len(emojis)

                        # Ajustamos el tamaño y la posición según cuántos haya
                        if cantidad == 1:
                            tam = int(self.tamano_celda * 0.8)
                            self.canvas.create_text(cx, cy, text=emojis[0], font=(_fuente_emoji(), tam))
                        elif cantidad == 2:
                            tam = int(self.tamano_celda * 0.5)
                            self.canvas.create_text(cx, cy - self.tamano_celda * 0.2, text=emojis[0], font=(_fuente_emoji(), tam))
                            self.canvas.create_text(cx, cy + self.tamano_celda * 0.2, text=emojis[1], font=(_fuente_emoji(), tam))
                        elif cantidad >= 3:
                            tam = int(self.tamano_celda * 0.4)
                            self.canvas.create_text(cx, cy - self.tamano_celda * 0.3, text=emojis[0], font=(_fuente_emoji(), tam))
                            self.canvas.create_text(cx, cy, text=emojis[1], font=(_fuente_emoji(), tam))
                            self.canvas.create_text(cx, cy + self.tamano_celda * 0.3, text=emojis[2], font=(_fuente_emoji(), tam))
                    # else:
                    #     # Rack vacío
                    #     tam = int(self.tamano_celda * 0.8)
                    #     self.canvas.create_text(cx, cy, text="📚", font=(_fuente_emoji(), tam))

                elif cell.tipo == PUERTA:
                    tam = int(self.tamano_celda * 0.8)
                    self.canvas.create_text(cx, cy, text="🚪", font=(_fuente_emoji(), tam))
                elif cell.tipo == DESPACHO:
                    # Despacho vacío (solo se ve el color verde de fondo)
                    pass

                # 4. Flechas de los pasillos
                elif cell.tipo == PASILLO and cell.sentido != AMBOS:
                    flecha = ""
                    if cell.sentido == N: flecha = "↑"
                    elif cell.sentido == S: flecha = "↓"
                    elif cell.sentido == E: flecha = "→"
                    elif cell.sentido == O: flecha = "←"
                    self.canvas.create_text(cx, cy, text=flecha, fill="#64748b", font=("Arial", 10, "bold"))

    def _dibujar_icono_paquete(self, cx, cy):
        """Dibuja una caja de cartón pequeña en el centro de la celda."""
        tam = self.tamano_celda * 0.45
        x1, y1 = cx - tam, cy - tam
        x2, y2 = cx + tam, cy + tam

        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill="#d97706", outline="#190b03", width=1
        )
        self.canvas.create_line(x1, cy, x2, cy, fill="#fde68a", width=1)
        self.canvas.create_line(cx, y1, cx, y2, fill="#fde68a", width=1)
        self.canvas.create_polygon(
            x1, y1, x1 + tam * 0.5, y1, x1, y1 + tam * 0.5,
            fill="#fef08a", outline=""
        )

    def dibujar_recorrido(self, ruta, color="#0ea5e9"):
        if not ruta or len(ruta) < 2:
            return
        puntos_px = []
        for (x, y) in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])
        self.canvas.create_line(puntos_px, fill=color, width=2, dash=(4, 2), arrow=tk.LAST)

    def dibujar_picker(self, x, y, p_data, color="#ef4444"):
        cx, cy = self._obtener_centro(x, y)

        esta_recolectando = p_data.get("recolectando", False)

        # --- CAMBIO DE COLOR SI ESTÁ RECOLECTANDO ---
        if esta_recolectando:
            color = "#10b981" # Verde brillante
        # --------------------------------------------

        carga = p_data.get('carga_actual_kg', 0)
        # Si lleva más de 0kg de carga, mostramos el camión, sino el carrito
        emoji = "🚚" if carga > 0 else "🛒"

        tamano_emoji = int(self.tamano_celda * 0.9)
        self.canvas.create_text(cx, cy, text=emoji, font=(_fuente_emoji(), tamano_emoji))

        # --- TEXTOS (ARRIBA Y ABAJO) ---
        radio = self.tamano_celda * 0.35

        wave = p_data.get('wave_actual', '?')
        cap = p_data.get('capacidad_carga_kg', 0)

        # Texto arriba: ID y Wave
        texto_arriba = f"{p_data['id']} | W{wave}"
        self.canvas.create_text(cx, cy - radio - 10, text=texto_arriba, fill=color, font=("Arial", 7, "bold"))

        # Texto abajo: Peso
        texto_abajo = f"{carga:.0f}/{cap:.0f}kg"
        self.canvas.create_text(cx, cy + radio + 10, text=texto_abajo, fill=color, font=("Arial", 7, "bold"))

    def actualizar_desde_simulacion(self):
        if not self.simulacion:
            return

        estado = self.simulacion.get_estado()
        self.canvas.delete("all")

        # --- OBTENER STOCK Y PASARLO AL DIBUJO ---
        stock_map = self._obtener_stock_por_celda()
        self.dibujar_warehouse(stock_map)
        # -----------------------------------------

        rutas = estado.get('rutas', [])
        pickers_estado = estado.get('pickers', [])

        for i, p in enumerate(pickers_estado):
            color = COLORES_PICKERS[i % len(COLORES_PICKERS)]

            if i < len(rutas):
                self.dibujar_recorrido(rutas[i], color=color)

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
                lbl = tk.Label(self.frame_carga_pickers, text="", bg="#f8fafc", font=("Arial", 9), justify=tk.LEFT, anchor="w")
                lbl.pack(fill=tk.X, pady=2)
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
        self._actualizar_boton_volver(estado)

        if estado.get('terminada', False):
            self.en_ejecucion = False
            self.btn_play_pause.config(text="▶ Iniciar")

    def iniciar(self):
        self.mainloop()
