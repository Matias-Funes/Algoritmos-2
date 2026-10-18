from __future__ import annotations

from math import isclose, isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.inventory import Producto


class Picker:
    def __init__(
        self,
        picker_id: str,
        posicion_inicial: tuple[int, int],
        capacidad_carga_kg: float,
    ) -> None:
        if not isinstance(picker_id, str) or not picker_id:
            raise ValueError("El id del picker debe ser un string no vacío.")
        self._validar_posicion(posicion_inicial)
        self._validar_peso(
            capacidad_carga_kg,
            "La capacidad de carga debe ser un número finito positivo.",
        )
        if capacidad_carga_kg <= 0:
            raise ValueError("La capacidad de carga debe ser un número finito positivo.")

        self.id = picker_id
        self.posicion_inicial = posicion_inicial
        self.posicion_actual = posicion_inicial
        self.capacidad_carga_kg = float(capacidad_carga_kg)
        self.carga_actual_kg = 0.0
        self.items_transportados: list[tuple[str, int]] = []

    @staticmethod
    def _validar_posicion(posicion: tuple[int, int]) -> None:
        if (
            not isinstance(posicion, (tuple, list))
            or len(posicion) != 2
            or any(
                not isinstance(coordenada, int) or isinstance(coordenada, bool)
                for coordenada in posicion
            )
        ):
            raise ValueError("La posición debe contener dos coordenadas enteras (x, y).")

    @staticmethod
    def _validar_peso(peso: float, mensaje: str) -> None:
        if (
            not isinstance(peso, (int, float))
            or isinstance(peso, bool)
            or not isfinite(peso)
            or peso < 0
        ):
            raise ValueError(mensaje)

    def puede_recoger(self, producto: Producto, cantidad: int) -> bool:
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            raise ValueError("La cantidad a recoger debe ser un entero positivo.")
        if not isinstance(producto.producto_id, str) or not producto.producto_id:
            raise ValueError("El producto debe tener un id no vacío.")
        self._validar_peso(
            producto.peso_kg,
            "El peso del producto debe ser finito y no negativo.",
        )

        nueva_carga = self.carga_actual_kg + producto.peso_kg * cantidad
        return nueva_carga <= self.capacidad_carga_kg or isclose(
            nueva_carga,
            self.capacidad_carga_kg,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )

    def recoger(self, producto: Producto, cantidad: int) -> None:
        if not self.puede_recoger(producto, cantidad):
            raise ValueError(
                f"El picker {self.id} no tiene capacidad para recoger "
                f"{cantidad} unidades de {producto.producto_id}."
            )

        for indice, (producto_id, cantidad_actual) in enumerate(
            self.items_transportados
        ):
            if producto_id == producto.producto_id:
                self.items_transportados[indice] = (
                    producto_id,
                    cantidad_actual + cantidad,
                )
                break
        else:
            self.items_transportados.append((producto.producto_id, cantidad))

        self.carga_actual_kg += producto.peso_kg * cantidad

    def mover_a(self, nueva_posicion: tuple[int, int]) -> None:
        self._validar_posicion(nueva_posicion)
        self.posicion_actual = tuple(nueva_posicion)

    def descargar(self) -> list[tuple[str, int]]:
        items_descargados = self.items_transportados.copy()
        self.items_transportados.clear()
        self.carga_actual_kg = 0.0
        return items_descargados

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "posicion_inicial": list(self.posicion_inicial),
            "posicion_actual": list(self.posicion_actual),
            "capacidad_carga_kg": self.capacidad_carga_kg,
            "carga_actual_kg": self.carga_actual_kg,
            "items_transportados": [
                [producto_id, cantidad]
                for producto_id, cantidad in self.items_transportados
            ],
        }

    @staticmethod
    def from_dict(datos: dict) -> Picker:
        try:
            picker = Picker(
                datos["id"],
                tuple(datos["posicion_inicial"]),
                datos["capacidad_carga_kg"],
            )
            picker.mover_a(tuple(datos["posicion_actual"]))
            carga_actual = datos["carga_actual_kg"]
            Picker._validar_peso(
                carga_actual,
                "La carga actual debe ser un número finito no negativo.",
            )
            if carga_actual > picker.capacidad_carga_kg and not isclose(
                carga_actual,
                picker.capacidad_carga_kg,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                raise ValueError("La carga actual supera la capacidad del picker.")

            items = []
            for item in datos["items_transportados"]:
                if (
                    not isinstance(item, (list, tuple))
                    or len(item) != 2
                    or not isinstance(item[0], str)
                    or not item[0]
                    or not isinstance(item[1], int)
                    or isinstance(item[1], bool)
                    or item[1] <= 0
                ):
                    raise ValueError("Los items transportados no tienen un formato válido.")
                items.append((item[0], item[1]))

            picker.carga_actual_kg = float(carga_actual)
            picker.items_transportados = items
            return picker
        except KeyError as error:
            raise ValueError(
                f"Falta el campo requerido del picker: {error.args[0]}."
            ) from error