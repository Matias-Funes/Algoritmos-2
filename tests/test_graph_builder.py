import unittest
from main import _obtener_puntos_despacho
from src.core.cell import DESPACHO
from src.core.graph_builder import construir_grafo
from src.core.warehouse import (
    Pasillo,
    Puerta,
    Warehouse,
    ZonaDespacho,
)
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

    def test_zona_despacho_es_transitable_y_se_usa_para_descargar(self):
        warehouse = Warehouse(8, 8)
        warehouse.add_puerta(Puerta("OUT", "OUTBOUND", 0, 3))
        warehouse.add_zona_despacho(
            ZonaDespacho("Z1", "OUT", 1, 2, 2, 2, 100.0)
        )
        warehouse.rellenar_pasillos_implicitos()
        grafo = construir_grafo(warehouse)

        celdas_zona = {(1, 2), (2, 2), (1, 3), (2, 3)}
        self.assertTrue(
            all(
                warehouse.grid[y][x].tipo == DESPACHO
                for x, y in celdas_zona
            )
        )
        self.assertTrue(celdas_zona.issubset(grafo.adj))
        self.assertIn((2, 2), grafo.get_neighbors((1, 2)))
        self.assertIn((1, 2), grafo.get_neighbors((2, 2)))
        self.assertTrue(
            celdas_zona.isdisjoint(
                {(celda.x, celda.y) for celda in warehouse.celdas_transitables()}
            ),
            "Los pickers deben iniciar en pasillos, no en la zona de despacho.",
        )
        self.assertEqual(
            _obtener_puntos_despacho(
                warehouse, grafo
            ),
            {"Z1": sorted(celdas_zona)},
        )

if __name__ == '__main__':
    unittest.main()