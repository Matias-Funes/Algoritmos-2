import unittest

from src.core.cell import DESPACHO, PASILLO, PUERTA, RACK, VACIA, N
from src.core.warehouse import Pasillo, Puerta, Rack, Warehouse, ZonaDespacho


class TestWarehouse(unittest.TestCase):
    def setUp(self):
        self.wh = Warehouse(10, 10)

    def test_inicializacion(self):
        self.assertEqual(self.wh.ancho_x, 10)
        self.assertEqual(self.wh.largo_y, 10)
        self.assertEqual(len(self.wh.grid), 10)  # 10 filas
        self.assertEqual(len(self.wh.grid[0]), 10)  # 10 columnas
        self.assertEqual(self.wh.grid[0][0].tipo, VACIA)

    def test_add_rack_valido(self):
        r = Rack("R1", 2, 2, 2, 5)
        self.wh.add_rack(r)
        self.assertIn("R1", self.wh.racks)
        # Verificar que la grilla se actualizó
        self.assertEqual(self.wh.grid[2][2].tipo, RACK)
        self.assertEqual(self.wh.grid[2][2].ref_id, "R1")

    def test_add_rack_regla_lado_2(self):
        with self.assertRaises(ValueError):
            # Rack de 3x3 (ningún lado es 2)
            Rack("R_ERROR", 0, 0, 3, 3)

    def test_solapamiento(self):
        self.wh.add_rack(Rack("R1", 2, 2, 2, 5))
        with self.assertRaises(ValueError):
            # Intentar poner un pasillo encima del rack
            self.wh.add_pasillo(Pasillo("P1", 2, 2, 2, 5, N))

    def test_puerta_borde(self):
        # Puerta válida en el borde
        p1 = Puerta("PU1", "OUTBOUND", 0, 5)
        self.wh.add_puerta(p1)

        # Puerta inválida en el medio
        p2 = Puerta("PU2", "OUTBOUND", 5, 5)
        with self.assertRaises(ValueError):
            self.wh.add_puerta(p2)

    def test_rellenar_pasillos_implicitos(self):
        self.wh.add_rack(Rack("R1", 2, 2, 2, 2))
        # Al principio hay celdas VACIAS
        self.assertEqual(self.wh.grid[0][0].tipo, VACIA)

        self.wh.rellenar_pasillos_implicitos()

        # Ahora todas las vacías son PASILLO
        self.assertEqual(self.wh.grid[0][0].tipo, PASILLO)
        # Y el rack sigue siendo rack
        self.assertEqual(self.wh.grid[2][2].tipo, RACK)


if __name__ == "__main__":
    unittest.main()
