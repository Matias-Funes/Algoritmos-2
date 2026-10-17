# src/io/scenario_loader.py
# ---------------------------------------------------------------
# Lee un archivo JSON de escenario y construye los objetos del modelo.
# ---------------------------------------------------------------

import json
import os
from src.core.warehouse import Warehouse, Rack, Pasillo, Puerta, ZonaDespacho


def cargar_escenario(ruta_json):
    """
    Lee el JSON y devuelve una tupla:
        (warehouse, productos_raw, pedidos_raw, pickers_raw, config)

    Lanza FileNotFoundError si el archivo no existe.
    Lanza ValueError si el JSON está mal formado.
    """
    if not os.path.exists(ruta_json):
        raise FileNotFoundError("No se encontró el archivo: %s" % ruta_json)

    with open(ruta_json, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    try:
        # 1. Extraer la sección del warehouse
        data_wh = datos["warehouse"]
        ancho_x = data_wh["dimensiones"]["ancho_x"]
        largo_y = data_wh["dimensiones"]["largo_y"]

        # 2. Crear el Warehouse vacío
        wh = Warehouse(ancho_x, largo_y)

        # 3. Agregar Puertas
        for p in data_wh.get("puertas", []):
            puerta = Puerta(
                puerta_id=p["id"],
                tipo=p["tipo"],
                x=p["ubicacion"]["x"],
                y=p["ubicacion"]["y"]
            )
            wh.add_puerta(puerta)

        # 4. Agregar Zonas de Despacho
        for z in data_wh.get("zonas_despacho", []):
            zona = ZonaDespacho(
                zona_id=z["id"],
                puerta_id=z["puerta_id"],
                x=z["ubicacion"]["x"],
                y=z["ubicacion"]["y"],
                ancho=z["ancho"],
                alto=z["alto"],
                peso_max_kg=z["peso_max_kg"]
            )
            wh.add_zona_despacho(zona)

        # 5. Agregar Racks
        for r in data_wh.get("racks", []):
            rack = Rack(
                rack_id=r["id"],
                x=r["ubicacion"]["x"],
                y=r["ubicacion"]["y"],
                ancho=r["ancho"],
                alto=r["alto"]
            )
            wh.add_rack(rack)

        # 6. Agregar Pasillos declarados
        for p in data_wh.get("pasillos", []):
            pasillo = Pasillo(
                pas_id=p["id"],
                x=p["ubicacion"]["x"],
                y=p["ubicacion"]["y"],
                ancho=p["ancho"],
                alto=p["alto"],
                sentido=p["sentido"]
            )
            wh.add_pasillo(pasillo)

        # 7. Rellenar el resto de celdas vacías como pasillos AMBOS
        wh.rellenar_pasillos_implicitos()

        # 8. Extraer el resto de secciones (crudas, sin convertir aún)
        productos_raw = datos.get("productos", [])
        pedidos_raw = datos.get("pedidos", [])
        pickers_raw = datos.get("pickers", [])
        config = datos.get("configuracion", {})

        return wh, productos_raw, pedidos_raw, pickers_raw, config

    except KeyError as e:
        raise ValueError("Falta una clave obligatoria en el JSON: %s" % e)


# =================================================================
# DEMO (ejecutar con: python -m src.io.scenario_loader)
# =================================================================
if __name__ == "__main__":
    print("=== Prueba del Cargador de Escenarios ===\n")
    
    # Asegurate de ejecutar esto desde la raíz del proyecto
    ruta = "data/scenarios/escenario_basico.json"
    
    try:
        wh, productos, pedidos, pickers, config = cargar_escenario(ruta)
        
        print("¡Escenario cargado con éxito!")
        print(wh)
        print("\n--- Vista ASCII del Escenario Básico ---")
        wh.print_ascii()
        
        print("\nDatos crudos cargados:")
        print("- Productos:", len(productos))
        print("- Pedidos:  ", len(pedidos))
        print("- Pickers:  ", len(pickers))
        print("- Config:   ", config)
        
    except Exception as e:
        print("Error:", e)