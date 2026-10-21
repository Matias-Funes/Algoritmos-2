import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.wave_manager import generar_waves, ordenar_por_prioridad
from core.inventory import GestorInventario, Producto
from core.order import Orden
from core.wave import Wave


def crear_inventario():
    inventario = GestorInventario()
    for producto_id, ubicacion, peso in (
        ("P1", (0, 0, 1), 1.0),
        ("P2", (10, 0, 1), 1.0),
        ("P3", (1, 0, 1), 1.0),
    ):
        inventario.agregar_producto(
            Producto(producto_id, producto_id, "R1", ubicacion, 20, peso)
        )
    return inventario


def crear_warehouse(peso_max_kg=10.0):
    return SimpleNamespace(
        zonas={"Z1": SimpleNamespace(peso_max_kg=peso_max_kg)}
    )


class TestWave(unittest.TestCase):
    def setUp(self):
        self.inventario = crear_inventario()

    def test_agrega_orden_y_calcula_unidades_y_peso(self):
        wave = Wave("WAVE_001", 2, 4, 4.0)
        primera = Orden("PED_1", 1, [("P1", 2)])
        segunda = Orden("PED_2", 1, [("P2", 2)])

        self.assertTrue(wave.agregar_pedido(primera, self.inventario))
        self.assertTrue(wave.agregar_pedido(segunda, self.inventario))
        self.assertEqual(wave.pedidos, [primera, segunda])
        self.assertEqual(wave.cantidad_productos(), 4)
        self.assertEqual(wave.peso_total(self.inventario), 4.0)

    def test_rechaza_orden_que_excede_capacidad(self):
        wave = Wave("WAVE_001", 1, 2, 1.0)
        orden = Orden("PED_1", 1, [("P1", 2)])

        self.assertFalse(wave.agregar_pedido(orden, self.inventario))
        self.assertEqual(len(wave), 0)

    def test_acepta_peso_en_limite_con_error_de_redondeo(self):
        inventario = GestorInventario()
        inventario.agregar_producto(Producto("P1", "P1", "R1", (0, 0, 1), 1, 0.1))
        inventario.agregar_producto(Producto("P2", "P2", "R1", (1, 0, 1), 1, 0.2))
        wave = Wave("WAVE_001", 2, 2, 0.3)

        self.assertTrue(wave.agregar_pedido(Orden("PED_1", 1, [("P1", 1)]), inventario))
        self.assertTrue(wave.agregar_pedido(Orden("PED_2", 1, [("P2", 1)]), inventario))


class TestGenerarWaves(unittest.TestCase):
    def test_prioriza_semilla_y_agrega_orden_mas_cercana(self):
        inventario = crear_inventario()
        ordenes = [
            Orden("PED_B", 4, [("P2", 1)]),
            Orden("PED_A", 5, [("P1", 1)]),
            Orden("PED_C", 4, [("P3", 1)]),
        ]

        waves = generar_waves(
            ordenes,
            inventario,
            crear_warehouse(),
            {"wave_max_pedidos": 2, "wave_max_productos": 5},
        )

        self.assertEqual(
            [[orden.orden_id for orden in wave.pedidos] for wave in waves],
            [["PED_A", "PED_C"], ["PED_B"]],
        )
        self.assertTrue(all(orden.estado == "EN_WAVE" for orden in ordenes))

    def test_ignora_ordenes_no_pendientes(self):
        orden = Orden("PED_LISTO", 5, [("P1", 1)], estado="PREPARADO")

        waves = generar_waves(
            [orden],
            crear_inventario(),
            crear_warehouse(),
            {"wave_max_pedidos": 2, "wave_max_productos": 5},
        )

        self.assertEqual(waves, [])
        self.assertEqual(orden.estado, "PREPARADO")

    def test_rechaza_orden_que_no_cabe_en_una_wave(self):
        orden = Orden("PED_GRANDE", 5, [("P1", 3)])

        with self.assertRaisesRegex(ValueError, "excede la capacidad"):
            generar_waves(
                [orden],
                crear_inventario(),
                crear_warehouse(),
                {"wave_max_pedidos": 2, "wave_max_productos": 2},
            )

    def test_rechaza_orden_que_excede_peso_de_despacho(self):
        orden = Orden("PED_PESADO", 5, [("P1", 2)])

        with self.assertRaisesRegex(ValueError, "excede la capacidad"):
            generar_waves(
                [orden],
                crear_inventario(),
                crear_warehouse(peso_max_kg=1.0),
                {"wave_max_pedidos": 2, "wave_max_productos": 5},
            )

    def test_ordenar_prioridad_desempata_por_id(self):
        ordenes = [
            Orden("PED_B", 3, [("P1", 1)]),
            Orden("PED_C", 5, [("P1", 1)]),
            Orden("PED_A", 3, [("P1", 1)]),
        ]

        self.assertEqual(
            [orden.orden_id for orden in ordenar_por_prioridad(ordenes)],
            ["PED_C", "PED_A", "PED_B"],
        )


if __name__ == "__main__":
    unittest.main()
