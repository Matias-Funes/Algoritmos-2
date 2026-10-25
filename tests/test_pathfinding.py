import unittest

from src.algorithms.pathfinding import CacheDistancias, dijkstra


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


if __name__ == "__main__":
    unittest.main()
