# python -m unittest tests.test_wave_manager -v

import unittest
 
from src.core.inventory import GestorInventario, Producto
from src.core.order import Orden, PENDIENTE, EN_WAVE, PREPARADO
from src.core.warehouse import Warehouse, Rack, Pasillo
from src.core.graph_builder import Graph, construir_grafo
from src.algorithms.wave_manager import generar_waves
 
CONFIG = {"max_pedidos": 10, "max_productos": 100, "peso_max_kg": 1000.0}
 
 
def crear_warehouse():
    """12 x 5, con un rack horizontal de 8x2 en (2..9, 2..3).
    Todo lo demas es pasillo de doble sentido:
 
        y=4  . . . . . . . . . . . .
        y=3  . . # # # # # # # # . .
        y=2  . . # # # # # # # # . .
        y=1  . . . . . . . . . . . .
        y=0  . . . . . . . . . . . .
             0 1 2 3 4 5 6 7 8 9 ...
 
    Un producto en (x, 2) se toma desde (x, 1) (abajo del rack) y uno en
    (x, 3) desde (x, 4) (arriba del rack). Para ir de un lado al otro hay
    que rodear el rack."""
    wh = Warehouse(12, 5)
    wh.add_rack(Rack("R1", x=2, y=2, ancho=8, alto=2))
    wh.rellenar_pasillos_implicitos()
    return wh
 
 
def inventario(*productos):
    """productos: (id, x, y, peso_kg)"""
    inv = GestorInventario()
    for pid, x, y, peso in productos:
        inv.agregar_producto(Producto(pid, pid, "R1", (x, y, 1), 100, peso))
    return inv
 
 
def ids(wave):
    return [o.orden_id for o in wave.pedidos]
 
 
class TestGenerarWaves(unittest.TestCase):
 
    def setUp(self):
        self.wh = crear_warehouse()
        self.grafo = construir_grafo(self.wh)   # generar_waves recibe el grafo ya armado
 
    def generar(self, pedidos, inv, config=CONFIG):
        return generar_waves(pedidos, inv, self.grafo, config)
 
    # ---------------- orden y prioridad ----------------
    def test_sin_pedidos(self):
        self.assertEqual(self.generar([], inventario()), [])
 
    def test_prioridad_de_mayor_a_menor(self):
        inv = inventario(("A", 5, 2, 1))  # mismo lugar: desempata la prioridad
        pedidos = [Orden("O1", 1, [("A", 1)]),
                   Orden("O5", 5, [("A", 1)]),
                   Orden("O3", 3, [("A", 1)])]
        waves = self.generar(pedidos, inv)
        self.assertEqual(len(waves), 1)
        self.assertEqual(ids(waves[0]), ["O5", "O3", "O1"])
 
    def test_la_prioridad_manda_sobre_la_cercania(self):
        # CERCA_PRIO1 esta pegado a la semilla pero tiene prioridad 1:
        # entra antes LEJOS_PRIO4, aunque este mas lejos
        inv = inventario(("A", 5, 2, 1), ("CERCA", 6, 2, 1), ("LEJOS", 2, 3, 1))
        pedidos = [Orden("SEMILLA", 5, [("A", 1)]),
                   Orden("CERCA_PRIO1", 1, [("CERCA", 1)]),
                   Orden("LEJOS_PRIO4", 4, [("LEJOS", 1)])]
        waves = self.generar(pedidos, inv, dict(CONFIG, max_pedidos=2))
        self.assertEqual(ids(waves[0]), ["SEMILLA", "LEJOS_PRIO4"])
 
    def test_primera_wave_se_arma_con_los_de_prioridad_5(self):
        """10 pedidos de prioridad 1 y 2 de prioridad 5 (lejos entre si y de
        los demas): la primera wave es la de los dos de prioridad 5."""
        pedidos, inv = self._diez_de_prio_1_y_dos_de_prio_5()
        waves = self.generar(pedidos, inv, dict(CONFIG, max_pedidos=2))
        self.assertCountEqual(ids(waves[0]), ["PRIO5_A", "PRIO5_B"])
 
    def test_la_primera_wave_completa_con_prioridad_1_despues_de_los_de_prioridad_5(self):
        pedidos, inv = self._diez_de_prio_1_y_dos_de_prio_5()
        waves = self.generar(pedidos, inv, dict(CONFIG, max_pedidos=5))
        primera = waves[0]
        self.assertEqual(len(primera), 5)
        self.assertCountEqual(ids(primera)[:2], ["PRIO5_A", "PRIO5_B"])
        self.assertTrue(all(p.prioridad == 1 for p in primera.pedidos[2:]))
        self.assertEqual(sum(len(w) for w in waves), 12)  # 5 + 5 + 2
 
    def _diez_de_prio_1_y_dos_de_prio_5(self):
        productos = [("P5A", 2, 2, 1), ("P5B", 9, 3, 1)]
        productos += [(f"P1_{i}", 5, 2, 1) for i in range(10)]
        pedidos = [Orden(f"PRIO1_{i}", 1, [(f"P1_{i}", 1)]) for i in range(10)]
        pedidos += [Orden("PRIO5_A", 5, [("P5A", 1)]),
                    Orden("PRIO5_B", 5, [("P5B", 1)])]
        return pedidos, inventario(*productos)
 
    # ---------------- cercania ----------------
    def test_a_igual_prioridad_la_cercania_se_mide_por_pasillos_y_no_en_linea_recta(self):
        # A (5,2) se toma desde abajo del rack, B (5,3) desde arriba:
        # estan pegados en linea recta (1) pero hay que rodear el rack (11 pasos).
        # C (8,2) esta mas lejos en linea recta (3) pero a 3 pasos por el pasillo.
        inv = inventario(("A", 5, 2, 1), ("B", 5, 3, 1), ("C", 8, 2, 1))
        pedidos = [Orden("SEMILLA", 5, [("A", 1)]),
                   Orden("OTRO_LADO", 4, [("B", 1)]),
                   Orden("MISMO_LADO", 4, [("C", 1)])]
        waves = self.generar(pedidos, inv, dict(CONFIG, max_pedidos=2))
        self.assertEqual(ids(waves[0]), ["SEMILLA", "MISMO_LADO"])
        self.assertEqual(ids(waves[1]), ["OTRO_LADO"])
 
    def test_respeta_el_sentido_de_los_pasillos(self):
        # Pasillo de un solo sentido: de (0,0) a (11,0) solo hacia E.
        wh = Warehouse(12, 3)
        wh.add_rack(Rack("R1", x=2, y=1, ancho=8, alto=2))
        wh.add_pasillo(Pasillo("ENTRADA", x=0, y=0, ancho=12, alto=1, sentido="E"))
        wh.rellenar_pasillos_implicitos()
        inv = inventario(("DER", 8, 1, 1), ("IZQ", 3, 1, 1), ("SEM", 5, 1, 1))
        pedidos = [Orden("SEMILLA", 5, [("SEM", 1)]),
                   Orden("IZQUIERDA", 4, [("IZQ", 1)]),
                   Orden("DERECHA", 4, [("DER", 1)])]
        # Desde x=5 solo se puede seguir hacia la derecha: DERECHA es la mas cercana
        waves = generar_waves(pedidos, inv, construir_grafo(wh), dict(CONFIG, max_pedidos=2))
        self.assertEqual(ids(waves[0]), ["SEMILLA", "DERECHA"])
 
    def test_solo_necesita_el_grafo(self):
        # un pasillo recto de 4 celdas; los productos estan al costado
        grafo = Graph()
        for x in range(4):
            grafo.add_node((x, 0))
        for x in range(3):
            grafo.add_edge((x, 0), (x + 1, 0))
            grafo.add_edge((x + 1, 0), (x, 0))
        inv = inventario(("A", 0, 1, 1), ("B", 3, 1, 1), ("C", 1, 1, 1))
        pedidos = [Orden("SEMILLA", 5, [("A", 1)]),
                   Orden("LEJOS", 4, [("B", 1)]),
                   Orden("CERCA", 4, [("C", 1)])]
        waves = generar_waves(pedidos, inv, grafo, dict(CONFIG, max_pedidos=2))
        self.assertEqual(ids(waves[0]), ["SEMILLA", "CERCA"])
        self.assertEqual(ids(waves[1]), ["LEJOS"])
 
    # ---------------- limites de la wave ----------------
    def test_cierra_la_wave_por_peso(self):
        inv = inventario(("A", 5, 2, 6))
        pedidos = [Orden("O1", 5, [("A", 1)]), Orden("O2", 4, [("A", 1)])]
        waves = self.generar(pedidos, inv, dict(CONFIG, peso_max_kg=10))
        self.assertEqual([ids(w) for w in waves], [["O1"], ["O2"]])
 
    def test_cierra_la_wave_por_cantidad_de_productos(self):
        inv = inventario(("A", 5, 2, 1))
        pedidos = [Orden("O1", 5, [("A", 3)]), Orden("O2", 4, [("A", 3)])]
        waves = self.generar(pedidos, inv, dict(CONFIG, max_productos=4))
        self.assertEqual(len(waves), 2)
 
    def test_un_pedido_que_no_entra_nunca_queda_pendiente(self):
        inv = inventario(("A", 5, 2, 1), ("PESADO", 5, 2, 500))
        enorme = Orden("ENORME", 5, [("PESADO", 1)])
        chico = Orden("CHICO", 1, [("A", 1)])
        waves = self.generar([enorme, chico], inv, dict(CONFIG, peso_max_kg=10))
        self.assertEqual([ids(w) for w in waves], [["CHICO"]])
        self.assertTrue(enorme.esta_pendiente())
 
    # ---------------- estados y entradas ----------------
    def test_cambia_el_estado_a_en_wave(self):
        inv = inventario(("A", 5, 2, 1))
        pedidos = [Orden("O1", 5, [("A", 1)]), Orden("O2", 4, [("A", 1)])]
        self.generar(pedidos, inv)
        self.assertTrue(all(p.estado == EN_WAVE for p in pedidos))
 
    def test_ignora_pedidos_no_pendientes_o_sin_items(self):
        inv = inventario(("A", 5, 2, 1))
        listo = Orden("LISTO", 5, [("A", 1)], estado=PREPARADO)
        vacio = Orden("VACIO", 5, [])
        ok = Orden("OK", 1, [("A", 1)])
        waves = self.generar([listo, vacio, ok], inv)
        self.assertEqual([ids(w) for w in waves], [["OK"]])
        self.assertEqual(listo.estado, PREPARADO)
        self.assertEqual(vacio.estado, PENDIENTE)
 
    def test_ids_de_wave_correlativos(self):
        inv = inventario(("A", 5, 2, 1))
        pedidos = [Orden(f"O{i}", 5, [("A", 1)]) for i in range(3)]
        waves = self.generar(pedidos, inv, dict(CONFIG, max_pedidos=1))
        self.assertEqual([w.id for w in waves], ["WAVE_001", "WAVE_002", "WAVE_003"])
 
    def test_cada_pedido_esta_en_una_sola_wave(self):
        inv = inventario(*[(f"P{i}", 2 + i % 8, 2 + i % 2, 1) for i in range(20)])
        pedidos = [Orden(f"O{i}", 1 + i % 5, [(f"P{i}", 1 + i % 3)]) for i in range(20)]
        waves = self.generar(pedidos, inv, dict(CONFIG, max_pedidos=4))
        asignados = [o for w in waves for o in ids(w)]
        self.assertEqual(sorted(asignados), sorted(p.orden_id for p in pedidos))
        self.assertTrue(all(len(w) <= 4 for w in waves))
 
    def test_producto_inexistente_propaga_keyerror(self):
        inv = inventario(("A", 5, 2, 1))
        with self.assertRaises(KeyError):
            self.generar([Orden("O1", 5, [("NADA", 1)])], inv)
 
 
if __name__ == "__main__":
    unittest.main()
 