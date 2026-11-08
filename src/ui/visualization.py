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
    "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#ef4444"
]

class Ventana(tk.Frame):
    """Vista de la simulación con escalado automático del mapa (Zoom to Fit)."""

    def __init__(self, warehouse, tamano_celda=30, master=None, on_volver=None):
        super().__init__(master)
        self.warehouse = warehouse
        self.tamano_celda = tamano_celda
        self.simulacion = None
        self.on_volver = on_volver
        self.en_ejecucion = False
        self.root = self.winfo_toplevel()
        
        # Variables para el centrado dinámico del mapa
        self.offset_x = 0
        self.offset_y = 0

        if master is None:
            self.root.title("Wave Picking - Simulador")
            self.root.state('zoomed') 
            self.pack(fill=tk.BOTH, expand=True)

        # ==========================================
        # PANEL IZQUIERDO (Controles y Métricas - SIN SCROLL)
        # ==========================================
        self.panel = tk.Frame(self, width=370, bg="#f8fafc", padx=10, pady=10)
        self.panel.pack(side=tk.LEFT, fill=tk.Y)
        self.panel.pack_propagate(False)

        # 0. BOTÓN VOLVER AL MENÚ (Movido arriba para que siempre se vea)
        self.btn_volver = tk.Button(self.panel, text="← Volver al menú", command=self.btn_volver_menu, font=("Arial", 10, "bold"))
        self.btn_volver.pack(fill=tk.X, pady=(0, 15))
        self._estilo_volver_original = {
            "bg": self.btn_volver.cget("bg"), "fg": self.btn_volver.cget("fg"),
            "activebackground": self.btn_volver.cget("activebackground"),
        }

        # 1. Controles
        tk.Label(self.panel, text="Controles", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(0, 5))
        
        frame_btn = tk.Frame(self.panel, bg="#f8fafc")
        frame_btn.pack(fill=tk.X)

        self.btn_play_pause = tk.Button(frame_btn, text="▶ Iniciar", command=self.btn_toggle_play_pause)
        self.btn_play_pause.grid(row=0, column=0, sticky="ew", pady=3, padx=(0, 3))
        
        tk.Button(frame_btn, text="🔄 Reiniciar", command=self.btn_reset).grid(row=0, column=1, sticky="ew", pady=3, padx=(3, 0))

        frame_pasos = tk.Frame(frame_btn, bg="#f8fafc")
        frame_pasos.grid(row=1, column=0, columnspan=2, sticky="ew", pady=3)
        tk.Button(frame_pasos, text="⏮ Atrás", command=self.btn_paso_atras).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        tk.Button(frame_pasos, text="⏭ Adelante", command=self.btn_paso).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        tk.Button(frame_btn, text="💾 Guardar Partida", command=self.btn_guardar_partida).grid(row=2, column=0, columnspan=2, sticky="ew", pady=3)
        tk.Button(frame_btn, text="📊 Comparar Estrategias", command=self.btn_comparar_estrategias, bg="#e0f2fe", font=("Arial", 9, "bold")).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 3))

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
        self.lbl_altura = tk.Label(self.panel, text="Última altura recogida: Nivel 0", font=("Arial", 10), bg="#f8fafc")
        self.lbl_altura.pack(anchor="w")

        # 3. Panel de Pickers
        tk.Label(self.panel, text="Estado Pickers", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))
        self.frame_carga_pickers = tk.Frame(self.panel, bg="#f8fafc")
        self.frame_carga_pickers.pack(fill=tk.X)
        self.lbl_carga_pickers = {}

        # 4. Pedidos de la Wave
        tk.Label(self.panel, text="Pedidos en Wave", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))
        # Reducimos un poco el alto del Text para que no ocupe tanto espacio vertical
        self.txt_pedidos = tk.Text(self.panel, height=5, width=38, font=("Arial", 9), bg="#ffffff", state=tk.DISABLED)
        self.txt_pedidos.pack(fill=tk.X)

        # ==========================================
        # PANEL DERECHO (Mapa Adaptable sin Scroll)
        # ==========================================
        self.frame_mapa = tk.Frame(self, bg="#e2e8f0")
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

    def _on_canvas_resize(self, event):
        self._recalcular_dimensiones()
        if self.simulacion:
            self.actualizar_desde_simulacion()
        else:
            self.canvas.delete("all")
            self.dibujar_warehouse(self._obtener_stock_por_celda())

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
        style.configure("Treeview", rowheight=25, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        notebook = ttk.Notebook(ventana)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab_global = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
        tab_detalle = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
        notebook.add(tab_global, text="Resumen Global")
        notebook.add(tab_detalle, text="Detalle por Wave")

        # Resumen Global
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

        tk.Label(frame_ganadores, text=f"🏆 Mejor Distancia: {nombres_ui.get(ganador_dist, ganador_dist)}", font=("Arial", 12, "bold"), fg="#0ea5e9", bg="#f8fafc").pack(anchor="w")
        tk.Label(frame_ganadores, text=f"⏱️ Mejor Tiempo: {nombres_ui.get(ganador_tiempo, ganador_tiempo)}", font=("Arial", 12, "bold"), fg="#0ea5e9", bg="#f8fafc").pack(anchor="w")

        # Detalle
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
        tk.Button(ventana, text="Cerrar", command=ventana.destroy, width=15).pack(pady=(0, 10))

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
            self.btn_volver.config(text="✔ Simulación terminada: Volver al menú", bg=COLOR_VOLVER_TERMINADA, fg="white", activebackground=COLOR_VOLVER_TERMINADA)
        else:
            self.btn_volver.config(text="← Volver al menú", **self._estilo_volver_original)

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

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#e2e8f0")

                if cell.tipo == RACK:
                    stock = stock_map.get((x, y), 0)
                    if stock > 0:
                        cx, cy = self._obtener_centro(x, y)
                        self._dibujar_icono_paquete(cx, cy)

                if cell.tipo == PASILLO and cell.sentido != AMBOS:
                    cx, cy = self._obtener_centro(x, y)
                    flecha = ""
                    if cell.sentido == N: flecha = "↑"
                    elif cell.sentido == S: flecha = "↓"
                    elif cell.sentido == E: flecha = "→"
                    elif cell.sentido == O: flecha = "←"
                    font_size = max(6, int(self.tamano_celda * 0.6))
                    self.canvas.create_text(cx, cy, text=flecha, fill="#64748b", font=("Arial", font_size, "bold"))

    def _dibujar_icono_paquete(self, cx, cy):
        tam = self.tamano_celda * 0.45
        x1, y1 = cx - tam, cy - tam
        x2, y2 = cx + tam, cy + tam
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#d97706", outline="#190b03", width=1)
        self.canvas.create_line(x1, cy, x2, cy, fill="#fde68a", width=1) 
        self.canvas.create_line(cx, y1, cx, y2, fill="#fde68a", width=1) 

    def dibujar_recorrido(self, ruta, color="#0ea5e9"):
        if not ruta or len(ruta) < 2: return
        puntos_px = []
        for (x, y) in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])
        grosor = max(1, int(self.tamano_celda * 0.1))
        self.canvas.create_line(puntos_px, fill=color, width=grosor, dash=(4, 2), arrow=tk.LAST)

    def dibujar_picker(self, x, y, p_data, color="#ef4444"):
        cx, cy = self._obtener_centro(x, y)
        radio = self.tamano_celda * 0.35
        
        if p_data.get("recolectando", False):
            color = "#10b981"
            
        self.canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill=color, outline="#1e293b", width=1)
        inicial = str(p_data['id'])[-1]
        font_size = max(6, int(self.tamano_celda * 0.4))
        self.canvas.create_text(cx, cy, text=inicial, fill="white", font=("Arial", font_size, "bold"))
        
        wave = p_data.get('wave_actual', '?')
        carga = p_data.get('carga_actual_kg', 0)
        cap = p_data.get('capacidad_carga_kg', 0)
        detalle = f"{p_data['id']} | W{wave} | {carga:.0f}/{cap:.0f}kg"
        font_detalle = max(6, int(self.tamano_celda * 0.35))
        self.canvas.create_text(cx, cy + radio + (font_detalle/2), text=detalle, fill=color, font=("Arial", font_detalle, "bold"))

    def actualizar_desde_simulacion(self):
        if not self.simulacion: return
        self._recalcular_dimensiones()
        
        estado = self.simulacion.get_estado()
        self.canvas.delete("all")
        
        stock_map = self._obtener_stock_por_celda()
        self.dibujar_warehouse(stock_map)

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
        self.lbl_altura.config(text=f"Última altura recogida: Nivel {estado.get('ultima_altura', 0)}")

        ids_pickers = {picker["id"] for picker in pickers_estado}
        for picker_id in list(self.lbl_carga_pickers):
            if picker_id not in ids_pickers:
                for widget in self.lbl_carga_pickers[picker_id]:
                    widget.destroy()
                del self.lbl_carga_pickers[picker_id]

        for picker in pickers_estado:
            picker_id = picker["id"]
            if picker_id not in self.lbl_carga_pickers:
                lbl = tk.Label(self.frame_carga_pickers, text="", bg="#f8fafc", font=("Arial", 9), justify=tk.LEFT, anchor="w", wraplength=340)
                lbl.pack(fill=tk.X, pady=2)
                self.lbl_carga_pickers[picker_id] = [lbl]

            cantidad_actual = picker.get("productos_transportados", 0)
            cantidad_objetivo = picker.get("productos_objetivo", 0)
            items = picker.get("items_transportados", [])
            detalle = ", ".join(f"{i['producto_id']}({i['cantidad']})" for i in items) or "Vacío"
            estado_texto = "📦 ¡RECOLECTANDO!" if picker.get("recolectando", False) else "🚶 En movimiento"
            
            texto = f"• {picker_id}: {cantidad_actual}/{cantidad_objetivo} items\n  {estado_texto}\n  {detalle}"
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