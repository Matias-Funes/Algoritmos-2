import unittest

from src.core.inventory import GestorInventario, Producto
from src.core.order import Orden
from src.core.wave import Wave


def crear_inventario():
    inventario = GestorInventario()
    inventario.agregar_producto(
        Producto("P001", "Monitor", "R1", (3, 5, 1), 10, 6.5)
    )
    inventario.agregar_producto(
        Producto("P002", "Teclado", "R1", (3, 6, 1), 10, 1.2)
    )
    inventario.agregar_producto(
        Producto("P003", "Mouse", "R2", (8, 5, 1), 10, 0.3)
    )
    return inventario


class TestWave(unittest.TestCase):
    def setUp(self):
        self.inventario = crear_inventario()

    def test_constructor_inicializa_wave_vacia(self):
        wave = Wave("WAVE_001", 3, 10, 30.0)

        self.assertEqual(wave.id, "WAVE_001")
        self.assertEqual(wave.pedidos, [])
        self.assertEqual(wave.capacidad_max_pedidos, 3)
        self.assertEqual(wave.capacidad_max_productos, 10)
        self.assertEqual(wave.peso_max_kg, 30.0)
        self.assertIsNone(wave.recorrido_A)
        self.assertIsNone(wave.recorrido_B)
        self.assertEqual(len(wave), 0)

    def test_constructor_rechaza_parametros_invalidos(self):
        casos_invalidos = [
            ("", 3, 10, 30.0),
            ("WAVE_001", 0, 10, 30.0),
            ("WAVE_001", 3, 0, 30.0),
            ("WAVE_001", 3, 10, -1.0),
            ("WAVE_001", True, 10, 30.0),
        ]

        for argumentos in casos_invalidos:
            with self.subTest(argumentos=argumentos):
                with self.assertRaises(ValueError):
                    Wave(*argumentos)

    def test_peso_y_cantidad_son_cero_si_no_hay_pedidos(self):
        wave = Wave("WAVE_001", 3, 10, 30.0)

        self.assertEqual(wave.peso_total(self.inventario), 0.0)
        self.assertEqual(wave.cantidad_productos(), 0)

    def test_agregar_pedido_actualiza_peso_y_cantidad(self):
        wave = Wave("WAVE_001", 3, 10, 30.0)
        orden = Orden("PED_001", 5, [("P001", 2), ("P002", 1)])

        self.assertTrue(wave.agregar_pedido(orden, self.inventario))
        self.assertEqual(wave.pedidos, [orden])
        self.assertEqual(wave.cantidad_productos(), 3)
        self.assertAlmostEqual(wave.peso_total(self.inventario), 14.2)
        self.assertEqual(len(wave), 1)

    def test_puede_aceptar_no_agrega_el_pedido(self):
        wave = Wave("WAVE_001", 3, 10, 30.0)
        orden = Orden("PED_001", 5, [("P001", 1)])

        self.assertTrue(wave.puede_aceptar(orden, self.inventario))
        self.assertEqual(wave.pedidos, [])

    def test_rechaza_orden_sin_productos(self):
        wave = Wave("WAVE_001", 3, 10, 30.0)
        orden = Orden("PED_VACIO", 1, [])

        with self.assertRaisesRegex(ValueError, "sin productos"):
            wave.puede_aceptar(orden, self.inventario)
        with self.assertRaisesRegex(ValueError, "sin productos"):
            wave.agregar_pedido(orden, self.inventario)

        self.assertEqual(wave.pedidos, [])

    def test_rechaza_cantidades_invalidas(self):
        wave = Wave("WAVE_001", 3, 10, 30.0)

        for cantidad in (0, -1, 1.5, True):
            orden = Orden("PED_INVALIDO", 1, [("P001", cantidad)])
            with self.subTest(cantidad=cantidad):
                with self.assertRaisesRegex(ValueError, "enteros positivos"):
                    wave.agregar_pedido(orden, self.inventario)

    def test_rechaza_orden_si_supera_cantidad_maxima_de_productos(self):
        wave = Wave("WAVE_001", 3, 2, 30.0)
        orden = Orden("PED_001", 5, [("P001", 3)])

        self.assertFalse(wave.puede_aceptar(orden, self.inventario))
        self.assertFalse(wave.agregar_pedido(orden, self.inventario))
        self.assertEqual(len(wave), 0)

    def test_rechaza_orden_si_supera_peso_maximo(self):
        wave = Wave("WAVE_001", 3, 10, 5.0)
        orden = Orden("PED_001", 5, [("P001", 1)])

        self.assertFalse(wave.puede_aceptar(orden, self.inventario))
        self.assertFalse(wave.agregar_pedido(orden, self.inventario))
        self.assertEqual(wave.peso_total(self.inventario), 0.0)

    def test_rechaza_orden_si_supera_cantidad_maxima_de_pedidos(self):
        wave = Wave("WAVE_001", 1, 10, 30.0)
        primera = Orden("PED_001", 5, [("P001", 1)])
        segunda = Orden("PED_002", 4, [("P002", 1)])

        self.assertTrue(wave.agregar_pedido(primera, self.inventario))
        self.assertFalse(wave.puede_aceptar(segunda, self.inventario))
        self.assertFalse(wave.agregar_pedido(segunda, self.inventario))
        self.assertEqual(wave.pedidos, [primera])
        self.assertEqual(len(wave), 1)

    def test_acepta_peso_en_limite_con_redondeo_decimal(self):
        inventario = GestorInventario()
        inventario.agregar_producto(
            Producto("P001", "Producto 1", "R1", (0, 0, 1), 2, 0.1)
        )
        inventario.agregar_producto(
            Producto("P002", "Producto 2", "R1", (0, 1, 1), 2, 0.2)
        )
        wave = Wave("WAVE_001", 2, 2, 0.3)

        self.assertTrue(
            wave.agregar_pedido(
                Orden("PED_001", 1, [("P001", 1)]),
                inventario,
            )
        )
        self.assertTrue(
            wave.agregar_pedido(
                Orden("PED_002", 1, [("P002", 1)]),
                inventario,
            )
        )

    def test_peso_cero_y_limites_validos(self):
        inventario = GestorInventario()
        inventario.agregar_producto(
            Producto("P001", "Producto liviano", "R1", (0, 0, 1), 1, 0.0)
        )
        wave = Wave("WAVE_001", 1, 1, 0.0)
        orden = Orden("PED_001", 1, [("P001", 1)])

        self.assertTrue(wave.agregar_pedido(orden, inventario))
        self.assertEqual(wave.peso_total(inventario), 0.0)
        self.assertEqual(wave.cantidad_productos(), 1)


if __name__ == "__main__":
    unittest.main()
