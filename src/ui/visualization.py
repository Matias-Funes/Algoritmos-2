# src/ui/visualization.py
import tkinter as tk
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.cell import PASILLO, RACK, PUERTA, DESPACHO, N, S, E, O, AMBOS

class Ventana:
    def __init__(self, warehouse, tamano_celda=30):
        self.warehouse = warehouse
        self.tamano_celda = tamano_celda
        self.simulacion = None

        self.root = tk.Tk()
        self.root.title("Wave Picking - Simulador")

        # --- Configuración del Panel Lateral (Izquierda) ---
        self.panel = tk.Frame(self.root, width=280, bg="#f8fafc", padx=10, pady=10)
        self.panel.pack(side=tk.LEFT, fill=tk.Y)
        self.panel.pack_propagate(False) # Evita que el frame se achique

        # 1. Controles (Punto 12 del PDF)
        tk.Label(self.panel, text="Controles", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", pady=(0, 5))
        
        frame_btn = tk.Frame(self.panel, bg="#f8fafc")
        frame_btn.pack(fill=tk.X)
        
        tk.Button(frame_btn, text="▶ Iniciar", command=self.btn_iniciar).grid(row=0, column=0, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="⏸ Pausar", command=self.btn_pausar).grid(row=0, column=1, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="⏯ Continuar", command=self.btn_continuar).grid(row=1, column=0, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="🔄 Reiniciar", command=self.btn_reset).grid(row=1, column=1, sticky="ew", pady=2, padx=2)
        tk.Button(frame_btn, text="⏭ Paso a Paso", command=self.btn_paso).grid(row=2, column=0, columnspan=2, sticky="ew", pady=2, padx=2)
        
        frame_btn.columnconfigure(0, weight=1)
        frame_btn.columnconfigure(1, weight=1)

        # 2. Métricas Globales (Punto 9, 10, 11)
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

        # --- Configuración del Canvas (Derecha) ---
        self.ancho_px = self.warehouse.ancho_x * self.tamano_celda
        self.alto_px = self.warehouse.largo_y * self.tamano_celda
        self.canvas = tk.Canvas(self.root, width=self.ancho_px, height=self.alto_px, bg="#e2e8f0")
        self.canvas.pack(side=tk.RIGHT, padx=10, pady=10)

    def set_simulacion(self, sim):
        self.simulacion = sim

    # --- Callbacks ---
    def btn_iniciar(self):
        if self.simulacion: self.simulacion.iniciar()
    
    def btn_pausar(self):
        if self.simulacion: self.simulacion.pausar()
        
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
            
    def btn_reset(self):
        if self.simulacion:
            self.simulacion.resetear()
            self.actualizar_desde_simulacion()

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

                # Colores base
                color = "#f1f5f9"
                if cell.tipo == RACK: color = "#1e3a8a"
                elif cell.tipo == DESPACHO: color = "#10b981"
                elif cell.tipo == PUERTA: color = "#f59e0b"
                elif cell.tipo == "VACIA": color = "#cbd5e1"
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#e2e8f0")

                # Flechas de sentido para los pasillos (Punto 11 del PDF)
                if cell.tipo == PASILLO and cell.sentido != AMBOS:
                    cx, cy = self._obtener_centro(x, y)
                    flecha = ""
                    if cell.sentido == N: flecha = "↑"
                    elif cell.sentido == S: flecha = "↓"
                    elif cell.sentido == E: flecha = "→"
                    elif cell.sentido == O: flecha = "←"
                    
                    self.canvas.create_text(cx, cy, text=flecha, fill="#64748b", font=("Arial", 10, "bold"))

    def dibujar_recorrido(self, ruta, color="#0ea5e9"):
        if not ruta or len(ruta) < 2: return
        puntos_px = []
        for (x, y) in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])
        self.canvas.create_line(puntos_px, fill=color, width=2, dash=(4, 2), arrow=tk.LAST)

    def dibujar_picker(self, x, y, id_picker, recolectando=False):
        cx, cy = self._obtener_centro(x, y)
        radio = self.tamano_celda * 0.35
        
        # Lógica de color: Verde si recolecta, Rojo si se mueve
        color_relleno = "#10b981" if recolectando else "#ef4444"
        color_borde = "#047857" if recolectando else "#991b1b"
        
        self.canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill=color_relleno, outline=color_borde, width=2)
        self.canvas.create_text(cx, cy, text=str(id_picker), fill="white", font=("Arial", 8, "bold"))

    def actualizar_desde_simulacion(self):
        if not self.simulacion: return
        
        estado = self.simulacion.get_estado()
        self.canvas.delete("all")
        self.dibujar_warehouse()
        
        # 1. Rutas
        for ruta in estado.get('rutas', []):
            self.dibujar_recorrido(ruta)
            
        # 2. Pickers
        for p in estado.get('pickers', []):
            if p.get("activo", True):
                # Le pasamos si está recolectando para que cambie de color
                self.dibujar_picker(p['x'], p['y'], p['id'], p.get("recolectando", False))

        # 3. Actualizar Panel de Texto (Métricas)
        self.lbl_wave.config(text=f"Wave: {estado.get('wave_actual', 0)} / {estado.get('waves_totales', 0)}")
        self.lbl_paso.config(text=f"Paso actual: {estado.get('paso_actual', 0)}")
        self.lbl_productos.config(text=f"Productos Recogidos: {estado.get('productos_recogidos', 0)} / {estado.get('total_productos', 0)}")
        self.lbl_distancia.config(text=f"Distancia Total: {estado.get('distancia', 0)} m")

        # 4. Actualizar Panel de Pickers
        pickers_estado = estado.get("pickers", [])
        ids_pickers = {picker["id"] for picker in pickers_estado}
        
        # Limpiar pickers que ya no están
        for picker_id in list(self.lbl_carga_pickers):
            if picker_id not in ids_pickers:
                for widget in self.lbl_carga_pickers[picker_id]:
                    widget.destroy()
                del self.lbl_carga_pickers[picker_id]

        # Crear/Actualizar pickers
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
            
            # NUEVO: Cartel de recolección
            esta_recolectando = picker.get("recolectando", False)
            estado_texto = "📦 ¡RECOLECTANDO!" if esta_recolectando else "🚶 En movimiento"
            
            texto = f"• {picker_id}: {cantidad_actual}/{cantidad_objetivo} items\n  {estado_texto}\n  {detalle}"
            self.lbl_carga_pickers[picker_id][0].config(text=texto)

        # 5. Actualizar Pedidos (Reales)
        self.txt_pedidos.config(state=tk.NORMAL)
        self.txt_pedidos.delete(1.0, tk.END)
        
        pedidos = estado.get('pedidos_actuales', {})
        if not pedidos:
            self.txt_pedidos.insert(tk.END, "No hay pedidos pendientes.\n¡Wave completada!")
        else:
            # Si es un diccionario de diccionarios (asignaciones por picker)
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
                # Si es un diccionario simple (demanda global)
                for prod_id, cant in pedidos.items():
                    self.txt_pedidos.insert(tk.END, f"- {prod_id}: {cant} unidades\n")
                
        self.txt_pedidos.config(state=tk.DISABLED)

    def iniciar(self):
        self.root.mainloop()