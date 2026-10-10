import tkinter as tk

from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.warehouse.warehouse import Warehouse

COLORES_TIPO = {
    TipoNodo.PASILLO: "#f5f5f5",
    TipoNodo.RACK: "#8b7355",
    TipoNodo.DESPACHO: "#c8e6c9",
    TipoNodo.PUERTA: "#ffb74d",
}

COLOR_BORDE_CELDA = "#dddddd"
COLOR_BORDE_EXT = "#333333"
COLOR_PICKER = "#1565c0"
COLOR_PRODUCTO_PENDIENTE = "#e53935"
COLOR_PRODUCTO_RECOGIDO = "#43a047"
COLOR_RECORRIDO_HECHO = "#1e88e5"
COLOR_RECORRIDO_PENDIENTE = "#bbbbbb"


def dibujar_warehouse(
    canvas: tk.Canvas,
    warehouse: Warehouse,
    celda_px: int,
    margen: int,
) -> dict[tuple[int, int], tuple[float, float, float, float]]:
    """
    Dibuja el warehouse y devuelve el mapa (x, y) -> (x0, y0, x1, y1) en píxeles.
    El eje y se invierte para que (0,0) quede abajo (despacho abajo, racks arriba).
    """
    coords: dict[tuple[int, int], tuple[float, float, float, float]] = {}
    ancho_px = warehouse.ancho * celda_px
    alto_px = warehouse.alto * celda_px

    def celda_a_px(x: int, y: int) -> tuple[float, float, float, float]:
        x0 = margen + x * celda_px
        y0 = margen + (warehouse.alto - 1 - y) * celda_px
        return (x0, y0, x0 + celda_px, y0 + celda_px)

    # Rectángulo de fondo
    canvas.create_rectangle(
        margen - 2,
        margen - 2,
        margen + ancho_px + 2,
        margen + alto_px + 2,
        fill="white",
        outline=COLOR_BORDE_EXT,
        width=2,
    )

    # Pasillos / despacho / puertas (nodos del grafo)
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
            outline=COLOR_BORDE_CELDA,
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
    canvas.create_oval(
        cx - radio, cy - radio, cx + radio, cy + radio, fill=color, outline=""
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
    kwargs = {"fill": color, "width": grosor}
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
