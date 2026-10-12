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
        {"id": r.id, "x": r.x, "y": r.y, "niveles": r.niveles}
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

    waves_dict = [_wave_a_dict(w) for w in escenario.waves]
    resultados_dict = {
        wave_id: _resultado_a_dict(r) for wave_id, r in escenario.resultados.items()
    }

    sesion_dict = None
    if escenario.sesion is not None:
        sesion_dict = {
            "wave_actual": escenario.sesion.wave_actual,
            "indice_actual": escenario.sesion.indice_actual,
            "estrategia_recorrido": escenario.sesion.estrategia_recorrido,
        }

    return {
        "version": "1.0",
        "nombre": escenario.nombre,
        "seed": escenario.seed,
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
        "waves": waves_dict,
        "resultados": resultados_dict,
        "sesion": sesion_dict,
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


def _wave_a_dict(wave) -> dict:
    return {
        "id": wave.id,
        "estado": wave.estado.value,
        "max_pedidos": wave.max_pedidos,
        "max_productos": wave.max_productos,
        "pedido_ids": [p.id for p in wave.pedidos],
    }


def _resultado_a_dict(r) -> dict:
    return {
        "estrategia": r.estrategia,
        "orden_paradas": list(r.orden_paradas),
        "camino_completo": list(r.camino_completo),
        "distancia_total": r.distancia_total,
        "nodos_visitados": r.nodos_visitados,
        "aristas_recorridas": r.aristas_recorridas,
        "tiempo_segundos": r.tiempo_segundos,
        "indices_de_paradas": list(r.indices_de_paradas),
    }
