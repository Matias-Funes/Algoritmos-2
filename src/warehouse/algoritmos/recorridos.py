from dataclasses import dataclass
from time import perf_counter

from warehouse.algoritmos.distancias import CacheDistancias
from warehouse.dominio.wave import Wave
from warehouse.warehouse.warehouse import Warehouse


@dataclass
class ResultadoRecorrido:
    estrategia: str
    orden_paradas: list[int]  # nodos de picking, en orden, sin duplicados
    camino_completo: list[int]  # secuencia completa incluyendo subcaminos
    distancia_total: float
    nodos_visitados: int
    aristas_recorridas: int
    tiempo_segundos: float


# --- helpers ---


def _nodo_despacho(warehouse: Warehouse, zona_despacho_id: str | None) -> int:
    if zona_despacho_id is None:
        if not warehouse.zonas:
            raise ValueError("El warehouse no tiene zonas de despacho")
        zona = next(iter(warehouse.zonas.values()))
    else:
        if zona_despacho_id not in warehouse.zonas:
            raise ValueError(f"No existe la zona de despacho: {zona_despacho_id}")
        zona = warehouse.zonas[zona_despacho_id]
    return zona.nodo_representativo


def _paradas_de_wave(wave: Wave, warehouse: Warehouse) -> list[int]:
    """Devuelve la lista de nodos de picking únicos de la wave,
    en el orden en que aparecen los pedidos."""
    paradas: list[int] = []
    vistos: set[int] = set()
    for pedido in wave.pedidos:
        for item in pedido.items:
            producto_id = item.producto_id
            if producto_id not in warehouse.productos:
                raise ValueError(
                    f"El pedido {pedido.id} referencia producto inexistente: {producto_id}"
                )
            nodo = warehouse.productos[producto_id].nodo_picking
            if nodo not in vistos:
                vistos.add(nodo)
                paradas.append(nodo)
    return paradas


def _armar_camino(
    secuencia: list[int],
    cache: CacheDistancias,
) -> tuple[list[int], float]:
    """Dada una secuencia de nodos [n0, n1, ..., nk] (paradas a visitar en orden),
    arma el camino completo concatenando los subcaminos mínimos entre cada par.

    Devuelve (camino_completo, distancia_total).
    Lanza ValueError si algún par no tiene camino.
    """
    if len(secuencia) < 2:
        return list(secuencia), 0.0

    camino_total: list[int] = []
    distancia_total = 0.0

    for i in range(len(secuencia) - 1):
        origen = secuencia[i]
        destino = secuencia[i + 1]
        sub = cache.camino(origen, destino)
        if not sub:
            raise ValueError(f"No hay camino entre los nodos {origen} y {destino}")
        # El primer nodo del subcamino coincide con el último del anterior
        if camino_total:
            camino_total.extend(sub[1:])
        else:
            camino_total.extend(sub)
        distancia_total += cache.distancia(origen, destino)

    return camino_total, distancia_total


# --- estrategias ---


def _estrategia_orden_pedidos(
    wave: Wave,
    warehouse: Warehouse,
    nodo_despacho: int,
    cache: CacheDistancias,
) -> ResultadoRecorrido:
    t0 = perf_counter()

    paradas = _paradas_de_wave(wave, warehouse)
    secuencia = [nodo_despacho] + paradas + [nodo_despacho]

    camino, distancia = _armar_camino(secuencia, cache)

    t1 = perf_counter()
    return ResultadoRecorrido(
        estrategia="orden_pedidos",
        orden_paradas=paradas,
        camino_completo=camino,
        distancia_total=distancia,
        nodos_visitados=len(camino),
        aristas_recorridas=max(0, len(camino) - 1),
        tiempo_segundos=t1 - t0,
    )


def _estrategia_vecino_mas_cercano(
    wave: Wave,
    warehouse: Warehouse,
    nodo_despacho: int,
    cache: CacheDistancias,
) -> ResultadoRecorrido:
    t0 = perf_counter()

    paradas = _paradas_de_wave(wave, warehouse)

    if not paradas:
        t1 = perf_counter()
        return ResultadoRecorrido(
            estrategia="vecino_mas_cercano",
            orden_paradas=[],
            camino_completo=[nodo_despacho],
            distancia_total=0.0,
            nodos_visitados=1,
            aristas_recorridas=0,
            tiempo_segundos=t1 - t0,
        )

    pendientes = set(paradas)
    secuencia = [nodo_despacho]
    actual = nodo_despacho

    while pendientes:
        # elegir el más cercano a 'actual'
        mejor = None
        mejor_dist = float("inf")
        for candidato in pendientes:
            d = cache.distancia(actual, candidato)
            if d < mejor_dist:
                mejor_dist = d
                mejor = candidato
        if mejor is None or mejor_dist == float("inf"):
            raise ValueError(f"Hay paradas inalcanzables desde el nodo {actual}")
        secuencia.append(mejor)
        pendientes.remove(mejor)
        actual = mejor

    secuencia.append(nodo_despacho)

    camino, distancia = _armar_camino(secuencia, cache)

    t1 = perf_counter()
    return ResultadoRecorrido(
        estrategia="vecino_mas_cercano",
        orden_paradas=secuencia[1:-1],
        camino_completo=camino,
        distancia_total=distancia,
        nodos_visitados=len(camino),
        aristas_recorridas=max(0, len(camino) - 1),
        tiempo_segundos=t1 - t0,
    )


# --- API pública ---

ESTRATEGIAS = {
    "orden_pedidos": _estrategia_orden_pedidos,
    "vecino_mas_cercano": _estrategia_vecino_mas_cercano,
}


def recorrer_wave(
    wave: Wave,
    warehouse: Warehouse,
    zona_despacho_id: str | None = None,
    estrategia: str = "orden_pedidos",
) -> ResultadoRecorrido:
    """
    Calcula el recorrido para preparar una wave.

    - zona_despacho_id: id de la zona de despacho. Si es None, usa la primera.
    - estrategia: "orden_pedidos" | "vecino_mas_cercano".

    Devuelve un ResultadoRecorrido con la secuencia y las métricas.
    Lanza ValueError si la estrategia es inválida o hay paradas inalcanzables.
    """
    if estrategia not in ESTRATEGIAS:
        raise ValueError(
            f"Estrategia desconocida: {estrategia}. "
            f"Disponibles: {list(ESTRATEGIAS.keys())}"
        )

    nodo_despacho = _nodo_despacho(warehouse, zona_despacho_id)
    cache = CacheDistancias(warehouse.grafo)
    return ESTRATEGIAS[estrategia](wave, warehouse, nodo_despacho, cache)
