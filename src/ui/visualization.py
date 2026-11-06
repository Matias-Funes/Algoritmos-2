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

class Ventana(tk.Frame):
    """Vista de la simulación (colores y diseño originales).

    Puede usarse embebida (master = ventana principal del controlador) o sola (master=None),
    en cuyo caso crea su propia ventana y se arranca con iniciar().
    on_volver: función que lleva de vuelta al menú (la entrega el controlador).
    """

    def __init__(self, warehouse, tamano_celda=30, master=None, on_volver=None):
        super().__init__(master)
        self.warehouse = warehouse
        self.tamano_celda = tamano_celda
        self.simulacion = None
        self.on_volver = on_volver
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

        tk.Button(frame_btn, text="▶ Iniciar", command=self.btn_iniciar).grid(row=0, column=0, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="⏸ Pausar", command=self.btn_pausar).grid(row=0, column=1, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="⏯ Continuar", command=self.btn_continuar).grid(row=1, column=0, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="🔄 Reiniciar", command=self.btn_reset).grid(row=1, column=1, sticky="ew", pady=2, padx=2)

        frame_pasos = tk.Frame(frame_btn, bg="#f8fafc")
        frame_pasos.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)

        tk.Button(frame_pasos, text="⏮ Atrás", command=self.btn_paso_atras).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 1))
        tk.Button(frame_pasos, text="⏭ Adelante", command=self.btn_paso).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1, 2))
        tk.Button(
            frame_btn,
            text="📊 Comparar Estrategias",
            command=self.btn_comparar_estrategias,
            bg="#e0f2fe", # Un color celestito para que resalte
            font=("Arial", 9, "bold")
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 2), padx=2)
        tk.Button(frame_btn, text="💾 Guardar Partida", command=self.btn_guardar_partida).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=2, padx=2
        )

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

        # 3. Panel de Pickers
        tk.Label(self.panel, text="Estado Pickers", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))
        self.frame_carga_pickers = tk.Frame(self.panel, bg="#f8fafc")
        self.frame_carga_pickers.pack(fill=tk.X)
        self.lbl_carga_pickers = {}

        # 4. Pedidos de la Wave
        tk.Label(self.panel, text="Pedidos en Wave", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(15, 5))
        self.txt_pedidos = tk.Text(self.panel, height=6, width=35, font=("Arial", 9), bg="#ffffff", state=tk.DISABLED)
        self.txt_pedidos.pack(fill=tk.X)

        # 5. Volver al menú (siempre visible, abajo del panel)
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

    def set_simulacion(self, sim):
        self.simulacion = sim

    # --- Callbacks ---
    def btn_iniciar(self):
        if self.simulacion:
            self.simulacion.iniciar()

    def btn_pausar(self):
        if self.simulacion:
            self.simulacion.pausar()

    def btn_continuar(self):
        if self.simulacion:
            if hasattr(self.simulacion, 'continuar'):
                self.simulacion.continuar()
            else:
                self.simulacion.iniciar()

    def btn_paso(self):
        if self.simulacion:
            self.simulacion.avanzar_paso()
            self.actualizar_desde_simulacion()

    def btn_paso_atras(self):
        if self.simulacion:
            if self.simulacion.retroceder_paso():
                self.actualizar_desde_simulacion()

    def btn_reset(self):
        if self.simulacion:
            self.simulacion.resetear()
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

        totales = comparacion["totales"]
        nombres = list(totales)

        # Crear ventana emergente
        ventana = tk.Toplevel(self.root)
        ventana.title("Comparación de Estrategias")
        ventana.geometry("600x400")
        ventana.minsize(400, 300) # Tamaño mínimo para que no se rompa
        ventana.transient(self.root) # Que quede adelante

        # Frame principal
        frame = tk.Frame(ventana, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Título
        tk.Label(frame, text="Resumen de Estrategias", font=("Arial", 14, "bold")).pack(pady=(0, 15))

        # Diccionario para mostrar nombres claros en la UI
        nombres_ui = {
            "A": "A (Orden de pedidos)",
            "B": "B (Vecino más cercano)"
        }

        # --- TABLA (Treeview) ---
        # Usamos los nombres claros en los encabezados
        columnas = ["Métrica"] + [nombres_ui.get(n, f"Estrategia {n}") for n in nombres]
        tabla = ttk.Treeview(frame, columns=columnas, show="headings", height=6)

        for col in columnas:
            tabla.heading(col, text=col)
            tabla.column(col, anchor="center", width=150) # Un poco más ancho para que entre el texto

        # Insertar datos
        filas = [
            ("Tiempo total (ms)", "tiempo_ms", "{:.3f}"),
            ("Distancia total", "distancia", "{}"),
            ("Nodos visitados", "nodos", "{}"),
            ("Aristas recorridas", "aristas", "{}"),
        ]

        for etiqueta, clave, fmt in filas:
            valores = [etiqueta] + [fmt.format(totales[n].get(clave, 0)) for n in nombres]
            tabla.insert("", tk.END, values=valores)

        tabla.pack(fill=tk.BOTH, expand=True)

        # --- Ganadores ---
        ganadores_frame = tk.Frame(frame, pady=10)
        ganadores_frame.pack(fill=tk.X)

        ganador_dist = comparacion.get('ganador_distancia', '-')
        ganador_tiempo = comparacion.get('ganador_tiempo', '-')

        texto_dist = f"🏆 Ganador distancia: {nombres_ui.get(ganador_dist, ganador_dist)}"
        texto_tiempo = f"⏱️ Ganador tiempo: {nombres_ui.get(ganador_tiempo, ganador_tiempo)}"

        tk.Label(ganadores_frame, text=texto_dist,
                 font=("Arial", 11, "bold"), fg="#0ea5e9").pack(anchor="w")
        tk.Label(ganadores_frame, text=texto_tiempo,
                 font=("Arial", 11, "bold"), fg="#0ea5e9").pack(anchor="w")

        # Botón cerrar
        tk.Button(frame, text="Cerrar", command=ventana.destroy, width=15).pack(pady=(10, 0))

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

    # --- Volver al menú ---
    def _simulacion_terminada(self, estado=None):
        """True si la simulación terminó (o si no hay ninguna en marcha)."""
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

    def dibujar_warehouse(self):
        for y in range(self.warehouse.largo_y):
            for x in range(self.warehouse.ancho_x):
                cell = self.warehouse.grid[y][x]
                x1 = x * self.tamano_celda
                y1 = (self.warehouse.largo_y - 1 - y) * self.tamano_celda
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

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#e2e8f0")

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
                    self.canvas.create_text(cx, cy, text=flecha, fill="#64748b", font=("Arial", 10, "bold"))

    def dibujar_recorrido(self, ruta, color="#0ea5e9"):
        if not ruta or len(ruta) < 2:
            return
        puntos_px = []
        for (x, y) in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])
        self.canvas.create_line(puntos_px, fill=color, width=2, dash=(4, 2), arrow=tk.LAST)

    def dibujar_picker(self, x, y, id_picker, color="#ef4444"):
        cx, cy = self._obtener_centro(x, y)
        radio = self.tamano_celda * 0.35
        # Usamos el color asignado para el relleno, y un gris oscuro para el borde
        self.canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill=color, outline="#1e293b", width=2)
        self.canvas.create_text(cx, cy, text=str(id_picker), fill="white", font=("Arial", 8, "bold"))

    def actualizar_desde_simulacion(self):
        if not self.simulacion:
            return

        estado = self.simulacion.get_estado()
        self.canvas.delete("all")
        self.dibujar_warehouse()

        # Obtenemos las rutas y los pickers
        rutas = estado.get('rutas', [])
        pickers_estado = estado.get('pickers', [])

        # Recorremos los pickers con su índice para asignarles un color
        for i, p in enumerate(pickers_estado):
            color = COLORES_PICKERS[i % len(COLORES_PICKERS)]

            # 1. Dibujar el recorrido del picker (si tiene ruta)
            if i < len(rutas):
                self.dibujar_recorrido(rutas[i], color=color)

            # 2. Dibujar el círculo del picker
            if p.get("activo", True):
                self.dibujar_picker(p['x'], p['y'], p['id'], color=color)

        self.lbl_wave.config(text=f"Wave: {estado.get('wave_actual', 0)} / {estado.get('waves_totales', 0)}")
        self.lbl_paso.config(text=f"Paso actual: {estado.get('paso_actual', 0)}")
        self.lbl_productos.config(text=f"Productos Recogidos: {estado.get('productos_recogidos', 0)} / {estado.get('total_productos', 0)}")
        self.lbl_distancia.config(text=f"Distancia Total: {estado.get('distancia', 0)} m")

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

            texto = f"• {picker_id}: {cantidad_actual}/{cantidad_objetivo} items\n  {detalle}"
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

            if es_anidado:
                for picker_id, demanda in pedidos.items():
                    if demanda:
                        self.txt_pedidos.insert(tk.END, f"Picker {picker_id}:\n")
                        for prod_id, cant in demanda.items():
                            self.txt_pedidos.insert(tk.END, f"  - {prod_id}: {cant} unidades\n")
            else:
                for prod_id, cant in pedidos.items():
                    self.txt_pedidos.insert(tk.END, f"- {prod_id}: {cant} unidades\n")

        self.txt_pedidos.config(state=tk.DISABLED)
        self._actualizar_boton_volver(estado)

    def iniciar(self):
        self.mainloop()
