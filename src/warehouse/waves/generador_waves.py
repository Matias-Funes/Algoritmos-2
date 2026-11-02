from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from warehouse.algoritmos.distancias import CacheDistancias
from warehouse.dominio.item_pedido import ItemPedido
from warehouse.dominio.pedido import Pedido
from warehouse.dominio.wave import Wave
from warehouse.warehouse.warehouse import Warehouse


@dataclass
class ItemWave:
    """Un item (producto_id, cantidad) atribuido a un pedido,
    que fue planificado en una wave concreta.
    Es la unidad atómica del split: un (pedido, producto) puede
    aparecer en N waves con cantidades disjuntas."""

    pedido_id: str
    producto_id: str
    cantidad: int


if TYPE_CHECKING:
    from warehouse.dominio.producto import Producto


class EstrategiaWaves(Enum):
    PRIORIDAD = "prioridad"
    PRIORIDAD_Y_CERCANIA = "prioridad_y_cercania"


# --- helpers ---


def _puede_agregar_con_peso(
    wave: Wave, pedido: Pedido, productos: dict[str, "Producto"], max_peso_kg: float
) -> bool:
    """Valida capacidad estándar + peso."""
    if not wave.puede_agregar(pedido):
        return False

    peso_actual = wave.peso_total(productos)
    peso_nuevo = sum(
        productos[item.producto_id].peso_kg * item.cantidad for item in pedido.items
    )
    return (peso_actual + peso_nuevo) <= max_peso_kg


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
    max_peso_kg: float,
) -> list[Wave]:
    pendientes = sorted(pedidos, key=lambda p: (-p.prioridad, p.id))
    waves: list[Wave] = []
    contador = 1

    while pendientes:
        wave = Wave(
            id=f"W{contador:03d}",
            max_pedidos=max_pedidos,
            max_productos=max_productos,
            max_peso_kg=max_peso_kg,
        )

        primero = pendientes.pop(0)

        # Validamos si el pedido semilla entra en una wave vacía (incluyendo peso)
        peso_primero = sum(
            warehouse.productos[it.producto_id].peso_kg * it.cantidad
            for it in primero.items
        )
        if (
            primero.cantidad_total_productos() > max_productos
            or peso_primero > max_peso_kg
        ):
            raise ValueError(f"El pedido {primero.id} no cabe ni en una wave vacía.")

        wave.agregar_pedido(primero)

        i = 0
        while i < len(pendientes):
            if _puede_agregar_con_peso(
                wave, pendientes[i], warehouse.productos, max_peso_kg
            ):
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
    max_peso_kg: float,
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
            max_peso_kg=max_peso_kg,
        )

        semilla = pendientes.pop(0)

        # Validamos si la semilla entra (incluyendo peso)
        peso_semilla = sum(
            warehouse.productos[it.producto_id].peso_kg * it.cantidad
            for it in semilla.items
        )
        if (
            semilla.cantidad_total_productos() > max_productos
            or peso_semilla > max_peso_kg
        ):
            raise ValueError(f"El pedido {semilla.id} no cabe ni en una wave vacía.")

        wave.agregar_pedido(semilla)

        while True:
            mejor_idx: int | None = None
            mejor_dist = float("inf")
            mejor_prioridad = -1

            for i, candidato in enumerate(pendientes):
                if not _puede_agregar_con_peso(
                    wave, candidato, warehouse.productos, max_peso_kg
                ):
                    continue
                d = _distancia_minima_pedido_wave(candidato, wave, warehouse, cache)
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
    max_peso_kg: float = 500.0,
    estrategia: EstrategiaWaves = EstrategiaWaves.PRIORIDAD_Y_CERCANIA,
) -> list[Wave]:
    if estrategia == EstrategiaWaves.PRIORIDAD:
        return _generar_waves_prioridad(
            pedidos, warehouse, max_pedidos, max_productos, max_peso_kg
        )
    if estrategia == EstrategiaWaves.PRIORIDAD_Y_CERCANIA:
        return _generar_waves_prioridad_cercania(
            pedidos, warehouse, max_pedidos, max_productos, max_peso_kg
        )
    raise ValueError(f"Estrategia desconocida: {estrategia}")


# --- split: waves con cobertura exacta de items ---


def _aplanar_pedidos_en_items(
    pedidos: list[Pedido],
) -> list[tuple[Pedido, ItemPedido]]:
    """Explota pedidos en pares (pedido, item). Cada par es atómico
    para el algoritmo (luego puede partirse por cantidad)."""
    out: list[tuple[Pedido, ItemPedido]] = []
    for p in pedidos:
        for it in p.items:
            out.append((p, it))
    return out


def _construir_wave_split(
    wave_id: str,
    wave_items: list[ItemWave],
    pedidos_por_id: dict[str, Pedido],
    max_pedidos: int,
    max_productos: int,
    max_peso_kg: float,
) -> Wave:
    wave = Wave(
        id=wave_id,
        max_pedidos=max_pedidos,
        max_productos=max_productos,
        max_peso_kg=max_peso_kg,
    )
    vistos: set[str] = set()
    for iw in wave_items:
        if iw.pedido_id not in vistos:
            wave.registrar_pedido_referencia(pedidos_por_id[iw.pedido_id])
            vistos.add(iw.pedido_id)
    wave.cerrar()
    return wave


def _puede_meter_item_split(
    item: ItemPedido,
    wave_items: list[ItemWave],
    pedidos_en_wave: set[str],
    pedido_id: str,
    productos: dict[str, "Producto"],
    max_pedidos: int,
    max_productos: int,
    max_peso_kg: float,
) -> int:
    """Devuelve cuántas unidades de `item` caben en la wave actual
    (0 si no entra nada)."""
    if pedido_id not in pedidos_en_wave and len(pedidos_en_wave) >= max_pedidos:
        return 0

    ya_prods = sum(iw.cantidad for iw in wave_items)
    espacio_prod = max_productos - ya_prods
    if espacio_prod <= 0:
        return 0

    peso_unit = productos[item.producto_id].peso_kg
    peso_actual = sum(
        productos[iw.producto_id].peso_kg * iw.cantidad for iw in wave_items
    )
    espacio_peso = int((max_peso_kg - peso_actual) / peso_unit)
    if espacio_peso <= 0:
        return 0

    return min(item.cantidad, espacio_prod, espacio_peso)


def _generar_waves_split_prioridad(
    pedidos: list[Pedido],
    warehouse: Warehouse,
    max_pedidos: int,
    max_productos: int,
    max_peso_kg: float,
) -> tuple[list[Wave], dict[str, list[ItemWave]]]:
    """Split greedy por prioridad.

    Ordena los items por (prioridad desc, pedido_id, producto_id) y
    llena waves secuencialmente. Un item que no cabe entero se parte:
    lo que cabe va a la wave actual, el resto se reencola.
    """
    items = _aplanar_pedidos_en_items(pedidos)
    items.sort(key=lambda pi: (-pi[0].prioridad, pi[0].id, pi[1].producto_id))

    pedidos_por_id = {p.id: p for p in pedidos}
    waves: list[Wave] = []
    items_por_wave: dict[str, list[ItemWave]] = {}
    contador = 1

    while items:
        wave_items: list[ItemWave] = []
        pedidos_en_wave: set[str] = set()

        i = 0
        while i < len(items):
            pedido, item = items[i]
            cant = _puede_meter_item_split(
                item,
                wave_items,
                pedidos_en_wave,
                pedido.id,
                warehouse.productos,
                max_pedidos,
                max_productos,
                max_peso_kg,
            )
            if cant <= 0:
                i += 1
                continue

            wave_items.append(ItemWave(pedido.id, item.producto_id, cant))
            pedidos_en_wave.add(pedido.id)

            if cant == item.cantidad:
                items.pop(i)
            else:
                items[i] = (pedido, ItemPedido(item.producto_id, item.cantidad - cant))
                # no avanzamos: puede meter más de este item si aún cabe algo

        if not wave_items:
            raise ValueError(
                f"No se pudo generar wave {contador}: ningún item restante cabe "
                f"(¿algún producto pesa más que max_peso_kg={max_peso_kg}?)"
            )

        wid = f"W{contador:03d}"
        waves.append(
            _construir_wave_split(
                wid,
                wave_items,
                pedidos_por_id,
                max_pedidos,
                max_productos,
                max_peso_kg,
            )
        )
        items_por_wave[wid] = wave_items
        contador += 1

    return waves, items_por_wave


def _generar_waves_split_prioridad_cercania(
    pedidos: list[Pedido],
    warehouse: Warehouse,
    max_pedidos: int,
    max_productos: int,
    max_peso_kg: float,
) -> tuple[list[Wave], dict[str, list[ItemWave]]]:
    """Split por prioridad + cercanía: arranca con el item más prioritario
    y agrega el más cercano a la wave en construcción."""
    cache = CacheDistancias(warehouse.grafo)
    pedidos_por_id = {p.id: p for p in pedidos}

    items = _aplanar_pedidos_en_items(pedidos)
    items.sort(key=lambda pi: (-pi[0].prioridad, pi[0].id, pi[1].producto_id))

    waves: list[Wave] = []
    items_por_wave: dict[str, list[ItemWave]] = {}
    contador = 1

    while items:
        wave_items: list[ItemWave] = []
        pedidos_en_wave: set[str] = set()

        # Semilla: primer item de la lista ordenada
        pedido0, item0 = items[0]
        cant0 = _puede_meter_item_split(
            item0,
            wave_items,
            pedidos_en_wave,
            pedido0.id,
            warehouse.productos,
            max_pedidos,
            max_productos,
            max_peso_kg,
        )
        if cant0 <= 0:
            raise ValueError(
                f"Semilla (pedido={pedido0.id}, prod={item0.producto_id}) no cabe "
                f"en una wave vacía. ¿peso_unit > max_peso_kg={max_peso_kg}?"
            )
        wave_items.append(ItemWave(pedido0.id, item0.producto_id, cant0))
        pedidos_en_wave.add(pedido0.id)
        if cant0 == item0.cantidad:
            items.pop(0)
        else:
            items[0] = (pedido0, ItemPedido(item0.producto_id, item0.cantidad - cant0))

        # Rellenar por cercanía
        while True:
            mejor_idx: int | None = None
            mejor_dist = float("inf")
            mejor_cant = 0

            for i, (pedido, item) in enumerate(items):
                cant = _puede_meter_item_split(
                    item,
                    wave_items,
                    pedidos_en_wave,
                    pedido.id,
                    warehouse.productos,
                    max_pedidos,
                    max_productos,
                    max_peso_kg,
                )
                if cant <= 0:
                    continue
                nodo_item = warehouse.productos[item.producto_id].nodo_picking
                d_min = min(
                    cache.distancia(
                        nodo_item, warehouse.productos[iw.producto_id].nodo_picking
                    )
                    for iw in wave_items
                )
                if d_min < mejor_dist:
                    mejor_dist = d_min
                    mejor_idx = i
                    mejor_cant = cant

            if mejor_idx is None:
                break

            pedido_b, item_b = items[mejor_idx]
            wave_items.append(ItemWave(pedido_b.id, item_b.producto_id, mejor_cant))
            pedidos_en_wave.add(pedido_b.id)
            if mejor_cant == item_b.cantidad:
                items.pop(mejor_idx)
            else:
                items[mejor_idx] = (
                    pedido_b,
                    ItemPedido(item_b.producto_id, item_b.cantidad - mejor_cant),
                )

        wid = f"W{contador:03d}"
        waves.append(
            _construir_wave_split(
                wid,
                wave_items,
                pedidos_por_id,
                max_pedidos,
                max_productos,
                max_peso_kg,
            )
        )
        items_por_wave[wid] = wave_items
        contador += 1

    return waves, items_por_wave


def generar_waves_con_split(
    pedidos: list[Pedido],
    warehouse: Warehouse,
    max_pedidos: int,
    max_productos: int,
    max_peso_kg: float = 500.0,
    estrategia: EstrategiaWaves = EstrategiaWaves.PRIORIDAD,
) -> tuple[list[Wave], dict[str, list[ItemWave]]]:
    """Genera waves permitiendo que un pedido se reparta entre varias.

    Devuelve (waves, items_por_wave). El segundo dict es la fuente de
    verdad de qué pickear en cada wave.

    Garantiza: Σ items_por_wave[wid] == pedidos.items (cobertura exacta).
    Validar con `validar_cobertura_waves`.
    """
    if estrategia == EstrategiaWaves.PRIORIDAD:
        return _generar_waves_split_prioridad(
            pedidos, warehouse, max_pedidos, max_productos, max_peso_kg
        )
    if estrategia == EstrategiaWaves.PRIORIDAD_Y_CERCANIA:
        return _generar_waves_split_prioridad_cercania(
            pedidos, warehouse, max_pedidos, max_productos, max_peso_kg
        )
    raise ValueError(f"Estrategia desconocida: {estrategia}")
