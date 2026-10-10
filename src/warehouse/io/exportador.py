import json
from pathlib import Path

from warehouse.warehouse.escenario import Escenario


def _producto_a_dict(prod, w) -> dict:
    return {
        "id": prod.id,
        "nombre": prod.nombre,
        "rack_id": prod.rack_id,
        "z": prod.z,
        "stock": prod.stock,
    }


def _pedido_a_dict(pedido) -> dict:
    return {
        "id": pedido.id,
        "prioridad": pedido.prioridad,
        "items": [
            {"producto_id": item.producto_id, "cantidad": item.cantidad}
            for item in pedido.items
        ],
    }


def escenario_a_dict(escenario: Escenario) -> dict:
    """Convierte un Escenario a un dict listo para serializar."""
    w = escenario.warehouse

    celdas = sorted((x, y) for (x, y) in w._nodo_por_xy.keys())
    # Excluir celdas que son racks (no deberían estar, pero por las dudas)
    celdas = [list(c) for c in celdas]

    racks = [
        {"id": r.id, "x": r.x, "y": r.y}
        for r in sorted(w.racks.values(), key=lambda r: r.id)
    ]

    zonas = [
        {"id": z.id, "p1": list(z.p1), "p2": list(z.p2)}
        for z in sorted(w.zonas.values(), key=lambda z: z.id)
    ]

    puertas = [
        {"id": p.id, "x": p.posicion.x, "y": p.posicion.y, "tipo": p.tipo}
        for p in sorted(w.puertas.values(), key=lambda p: p.id)
    ]

    productos = [
        _producto_a_dict(p, w) for p in sorted(w.productos.values(), key=lambda p: p.id)
    ]

    pedidos = [_pedido_a_dict(p) for p in escenario.pedidos]

    return {
        "version": "1.0",
        "nombre": escenario.nombre,
        "warehouse": {
            "ancho": w.ancho,
            "alto": w.alto,
            "celdas_transitables": celdas,
            "racks": racks,
            "zonas_despacho": zonas,
            "puertas": puertas,
        },
        "productos": productos,
        "pedidos": pedidos,
        "wave_config": {
            "max_pedidos": escenario.wave_config.max_pedidos,
            "max_productos": escenario.wave_config.max_productos,
        },
    }


def exportar_escenario(escenario: Escenario, path: str | Path) -> None:
    """Serializa un Escenario a JSON en la ruta indicada."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = escenario_a_dict(escenario)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
