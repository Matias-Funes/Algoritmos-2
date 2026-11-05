import unittest
from pathlib import Path

from src.algorithms.wave_manager import generar_waves
from src.core.graph_builder import construir_grafo
from src.core.inventory import GestorInventario
from src.core.warehouse import Warehouse
from src.core.wave import Wave
from src.utils.benchmark import (
    cargar_escenario,
    comparar_estrategias,
    listar_escenarios,
    nombre_escenario,
)


class TestComparacion(unittest.TestCase):
    def test_comparacion_basica(self):
        # Cargamos el escenario
        ruta = next(r for r in listar_escenarios() if nombre_escenario(r) == "basico")
        e = cargar_escenario(ruta)
        grafo = construir_grafo(e["warehouse"])
        waves = generar_waves(e["pedidos"], e["inventario"], grafo, e["config"])

        # Corremos la comparación
        resultado = comparar_estrategias(grafo, waves, e["warehouse"], e["inventario"])

        # Verificamos que las métricas coinciden con el CSV de benchmark
        self.assertEqual(resultado["totales"]["A"]["distancia"], 74)
        self.assertEqual(resultado["totales"]["B"]["distancia"], 60)
        self.assertEqual(resultado["ganador_distancia"], "B")
        self.assertEqual(len(resultado["errores"]), 0)

    def test_comparacion_wave_vacia_no_rompe(self):
        """Si le pasamos una wave sin productos, debe devolver todo en 0."""
        warehouse = Warehouse(10, 10)
        inventario = GestorInventario()

        # Creamos una wave vacía (0 pedidos)
        wave_vacia = Wave("WAVE_VACIA", 3, 10, 100.0)

        resultado = comparar_estrategias(
            grafo=None, waves=[wave_vacia], warehouse=warehouse, inventario=inventario
        )

        # Comprobamos que no explotó y devolvió métricas en 0
        self.assertEqual(resultado["totales"]["A"]["distancia"], 0)
        self.assertEqual(resultado["totales"]["B"]["distancia"], 0)
        self.assertEqual(resultado["totales"]["A"]["tiempo_ms"], 0)
        self.assertEqual(resultado["totales"]["B"]["tiempo_ms"], 0)

    def test_comparacion_sin_waves(self):
        """Si no hay waves (lista vacía), debe devolver el diccionario base en 0."""
        resultado = comparar_estrategias(
            grafo=None, waves=[], warehouse=None, inventario=None
        )
        self.assertEqual(resultado["por_wave"], [])
        self.assertIsNone(resultado["ganador_distancia"])
