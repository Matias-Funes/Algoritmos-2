"""
test_warehouse.py
=================
Pruebas unitarias para src/core/warehouse.py

Ejecutar:
    python -m unittest tests.test_warehouse -v
o, desde la raíz:
    python -m unittest discover -s tests -v
"""

import math
import unittest

from src.core.warehouse import (
    Position,
    Node,
    NodeType,
    WarehouseGraph,
)


# ---------------------------------------------------------------------------
# 1. Position
# ---------------------------------------------------------------------------
class TestPosition(unittest.TestCase):

    def test_creacion_y_atributos(self):
        p = Position(1.5, 2.5, 3.5)
        self.assertEqual(p.x, 1.5)
        self.assertEqual(p.y, 2.5)
        self.assertEqual(p.z, 3.5)

    def test_z_por_defecto_es_cero(self):
        p = Position(1, 2)
        self.assertEqual(p.z, 0.0)

    def test_igualdad(self):
        self.assertEqual(Position(1, 2, 3), Position(1, 2, 3))
        self.assertNotEqual(Position(1, 2, 3), Position(1, 2, 4))

    def test_hash_consistente_con_igualdad(self):
        """Dos posiciones iguales deben tener el mismo hash."""
        p1 = Position(1, 2, 3)
        p2 = Position(1, 2, 3)
        self.assertEqual(hash(p1), hash(p2))

    def test_usable_como_clave_de_dict(self):
        d = {Position(0, 0, 0): "origen", Position(1, 1, 1): "diagonal"}
        self.assertEqual(d[Position(0, 0, 0)], "origen")
        self.assertEqual(d[Position(1, 1, 1)], "diagonal")

    def test_distancia_euclidea(self):
        a = Position(0, 0, 0)
        b = Position(3, 4, 0)
        self.assertAlmostEqual(a.distance_to(b), 5.0, places=9)

    def test_distancia_euclidea_3d(self):
        a = Position(0, 0, 0)
        b = Position(1, 1, 1)
        self.assertAlmostEqual(a.distance_to(b), math.sqrt(3), places=9)

    def test_distancia_a_si_mismo_es_cero(self):
        p = Position(7, 8, 9)
        self.assertEqual(p.distance_to(p), 0.0)

    def test_distancia_manhattan(self):
        a = Position(0, 0, 0)
        b = Position(3, 4, 5)
        self.assertEqual(a.manhattan_to(b), 12)

    def test_as_tuple(self):
        self.assertEqual(Position(1, 2, 3).as_tuple(), (1, 2, 3))


# ---------------------------------------------------------------------------
# 2. Node
# ---------------------------------------------------------------------------
class TestNode(unittest.TestCase):

    def test_creacion_basica(self):
        n = Node(1, Position(0, 0, 0))
        self.assertEqual(n.node_id, 1)
        self.assertEqual(n.node_type, NodeType.INTERSECTION)
        self.assertEqual(n.metadata, {})

    def test_igualdad_por_id(self):
        n1 = Node(1, Position(0, 0, 0))
        n2 = Node(1, Position(99, 99, 99))   # misma id, distinta pos
        self.assertEqual(n1, n2)

    def test_desigualdad_por_id(self):
        n1 = Node(1, Position(0, 0, 0))
        n2 = Node(2, Position(0, 0, 0))
        self.assertNotEqual(n1, n2)

    def test_hash_por_id(self):
        n1 = Node(1, Position(0, 0, 0))
        n2 = Node(1, Position(5, 5, 5))
        self.assertEqual(hash(n1), hash(n2))

    def test_metadata_por_defecto_no_compartido(self):
        """Cada nodo debe tener su propio dict de metadata (no aliasing)."""
        n1 = Node(1, Position(0, 0, 0))
        n2 = Node(2, Position(0, 0, 0))
        n1.metadata["x"] = 1
        self.assertNotIn("x", n2.metadata)


# ---------------------------------------------------------------------------
# 3. WarehouseGraph — nodos
# ---------------------------------------------------------------------------
class TestWarehouseGraphNodes(unittest.TestCase):

    def setUp(self):
        self.g = WarehouseGraph(name="Test")

    def test_grafo_vacio(self):
        self.assertEqual(self.g.node_count(), 0)
        self.assertEqual(self.g.edge_count(), 0)
        self.assertEqual(len(self.g), 0)

    def test_add_node_basico(self):
        n = self.g.add_node(1, Position(0, 0, 0))
        self.assertEqual(n.node_id, 1)
        self.assertTrue(self.g.has_node(1))
        self.assertEqual(self.g.node_count(), 1)

    def test_add_node_duplicado_lanza_error(self):
        self.g.add_node(1, Position(0, 0, 0))
        with self.assertRaises(ValueError):
            self.g.add_node(1, Position(1, 1, 1))

    def test_add_node_con_metadata(self):
        n = self.g.add_node(1, Position(0, 0, 0), NodeType.RACK, rack_id="R1")
        self.assertEqual(n.metadata["rack_id"], "R1")
        self.assertEqual(n.node_type, NodeType.RACK)

    def test_get_node(self):
        self.g.add_node(7, Position(1, 2, 3), NodeType.DISPATCH)
        n = self.g.get_node(7)
        self.assertEqual(n.node_id, 7)
        self.assertEqual(n.position, Position(1, 2, 3))

    def test_get_node_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            self.g.get_node(99)

    def test_remove_node_simple(self):
        self.g.add_node(1, Position(0, 0, 0))
        self.g.remove_node(1)
        self.assertFalse(self.g.has_node(1))
        self.assertEqual(self.g.node_count(), 0)

    def test_remove_node_con_aristas(self):
        self.g.add_node(1, Position(0, 0, 0))
        self.g.add_node(2, Position(1, 0, 0))
        self.g.add_node(3, Position(2, 0, 0))
        self.g.add_edge(1, 2)
        self.g.add_edge(2, 3)
        self.assertEqual(self.g.edge_count(), 2)

        self.g.remove_node(2)
        self.assertEqual(self.g.node_count(), 2)
        self.assertEqual(self.g.edge_count(), 0)
        # Los vecinos ya no deben conocer a 2
        self.assertNotIn(2, self.g.get_neighbors(1))
        self.assertNotIn(2, self.g.get_neighbors(3))

    def test_remove_node_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            self.g.remove_node(99)

    def test_contains_dunder(self):
        self.g.add_node(5, Position(0, 0, 0))
        self.assertIn(5, self.g)
        self.assertNotIn(6, self.g)

    def test_nodes_iterator(self):
        self.g.add_node(1, Position(0, 0, 0))
        self.g.add_node(2, Position(1, 1, 1))
        ids = sorted(n.node_id for n in self.g.nodes())
        self.assertEqual(ids, [1, 2])

    def test_nodes_by_type(self):
        self.g.add_node(1, Position(0, 0, 0), NodeType.RACK)
        self.g.add_node(2, Position(1, 0, 0), NodeType.RACK)
        self.g.add_node(3, Position(2, 0, 0), NodeType.DISPATCH)
        racks = self.g.nodes_by_type(NodeType.RACK)
        self.assertEqual(len(racks), 2)
        self.assertEqual(sorted(r.node_id for r in racks), [1, 2])

    def test_get_dispatch_node(self):
        self.g.add_node(1, Position(0, 0, 0), NodeType.DISPATCH)
        self.g.add_node(2, Position(1, 0, 0), NodeType.RACK)
        d = self.g.get_dispatch_node()
        self.assertEqual(d.node_id, 1)

    def test_get_dispatch_node_sin_dispatch_lanza_error(self):
        with self.assertRaises(LookupError):
            self.g.get_dispatch_node()


# ---------------------------------------------------------------------------
# 4. WarehouseGraph — aristas
# ---------------------------------------------------------------------------
class TestWarehouseGraphEdges(unittest.TestCase):

    def setUp(self):
        self.g = WarehouseGraph()
        self.g.add_node(1, Position(0, 0, 0))
        self.g.add_node(2, Position(3, 4, 0))   # dist = 5
        self.g.add_node(3, Position(6, 8, 0))   # dist(2,3) = 5

    def test_add_edge_peso_automatico(self):
        w = self.g.add_edge(1, 2)
        self.assertAlmostEqual(w, 5.0, places=9)
        self.assertEqual(self.g.edge_count(), 1)

    def test_add_edge_peso_explicito(self):
        w = self.g.add_edge(1, 2, weight=10.0)
        self.assertEqual(w, 10.0)
        self.assertEqual(self.g.get_weight(1, 2), 10.0)

    def test_arista_es_bidireccional_por_defecto(self):
        self.g.add_edge(1, 2, weight=7.0)
        self.assertTrue(self.g.has_edge(1, 2))
        self.assertTrue(self.g.has_edge(2, 1))
        self.assertEqual(self.g.get_weight(2, 1), 7.0)

    def test_arista_dirigida(self):
        self.g.add_edge(1, 2, weight=7.0, bidirectional=False)
        self.assertTrue(self.g.has_edge(1, 2))
        self.assertFalse(self.g.has_edge(2, 1))

    def test_add_edge_auto_lazo_lanza_error(self):
        with self.assertRaises(ValueError):
            self.g.add_edge(1, 1)

    def test_add_edge_nodo_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            self.g.add_edge(1, 99)

    def test_add_edge_peso_invalido_lanza_error(self):
        with self.assertRaises(ValueError):
            self.g.add_edge(1, 2, weight=0)
        with self.assertRaises(ValueError):
            self.g.add_edge(1, 2, weight=-1.5)

    def test_reemplazo_de_peso_no_duplica_arista(self):
        self.g.add_edge(1, 2, weight=5.0)
        self.g.add_edge(1, 2, weight=8.0)
        self.assertEqual(self.g.edge_count(), 1)
        self.assertEqual(self.g.get_weight(1, 2), 8.0)

    def test_remove_edge(self):
        self.g.add_edge(1, 2)
        self.g.remove_edge(1, 2)
        self.assertFalse(self.g.has_edge(1, 2))
        self.assertFalse(self.g.has_edge(2, 1))
        self.assertEqual(self.g.edge_count(), 0)

    def test_get_neighbors(self):
        self.g.add_edge(1, 2, weight=5.0)
        self.g.add_edge(1, 3, weight=10.0)
        n = self.g.get_neighbors(1)
        self.assertEqual(n, {2: 5.0, 3: 10.0})

    def test_edges_iterator_sin_duplicados(self):
        self.g.add_edge(1, 2)
        self.g.add_edge(2, 3)
        edges = list(self.g.edges())
        self.assertEqual(len(edges), 2)
        # Solo debe aparecer u < v
        for (u, v, _w) in edges:
            self.assertLess(u, v)


# ---------------------------------------------------------------------------
# 5. Búsqueda del nodo más cercano
# ---------------------------------------------------------------------------
class TestFindNearestNode(unittest.TestCase):

    def setUp(self):
        self.g = WarehouseGraph()
        self.g.add_node(1, Position(0, 0, 0), NodeType.RACK)
        self.g.add_node(2, Position(10, 10, 0), NodeType.RACK)
        self.g.add_node(3, Position(5, 5, 0), NodeType.DISPATCH)

    def test_encuentra_mas_cercano(self):
        n = self.g.find_nearest_node(Position(1, 1, 0))
        self.assertEqual(n.node_id, 1)

    def test_encuentra_mas_cercano_con_filtro_de_tipo(self):
        n = self.g.find_nearest_node(Position(1, 1, 0), NodeType.DISPATCH)
        self.assertEqual(n.node_id, 3)

    def test_devuelve_none_si_no_hay_candidatos(self):
        n = self.g.find_nearest_node(Position(0, 0, 0), NodeType.DOOR)
        self.assertIsNone(n)

    def test_grafo_vacio_devuelve_none(self):
        g = WarehouseGraph()
        self.assertIsNone(g.find_nearest_node(Position(0, 0, 0)))


# ---------------------------------------------------------------------------
# 6. Serialización
# ---------------------------------------------------------------------------
class TestWarehouseSerialization(unittest.TestCase):

    def _build_graph(self):
        g = WarehouseGraph(name="SerTest")
        g.add_node(0, Position(0, 0, 0), NodeType.DISPATCH, zone_name="A")
        g.add_node(1, Position(5, 0, 0), NodeType.RACK, rack_id="R1")
        g.add_node(2, Position(5, 5, 0), NodeType.RACK, rack_id="R2")
        g.add_edge(0, 1, weight=5.0)
        g.add_edge(1, 2, weight=5.0)
        return g

    def test_to_dict_estructura(self):
        g = self._build_graph()
        d = g.to_dict()
        self.assertEqual(d["name"], "SerTest")
        self.assertEqual(len(d["nodes"]), 3)
        self.assertEqual(len(d["edges"]), 2)

    def test_round_trip(self):
        g1 = self._build_graph()
        d = g1.to_dict()
        g2 = WarehouseGraph.from_dict(d)

        self.assertEqual(g1.name, g2.name)
        self.assertEqual(g1.node_count(), g2.node_count())
        self.assertEqual(g1.edge_count(), g2.edge_count())

        # Verificar nodos
        for nid in [0, 1, 2]:
            n1 = g1.get_node(nid)
            n2 = g2.get_node(nid)
            self.assertEqual(n1.position, n2.position)
            self.assertEqual(n1.node_type, n2.node_type)
            self.assertEqual(n1.metadata, n2.metadata)

        # Verificar pesos
        self.assertAlmostEqual(g1.get_weight(0, 1), g2.get_weight(0, 1))
        self.assertAlmostEqual(g1.get_weight(1, 2), g2.get_weight(1, 2))


# ---------------------------------------------------------------------------
# 7. Propiedades de complejidad (sanity checks de escala)
# ---------------------------------------------------------------------------
class TestEscalabilidad(unittest.TestCase):

    def test_add_nodes_en_linea(self):
        """Insertar V nodos en cadena debe completarse sin problemas."""
        g = WarehouseGraph()
        N = 500
        for i in range(N):
            g.add_node(i, Position(i, 0, 0))
        for i in range(N - 1):
            g.add_edge(i, i + 1)
        self.assertEqual(g.node_count(), N)
        self.assertEqual(g.edge_count(), N - 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)