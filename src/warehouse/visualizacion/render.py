import tkinter as tk

from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.warehouse.warehouse import Warehouse

COLORES_TIPO = {
    TipoNodo.PASILLO: "#ffffff",
    TipoNodo.RACK: "#a1887f",
    TipoNodo.DESPACHO: "#c8e6c9",
    TipoNodo.PUERTA: "#ffcc80",
}

COLOR_BORDE_CELDA = "#e0e0e0"
COLOR_BORDE_RACK = "#8d6e63"
COLOR_BORDE_EXT = "#424242"

COLOR_PICKER = "#1565c0"
COLOR_PICKER_BORDE = "#ffffff"

COLOR_PRODUCTO_PENDIENTE = "#ef5350"
COLOR_PRODUCTO_RECOGIDO = "#66bb6a"
COLOR_PRODUCTO_INVENTARIO = "#d0d0d0"

COLOR_RECORRIDO_HECHO = "#2196f3"
COLOR_RECORRIDO_PENDIENTE = "#cfd8dc"

COLOR_CANVAS_FONDO = "#fafafa"


def dibujar_warehouse(
    canvas: tk.Canvas,
    warehouse: Warehouse,
    celda_px: int,
    margen: int,
) -> dict[tuple[int, int], tuple[float, float, float, float]]:
    """
    Dibuja el warehouse centrado en el canvas.
    El canvas debe tener width/height configurados.
    """
    coords: dict[tuple[int, int], tuple[float, float, float, float]] = {}

    ancho_warehouse = warehouse.ancho * celda_px
    alto_warehouse = warehouse.alto * celda_px

    ancho_canvas = int(canvas["width"])
    alto_canvas = int(canvas["height"])

    # Offset para centrar (mínimo margen)
    offset_x = max((ancho_canvas - ancho_warehouse) // 2, margen)
    offset_y = max((alto_canvas - alto_warehouse) // 2, margen)

    def celda_a_px(x: int, y: int) -> tuple[float, float, float, float]:
        x0 = offset_x + x * celda_px
        y0 = offset_y + (warehouse.alto - 1 - y) * celda_px
        return (x0, y0, x0 + celda_px, y0 + celda_px)

    # Rectángulo exterior
    canvas.create_rectangle(
        offset_x - 2,
        offset_y - 2,
        offset_x + ancho_warehouse + 2,
        offset_y + alto_warehouse + 2,
        fill="white",
        outline=COLOR_BORDE_EXT,
        width=2,
    )

    # Pasillos, despacho, puertas (nodos del grafo)
    for nodo in warehouse.grafo.nodos():
        x, y = nodo.posicion.x, nodo.posicion.y
        coords[(x, y)] = celda_a_px(x, y)
        x0, y0, x1, y1 = coords[(x, y)]
        canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=COLORES_TIPO[nodo.tipo],
            outline=COLOR_BORDE_CELDA,
        )

    # Racks (no están en el grafo)
    for rack in warehouse.racks.values():
        x, y = rack.x, rack.y
        coords[(x, y)] = celda_a_px(x, y)
        x0, y0, x1, y1 = coords[(x, y)]
        canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=COLORES_TIPO[TipoNodo.RACK],
            outline=COLOR_BORDE_RACK,
        )

    return coords


def centro_celda_px(
    coords: dict[tuple[int, int], tuple[float, float, float, float]],
    x: int,
    y: int,
) -> tuple[float, float]:
    x0, y0, x1, y1 = coords[(x, y)]
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def dibujar_punto(
    canvas: tk.Canvas,
    cx: float,
    cy: float,
    radio: float,
    color: str,
) -> None:
    borde = COLOR_PICKER_BORDE
    canvas.create_oval(
        cx - radio,
        cy - radio,
        cx + radio,
        cy + radio,
        fill=color,
        outline=borde if borde else "",
        width=2 if borde else 0,
    )


def dibujar_polilinea(
    canvas: tk.Canvas,
    puntos: list[tuple[float, float]],
    color: str,
    grosor: int = 2,
    dash: tuple[int, int] | None = None,
) -> None:
    if len(puntos) < 2:
        return
    flat = [c for p in puntos for c in p]
    kwargs = {
        "fill": color,
        "width": grosor,
        "capstyle": tk.ROUND,
        "joinstyle": tk.ROUND,
    }
    if dash:
        kwargs["dash"] = dash
    canvas.create_line(*flat, **kwargs)


def dibujar_zonas(
    canvas: tk.Canvas,
    warehouse: Warehouse,
    coords: dict[tuple[int, int], tuple[float, float, float, float]],
) -> None:
    for zona in warehouse.zonas.values():
        x0, y0, _, _ = coords[(zona.p1[0], zona.p1[1])]
        _, _, x1, y1 = coords[(zona.p2[0], zona.p2[1])]
        canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            outline="#2e7d32",
            width=2,
            dash=(4, 4),
        )


def crear_panel_leyenda(parent: tk.Widget) -> tk.Frame:
    """Crea un frame con la leyenda de colores."""
    frame = tk.LabelFrame(
        parent,
        text="Leyenda",
        padx=10,
        pady=8,
        font=("sans-serif", 10, "bold"),
        bg=COLOR_CANVAS_FONDO,
    )

    items = [
        ("Pasillo", COLORES_TIPO[TipoNodo.PASILLO], COLOR_BORDE_CELDA),
        ("Rack", COLORES_TIPO[TipoNodo.RACK], COLOR_BORDE_RACK),
        ("Zona de despacho", COLORES_TIPO[TipoNodo.DESPACHO], "#2e7d32"),
        ("Puerta", COLORES_TIPO[TipoNodo.PUERTA], ""),
        ("Producto pendiente", COLOR_PRODUCTO_PENDIENTE, ""),
        ("Producto recogido", COLOR_PRODUCTO_RECOGIDO, ""),
        ("Picker", COLOR_PICKER, COLOR_PICKER_BORDE),
        ("Recorrido hecho", COLOR_RECORRIDO_HECHO, ""),
        ("Recorrido pendiente", COLOR_RECORRIDO_PENDIENTE, ""),
        ("Producto en inventario", COLOR_PRODUCTO_INVENTARIO, ""),
    ]

    for texto, color, borde in items:
        fila = tk.Frame(frame, bg=COLOR_CANVAS_FONDO)
        fila.pack(fill="x", pady=2)

        swatch = tk.Canvas(
            fila,
            width=20,
            height=20,
            bg=COLOR_CANVAS_FONDO,
            highlightthickness=0,
        )
        swatch.pack(side="left", padx=(0, 8))
        swatch.create_rectangle(
            3,
            3,
            17,
            17,
            fill=color,
            outline=borde if borde else color,
            width=1,
        )

        tk.Label(
            fila,
            text=texto,
            anchor="w",
            bg=COLOR_CANVAS_FONDO,
            font=("sans-serif", 9),
        ).pack(side="left", fill="x", expand=True)

    return frame
