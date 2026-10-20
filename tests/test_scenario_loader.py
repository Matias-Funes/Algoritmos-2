"""
Tests para src/io/scenario_loader.py

Mientras Integrante A no entregue el Warehouse real, los tests
importan el stub. Cuando A entregue, el import real reemplaza al
stub automáticamente y los tests siguen corriendo.
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.io._deps import USANDO_STUB, Pasillo, Puerta, Rack, Warehouse, ZonaDespacho
from src.io.scenario_loader import cargar_escenario

RUTA_BASICO = "data/scenarios/escenario_basico.json"


# ---------------------------------------------------------------------------
# Carga exitosa
# ---------------------------------------------------------------------------


class TestCargaBasica(unittest.TestCase):

    def setUp(self):
        if not Path(RUTA_BASICO).exists():
            self.skipTest("No existe %s" % RUTA_BASICO)
        self.wh, self.productos, self.pedidos, self.pickers, self.config = (
            cargar_escenario(RUTA_BASICO)
        )

    def test_devuelve_un_warehouse(self):
        self.assertIsInstance(self.wh, Warehouse)

    def test_dimensiones_positivas(self):
        self.assertGreater(self.wh.ancho_x, 0)
        self.assertGreater(self.wh.largo_y, 0)

    def test_hay_racks(self):
        self.assertGreater(len(self.wh.racks), 0)

    def test_hay_pasillos(self):
        self.assertGreater(len(self.wh.pasillos), 0)

    def test_hay_puertas(self):
        self.assertGreater(len(self.wh.puertas), 0)

    def test_hay_zonas(self):
        self.assertGreater(len(self.wh.zonas), 0)

    def test_productos_crudos(self):
        self.assertGreater(len(self.productos), 0)
        for p in self.productos:
            self.assertIsInstance(p, dict)
            self.assertIn("id", p)
            self.assertIn("rack_id", p)
            self.assertIn("peso_kg", p)

    def test_pedidos_crudos(self):
        self.assertGreater(len(self.pedidos), 0)
        for p in self.pedidos:
            self.assertIsInstance(p, dict)
            self.assertIn("id", p)
            self.assertIn("items", p)
            self.assertIn("prioridad", p)

    def test_pickers_crudos(self):
        self.assertGreater(len(self.pickers), 0)
        for p in self.pickers:
            self.assertIsInstance(p, dict)
            self.assertIn("id", p)
            self.assertIn("capacidad_carga_kg", p)

    def test_config_tiene_campos(self):
        self.assertIn("wave_max_pedidos", self.config)
        self.assertIn("wave_max_productos", self.config)


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------


class TestErrores(unittest.TestCase):

    def _escribir(self, contenido):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write(contenido)
        tmp.close()
        return tmp.name

    def test_archivo_no_existe(self):
        with self.assertRaises(FileNotFoundError):
            cargar_escenario("no/existe.json")

    def test_json_malformado(self):
        ruta = self._escribir("{ no es json")
        with self.assertRaises(ValueError):
            cargar_escenario(ruta)

    def test_falta_seccion(self):
        ruta = self._escribir('{"warehouse": {}}')
        with self.assertRaises(ValueError) as ctx:
            cargar_escenario(ruta)
        self.assertIn("pickers", str(ctx.exception))

    def test_falta_campo_en_warehouse(self):
        data = {
            "warehouse": {"dimensiones": {"ancho_x": 10, "largo_y": 10}},
            "pickers": [],
            "productos": [],
            "pedidos": [],
            "configuracion": {},
        }
        ruta = self._escribir(json.dumps(data))
        with self.assertRaises(ValueError) as ctx:
            cargar_escenario(ruta)
        self.assertIn("puertas", str(ctx.exception))

    def test_dimensiones_invalidas(self):
        data = {
            "warehouse": {
                "dimensiones": {"ancho_x": 0, "largo_y": 5},
                "puertas": [],
                "zonas_despacho": [],
                "racks": [],
                "pasillos": [],
            },
            "pickers": [],
            "productos": [],
            "pedidos": [],
            "configuracion": {},
        }
        ruta = self._escribir(json.dumps(data))
        with self.assertRaises(ValueError):
            cargar_escenario(ruta)


if __name__ == "__main__":
    print("Usando stub:", USANDO_STUB)
    unittest.main(verbosity=2)
