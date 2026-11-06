# src/io/scenario_generator.py
import json
import random
import os

def generar_escenario(ancho_x = 18, largo_y = 16, cant_racks = 3, cant_productos = 10, cant_pedidos = 5, ruta_salida = "data/scenarios/generado.json"):
    """
    Genera un escenario aleatorio válido y lo guarda como JSON.
    """
    if ancho_x < 10 or largo_y < 12:
        raise ValueError("El almacén debe medir al menos 10 x 12 celdas.")
    print(f"Generando escenario de {ancho_x}x{largo_y}...")

    # 1. Estructura base del JSON
    escenario = {
        "warehouse": {
            "dimensiones": {"ancho_x": ancho_x, "largo_y": largo_y},
            "puertas": [],
            "zonas_despacho": [],
            "racks": [],
            "pasillos": []
        },
        "pickers": [
            {"id": "PK_01", "posicion_inicial": {"x": 1, "y": 1}, "capacidad_carga_kg": 150.0}
        ],
        "productos": [],
        "pedidos": [],
        "configuracion": {"wave_max_pedidos": 3, "wave_max_productos": 10, "wave_max_peso_kg": 1000.0}
    }

    # 2. Crear una puerta y su zona de despacho (en el borde inferior)
    ZONA_W, ZONA_H = 3, 2
    puerta_x = min(max(ancho_x // 2, 1), ancho_x - 2) # la zona (3 de ancho) cabe dentro
    escenario["warehouse"]["puertas"].append({
        "id": "P_OUT", "tipo": "OUTBOUND", "ubicacion": {"x": puerta_x, "y": 0}
    })
    escenario["warehouse"]["zonas_despacho"].append({
        "id": "ZONA_A", "puerta_id": "P_OUT",
        "ubicacion": {"x": puerta_x - 1, "y": 1}, "ancho": ZONA_W, "alto": ZONA_H, "peso_max_kg": 500.0
    })

    # 3. Generar Racks (evitando solapamientos de forma simple)
    # Los ponemos en columnas separadas
    racks_creados = 0
    intentos = 0
    celdas_ocupadas = set()

    # Ocupar celdas de despacho para que los racks no se pongan ahí
    for dx in range(ZONA_W):
        for dy in range(ZONA_H):
            celdas_ocupadas.add((puerta_x - 1 + dx, 1 + dy))

    while racks_creados < cant_racks and intentos < 500:
        intentos += 1
        # Racks verticales de ancho 2, siempre completos dentro del almacén y con
        # una celda libre alrededor (borde incluido) para que haya pasillo.
        r_ancho, r_alto = 2, random.randint(3, 5)
        rx = random.randint(2, ancho_x - r_ancho - 2)
        ry = random.randint(4, largo_y - r_alto - 2)

        # Chequear solapamiento (con margen de 1 celda para pasillos)
        solapa = False
        for dx in range(-1, r_ancho + 1):
            for dy in range(-1, r_alto + 1):
                if (rx + dx, ry + dy) in celdas_ocupadas:
                    solapa = True
                    break
            if solapa: break

        if not solapa:
            racks_creados += 1
            rack_id = f"R{racks_creados}"
            escenario["warehouse"]["racks"].append({
                "id": rack_id, "ubicacion": {"x": rx, "y": ry},
                "ancho": r_ancho, "alto": r_alto
            })
            # Marcar celdas ocupadas
            for dx in range(r_ancho):
                for dy in range(r_alto):
                    celdas_ocupadas.add((rx + dx, ry + dy))

    # Generar 3 productos por rack
    for p in range(3):
        if len(escenario["productos"]) >= cant_productos: break
        pid = f"P{len(escenario['productos'])+1:03d}"
        escenario["productos"].append({
            "id": pid, "nombre": f"Producto {pid}", "rack_id": rack_id,
            "ubicacion": {"x": rx, "y": ry + (p % r_alto), "z": 1},
            "cantidad_disponible": 20, "peso_kg": round(random.uniform(0.5, 10.0), 2)
        })

    if racks_creados < cant_racks:
        print(f"Aviso: solo entraron {racks_creados} de {cant_racks} racks; "
              "use un almacén más grande.")
    if not escenario["productos"]:
        raise ValueError("No se pudo ubicar ningún rack: agrande el almacén.")

    # 4. Generar Pedidos
    for i in range(cant_pedidos):
        pedido_items = []
        # Elegir 2 productos al azar
        prods_elegidos = random.sample(escenario["productos"], min(2, len(escenario["productos"])))
        for prod in prods_elegidos:
            pedido_items.append({"producto_id": prod["id"], "cantidad": random.randint(1, 3)})

        escenario["pedidos"].append({
            "id": f"PED_{i+1:02d}", "prioridad": random.randint(1, 5),
            "estado": "PENDIENTE", "items": pedido_items
        })

    # 5. Guardar el archivo
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(escenario, f, indent=2, ensure_ascii=False)

    print(f"Escenario guardado en: {ruta_salida}")
    print(f"({racks_creados} racks, {len(escenario['productos'])} productos, {cant_pedidos} pedidos)")

if __name__ == "__main__":
    generar_escenario(ancho_x = 20, largo_y = 20, cant_racks = 5, cant_productos = 15, cant_pedidos = 8)