"""
scenario_loader.py
==================
Carga de escenarios desde JSON.

Etapa 1: devuelve el Warehouse construido + los datos crudos de
productos, pedidos, pickers y configuración.

Los productos/pedidos/pickers se devuelven crudos (list[dict]) porque
en Etapa 3 se convertirán en objetos Product/Order/Picker.

Uso:
    python -m src.io.scenario_loader data/scenarios/escenario_basico.json
"""

import json

from src.io._deps import Pasillo, Puerta, Rack, Warehouse, ZonaDespacho


class ErrorDeCarga(ValueError):
    """Error al cargar un escenario desde JSON."""

    pass


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def cargar_escenario(ruta_json):
    """
    Lee un archivo JSON y devuelve:
        (warehouse, productos_raw, pedidos_raw, pickers_raw, config)

    Lanza:
        FileNotFoundError si la ruta no existe.
        ValueError si el JSON es inválido o le faltan campos obligatorios.
    """
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("No existe el archivo: %s" % ruta_json)
    except json.JSONDecodeError as e:
        raise ValueError("JSON mal formado: %s" % e) from e

    _validar_secciones(data)

    warehouse = _construir_warehouse(data["warehouse"])
    warehouse.rellenar_pasillos_implicitos()

    return (
        warehouse,
        data["productos"],
        data["pedidos"],
        data["pickers"],
        data["configuracion"],
    )


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------


def _validar_secciones(data):
    """Verifica que el JSON tenga todas las secciones y campos obligatorios."""
    for seccion in ("warehouse", "pickers", "productos", "pedidos", "configuracion"):
        if seccion not in data:
            raise ValueError("Falta sección obligatoria: '%s'" % seccion)

    w = data["warehouse"]
    for campo in ("dimensiones", "puertas", "zonas_despacho", "racks", "pasillos"):
        if campo not in w:
            raise ValueError("Falta campo '%s' en warehouse" % campo)

    dim = w["dimensiones"]
    for campo in ("ancho_x", "largo_y"):
        if campo not in dim:
            raise ValueError("Falta campo '%s' en warehouse.dimensiones" % campo)


def _requerir(d, campos, contexto):
    """Verifica que el diccionario d tenga todos los campos indicados."""
    for campo in campos:
        if campo not in d:
            raise ValueError("Falta campo '%s' en %s: %s" % (campo, contexto, d))


# ---------------------------------------------------------------------------
# Construcción del warehouse
# ---------------------------------------------------------------------------


def _construir_warehouse(w_data):
    """Construye un Warehouse a partir de la sección 'warehouse' del JSON."""
    # Leer dimensiones
    ancho_x = int(w_data["dimensiones"]["ancho_x"])
    largo_y = int(w_data["dimensiones"]["largo_y"])

    if ancho_x <= 0 or largo_y <= 0:
        raise ValueError(
            "Dimensiones inválidas: ancho_x=%d, largo_y=%d" % (ancho_x, largo_y)
        )

    warehouse = Warehouse(ancho_x, largo_y)

    # Puertas
    for p in w_data["puertas"]:
        _requerir(p, ("id", "tipo", "ubicacion"), "puerta")
        try:
            puerta = Puerta(
                puerta_id=p["id"],
                tipo=p["tipo"],
                x=int(p["ubicacion"]["x"]),
                y=int(p["ubicacion"]["y"]),
            )
            warehouse.add_puerta(puerta)
        except ValueError as e:
            id_puerta = p.get("id", "?")
            raise ValueError("Puerta inválida '%s': %s" % (id_puerta, e))

    # Zonas de despacho
    for z in w_data["zonas_despacho"]:
        _requerir(
            z,
            ("id", "puerta_id", "ubicacion", "ancho", "alto", "peso_max_kg"),
            "zona_despacho",
        )
        try:
            zona = ZonaDespacho(
                zona_id=z["id"],
                puerta_id=z["puerta_id"],
                x=int(z["ubicacion"]["x"]),
                y=int(z["ubicacion"]["y"]),
                ancho=int(z["ancho"]),
                alto=int(z["alto"]),
                peso_max_kg=float(z["peso_max_kg"]),
            )
            warehouse.add_zona_despacho(zona)
        except ValueError as e:
            id_zona = z.get("id", "?")
            raise ValueError("Zona inválida '%s': %s" % (id_zona, e))

    # Racks
    for r in w_data["racks"]:
        _requerir(r, ("id", "ubicacion", "ancho", "alto"), "rack")
        try:
            rack = Rack(
                rack_id=r["id"],
                x=int(r["ubicacion"]["x"]),
                y=int(r["ubicacion"]["y"]),
                ancho=int(r["ancho"]),
                alto=int(r["alto"]),
            )
            warehouse.add_rack(rack)
        except ValueError as e:
            id_rack = r.get("id", "?")
            raise ValueError("Rack inválido '%s': %s" % (id_rack, e))

    # Pasillos
    for p in w_data["pasillos"]:
        _requerir(p, ("id", "ubicacion", "ancho", "alto", "sentido"), "pasillo")
        try:
            pasillo = Pasillo(
                pas_id=p["id"],
                x=int(p["ubicacion"]["x"]),
                y=int(p["ubicacion"]["y"]),
                ancho=int(p["ancho"]),
                alto=int(p["alto"]),
                sentido=p["sentido"],
            )
            warehouse.add_pasillo(pasillo)
        except ValueError as e:
            id_pasillo = p.get("id", "?")
            raise ValueError("Pasillo inválido '%s': %s" % (id_pasillo, e))

    return warehouse


# ---------------------------------------------------------------------------
# Demo CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = "data/scenarios/escenario_basico.json"

    try:
        wh, productos, pedidos, pickers, config = cargar_escenario(ruta)
        print("OK Escenario cargado: %s" % ruta)
        print("  Dimensiones:  %d x %d" % (wh.ancho_x, wh.largo_y))
        print("  Racks:        %d" % len(wh.racks))
        print("  Pasillos:     %d" % len(wh.pasillos))
        print("  Puertas:      %d" % len(wh.puertas))
        print("  Zonas:        %d" % len(wh.zonas))
        print("  Productos:    %d" % len(productos))
        print("  Pedidos:      %d" % len(pedidos))
        print("  Pickers:      %d" % len(pickers))
        print("  Config:       %s" % config)
        print()
        wh.print_ascii()
    except Exception as e:
        print("ERROR: %s: %s" % (type(e).__name__, e))
        sys.exit(1)
