import unittest
from src.core.cell import VACIA, PASILLO
from src.core.warehouse import Warehouse, Rack, Puerta

class TestWarehouse(unittest.TestCase):
    def setUp(self):
        # Este método se ejecuta antes de CADA test.
        self.wh = Warehouse(20, 20)

    def test_dimensiones_correctas(self):
        self.assertEqual(self.wh.ancho_x, 20)
        self.assertEqual(len(self.wh.grid[0]), 20)

    def test_agregar_rack_valido(self):
        rack = Rack("R1", x=2, y=2, ancho=2, alto=5)
        self.wh.add_rack(rack)
        # Verificamos que la celda (2,2) ahora sea del R1
        self.assertEqual(self.wh.grid[2][2].ref_id, "R1")

    def test_rack_lado_incorrecto_lanza_error(self):
        # Metemos la creación del Rack ADENTRO del bloque assertRaises
        with self.assertRaises(ValueError):
            rack = Rack("R_malo", x=2, y=2, ancho=3, alto=3)
            self.wh.add_rack(rack)

    def test_solapamiento_lanza_error(self):
        rack1 = Rack("R1", x=2, y=2, ancho=2, alto=5)
        rack2 = Rack("R2", x=3, y=3, ancho=2, alto=5) # Se pisan
        self.wh.add_rack(rack1)
        with self.assertRaises(ValueError):
            self.wh.add_rack(rack2)

    def test_puerta_fuera_de_borde_lanza_error(self):
        puerta = Puerta("P1", "OUTBOUND", x=5, y=5) # Está en el medio
        with self.assertRaises(ValueError):
            self.wh.add_puerta(puerta)

    def test_rellenar_pasillos_implicitos(self):
        # La celda (0,0) arranca vacía
        self.assertEqual(self.wh.grid[0][0].tipo, VACIA)
        self.wh.rellenar_pasillos_implicitos()
        # Después de rellenar, debe ser un pasillo
        self.assertEqual(self.wh.grid[0][0].tipo, PASILLO)

if __name__ == '__main__':
    unittest.main()