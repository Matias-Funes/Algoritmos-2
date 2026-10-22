import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.inventory import Producto
from core.picker import Picker


class TestPicker(unittest.TestCase):
    def test_inicializa_atributos_basicos(self):
        picker = Picker("PK_01", (2, 3), 100.0)

        self.assertEqual(picker.id, "PK_01")
        self.assertEqual(picker.posicion_inicial, (2, 3))
        self.assertEqual(picker.posicion_actual, (2, 3))
        self.assertEqual(picker.capacidad_carga_kg, 100.0)
        self.assertEqual(picker.carga_actual_kg, 0.0)
        self.assertEqual(picker.items_transportados, [])

    def test_cada_picker_tiene_su_lista_de_items(self):
        picker_1 = Picker("PK_01", (0, 0), 50.0)
        picker_2 = Picker("PK_02", (1, 1), 75.0)
        picker_1.items_transportados.append(("P001", 1))

        self.assertEqual(picker_1.items_transportados, [("P001", 1)])
        self.assertEqual(picker_2.items_transportados, [])

    def test_recoger_agrega_producto_y_actualiza_carga(self):
        picker = Picker("PK_01", (0, 0), 10.0)
        producto = Producto("P001", "Monitor", "R1", (1, 2, 1), 5, 2.5)

        picker.recoger(producto, 2)
        picker.recoger(producto, 1)

        self.assertEqual(picker.items_transportados, [("P001", 3)])
        self.assertEqual(picker.carga_actual_kg, 7.5)

    def test_no_recoge_si_supera_capacidad(self):
        picker = Picker("PK_01", (0, 0), 5.0)
        producto = Producto("P001", "Monitor", "R1", (1, 2, 1), 5, 2.5)

        self.assertFalse(picker.puede_recoger(producto, 3))
        with self.assertRaises(ValueError):
            picker.recoger(producto, 3)
        self.assertEqual(picker.items_transportados, [])
        self.assertEqual(picker.carga_actual_kg, 0.0)

    def test_rechaza_cantidad_invalida(self):
        picker = Picker("PK_01", (0, 0), 5.0)
        producto = Producto("P001", "Monitor", "R1", (1, 2, 1), 5, 2.5)

        with self.assertRaises(ValueError):
            picker.puede_recoger(producto, 0)

    def test_mover_y_descargar(self):
        picker = Picker("PK_01", (0, 0), 10.0)
        producto = Producto("P001", "Monitor", "R1", (1, 2, 1), 5, 2.5)
        picker.recoger(producto, 2)

        picker.mover_a((4, 5))
        descargados = picker.descargar()

        self.assertEqual(picker.posicion_actual, (4, 5))
        self.assertEqual(descargados, [("P001", 2)])
        self.assertEqual(picker.items_transportados, [])
        self.assertEqual(picker.carga_actual_kg, 0.0)

    def test_serializacion_y_restauracion(self):
        picker = Picker("PK_01", (0, 0), 10.0)
        producto = Producto("P001", "Monitor", "R1", (1, 2, 1), 5, 2.5)
        picker.recoger(producto, 2)
        picker.mover_a((4, 5))

        restaurado = Picker.from_dict(picker.to_dict())

        self.assertEqual(restaurado.to_dict(), picker.to_dict())


if __name__ == "__main__":
    unittest.main()
