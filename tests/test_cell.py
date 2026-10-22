import unittest

from src.core.cell import (
    AMBOS,
    DESPACHO,
    PASILLO,
    PUERTA,
    RACK,
    VACIA,
    Cell,
    E,
    N,
    O,
    S,
)


class TestCell(unittest.TestCase):
    def test_inicializacion(self):
        c = Cell(3, 5)
        self.assertEqual(c.x, 3)
        self.assertEqual(c.y, 5)
        self.assertEqual(c.tipo, VACIA)
        self.assertEqual(c.sentido, AMBOS)
        self.assertIsNone(c.ref_id)

    def test_es_transitable(self):
        c = Cell(0, 0)
        self.assertFalse(c.es_transitable())  # VACIA no es transitable

        c.tipo = PASILLO
        self.assertTrue(c.es_transitable())

        c.tipo = RACK
        self.assertFalse(c.es_transitable())

    def test_es_adyacente_a_transitable(self):
        c = Cell(0, 0)
        self.assertFalse(c.es_adyacente_a_transitable())  # VACIA no es adyacente

        c.tipo = RACK
        self.assertTrue(c.es_adyacente_a_transitable())

        c.tipo = PUERTA
        self.assertTrue(c.es_adyacente_a_transitable())

        c.tipo = DESPACHO
        self.assertTrue(c.es_adyacente_a_transitable())

    def test_repr(self):
        c = Cell(1, 2)
        c.tipo = PASILLO
        c.sentido = N
        self.assertEqual(repr(c), "Cell(1,2,tipo=PASILLO,sentido=N)")

    def test_sentidos_validos(self):
        c = Cell(0, 0)
        for sentido in (N, S, E, O, AMBOS):
            c.sentido = sentido
            self.assertEqual(c.sentido, sentido)


if __name__ == "__main__":
    unittest.main()
