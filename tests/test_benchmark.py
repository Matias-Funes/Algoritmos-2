import csv
import tempfile
import unittest
from pathlib import Path
 
from src.algorithms.wave_manager import generar_waves
from src.core.graph_builder import construir_grafo
from src.utils.benchmark import (COLUMNAS, DIR_ESCENARIOS, ESTRATEGIAS,
                                 cargar_escenario, correr_escenario,
                                 escribir_csv, listar_escenarios,
                                 nombre_escenario)
 
 
def escenario(nombre):
    ruta = next(r for r in listar_escenarios() if nombre_escenario(r) == nombre)
    return cargar_escenario(ruta)
 
 
class TestCargaDeEscenarios(unittest.TestCase):
 
    def test_lista_los_escenarios_de_menor_a_mayor_cantidad_de_pedidos(self):
        nombres = [nombre_escenario(r) for r in listar_escenarios()]
        self.assertEqual(nombres, ["basico", "generado", "grande"])
 
    def test_carga_el_escenario_basico(self):
        e = escenario("basico")
        self.assertEqual((e["warehouse"].ancho_x, e["warehouse"].largo_y), (18, 16))
        self.assertEqual(len(e["warehouse"].racks), 3)
        self.assertEqual(len(e["inventario"]), 8)
        self.assertEqual(len(e["pedidos"]), 3)
        self.assertEqual(e["inventario"].obtener_ubicacion("P001"), (3, 5, 1))
        self.assertEqual(e["pedidos"][0].items, [("P001", 2), ("P002", 1)])
        self.assertEqual(e["config"]["max_pedidos"], 3)
        self.assertEqual(e["config"]["max_productos"], 15)
 
    def test_el_peso_maximo_de_la_wave_es_la_mayor_capacidad_de_los_pickers(self):
        self.assertEqual(escenario("basico")["config"]["peso_max_kg"], 150.0)
        self.assertEqual(escenario("grande")["config"]["peso_max_kg"], 150.0)
 
    def test_en_todos_los_escenarios_se_asignan_todos_los_pedidos(self):
        for ruta in listar_escenarios():
            e = cargar_escenario(ruta)
            grafo = construir_grafo(e["warehouse"])
            waves = generar_waves(e["pedidos"], e["inventario"], grafo, e["config"])
            self.assertEqual(sum(len(w) for w in waves), len(e["pedidos"]),
                             nombre_escenario(ruta))
            self.assertTrue(all(len(w) <= e["config"]["max_pedidos"] for w in waves))
 
 
class TestBenchmark(unittest.TestCase):
 
    def test_una_fila_por_estrategia(self):
        filas, waves = correr_escenario("basico", escenario("basico"), repeticiones=1)
        self.assertEqual([f["Estrategia"] for f in filas], list(ESTRATEGIAS))
        self.assertGreaterEqual(len(waves), 1)
        for f in filas:
            self.assertEqual(f["Escenario"], "basico")
            self.assertGreater(f["Distancia"], 0)
            self.assertGreater(f["Nodos_Visitados"], 0)
            self.assertGreaterEqual(f["Tiempo_ms"], 0)
 
    def test_los_resultados_son_reproducibles(self):
        a, _ = correr_escenario("generado", escenario("generado"), repeticiones=1)
        b, _ = correr_escenario("generado", escenario("generado"), repeticiones=1)
        for fa, fb in zip(a, b):
            self.assertEqual(fa["Distancia"], fb["Distancia"])
            self.assertEqual(fa["Nodos_Visitados"], fb["Nodos_Visitados"])
 
    def test_escribir_csv_crea_la_carpeta_y_las_columnas_pedidas(self):
        filas, _ = correr_escenario("basico", escenario("basico"), repeticiones=1)
        with tempfile.TemporaryDirectory() as tmp:
            ruta = escribir_csv(filas, Path(tmp) / "results" / "experimentos.csv")
            with open(ruta, newline="", encoding="utf-8") as f:
                leidas = list(csv.DictReader(f))
        self.assertEqual(list(leidas[0].keys()),
                         ["Escenario", "Estrategia", "Tiempo_ms", "Distancia", "Nodos_Visitados"])
        self.assertEqual(COLUMNAS, list(leidas[0].keys()))
        self.assertEqual(len(leidas), len(filas))
 
    def test_los_escenarios_estan_en_data_scenarios(self):
        self.assertTrue(DIR_ESCENARIOS.name == "scenarios" and DIR_ESCENARIOS.parent.name == "data")
 
 
if __name__ == "__main__":
    unittest.main()
 