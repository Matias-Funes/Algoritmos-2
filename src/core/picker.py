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










#demo de picker para probar que funciona correctamente, se puede ejecutar este archivo directamente
def _demo_picker() -> None:
    if not __package__:
        import sys
        from pathlib import Path

        raiz_proyecto = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(raiz_proyecto))

    from src.core.inventory import Producto

    print("DEMO DE PICKER")
    print("==============")
    monitor = Producto("P001", "Monitor", "R1", (3, 5, 1), 10, 6.5)
    teclado = Producto("P002", "Teclado", "R1", (3, 6, 1), 10, 1.2)
    picker = Picker("PK_01", (0, 0), 15.0)

    print("\n1. Constructor")
    print(f"Picker creado: {picker.id}")
    print(f"Posición inicial y actual: {picker.posicion_inicial}")
    print(f"Capacidad: {picker.capacidad_carga_kg:.2f} kg")
    print(f"Carga inicial: {picker.carga_actual_kg:.2f} kg")
    print(f"Items iniciales: {picker.items_transportados}")

    print("\n2. puede_recoger")
    puede_cargar_monitor = picker.puede_recoger(monitor, 2)
    print(f"¿Puede recoger 2 monitores? {puede_cargar_monitor}")

    print("\n3. recoger")
    picker.recoger(monitor, 2)
    picker.recoger(teclado, 1)
    print(f"Items transportados: {picker.items_transportados}")
    print(f"Carga actual: {picker.carga_actual_kg:.2f} kg")

    puede_exceder = picker.puede_recoger(monitor, 1)
    print(f"¿Puede recoger 1 monitor más? {puede_exceder}")
    try:
        picker.recoger(monitor, 1)
    except ValueError as error:
        print(f"recoger rechaza el exceso: {error}")

    print("\n4. mover_a")
    picker.mover_a((4, 7))
    print(f"Nueva posición: {picker.posicion_actual}")

    print("\n5. to_dict y from_dict")
    datos = picker.to_dict()
    print(f"Picker serializado: {datos}")
    picker_restaurado = Picker.from_dict(datos)
    print(f"Picker restaurado: {picker_restaurado.to_dict()}")

    print("\n6. descargar")
    items_descargados = picker.descargar()
    print(f"Items descargados: {items_descargados}")
    print(f"Carga después de descargar: {picker.carga_actual_kg:.2f} kg")
    print(f"Items restantes: {picker.items_transportados}")


if __name__ == "__main__":
    _demo_picker()