import unittest
from src.core.warehouse import Warehouse, Pasillo
from src.core.graph_builder import construir_grafo
from src.core.cell import N

class TestGraphBuilder(unittest.TestCase):
    def setUp(self):
        self.wh = Warehouse(10, 10)
        # Creamos un pasillo que SOLO va hacia el Norte (N)
        self.wh.add_pasillo(Pasillo("P1", x=5, y=5, ancho=1, alto=1, sentido=N))
        self.wh.rellenar_pasillos_implicitos()
        self.grafo = construir_grafo(self.wh)

    def test_grafo_no_esta_vacio(self):
        self.assertGreater(self.grafo.node_count(), 0)
        self.assertGreater(self.grafo.edge_count(), 0)

    def test_respeta_sentido_norte(self):
        # El nodo (5,5) tiene sentido N. Sus vecinos deben incluir a (5,6) pero NO a (5,4)
        vecinos = self.grafo.get_neighbors((5, 5))
        
        self.assertIn((5, 6), vecinos, "Debería poder ir al Norte")
        self.assertNotIn((5, 4), vecinos, "NO debería poder ir al Sur")

if __name__ == '__main__':
    unittest.main()