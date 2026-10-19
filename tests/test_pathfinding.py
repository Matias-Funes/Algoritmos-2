import unittest

from src.algorithms.pathfinding import dijkstra, matriz_distancias


class FakeGraph:
    def __init__(self):
        # Un grafo de prueba: (0,0) --1--> (1,0) --2--> (2,0)
        #                     \--5--> (0,1) ----------/
        self.adj = {
            (0, 0): {(1, 0): 1, (0, 1): 5},
            (1, 0): {(2, 0): 2},
            (0, 1): {(2, 0): 1},
            (2, 0): {},
        }

    def get_neighbors(self, nodo):
        return self.adj.get(nodo, {})


class TestPathfinding(unittest.TestCase):
    def setUp(self):
        self.g = FakeGraph()

    def test_dijkstra_camino_corto(self):
        camino = dijkstra(self.g, (0, 0), (2, 0))
        # El camino mas corto es (0,0) -> (1,0) -> (2,0) con peso 3
        # en vez de (0,0) -> (0,1) -> (2,0) con peso 6
        self.assertEqual(camino, [(0, 0), (1, 0), (2, 0)])

    def test_dijkstra_sin_camino(self):
        camino = dijkstra(self.g, (2, 0), (0, 0))
        self.assertEqual(camino, [])  # No hay retorno en este grafo dirigido

    def test_matriz_distancias(self):
        nodos = [(0, 0), (1, 0), (2, 0)]
        matriz = matriz_distancias(self.g, nodos)
        self.assertEqual(matriz[(0, 0)][(2, 0)], 2)  # Distancia en aristas (nodos-1)


if __name__ == "__main__":
    unittest.main()
