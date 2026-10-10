from enum import Enum

from warehouse.algoritmos.distancias import CacheDistancias
from warehouse.dominio.pedido import Pedido
from warehouse.dominio.wave import Wave
from warehouse.warehouse.warehouse import Warehouse


class EstrategiaWaves(Enum):
    PRIORIDAD = "prioridad"
    PRIORIDAD_Y_CERCANIA = "prioridad_y_cercania"


# --- helpers ---


def _productos_de_wave(wave: Wave) -> set[str]:
    ids: set[str] = set()
    for p in wave.pedidos:
        ids |= p.productos_ids()
    return ids


def _distancia_minima_pedido_wave(
    pedido: Pedido,
    wave: Wave,
    warehouse: Warehouse,
    cache: CacheDistancias,
) -> float:
    """Distancia mínima entre cualquier producto del pedido y cualquier producto
    ya presente en la wave. Si la wave está vacía, retorna inf."""
    productos_wave = _productos_de_wave(wave)
    if not productos_wave:
        return float("inf")

    mejor = float("inf")
    for pid_ped in pedido.productos_ids():
        nodo_ped = warehouse.productos[pid_ped].nodo_picking
        for pid_wave in productos_wave:
            nodo_wave = warehouse.productos[pid_wave].nodo_picking
            d = cache.distancia(nodo_ped, nodo_wave)
            if d < mejor:
                mejor = d
    return mejor


# --- estrategias ---


def _generar_waves_prioridad(
    pedidos: list[Pedido],
    warehouse: Warehouse,
    max_pedidos: int,
    max_productos: int,
) -> list[Wave]:
    pendientes = sorted(pedidos, key=lambda p: (-p.prioridad, p.id))
    waves: list[Wave] = []
    contador = 1

    while pendientes:
        wave = Wave(
            id=f"W{contador:03d}",
            max_pedidos=max_pedidos,
            max_productos=max_productos,
        )
        primero = pendientes.pop(0)
        try:
            wave.agregar_pedido(primero)
        except ValueError as e:
            raise ValueError(
                f"El pedido {primero.id} no cabe ni en una wave vacía. "
                f"Revisar max_productos={max_productos}. Detalle: {e}"
            ) from e

        i = 0
        while i < len(pendientes):
            if wave.puede_agregar(pendientes[i]):
                wave.agregar_pedido(pendientes.pop(i))
            else:
                i += 1

        wave.cerrar()
        waves.append(wave)
        contador += 1

    return waves


def _generar_waves_prioridad_cercania(
    pedidos: list[Pedido],
    warehouse: Warehouse,
    max_pedidos: int,
    max_productos: int,
) -> list[Wave]:
    pendientes = sorted(pedidos, key=lambda p: (-p.prioridad, p.id))
    cache = CacheDistancias(warehouse.grafo)
    waves: list[Wave] = []
    contador = 1

    while pendientes:
        wave = Wave(
            id=f"W{contador:03d}",
            max_pedidos=max_pedidos,
            max_productos=max_productos,
        )
        semilla = pendientes.pop(0)
        try:
            wave.agregar_pedido(semilla)
        except ValueError as e:
            raise ValueError(
                f"El pedido {semilla.id} no cabe ni en una wave vacía. "
                f"Revisar max_productos={max_productos}. Detalle: {e}"
            ) from e

        while True:
            mejor_idx: int | None = None
            mejor_dist = float("inf")
            mejor_prioridad = -1

            for i, candidato in enumerate(pendientes):
                if not wave.puede_agregar(candidato):
                    continue
                d = _distancia_minima_pedido_wave(candidato, wave, warehouse, cache)
                # criterio: menor distancia; desempate por prioridad desc
                if d < mejor_dist or (
                    d == mejor_dist and candidato.prioridad > mejor_prioridad
                ):
                    mejor_idx = i
                    mejor_dist = d
                    mejor_prioridad = candidato.prioridad

            if mejor_idx is None:
                break
            wave.agregar_pedido(pendientes.pop(mejor_idx))

        wave.cerrar()
        waves.append(wave)
        contador += 1

    return waves


# --- API pública ---


def generar_waves(
    pedidos: list[Pedido],
    warehouse: Warehouse,
    max_pedidos: int,
    max_productos: int,
    estrategia: EstrategiaWaves = EstrategiaWaves.PRIORIDAD_Y_CERCANIA,
) -> list[Wave]:
    """Agrupa los pedidos pendientes en waves.

    - Los pedidos modifican su estado a EN_WAVE al ser agregados.
    - Las waves se devuelven ya cerradas.
    - Si algún pedido no cabe ni en una wave vacía, lanza ValueError.
    """
    if estrategia == EstrategiaWaves.PRIORIDAD:
        return _generar_waves_prioridad(pedidos, warehouse, max_pedidos, max_productos)
    if estrategia == EstrategiaWaves.PRIORIDAD_Y_CERCANIA:
        return _generar_waves_prioridad_cercania(
            pedidos, warehouse, max_pedidos, max_productos
        )
    raise ValueError(f"Estrategia desconocida: {estrategia}")
