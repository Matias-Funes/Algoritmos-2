from __future__ import annotations

from collections.abc import Mapping
from math import isclose, isfinite
from typing import TYPE_CHECKING, Protocol

if __package__ and "." in __package__:
    from ..core.wave import Wave
else:
    from core.wave import Wave

if TYPE_CHECKING:
    from core.inventory import GestorInventario
    from core.order import Orden


class _ZonaDespacho(Protocol):
    peso_max_kg: float


class _Warehouse(Protocol):
    @property
    def zonas(self) -> Mapping[str, _ZonaDespacho]: ...


PENDIENTE = "PENDIENTE"
EN_WAVE = "EN_WAVE"


def _id_orden(orden: Orden) -> str:
    orden_id = orden.orden_id
    if not isinstance(orden_id, str) or not orden_id:
        raise ValueError("Cada orden debe tener un id no vacío.")
    return orden_id


def _esta_pendiente(orden: Orden) -> bool:
    return orden.esta_pendiente()


def _cantidad_productos(orden: Orden) -> int:
    if not orden.items:
        raise ValueError(f"La orden {_id_orden(orden)} no tiene productos.")

    total = 0
    for producto_id, cantidad in orden.items:
        if not isinstance(producto_id, str) or not producto_id:
            raise ValueError("Cada producto debe tener un id no vacío.")
        if (
            not isinstance(cantidad, int)
            or isinstance(cantidad, bool)
            or cantidad <= 0
        ):
            raise ValueError(
                f"La cantidad del producto {producto_id} debe ser positiva."
            )
        total += cantidad
    return total


def _obtener_peso_maximo(warehouse: object) -> float:
    zonas = getattr(warehouse, "zonas", None)
    if not isinstance(zonas, dict) or not zonas:
        raise ValueError("El warehouse debe tener al menos una zona de despacho.")

    pesos = [zona.peso_max_kg for zona in zonas.values()]
    if any(
        not isinstance(peso, (int, float))
        or isinstance(peso, bool)
        or not isfinite(peso)
        or peso < 0
        for peso in pesos
    ):
        raise ValueError("Cada zona debe tener un peso máximo finito no negativo.")
    return float(min(pesos))


def _ubicaciones(
    orden: Orden, inventario: GestorInventario
) -> list[tuple[float, float]]:
    ubicaciones = []
    for producto_id, _ in orden.items:
        ubicacion = inventario.obtener_producto(producto_id).ubicacion
        if not isinstance(ubicacion, (tuple, list)) or len(ubicacion) < 2:
            raise ValueError(
                f"El producto {producto_id} debe tener una ubicación (x, y, z)."
            )
        coordenadas = ubicacion[:2]
        if any(
            not isinstance(coordenada, (int, float))
            or isinstance(coordenada, bool)
            or not isfinite(coordenada)
            for coordenada in coordenadas
        ):
            raise ValueError(f"El producto {producto_id} tiene coordenadas inválidas.")
        ubicaciones.append((coordenadas[0], coordenadas[1]))
    return ubicaciones


def _distancia(
    ubicaciones_wave: list[tuple[float, float]],
    ubicaciones_orden: list[tuple[float, float]],
) -> float:
    return min(
        abs(x_wave - x_orden) + abs(y_wave - y_orden)
        for x_wave, y_wave in ubicaciones_wave
        for x_orden, y_orden in ubicaciones_orden
    )


def _peso_cabe(peso: float, limite: float) -> bool:
    return peso <= limite or isclose(peso, limite, rel_tol=1e-9, abs_tol=1e-9)


def ordenar_por_prioridad(ordenes: list[Orden]) -> list[Orden]:
    for orden in ordenes:
        if (
            not isinstance(orden.prioridad, int)
            or isinstance(orden.prioridad, bool)
            or not 1 <= orden.prioridad <= 5
        ):
            raise ValueError(
                f"La prioridad de la orden {_id_orden(orden)} debe estar entre 1 y 5."
            )
    return sorted(ordenes, key=lambda orden: (-orden.prioridad, _id_orden(orden)))


def generar_waves(
    ordenes: list[Orden],
    inventario: GestorInventario,
    warehouse: _Warehouse,
    config: dict,
) -> list[Wave]:
    capacidad_pedidos = config.get("wave_max_pedidos")
    capacidad_productos = config.get("wave_max_productos")
    for nombre, capacidad in (
        ("wave_max_pedidos", capacidad_pedidos),
        ("wave_max_productos", capacidad_productos),
    ):
        if (
            not isinstance(capacidad, int)
            or isinstance(capacidad, bool)
            or capacidad <= 0
        ):
            raise ValueError(f"'{nombre}' debe ser un entero positivo.")

    pendientes = [orden for orden in ordenes if _esta_pendiente(orden)]
    if not pendientes:
        return []

    ordenadas = ordenar_por_prioridad(pendientes)
    ids = [_id_orden(orden) for orden in ordenadas]
    if len(ids) != len(set(ids)):
        raise ValueError("Los ids de las órdenes pendientes deben ser únicos.")

    cantidades = {}
    pesos = {}
    ubicaciones_por_orden = {}
    for orden in ordenadas:
        clave = id(orden)
        cantidades[clave] = _cantidad_productos(orden)
        peso = orden.peso_total(inventario)
        if (
            not isinstance(peso, (int, float))
            or isinstance(peso, bool)
            or not isfinite(peso)
            or peso < 0
        ):
            raise ValueError(
                f"El peso de la orden {_id_orden(orden)} debe ser finito y no negativo."
            )
        pesos[clave] = peso
        ubicaciones_por_orden[clave] = _ubicaciones(orden, inventario)

    peso_max_kg = _obtener_peso_maximo(warehouse)
    waves = []
    restantes = list(ordenadas)
    numero_wave = 1

    while restantes:
        semilla = restantes.pop(0)
        wave = Wave(
            f"WAVE_{numero_wave:03d}",
            capacidad_pedidos,
            capacidad_productos,
            peso_max_kg,
        )
        if not wave.agregar_pedido(semilla, inventario):
            raise ValueError(
                f"La orden {_id_orden(semilla)} excede la capacidad de una wave."
            )

        ubicaciones_wave = list(ubicaciones_por_orden[id(semilla)])
        unidades_wave = cantidades[id(semilla)]
        peso_wave = pesos[id(semilla)]

        while len(wave) < capacidad_pedidos:
            candidatos = []
            for indice, orden in enumerate(restantes):
                clave = id(orden)
                peso_candidato = peso_wave + pesos[clave]
                if (
                    unidades_wave + cantidades[clave] > capacidad_productos
                    or not _peso_cabe(peso_candidato, peso_max_kg)
                ):
                    continue
                candidatos.append(
                    (
                        _distancia(
                            ubicaciones_wave,
                            ubicaciones_por_orden[clave],
                        ),
                        -orden.prioridad,
                        _id_orden(orden),
                        indice,
                    )
                )

            if not candidatos:
                break

            _, _, _, indice_elegido = min(candidatos)
            elegido = restantes.pop(indice_elegido)
            if not wave.agregar_pedido(elegido, inventario):
                raise RuntimeError("No se pudo agregar una orden validada.")

            ubicaciones_wave.extend(ubicaciones_por_orden[id(elegido)])
            unidades_wave += cantidades[id(elegido)]
            peso_wave += pesos[id(elegido)]

        waves.append(wave)
        numero_wave += 1

    for wave in waves:
        for orden in wave.pedidos:
            orden.cambiar_estado(EN_WAVE)

    return waves
