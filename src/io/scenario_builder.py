# src/io/scenario_builder.py
# Convierte la configuración manual (la que se carga en la vista) en un escenario JSON
# con la misma estructura que los escenarios de ejemplo, y hace el camino inverso al
# importar. No usa tkinter: se puede probar y reutilizar sin interfaz.
#
# El usuario NO elige ids ni ubicaciones: todo se genera aquí.
#   - El tamaño del almacén sale de la cantidad de racks (y de las puertas).
#   - Los racks se ubican en bandas con pasillos de sentido alternado.
#   - Las puertas van sobre el borde y cada zona de despacho queda frente a su puerta.
#   - Los productos se acomodan en huecos libres del rack elegido (o repartidos).
#   - Los pickers arrancan separados, sobre los pasillos horizontales.
# src/io/scenario_builder.py
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

LARGO_RACK_MIN = 2
LARGO_RACK_MAX = 10
MAX_PUERTAS = 4
ANCHO_RACK = 2
NIVELES_RACK = 3
AUTOMATICO = "Automático"

SEPARACION_RACKS = 5
ZONA_ANCHO = 7
ZONA_ALTO_SALIDA = 2
ZONA_ALTO_ENTRADA = 3
ALTO_PASILLO_INFERIOR = 3
ALTO_PASILLO_MEDIO = 4

ETIQUETAS_PUERTA = {
    "OUTBOUND": "Salida (OUTBOUND)",
    "INBOUND": "Entrada (INBOUND)",
    "AMBOS": "Ambas (AMBOS)",
}
_PREFIJO_PUERTA = {"OUTBOUND": "OUT", "INBOUND": "IN", "AMBOS": "MIX"}


class ErrorConfiguracion(ValueError):
    # Se acumulan varios problemas para que la interfaz pueda pedir al usuario
    # corregirlos todos juntos, en vez de detenerse ante el primer campo.
    def __init__(self, mensajes):
        self.mensajes = list(mensajes)
        super().__init__("; ".join(self.mensajes))

    def mensaje_completo(self):
        return "\n".join(f"• {m}" for m in self.mensajes)


def _letras(indice):
    # Convierte indices en etiquetas tipo Excel: A..Z, AA..AZ, etc. Se usa
    # para generar IDs legibles de bandas y zonas sin colisiones por limite 26.
    indice += 1
    texto = ""
    while indice:
        indice, resto = divmod(indice - 1, 26)
        texto = chr(65 + resto) + texto
    return texto


def tipo_puerta(valor):
    texto = str(valor).upper()
    for tipo in ("OUTBOUND", "INBOUND", "AMBOS"):
        if tipo in texto:
            return tipo
    raise ValueError(f"Tipo de puerta desconocido: {valor!r}")


def ids_puertas(tipos):
    # Los contadores son independientes por tipo: puede haber OUT_1 e IN_1.
    contadores = {}
    ids = []
    for valor in tipos:
        tipo = tipo_puerta(valor)
        contadores[tipo] = contadores.get(tipo, 0) + 1
        ids.append(f"PUERTA_{_PREFIJO_PUERTA[tipo]}_{contadores[tipo]}")
    return ids


def id_zona(indice):
    return f"ZONA_{_letras(indice)}"


def id_picker(indice):
    return f"PK_{indice + 1:02d}"


def id_producto(indice):
    return f"P{indice + 1:03d}"


def id_pedido(indice):
    return f"PED_{indice + 1:02d}"


def calcular_layout(n_racks, largo, n_puertas_inferiores=0, n_puertas_superiores=0):
    """Calcula el layout del almacén sin solapamientos.

    Todo lo que devuelve cumple: x en [0, ancho), y en [0, alto); racks, pasillos y zonas
    no comparten celdas. Las zonas de despacho quedan adyacentes a un pasillo horizontal.
    """
    n_racks = max(1, int(n_racks))
    largo = min(max(int(largo), LARGO_RACK_MIN), LARGO_RACK_MAX)
    tiene_superior = n_puertas_superiores > 0

    # Se prueban distintas cantidades de bandas. El puntaje favorece un almacen
    # ancho (aprox. 1.5 veces su alto), para evitar layouts excesivamente largos.
    mejor = None
    for bandas in range(1, min(n_racks, 26) + 1):
        columnas = math.ceil(n_racks / bandas)
        ancho = SEPARACION_RACKS * columnas + SEPARACION_RACKS
        alto = 7 + bandas * largo + (bandas - 1) * ALTO_PASILLO_MEDIO + 10
        puntaje = abs(math.log(ancho / (1.5 * alto)))
        if mejor is None or puntaje < mejor[0] - 1e-9:
            mejor = (puntaje, bandas, columnas)
    _, bandas, columnas = mejor
    # Reparto equilibrado: las primeras bandas reciben como mucho un rack extra.
    por_banda = [n_racks // bandas + (1 if b < n_racks % bandas else 0) for b in range(bandas)]

    ancho_base = SEPARACION_RACKS * columnas + SEPARACION_RACKS
    ancho = max(ancho_base, 8 * n_puertas_inferiores, 8 * n_puertas_superiores)

    # Verticalmente, de abajo hacia arriba (sin solapes; cada franja toca a la siguiente):
    #   y=0                       puertas (borde)
    #   y=1 .. ZONA_ALTO_SALIDA   zonas de despacho inferiores
    #   y_pas_inf ..              pasillo inferior (adyacente a la zona, no la pisa)
    #   y_banda0 ..               primera banda de racks
    y_pas_inf = ZONA_ALTO_SALIDA + 1
    y_banda0 = y_pas_inf + ALTO_PASILLO_INFERIOR

    alto_corredor_sup = 5 if tiene_superior else 3
    y_sup = y_banda0 + bandas * largo + (bandas - 1) * ALTO_PASILLO_MEDIO
    alto = y_sup + alto_corredor_sup + (ZONA_ALTO_ENTRADA + 1 if tiene_superior else 0)

    # Alternar N/S entre pasillos contiguos reduce cruces enfrentados; los
    # corredores horizontales AMBOS conectan los extremos de esas bandas.
    racks, pasillos = [], []
    for b in range(bandas):
        y0 = y_banda0 + b * (largo + ALTO_PASILLO_MEDIO)
        for k in range(por_banda[b]):
            racks.append({
                "id": f"R{_letras(b)}{k + 1:02d}",
                "x": 4 + SEPARACION_RACKS * k, "y": y0,
                "ancho": ANCHO_RACK, "alto": largo,
            })
        for k in range(por_banda[b] + 1):
            if k == 0:
                x, w = 0, 4
            elif k == columnas:
                x, w = 1 + SEPARACION_RACKS * k, ancho - (1 + SEPARACION_RACKS * k)
            else:
                x, w = 1 + SEPARACION_RACKS * k, 3
            pasillos.append({
                "id": f"PAS_V{_letras(b)}{k:02d}", "x": x, "y": y0, "ancho": w, "alto": largo,
                "sentido": "N" if (k + b) % 2 == 0 else "S",
            })

    alto_pasillo_inf = ALTO_PASILLO_INFERIOR
    corredores = [{"id": "PAS_H_INF", "x": 0, "y": y_pas_inf,
                   "ancho": ancho, "alto": alto_pasillo_inf, "sentido": "AMBOS"}]
    for b in range(1, bandas):
        y = y_banda0 + b * (largo + ALTO_PASILLO_MEDIO) - ALTO_PASILLO_MEDIO
        nombre = "PAS_H_MED" if bandas == 2 else f"PAS_H_MED_{b}"
        corredores.append({"id": nombre, "x": 0, "y": y, "ancho": ancho,
                           "alto": ALTO_PASILLO_MEDIO, "sentido": "AMBOS"})
    corredores.append({"id": "PAS_H_SUP", "x": 0, "y": y_sup, "ancho": ancho,
                       "alto": alto_corredor_sup, "sentido": "AMBOS"})

    return {
        "ancho": ancho, "alto": alto, "bandas": bandas, "columnas": columnas,
        "largo": largo, "racks": racks, "pasillos": pasillos + corredores,
        "corredores": corredores,
    }


def ids_racks(n_racks, largo):
    return [r["id"] for r in calcular_layout(n_racks, largo)["racks"]]


def dimensiones_estimadas(config):
    racks = config.get("racks", {})
    inferiores, superiores = _contar_puertas(config.get("puertas", []))
    layout = calcular_layout(racks.get("cantidad", 1), racks.get("largo", LARGO_RACK_MAX),
                             inferiores, superiores)
    return layout["ancho"], layout["alto"]


def _contar_puertas(puertas):
    inferiores = superiores = 0
    for puerta in puertas:
        try:
            if tipo_puerta(puerta.get("tipo")) == "INBOUND":
                superiores += 1
            else:
                inferiores += 1
        except ValueError:
            pass
    return inferiores, superiores


def _posiciones_en_borde(cantidad, ancho):
    return [int(ancho * (2 * i + 1) / (2 * cantidad)) for i in range(cantidad)]


_TOKEN = re.compile(r"^(?P<nombre>.+?)(?:\s*[xX×*]\s*(?P<cantidad>\d+))?$")


def resolver_items(texto, productos):
    # Se indexa por ID y por nombre una sola vez. Asi cada token se resuelve
    # rapido, y los nombres repetidos se detectan en lugar de elegir al azar.
    por_id = {str(p["id"]).casefold(): p["id"] for p in productos}
    por_nombre = {}
    for p in productos:
        por_nombre.setdefault(str(p["nombre"]).strip().casefold(), []).append(p["id"])

    # Un diccionario agrupa referencias repetidas al mismo producto, por ejemplo
    # "P001 x2, P001 x3" se normaliza a una unica entrada de 5 unidades.
    items = {}
    for token in str(texto).split(","):
        token = token.strip()
        if not token:
            continue
        coincidencia = _TOKEN.match(token)
        nombre = coincidencia.group("nombre").strip()
        cantidad = int(coincidencia.group("cantidad") or 1)
        if cantidad <= 0:
            raise ValueError(f"La cantidad de «{nombre}» debe ser mayor que 0.")
        clave = nombre.casefold()
        if clave in por_id:
            producto_id = por_id[clave]
        elif clave in por_nombre:
            if len(por_nombre[clave]) > 1:
                raise ValueError(
                    f"El nombre «{nombre}» corresponde a varios productos; use el ID "
                    f"({', '.join(por_nombre[clave][:4])})...")
            producto_id = por_nombre[clave][0]
        else:
            pista = ""
            if re.search(r"[xX×*]\s*\d+\s+\S", nombre) or re.search(r"\b[Pp]\d+\s+[Pp]\d+", nombre):
                pista = " ¿Falta una coma entre productos?"
            raise ValueError(f"No existe el producto «{nombre}».{pista} "
                             "Formato: ID x cantidad, separados por comas (ej. P001 x2, P005 x1).")
        items[producto_id] = items.get(producto_id, 0) + cantidad
    if not items:
        raise ValueError("El pedido debe tener al menos un producto (ej. P001 x2).")
    return list(items.items())


def reasignar_ids_en_texto(texto, mapa):
    partes, quitados = [], 0
    for token in str(texto).split(","):
        token = token.strip()
        if not token:
            continue
        coincidencia = _TOKEN.match(token)
        nombre = coincidencia.group("nombre").strip()
        if nombre in mapa:
            nuevo = mapa[nombre]
            if nuevo is None:
                quitados += 1
                continue
            token = f"{nuevo} x{coincidencia.group('cantidad') or 1}"
        partes.append(token)
    return ", ".join(partes), quitados


def formatear_items(items):
    return ", ".join(f"{producto_id} x{cantidad}" for producto_id, cantidad in items)


def _orden_celdas(largo):
    # El paso es coprimo con el total de huecos; el recorrido modular visita
    # todas las celdas del rack antes de repetir una. Esto distribuye productos
    # consecutivos en vez de llenar primero una sola zona del rack.
    celdas = 2 * largo
    paso = max(1, celdas // 3)
    while math.gcd(paso, celdas) != 1:
        paso += 1
    return [(i * paso) % celdas for i in range(celdas)]


def _ubicacion_en_rack(rack, indice_hueco, largo):
    orden = _orden_celdas(largo)
    celdas = 2 * largo
    celda = orden[indice_hueco % celdas]
    nivel = indice_hueco // celdas + 1
    return {"x": rack["x"] + celda % 2, "y": rack["y"] + celda // 2, "z": nivel}


def _entero(valor):
    try:
        if isinstance(valor, bool):
            return None
        numero = float(valor)
        return int(numero) if numero == int(numero) else None
    except (TypeError, ValueError):
        return None


def _numero(valor):
    try:
        if isinstance(valor, bool):
            return None
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _capacidad_corredores(corredores):
    return sum(c["ancho"] * c["alto"] for c in corredores)


def capacidad_pickers(config):
    """Cantidad máxima de pickers que entra (uno por celda) en los pasillos horizontales."""
    racks = config.get("racks", {})
    inferiores, superiores = _contar_puertas(config.get("puertas", []))
    layout = calcular_layout(racks.get("cantidad", 1), racks.get("largo", LARGO_RACK_MAX),
                             inferiores, superiores)
    return _capacidad_corredores(layout["corredores"])


def _posiciones_pickers(n, corredores, ancho):
    """Una posición distinta por picker, siempre sobre un pasillo horizontal."""
    restante = [c["ancho"] * c["alto"] for c in corredores]
    cuenta = [0] * len(corredores)
    for _ in range(n):  # reparto rotativo entre corredores con lugar libre
        for k in range(len(corredores)):
            idx = (sum(cuenta) + k) % len(corredores)
            if cuenta[idx] < restante[idx]:
                cuenta[idx] += 1
                break
    posiciones, indice = [], 0
    for corredor, m in zip(corredores, cuenta):
        total = corredor["ancho"] * corredor["alto"]
        for orden in range(m):
            if m <= corredor["ancho"]:  # una sola fila (la segunda del corredor)
                x = int(corredor["ancho"] * (2 * orden + 1) / (2 * m))
                y = corredor["y"] + min(1, corredor["alto"] - 1)
            else:  # hay muchos: se reparten por todas las celdas del corredor
                hueco = int(total * (2 * orden + 1) / (2 * m))
                x, y = hueco % corredor["ancho"], corredor["y"] + hueco // corredor["ancho"]
            posiciones.append((indice, {"x": corredor["x"] + x, "y": y}))
            indice += 1
    return {i: p for i, (_o, p) in enumerate(posiciones)}


def validar_geometria(escenario):
    """Revisa un escenario ya armado. Devuelve una lista de problemas (vacía = todo bien)."""
    almacen = escenario["warehouse"]
    ancho = almacen["dimensiones"]["ancho_x"]
    alto = almacen["dimensiones"]["largo_y"]
    problemas = []

    def celdas(o):
        u = o["ubicacion"]
        return {(u["x"] + i, u["y"] + j) for i in range(o["ancho"]) for j in range(o["alto"])}

    # El mapa coordenada -> objetos que la ocupan permite detectar solapamientos
    # con consultas promedio O(1), y tambien informa que elementos chocaron.
    ocupadas = {}

    def registrar(nombre, conjunto, clase):
        for c in conjunto:
            if not (0 <= c[0] < ancho and 0 <= c[1] < alto):
                problemas.append(f"{nombre} queda fuera del almacén ({ancho}x{alto}) en {c}.")
                break
        for c in conjunto:
            ocupadas.setdefault(c, []).append((clase, nombre))

    for r in almacen["racks"]:
        registrar(r["id"], celdas(r), "rack")
    for z in almacen["zonas_despacho"]:
        registrar(z["id"], celdas(z), "zona")
    for p in almacen["pasillos"]:
        registrar(p["id"], celdas(p), "pasillo")
    for p in almacen["puertas"]:
        registrar(p["id"], {(p["ubicacion"]["x"], p["ubicacion"]["y"])}, "puerta")
    vistos = set()
    for c, lista in sorted(ocupadas.items()):
        if len(lista) > 1:
            par = tuple(sorted(n for _cl, n in lista))
            if par not in vistos:
                vistos.add(par)
                problemas.append(f"{' y '.join(par)} se superponen (por ejemplo en {c}).")
    pasillos = {c for c, l in ocupadas.items() if l[0][0] == "pasillo"}

    usadas = set()
    for p in escenario["pickers"]:
        c = (p["posicion_inicial"]["x"], p["posicion_inicial"]["y"])
        if c not in pasillos:
            problemas.append(f"El picker {p['id']} empieza en {c}, fuera de un pasillo.")
        if c in usadas:
            problemas.append(f"El picker {p['id']} empieza en {c}, ocupado por otro picker.")
        usadas.add(c)

    celdas_rack = {r["id"]: celdas(r) for r in almacen["racks"]}
    ubicaciones = set()
    for p in escenario["productos"]:
        u = p["ubicacion"]
        if (u["x"], u["y"]) not in celdas_rack.get(p["rack_id"], set()):
            problemas.append(f"El producto {p['id']} no está dentro de su rack {p['rack_id']}.")
        clave = (u["x"], u["y"], u["z"])
        if clave in ubicaciones:
            problemas.append(f"El producto {p['id']} repite la ubicación {clave}.")
        ubicaciones.add(clave)

    puertas = {p["id"]: p for p in almacen["puertas"]}
    for z in almacen["zonas_despacho"]:
        zc = celdas(z)
        puerta = puertas.get(z["puerta_id"])
        if puerta is None:
            problemas.append(f"La zona {z['id']} usa una puerta inexistente.")
            continue
        px_, py_ = puerta["ubicacion"]["x"], puerta["ubicacion"]["y"]
        if not any((px_, py_ + d) in zc for d in (-1, 1)):
            problemas.append(f"La zona {z['id']} no queda pegada a su puerta {puerta['id']}.")
        if not any((x + a, y + b) in pasillos for x, y in zc
                   for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            problemas.append(f"La zona {z['id']} no toca ningún pasillo: nadie podría llegar.")
    return problemas


def construir_escenario(config):
    # La funcion sigue tres etapas: validar entradas, convertirlas a objetos
    # serializables y validar el layout final. Se acumulan errores para dar un
    # reporte completo sin escribir un escenario parcialmente valido.
    errores = []

    datos_racks = config.get("racks", {})
    n_racks = _entero(datos_racks.get("cantidad"))
    largo = _entero(datos_racks.get("largo"))
    if n_racks is None or n_racks < 1:
        errores.append("La cantidad de racks debe ser un entero de 1 o más.")
        n_racks = 1
    if largo is None or not LARGO_RACK_MIN <= largo <= LARGO_RACK_MAX:
        errores.append(f"El largo de los racks debe estar entre {LARGO_RACK_MIN} y {LARGO_RACK_MAX}.")
        largo = LARGO_RACK_MAX

    puertas_cfg = config.get("puertas", [])
    tipos = []
    for puerta in puertas_cfg:
        try:
            tipos.append(tipo_puerta(puerta.get("tipo")))
        except ValueError as error:
            errores.append(str(error))
    if not puertas_cfg:
        errores.append("Agregue al menos una puerta.")
    if len(puertas_cfg) > MAX_PUERTAS:
        errores.append(f"Se admiten como máximo {MAX_PUERTAS} puertas.")
    ids_p = ids_puertas(tipos) if len(tipos) == len(puertas_cfg) else []

    zonas_cfg = config.get("zonas_despacho", [])
    zona_de_puerta = {}
    for indice, zona in enumerate(zonas_cfg):
        puerta_id = zona.get("puerta")
        peso = _numero(zona.get("peso_max"))
        if puerta_id not in ids_p:
            errores.append(f"La zona {id_zona(indice)} usa una puerta que no existe ({puerta_id}).")
            continue
        if peso is None or peso <= 0:
            errores.append(f"El peso máximo de la zona {id_zona(indice)} debe ser mayor que 0.")
            continue
        if puerta_id in zona_de_puerta:
            errores.append(f"La puerta {puerta_id} tiene más de una zona de despacho.")
            continue
        zona_de_puerta[puerta_id] = (id_zona(indice), peso)
    if ids_p and not any(
        tipos[ids_p.index(pid)] in ("OUTBOUND", "AMBOS") for pid in zona_de_puerta
    ):
        errores.append("Hace falta una zona de despacho en una puerta de salida o mixta "
                       "para que los pickers puedan entregar los pedidos.")

    pickers_cfg = config.get("pickers", [])
    if not pickers_cfg:
        errores.append("Agregue al menos un picker.")
    capacidades = []
    for indice, picker in enumerate(pickers_cfg):
        capacidad = _numero(picker.get("capacidad"))
        if capacidad is None or capacidad <= 0:
            errores.append(f"La capacidad del picker {id_picker(indice)} debe ser mayor que 0.")
        else:
            capacidades.append(capacidad)

    inferiores = sum(1 for t in tipos if t != "INBOUND")
    superiores = sum(1 for t in tipos if t == "INBOUND")
    layout = calcular_layout(n_racks, largo, inferiores, superiores)
    racks_por_id = {r["id"]: r for r in layout["racks"]}
    lugares_pickers = _capacidad_corredores(layout["corredores"])
    if len(pickers_cfg) > lugares_pickers:
        errores.append(f"Con este almacén solo caben {lugares_pickers} pickers en los pasillos "
                       f"y hay {len(pickers_cfg)}. Agregue racks o reduzca los pickers.")

    # Cada rack tiene dos columnas, `largo` posiciones y niveles verticales.
    # El contador por rack asigna huecos distintos y permite detectar cuando
    # la capacidad fisica ya se completo.
    productos_cfg = config.get("productos", [])
    if not productos_cfg:
        errores.append("Agregue al menos un producto.")
    usados = {rack_id: 0 for rack_id in racks_por_id}
    capacidad_rack = 2 * largo * NIVELES_RACK
    productos = []
    for indice, producto in enumerate(productos_cfg):
        pid = id_producto(indice)
        nombre = str(producto.get("nombre", "")).strip()
        cantidad = _entero(producto.get("cantidad"))
        peso = _numero(producto.get("peso"))
        if not nombre:
            errores.append(f"El producto {pid} no tiene nombre.")
        if cantidad is None or cantidad < 1:
            errores.append(f"La cantidad disponible de {pid} debe ser un entero de 1 o más.")
        if peso is None or peso <= 0:
            errores.append(f"El peso de {pid} debe ser mayor que 0.")
            continue
        if capacidades and peso > max(capacidades):
            errores.append(f"{pid} pesa {peso:g} kg y ningún picker puede cargarlo "
                           f"(capacidad máxima {max(capacidades):g} kg).")
        rack_pedido = producto.get("rack") or AUTOMATICO
        if rack_pedido == AUTOMATICO:
            rack_id = min(usados, key=lambda r: (usados[r], r))
        elif rack_pedido in racks_por_id:
            rack_id = rack_pedido
        else:
            errores.append(f"{pid} usa el rack {rack_pedido}, que no existe con "
                           f"{n_racks} racks. Elija otro o «{AUTOMATICO}».")
            continue
        if usados[rack_id] >= capacidad_rack:
            if rack_pedido == AUTOMATICO:
                errores.append("No hay lugar para todos los productos en los racks: "
                               "aumente la cantidad o el largo de los racks.")
            else:
                errores.append(f"El rack {rack_id} está lleno ({capacidad_rack} lugares); "
                               f"{pid} no entra. Elija otro rack o «{AUTOMATICO}».")
            continue
        ubicacion = _ubicacion_en_rack(racks_por_id[rack_id], usados[rack_id], largo)
        usados[rack_id] += 1
        productos.append({
            "id": pid, "nombre": nombre, "rack_id": rack_id, "ubicacion": ubicacion,
            "cantidad_disponible": cantidad if cantidad is not None else 0,
            "peso_kg": peso,
        })

    datos_waves = config.get("waves", {})
    max_pedidos = _entero(datos_waves.get("max_pedidos"))
    max_productos = _entero(datos_waves.get("max_productos"))
    max_peso = _numero(datos_waves.get("max_peso"))
    if max_pedidos is None or max_pedidos < 1:
        errores.append("El máximo de pedidos por wave debe ser un entero de 1 o más.")
    if max_productos is None or max_productos < 1:
        errores.append("El máximo de productos por wave debe ser un entero de 1 o más.")
    if max_peso is None or max_peso <= 0:
        errores.append("El peso máximo por wave debe ser mayor que 0.")

    # Los pedidos se convierten a IDs de producto antes de calcular unidades y
    # peso: asi se valida el limite de wave usando los mismos datos del motor.
    pedidos_cfg = config.get("pedidos", [])
    if not pedidos_cfg:
        errores.append("Agregue al menos un pedido.")
    base_productos = [{"id": p["id"], "nombre": p["nombre"]} for p in productos]
    peso_de = {p["id"]: p["peso_kg"] for p in productos}
    pedidos = []
    for indice, pedido in enumerate(pedidos_cfg):
        pid = id_pedido(indice)
        prioridad = _entero(pedido.get("prioridad"))
        if prioridad is None or prioridad < 1:
            errores.append(f"La prioridad del pedido {pid} debe ser un entero de 1 o más.")
            continue
        try:
            items = resolver_items(pedido.get("productos", ""), base_productos)
        except ValueError as error:
            errores.append(f"Pedido {pid}: {error}")
            continue
        unidades = sum(c for _, c in items)
        if max_productos and unidades > max_productos:
            errores.append(f"El pedido {pid} tiene {unidades} unidades y una wave admite "
                           f"como máximo {max_productos}.")
        peso_pedido = sum(peso_de[i] * c for i, c in items)
        if max_peso and peso_pedido > max_peso:
            errores.append(f"El pedido {pid} pesa {peso_pedido:g} kg y una wave admite como máximo "
                           f"{max_peso:g} kg.")
        pedidos.append({
            "id": pid, "prioridad": prioridad, "estado": "PENDIENTE",
            "items": [{"producto_id": i, "cantidad": c} for i, c in items],
        })

    if errores:
        raise ErrorConfiguracion(errores)

    # Las puertas INBOUND se colocan arriba; las OUTBOUND/AMBOS, abajo. Las
    # zonas se centran frente a su puerta y se ordenan para IDs reproducibles.
    bordes = {"inf": [], "sup": []}
    for indice, tipo in enumerate(tipos):
        bordes["sup" if tipo == "INBOUND" else "inf"].append(indice)
    ancho, alto = layout["ancho"], layout["alto"]
    puertas, zonas = [], []
    for lado, indices in bordes.items():
        for indice, x in zip(indices, _posiciones_en_borde(len(indices), ancho)):
            y = 0 if lado == "inf" else alto - 1
            puertas.append((indice, {"id": ids_p[indice], "tipo": tipos[indice],
                                      "ubicacion": {"x": x, "y": y}}))
            if ids_p[indice] in zona_de_puerta:
                zona_id, peso = zona_de_puerta[ids_p[indice]]
                alto_zona = ZONA_ALTO_SALIDA if lado == "inf" else ZONA_ALTO_ENTRADA
                zonas.append((zona_id, {
                    "id": zona_id, "puerta_id": ids_p[indice],
                    "ubicacion": {"x": x - ZONA_ANCHO // 2, "y": 1 if lado == "inf" else y - alto_zona},
                    "ancho": ZONA_ANCHO, "alto": alto_zona, "peso_max_kg": peso,
                }))
    puertas = [p for _, p in sorted(puertas, key=lambda t: t[0])]
    zonas = [z for _, z in sorted(zonas, key=lambda t: t[0])]

    posiciones = _posiciones_pickers(len(pickers_cfg), layout["corredores"], ancho)
    pickers = [{
        "id": id_picker(i), "posicion_inicial": posiciones[i],
        "capacidad_carga_kg": _numero(p.get("capacidad")),
    } for i, p in enumerate(pickers_cfg)]

    escenario = {
        "warehouse": {
            "dimensiones": {"ancho_x": ancho, "largo_y": alto},
            "puertas": puertas,
            "zonas_despacho": zonas,
            "racks": [{"id": r["id"], "ubicacion": {"x": r["x"], "y": r["y"]},
                       "ancho": r["ancho"], "alto": r["alto"]} for r in layout["racks"]],
            "pasillos": [{"id": p["id"], "ubicacion": {"x": p["x"], "y": p["y"]},
                          "ancho": p["ancho"], "alto": p["alto"], "sentido": p["sentido"]}
                         for p in layout["pasillos"]],
        },
        "pickers": pickers,
        "productos": productos,
        "pedidos": pedidos,
        "configuracion": {"wave_max_pedidos": max_pedidos, "wave_max_productos": max_productos,
                          "wave_max_peso_kg": float(max_peso)},
    }
    problemas = validar_geometria(escenario)
    if problemas:
        raise ErrorConfiguracion(["Error de geometría: " + p for p in problemas[:8]])
    return escenario


def guardar_escenario(config, carpeta):
    # El nombre con fecha evita pisar escenarios anteriores; el sufijo resuelve
    # una posible colision si ya existe un archivo del mismo segundo.
    escenario = construir_escenario(config)
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"escenario_manual_{datetime.now():%Y%m%d_%H%M%S}.json"
    contador = 1
    while ruta.exists():
        ruta = carpeta / f"escenario_manual_{datetime.now():%Y%m%d_%H%M%S}_{contador}.json"
        contador += 1
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(escenario, archivo, indent=2, ensure_ascii=False)
    return ruta, escenario


def escenario_a_config(datos):
    # La vista manual admite un layout regular propio. Al importar un escenario
    # arbitrario se conservan los datos de negocio, pero IDs y ubicaciones se
    # regeneran; los avisos hacen visibles las partes que no pudieron mapearse.
    if not isinstance(datos, dict) or not isinstance(datos.get("warehouse"), dict):
        raise ValueError("El archivo no tiene el formato de un escenario (falta «warehouse»).")
    avisos = []
    almacen = datos["warehouse"]

    racks = almacen.get("racks", [])
    n_racks = max(1, len(racks))
    largos = {max(int(r.get("ancho", 2)), int(r.get("alto", 2))) for r in racks} or {LARGO_RACK_MAX}
    largo = min(max(max(largos), LARGO_RACK_MIN), LARGO_RACK_MAX)
    if len(largos) > 1:
        avisos.append("Los racks del archivo tienen distintos tamaños; todos pasan a ser iguales.")
    if max(largos) > LARGO_RACK_MAX:
        avisos.append(f"El largo de los racks se limitó al máximo permitido ({LARGO_RACK_MAX}).")
    nuevos_racks = ids_racks(n_racks, largo)
    mapa_racks = {r.get("id"): nuevos_racks[i] for i, r in enumerate(racks)}

    puertas_json = almacen.get("puertas", [])
    tipos = []
    for puerta in puertas_json:
        try:
            tipos.append(tipo_puerta(puerta.get("tipo")))
        except ValueError:
            tipos.append("OUTBOUND")
    nuevos_ids_puertas = ids_puertas(tipos)
    mapa_puertas = {p.get("id"): nuevos_ids_puertas[i] for i, p in enumerate(puertas_json)}

    zonas = []
    for zona in almacen.get("zonas_despacho", []):
        puerta = mapa_puertas.get(zona.get("puerta_id"))
        if puerta is None:
            avisos.append(f"La zona {zona.get('id')} se omitió: su puerta no existe.")
            continue
        zonas.append({"puerta": puerta, "peso_max": zona.get("peso_max_kg", 500.0)})

    productos_json = datos.get("productos", [])
    mapa_productos = {p.get("id"): id_producto(i) for i, p in enumerate(productos_json)}
    productos = []
    for p in productos_json:
        productos.append({
            "nombre": p.get("nombre", ""),
            "rack": mapa_racks.get(p.get("rack_id"), AUTOMATICO),
            "cantidad": p.get("cantidad_disponible", 1),
            "peso": p.get("peso_kg", 1.0),
        })

    pedidos = []
    for pedido in datos.get("pedidos", []):
        items = []
        for item in pedido.get("items", []):
            nuevo = mapa_productos.get(item.get("producto_id"))
            if nuevo is None:
                avisos.append(f"Un ítem del pedido {pedido.get('id')} se omitió: "
                              f"el producto {item.get('producto_id')} no existe.")
                continue
            items.append((nuevo, int(item.get("cantidad", 1))))
        if not items:
            continue
        pedidos.append({"prioridad": pedido.get("prioridad", 1), "productos": formatear_items(items)})

    ajustes = datos.get("configuracion", {})
    peso_wave = ajustes.get("wave_max_peso_kg")
    if peso_wave is None:
        pesos = {p.get("id"): float(p.get("peso_kg", 0)) for p in productos_json}
        mayor = max((sum(pesos.get(i.get("producto_id"), 0) * int(i.get("cantidad", 1))
                         for i in ped.get("items", [])) for ped in datos.get("pedidos", [])), default=0)
        peso_wave = max(1000, math.ceil(mayor))
    config = {
        "racks": {"cantidad": n_racks, "largo": largo},
        "puertas": [{"tipo": ETIQUETAS_PUERTA[t]} for t in tipos],
        "zonas_despacho": zonas,
        "pickers": [{"capacidad": p.get("capacidad_carga_kg", 100.0)} for p in datos.get("pickers", [])],
        "productos": productos,
        "pedidos": pedidos,
        "waves": {"max_pedidos": ajustes.get("wave_max_pedidos", 3),
                  "max_productos": ajustes.get("wave_max_productos", 15),
                  "max_peso": int(math.ceil(float(peso_wave)))},
    }
    avisos.append("Los ids y las ubicaciones se generan automáticamente al guardar.")
    return config, avisos