from __future__ import annotations

from math import isclose, isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.inventory import GestorInventario
    from core.order import Orden




class Wave:
    def __init__(
        self,
        wave_id: str,
        capacidad_max_pedidos: int,
        capacidad_max_productos: int,
        peso_max_kg: float,
        #cosas por si te salis de los parametros que debe tener una wave
    ) -> None:
        if not isinstance(wave_id, str) or not wave_id:
            raise ValueError("El id de la wave debe ser un string no vacío.")
        if (
            not isinstance(capacidad_max_pedidos, int)
            or isinstance(capacidad_max_pedidos, bool)
            or capacidad_max_pedidos <= 0
        ):
            raise ValueError("La capacidad máxima de pedidos debe ser positiva.")
        if (
            not isinstance(capacidad_max_productos, int)
            or isinstance(capacidad_max_productos, bool)
            or capacidad_max_productos <= 0
        ):
            raise ValueError("La capacidad máxima de productos debe ser positiva.")
        if (
            not isinstance(peso_max_kg, (int, float))
            or isinstance(peso_max_kg, bool)
            or not isfinite(peso_max_kg)
            or peso_max_kg < 0
        ):
            raise ValueError("El peso máximo debe ser un número finito no negativo.")

        self.id = wave_id
        self.pedidos: list[Orden] = []
        self.capacidad_max_pedidos = capacidad_max_pedidos
        self.capacidad_max_productos = capacidad_max_productos
        self.peso_max_kg = float(peso_max_kg)
        #esto lo puse por si queres guardar el recorrido desde una wave y que se puedan guardar dos recorridos segun dos estrategias distintas, A y B, que se pueden usar para comparar cual es mejor
        self.recorrido_A: list[int] | None = None
        self.recorrido_B: list[int] | None = None

    def peso_total(self, inventario: GestorInventario) -> float:
        return sum(orden.peso_total(inventario) for orden in self.pedidos)

    def cantidad_productos(self) -> int:
        return sum(
            cantidad
            for orden in self.pedidos
            for _, cantidad in orden.items
        )

    def puede_aceptar(
        self, orden: Orden, inventario: GestorInventario
    ) -> bool:
        if not orden.items:
            raise ValueError("No se puede agregar una orden sin productos.")

        cantidades = [cantidad for _, cantidad in orden.items]
        if any(
            not isinstance(cantidad, int)
            or isinstance(cantidad, bool)
            or cantidad <= 0
            for cantidad in cantidades
        ):
            raise ValueError("Las cantidades deben ser enteros positivos.")

        peso_orden = orden.peso_total(inventario)
        if (
            not isinstance(peso_orden, (int, float))
            or isinstance(peso_orden, bool)
            or not isfinite(peso_orden)
            or peso_orden < 0
        ):
            raise ValueError("El peso de la orden debe ser finito y no negativo.")

        peso_resultante = self.peso_total(inventario) + peso_orden
        return (
            len(self.pedidos) < self.capacidad_max_pedidos
            and self.cantidad_productos() + sum(cantidades)
            <= self.capacidad_max_productos
            and (
                peso_resultante <= self.peso_max_kg
                or isclose(
                    peso_resultante,
                    self.peso_max_kg,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
            )
        )

    def agregar_pedido(
        self, orden: Orden, inventario: GestorInventario
    ) -> bool:
        if not self.puede_aceptar(orden, inventario):
            return False
        self.pedidos.append(orden)
        return True

    def __len__(self) -> int:
        return len(self.pedidos)
