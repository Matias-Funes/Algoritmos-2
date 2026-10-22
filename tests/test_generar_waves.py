# Ejecutar desde la raíz del proyecto:  python -m unittest tests.test_generar_waves -v

import unittest
 
from src.algorithms.wave_manager import generar_waves
from src.core.inventory import GestorInventario, Producto
from src.core.order import EN_WAVE, PENDIENTE, Orden
 
 
def hacer_orden(orden_id, prioridad, items, estado=PENDIENTE):
    return Orden(orden_id, prioridad, items, estado)
 
 
def ids(wave):
    return [o.orden_id for o in wave.pedidos]
 
 
class TestGenerarWaves(unittest.TestCase):
    def setUp(self):
        self.inv = GestorInventario()
        self.inv.agregar_producto(Producto("P001", "Monitor", "R1", (3, 5, 1), 100, 6.5))
        self.inv.agregar_producto(Producto("P002", "Teclado", "R1", (3, 6, 1), 100, 1.2))
        self.inv.agregar_producto(Producto("P003", "Mouse", "R2", (8, 5, 1), 100, 0.3))
        # límites holgados; cada test ajusta el que quiere probar
        self.cfg = {"max_pedidos": 10, "max_productos": 100, "peso_max_kg": 1000.0}
 
    def generar(self, pedidos, **limites):
        cfg = {**self.cfg, **limites}
        return generar_waves(pedidos, self.inv, None, cfg)
 
    # ---------------------------------------------------------- casos simples
    def test_lista_vacia_devuelve_sin_waves(self):
        self.assertEqual(self.generar([]), [])
 
    def test_todos_entran_en_una_sola_wave(self):
        pedidos = [hacer_orden("A", 3, [("P003", 1)]), hacer_orden("B", 2, [("P002", 1)])]
        waves = self.generar(pedidos)
        self.assertEqual(len(waves), 1)
        self.assertEqual(len(waves[0]), 2)
 
    # ------------------------------------------------------------ filtrado
    def test_ignora_pedidos_que_no_estan_pendientes(self):
        pedidos = [
            hacer_orden("A", 5, [("P003", 1)]),
            hacer_orden("B", 5, [("P003", 1)], estado=EN_WAVE),
        ]
        waves = self.generar(pedidos)
        self.assertEqual([ids(w) for w in waves], [["A"]])
 
    def test_ignora_pedidos_sin_productos(self):
        pedidos = [hacer_orden("A", 5, []), hacer_orden("B", 4, [("P003", 1)])]
        waves = self.generar(pedidos)
        self.assertEqual([ids(w) for w in waves], [["B"]])
 
    # ----------------------------------------------------------- prioridad
    def test_ordena_de_mayor_a_menor_prioridad(self):
        pedidos = [
            hacer_orden("baja", 1, [("P003", 1)]),
            hacer_orden("alta", 5, [("P003", 1)]),
            hacer_orden("media", 3, [("P003", 1)]),
        ]
        waves = self.generar(pedidos)
        self.assertEqual(ids(waves[0]), ["alta", "media", "baja"])
 
    def test_empate_de_prioridad_respeta_el_orden_original(self):
        pedidos = [
            hacer_orden("X", 4, [("P003", 1)]),
            hacer_orden("Y", 4, [("P003", 1)]),
            hacer_orden("Z", 4, [("P003", 1)]),
        ]
        waves = self.generar(pedidos)
        self.assertEqual(ids(waves[0]), ["X", "Y", "Z"])
 
    def test_no_modifica_la_lista_original(self):
        pedidos = [hacer_orden("baja", 1, [("P003", 1)]), hacer_orden("alta", 5, [("P003", 1)])]
        self.generar(pedidos)
        self.assertEqual([p.orden_id for p in pedidos], ["baja", "alta"])
 
    # --------------------------------------------------------------- límites
    def test_respeta_max_pedidos(self):
        pedidos = [hacer_orden(f"P{i}", 3, [("P003", 1)]) for i in range(5)]
        waves = self.generar(pedidos, max_pedidos=2)
        self.assertEqual([len(w) for w in waves], [2, 2, 1])
 
    def test_respeta_max_productos(self):
        pedidos = [
            hacer_orden("A", 5, [("P003", 3)]),
            hacer_orden("B", 4, [("P003", 3)]),  # 3 + 3 = 6 > 5 -> wave nueva
        ]
        waves = self.generar(pedidos, max_productos=5)
        self.assertEqual([ids(w) for w in waves], [["A"], ["B"]])
 
    def test_respeta_peso_maximo(self):
        pedidos = [
            hacer_orden("A", 5, [("P001", 2)]),  # 13.0 kg
            hacer_orden("B", 4, [("P001", 1)]),  # 6.5 kg -> 19.5 kg, entra
            hacer_orden("C", 3, [("P001", 1)]),  # 6.5 kg -> 26.0 kg, no entra
        ]
        waves = self.generar(pedidos, peso_max_kg=20.0)
        self.assertEqual([ids(w) for w in waves], [["A", "B"], ["C"]])
        for w in waves:
            self.assertLessEqual(w.peso_total(self.inv), 20.0)
 
    def test_ninguna_wave_supera_sus_limites(self):
        pedidos = [hacer_orden(f"P{i}", (i % 5) + 1, [("P001", 1), ("P003", 2)]) for i in range(12)]
        waves = self.generar(pedidos, max_pedidos=3, max_productos=7, peso_max_kg=20.0)
        for w in waves:
            self.assertLessEqual(len(w), 3)
            self.assertLessEqual(w.cantidad_productos(), 7)
            self.assertLessEqual(w.peso_total(self.inv), 20.0)
 
    # ------------------------------------------- pedidos que no entran nunca
    def test_pedido_demasiado_grande_queda_pendiente(self):
        grande = hacer_orden("GRANDE", 5, [("P001", 9)])  # 58.5 kg > 20
        chico = hacer_orden("CHICO", 1, [("P003", 1)])
        waves = self.generar([grande, chico], peso_max_kg=20.0)
        self.assertEqual([ids(w) for w in waves], [["CHICO"]])
        self.assertEqual(grande.estado, PENDIENTE)
 
    def test_si_ninguno_entra_no_devuelve_waves_vacias(self):
        grande = hacer_orden("GRANDE", 5, [("P001", 9)])
        self.assertEqual(self.generar([grande], peso_max_kg=20.0), [])
 
    # --------------------------------------------------------- estados e ids
    def test_los_pedidos_asignados_pasan_a_en_wave(self):
        pedidos = [hacer_orden("A", 3, [("P003", 1)]), hacer_orden("B", 2, [("P003", 1)])]
        self.generar(pedidos)
        self.assertTrue(all(p.estado == EN_WAVE for p in pedidos))
 
    def test_cada_pedido_esta_en_una_sola_wave(self):
        pedidos = [hacer_orden(f"P{i}", (i % 5) + 1, [("P003", 1)]) for i in range(9)]
        waves = self.generar(pedidos, max_pedidos=4)
        todos = [i for w in waves for i in ids(w)]
        self.assertEqual(sorted(todos), sorted(p.orden_id for p in pedidos))
 
    def test_los_ids_de_las_waves_son_unicos(self):
        pedidos = [hacer_orden(f"P{i}", 3, [("P003", 1)]) for i in range(6)]
        waves = self.generar(pedidos, max_pedidos=2)
        wave_ids = [w.id for w in waves]
        self.assertEqual(len(wave_ids), len(set(wave_ids)))
        self.assertEqual(wave_ids, ["WAVE_001", "WAVE_002", "WAVE_003"])
 
 
if __name__ == "__main__":
    unittest.main()
 