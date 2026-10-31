# src/ui/visualization.py
import tkinter as tk
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.cell import PASILLO, RACK, PUERTA, DESPACHO

class Ventana:
    def __init__(self, warehouse, tamano_celda=30):
        self.warehouse = warehouse
        self.tamano_celda = tamano_celda
        self.simulacion = None  # D nos pasará esto después

        self.root = tk.Tk()
        self.root.title("Wave Picking - Simulador")

        # --- Panel Lateral (Controles) ---
        self.panel = tk.Frame(self.root, width=250, bg="#b92f0c")
        self.panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(self.panel, text="Controles", font=("Arial", 14, "bold"), bg="#e2e8f0").pack(pady=10)
        
        # Botones (llaman a métodos de D)
        tk.Button(self.panel, text="▶ Iniciar", width=20, command=self.btn_iniciar).pack(pady=5)
        tk.Button(self.panel, text="⏸ Pausar", width=20, command=self.btn_pausar).pack(pady=5)
        tk.Button(self.panel, text="⏭ Paso a Paso", width=20, command=self.btn_paso).pack(pady=5)
        tk.Button(self.panel, text="🔄 Reiniciar", width=20, command=self.btn_reset).pack(pady=5)

        # --- Panel de Métricas ---
        tk.Label(self.panel, text="Métricas", font=("Arial", 14, "bold"), bg="#e2e8f0").pack(pady=(20, 10))
        tk.Label(
            self.panel,
            text="Carga por picker",
            bg="#e2e8f0",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", padx=10)
        self.frame_carga_pickers = tk.Frame(self.panel, bg="#e2e8f0")
        self.frame_carga_pickers.pack(fill=tk.X, padx=8)
        self.lbl_carga_pickers = {}
        self.lbl_distancia = tk.Label(self.panel, text="Distancia: 0 m", bg="#e2e8f0", font=("Arial", 11))
        self.lbl_distancia.pack(anchor="w", padx=10)

        # --- Canvas del Warehouse ---
        self.ancho_px = self.warehouse.ancho_x * self.tamano_celda
        self.alto_px = self.warehouse.largo_y * self.tamano_celda
        self.canvas = tk.Canvas(self.root, width=self.ancho_px, height=self.alto_px, bg="white")
        self.canvas.pack(side=tk.RIGHT, padx=10, pady=10)

    def set_simulacion(self, sim):
        """D llama a esto para conectar su motor con nuestra UI."""
        self.simulacion = sim

    # --- Callbacks de los botones ---
    def btn_iniciar(self):
        if self.simulacion: self.simulacion.iniciar()
    
    def btn_pausar(self):
        if self.simulacion: self.simulacion.pausar()
    
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

                color = "#f1f5f9"
                if cell.tipo == RACK: color = "#1e3a8a"
                elif cell.tipo == DESPACHO: color = "#10b981"
                elif cell.tipo == PUERTA: color = "#f59e0b"
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#cbd5e1")

    def dibujar_recorrido(self, ruta, color="blue"):
        if not ruta or len(ruta) < 2: return
        puntos_px = []
        for (x, y) in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])
        self.canvas.create_line(puntos_px, fill=color, width=3, arrow=tk.LAST)

    def dibujar_picker(self, x, y, id_picker):
        cx, cy = self._obtener_centro(x, y)
        radio = self.tamano_celda * 0.3
        self.canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill="red", outline="darkred", width=2)
        self.canvas.create_text(cx, cy, text=str(id_picker), fill="white", font=("Arial", 8, "bold"))

    def actualizar_desde_simulacion(self):
        """Lee el estado del motor de D y redibuja todo."""
        if not self.simulacion: return
        
        estado = self.simulacion.get_estado()
        self.canvas.delete("all")
        self.dibujar_warehouse()
        
        # Dibujar rutas (si las hay)
        for ruta in estado.get('rutas', []):
            self.dibujar_recorrido(ruta)
            
        # Dibujar pickers
        for p in estado.get('pickers', []):
            if p.get("activo", True):
                self.dibujar_picker(p['x'], p['y'], p['id'])

        # Actualizar métricas
        pickers_estado = estado.get("pickers", [])
        ids_pickers = {picker["id"] for picker in pickers_estado}
        for picker_id in list(self.lbl_carga_pickers):
            if picker_id not in ids_pickers:
                fila = self.lbl_carga_pickers.pop(picker_id)
                fila[0].destroy()
                fila[1].destroy()

        for picker in pickers_estado:
            picker_id = picker["id"]
            if picker_id not in self.lbl_carga_pickers:
                lbl_carga = tk.Label(
                    self.frame_carga_pickers,
                    bg="#e2e8f0",
                    font=("Arial", 10, "bold"),
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=220,
                )
                lbl_carga.pack(anchor="w", fill=tk.X, pady=(5, 0))
                lbl_items = tk.Label(
                    self.frame_carga_pickers,
                    bg="#e2e8f0",
                    font=("Arial", 9),
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=220,
                )
                lbl_items.pack(anchor="w", fill=tk.X)
                self.lbl_carga_pickers[picker_id] = (
                    lbl_carga,
                    lbl_items,
                )

            cantidad_actual = picker.get("productos_transportados", 0)
            cantidad_objetivo = picker.get("productos_objetivo", 0)
            items = picker.get("items_transportados", [])
            detalle_items = ", ".join(
                f"{item['producto_id']} x{item['cantidad']}"
                for item in items
            ) or "ninguno"
            self.lbl_carga_pickers[picker_id][0].config(
                text=(
                    f"{picker_id}: {cantidad_actual}/{cantidad_objetivo} "
                    "productos"
                )
            )
            self.lbl_carga_pickers[picker_id][1].config(
                text=f"Lleva: {detalle_items}"
            )
        self.lbl_distancia.config(text=f"Distancia: {estado.get('distancia', 0)} m")

    def iniciar(self):
        self.root.mainloop()



if __name__ == "__main__":
    from src.io.scenario_loader import cargar_escenario
    print("1. Cargando escenario...") # Agregamos prints para debuggear
    wh, _, _, _, _ = cargar_escenario("data/scenarios/generado.json")
    print("2. Escenario cargado. Creando ventana...")
    
    ventana = Ventana(wh, tamano_celda=16)
    
    class SimulacionFalsa:
        def __init__(self): self.paso = 0
        def iniciar(self): print("Dice: Iniciar simulación")
        def pausar(self): print("Dice: Pausar simulación")
        def avanzar_paso(self): 
            self.paso += 1
            print(f"Dice: Avanzando al paso {self.paso}")
        def resetear(self): print("Dice: Reiniciar")
        def get_estado(self):
            return {
                'pickers': [{'x': 5 + self.paso, 'y': 5, 'id': 'PK1'}],
                'rutas': [[(5,5), (6,5), (7,5)]],
                'productos_recogidos': self.paso,
                'total_productos': 10,
                'distancia': self.paso * 2
            }

    sim_falsa = SimulacionFalsa()
    ventana.set_simulacion(sim_falsa)
    print("3. Abriendo ventana...")
    ventana.iniciar()
    print("4. Ventana cerrada.")