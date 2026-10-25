# src/ui/visualization.py
# ---------------------------------------------------------------
# Ventana de Tkinter para dibujar el Warehouse, rutas y pickers.
# ---------------------------------------------------------------

import tkinter as tk

from src.core.cell import DESPACHO, PASILLO, PUERTA, RACK


class Ventana:
    def __init__(self, warehouse, tamano_celda=None):
        self.warehouse = warehouse

        # 1. Calculamos el tamaño de la celda dinámicamente si no se pasa uno
        if tamano_celda is None:
            max_ancho_px = 1000
            max_alto_px = 700
            self.tamano_celda = min(
                max_ancho_px // self.warehouse.ancho_x,
                max_alto_px // self.warehouse.largo_y,
            )
            # Nos aseguramos de que la celda no sea microscópica
            self.tamano_celda = max(self.tamano_celda, 5)
        else:
            self.tamano_celda = tamano_celda

        # 2. Creamos la ventana principal (UNA SOLA VEZ)
        self.root = tk.Tk()
        self.root.title("Wave Picking - Simulación")

        # 3. Calculamos el tamaño total de la ventana en píxeles
        self.ancho_px = self.warehouse.ancho_x * self.tamano_celda
        self.alto_px = self.warehouse.largo_y * self.tamano_celda

        # 4. Creamos el lienzo (Canvas) con las dimensiones calculadas
        self.canvas = tk.Canvas(
            self.root, width=self.ancho_px, height=self.alto_px, bg="white"
        )
        self.canvas.pack(padx=10, pady=10)

        # 5. Inicializamos las variables para guardar rutas y pickers
        self.rutas_actuales = []
        self.pickers_actuales = []  # Lista de (x, y, id_picker)

    def _obtener_centro(self, x, y):
        """
        Convierte coordenadas de la grilla (x,y) a píxeles en el canvas.
        Invierte el eje Y para que (0,0) esté abajo a la izquierda.
        Devuelve el centro de la celda.
        """
        cx = (x * self.tamano_celda) + (self.tamano_celda / 2)
        cy = ((self.warehouse.largo_y - 1 - y) * self.tamano_celda) + (
            self.tamano_celda / 2
        )
        return cx, cy

    def dibujar_warehouse(self):
        """Pinta el grid base del almacén."""
        for y in range(self.warehouse.largo_y):
            for x in range(self.warehouse.ancho_x):
                cell = self.warehouse.grid[y][x]

                x1 = x * self.tamano_celda
                y1 = (self.warehouse.largo_y - 1 - y) * self.tamano_celda
                x2 = x1 + self.tamano_celda
                y2 = y1 + self.tamano_celda

                color = "#cfe1f4"  # Default pasillo
                if cell.tipo == RACK:
                    color = "#000000"
                elif cell.tipo == DESPACHO:
                    color = "#56ce7c"
                elif cell.tipo == PUERTA:
                    color = "#714803"

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline="#8C8989"
                )

    def dibujar_recorrido(self, ruta, color="blue"):
        """Dibuja una línea conectando los nodos de una ruta."""
        if len(ruta) < 2:
            return

        # Convertir todos los nodos a pixeles
        puntos_px = []
        for x, y in ruta:
            cx, cy = self._obtener_centro(x, y)
            puntos_px.extend([cx, cy])

        # Dibujar la línea
        self.canvas.create_line(puntos_px, fill=color, width=3, arrow=tk.LAST)

    def dibujar_picker(self, x, y, id_picker):
        """Dibuja un picker moderno, estilizado y profesional dentro de su celda."""
        cx, cy = self._obtener_centro(x, y)

        # Escalar según el tamaño de la celda para que nunca se deforme
        radio = self.tamano_celda * 0.32

        # 1. SOMBRA SUTIL (Da efecto de profundidad sobre la celda)
        self.canvas.create_oval(
            cx - radio * 0.9,
            cy - radio * 0.4 + 4,
            cx + radio * 0.9,
            cy + radio * 1.3 + 4,
            fill="#cbd5e1",
            outline="",
        )

        # 2. CUERPO (Camisa estilo corporativa / uniforme azul moderno)
        self.canvas.create_rectangle(
            cx - radio * 0.7,
            cy - radio * 0.1,
            cx + radio * 0.7,
            cy + radio * 1.1,
            fill="#2563eb",
            outline="#1d4ed8",
            width=1.5,
        )

        # 3. CABEZA (Círculo con tono de piel cálido y borde definido)
        r_cabeza = radio * 0.55
        self.canvas.create_oval(
            cx - r_cabeza,
            cy - r_cabeza * 1.8,
            cx + r_cabeza,
            cy - r_cabeza * 0.4,
            fill="#fde68a",
            outline="#d97706",
            width=1.5,
        )

        # 4. GORRA (Casquete rojo elegante + visera moderna saliente)
        # Casquete superior
        self.canvas.create_arc(
            cx - r_cabeza * 1.2,
            cy - r_cabeza * 2.3,
            cx + r_cabeza * 1.2,
            cy - r_cabeza * 0.9,
            start=0,
            extent=180,
            fill="#dc2626",
            outline="#991b1b",
            width=1.5,
            style="pieslice",
        )
        # Visera frontal (hacia adelante)
        self.canvas.create_oval(
            cx - r_cabeza * 0.1,
            cy - r_cabeza * 1.5,
            cx + r_cabeza * 1.3,
            cy - r_cabeza * 1.1,
            fill="#991b1b",
            outline="",
        )
        # Pequeño detalle de logo en la gorra (una letra blanca sutil)
        self.canvas.create_text(
            cx - r_cabeza * 0.3,
            cy - r_cabeza * 1.6,
            text="P",
            fill="white",
            font=("Arial", max(6, int(self.tamano_celda * 0.08)), "bold"),
        )

        # 5. ETIQUETA DE ID FLOTANTE (Diseño minimalista oscuro con bordes redondeados simulados)
        # Fondo del cartelito
        self.canvas.create_rectangle(
            cx - radio * 0.9,
            cy + radio * 1.15,
            cx + radio * 0.9,
            cy + radio * 1.75,
            fill="#0f172a",
            outline="#334155",
            width=1.5,
        )
        # Texto del ID perfectamente centrado
        self.canvas.create_text(
            cx,
            cy + radio * 1.45,
            text=f"ID: {id_picker}",
            fill="#f8fafc",
            font=("Arial", max(7, int(self.tamano_celda * 0.11)), "bold"),
        )

    def actualizar(self, rutas=None, pickers=None):
        """
        Limpia el canvas y redibuja todo.
        rutas: lista de rutas (cada ruta es una lista de tuplas (x,y)).
        pickers: lista de diccionarios con {'x', 'y', 'id'}.
        """
        self.canvas.delete("all")  # Limpiar todo

        # 1. Dibujar el piso (warehouse)
        self.dibujar_warehouse()

        # 2. Dibujar rutas
        if rutas:
            for ruta in rutas:
                self.dibujar_recorrido(ruta, color="#0ea5e9")  # Color azul claro

        # 3. Dibujar pickers
        if pickers:
            for p in pickers:
                self.dibujar_picker(p["x"], p["y"], p["id"])

    def iniciar(self):
        self.root.mainloop()


# =================================================================
# DEMO (ejecutar con: python -m src.ui.visualization)
# =================================================================
if __name__ == "__main__":
    from src.io.scenario_loader import cargar_escenario

    print("Cargando escenario...")
    wh, _, _, _, _ = cargar_escenario("data/scenarios/escenario_basico.json")

    print("Creando ventana...")
    ventana = Ventana(wh)

    # Probamos dibujar una ruta falsa y un picker
    ruta_falsa = [(1, 3), (2, 3), (3, 3), (4, 3)]
    pickers_falsos = [{"x": 4, "y": 3, "id": "PK1"}]

    ventana.actualizar(rutas=[ruta_falsa], pickers=pickers_falsos)
    ventana.iniciar()
