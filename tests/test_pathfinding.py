import unittest

from src.algorithms.pathfinding import (
    CacheDistancias,
    RutaInalcanzableError,
    dijkstra,
    expandir_ruta,
)


class FakeGraph:
    def __init__(self):
        self.adj = {
            (0, 0): {(1, 0): 1, (0, 1): 5},
            (1, 0): {(2, 0): 2},
            (0, 1): {(2, 0): 1},
            (2, 0): {},
        }

    def get_neighbors(self, nodo):
        return self.adj.get(nodo, {})

    def nodes(self):
        return list(self.adj.keys())


class TestPathfinding(unittest.TestCase):
    def setUp(self):
        self.g = FakeGraph()
        self.cache = CacheDistancias(self.g)

    def test_dijkstra_y_camino(self):
        # Usamos el caché que a su vez usa dijkstra
        camino = self.cache.camino((0, 0), (2, 0))
        distancia = self.cache.distancia((0, 0), (2, 0))

        self.assertEqual(camino, [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(distancia, 3)

    def test_dijkstra_sin_camino(self):
        camino = self.cache.camino((2, 0), (0, 0))
        self.assertEqual(camino, [])

    def test_hashtable_soporta_tuplas(self):
        # Verifica que la HashTable de Jony acepta (x,y) como clave
        cache = CacheDistancias(self.g)
        cache._asegurar_origen((0, 0))
        # Si no explotó, podemos buscar la distancia
        self.assertEqual(cache.distancia((0, 0), (2, 0)), 3)

    def test_expandir_ruta_exitosa(self):
        # Usando el grafo de prueba, el camino de (0,0) a (2,0) debe pasar por (1,0)
        ruta = expandir_ruta(self.g, [(0, 0), (2, 0)])
        self.assertEqual(ruta, [(0, 0), (1, 0), (2, 0)])

    def test_expandir_ruta_error(self):
        # En nuestro FakeGraph no hay camino de vuelta de (2,0) a (0,0)
        with self.assertRaises(RutaInalcanzableError):
            expandir_ruta(self.g, [(2, 0), (0, 0)])

    def test_estrategia_A_metricas(self):
        from src.algorithms.pathfinding import estrategia_A

        # Creamos objetos falsos para simular el inventario y la wave
        class FakeProducto:
            def __init__(self, pid, x, y):
                self.ubicacion = (x, y)

        class FakeInventario:
            def obtener_producto(self, pid):
                # P1 en (0,0) buscará pasillo en (1,0)
                # P2 en (1,0) buscará pasillo en (2,0)
                if pid == "P1":
                    return FakeProducto("P1", 0, 0)
                if pid == "P2":
                    return FakeProducto("P2", 1, 0)
                return None

        class FakePedido:
            def __init__(self):
                self.items = [("P1", 1), ("P2", 1)]

        class FakeWave:
            def __init__(self):
                self.pedidos = [FakePedido()]

        class FakeWarehouse:
            ancho_x = 10
            largo_y = 10

            def __init__(self):
                self.grid = [
                    [type("Cell", (), {"tipo": "PASILLO"})() for _ in range(10)]
                    for _ in range(10)
                ]

        wave = FakeWave()
        inv = FakeInventario()
        wh = FakeWarehouse()

        resultado = estrategia_A(self.g, wave, wh, inv, self.cache)

        # 1. Verifica que la ruta se haya armado
        self.assertGreater(len(resultado["ruta"]), 0)

        # 2. Verifica que la distancia se sume bien
        # (En FakeGraph, de (1,0) a (2,0) el peso es 2)
        self.assertEqual(resultado["distancia_total"], 2)

        # 3. ¡EL TEST CLAVE! Verifica que nodos_visitados NO sea 0
        self.assertGreater(resultado["nodos_visitados"], 0)

    def test_obtener_celda_piso_bloqueado(self):
        from src.algorithms.pathfinding import RutaInalcanzableError, obtener_celda_piso

        class FakeProducto:
            ubicacion = (0, 0)

        class FakeWarehouse:
            ancho_x = 2
            largo_y = 2
            # Simulamos que TODO es RACK (no hay PASILLO)
            grid = [
                [type("Cell", (), {"tipo": "RACK"})() for _ in range(2)]
                for _ in range(2)
            ]

        with self.assertRaises(RutaInalcanzableError):
            obtener_celda_piso(FakeProducto(), FakeWarehouse())


if __name__ == "__main__":
    unittest.main()
