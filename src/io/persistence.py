# src/io/persistence.py
import json
import os

def guardar_escenario(ruta_json, warehouse, productos_raw, pedidos_raw, pickers_raw, config):
    """
    Guarda el estado actual del sistema en un archivo JSON.
    Usa el mismo formato que el scenario_loader para que sea compatible.
    """
    escenario = {
        "warehouse": {
            "dimensiones": {"ancho_x": warehouse.ancho_x, "largo_y": warehouse.largo_y},
            "puertas": [p.__dict__ for p in warehouse.puertas.values()],
            "zonas_despacho": [z.__dict__ for z in warehouse.zonas.values()],
            "racks": [{"id": r.id, "ubicacion": {"x": r.x, "y": r.y}, "ancho": r.ancho, "alto": r.alto} for r in warehouse.racks.values()],
            "pasillos": [{"id": p.id, "ubicacion": {"x": p.x, "y": p.y}, "ancho": p.ancho, "alto": p.alto, "sentido": p.sentido} for p in warehouse.pasillos.values()]
        },
        "pickers": pickers_raw,
        "productos": productos_raw,
        "pedidos": pedidos_raw,
        "configuracion": config
    }

    os.makedirs(os.path.dirname(ruta_json), exist_ok=True)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(escenario, f, indent=2, ensure_ascii=False)
    print(f"Estado guardado exitosamente en {ruta_json}")