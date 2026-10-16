"""
Tests de integración loader <-> Warehouse real.

A diferencia de test_scenario_loader.py (que corre siempre, contra
stub o real según USAR_STUB), este archivo SIEMPRE usa el Warehouse
REAL de src/core/ y se saltea si todavía no existe.

Objetivo: el día que Juli mergee cell.py y warehouse.py, estos tests
se activan solos y verifican que el loader respeta el contrato.
"""

import unittest
from pathlib import Path

# ------------------------------------------------------------------
# Detectar si el Warehouse real existe. Si no, skipear TODO el módulo.
# ------------------------------------------------------------------

try:
    from src.core.cell import Pasillo, Puerta, Rack, ZonaDespacho
    from src.core.warehouse import Warehouse

    WAREHOUSE_REAL_DISPONIBLE = True
    MOTIVO_SKIP = None
except ImportError as e:
    WAREHOUSE_REAL_DISPONIBLE = False
    MOTIVO_SKIP = "Warehouse real no disponible todavía: %s" % e

from src.io.scenario_loader import cargar_escenario

RUTA_BASICO = "data/scenarios/escenario_basico.json"
RUTA_GRANDE = "data/scenarios/escenario_grande.json"


@unittest.skipUnless(WAREHOUSE_REAL_DISPONIBLE, MOTIVO_SKIP or "")
class TestIntegracionWarehouseReal(unittest.TestCase):
    """Verifica que el loader produce instancias del Warehouse real."""

    def setUp(self):
        if not Path(RUTA_BASICO).exists():
            self.skipTest("No existe %s" % RUTA_BASICO)
        self.wh, self.productos, self.pedidos, self.pickers, self.config = (
            cargar_escenario(RUTA_BASICO)
        )

    # -- Tipo de las instancias -------------------------------------

    def test_warehouse_es_instancia_real(self):
        self.assertIsInstance(self.wh, Warehouse)

    def test_racks_son_instancias_reales(self):
        for rid, rack in self.wh.racks.items():
            self.assertIsInstance(
                rack,
                Rack,
                "rack %s no es instancia de Rack real" % rid,
            )

    def test_pasillos_son_instancias_reales(self):
        for pid, pas in self.wh.pasillos.items():
            self.assertIsInstance(
                pas,
                Pasillo,
                "pasillo %s no es instancia de Pasillo real" % pid,
            )

    def test_puertas_son_instancias_reales(self):
        for pid, p in self.wh.puertas.items():
            self.assertIsInstance(
                p,
                Puerta,
                "puerta %s no es instancia de Puerta real" % pid,
            )

    def test_zonas_son_instancias_reales(self):
        for zid, z in self.wh.zonas.items():
            self.assertIsInstance(
                z,
                ZonaDespacho,
                "zona %s no es instancia de ZonaDespacho real" % zid,
            )

    # -- Contrato del Warehouse -------------------------------------

    def test_warehouse_tiene_grid(self):
        self.assertTrue(hasattr(self.wh, "grid"))
        self.assertEqual(len(self.wh.grid), self.wh.largo_y)
        for fila in self.wh.grid:
            self.assertEqual(len(fila), self.wh.ancho_x)

    def test_racks_respetan_regla_lado_2(self):
        """El contrato dice: un rack debe tener ancho==2 o alto==2."""
        for rid, rack in self.wh.racks.items():
            ok = (rack.ancho == 2) or (rack.alto == 2)
            self.assertTrue(
                ok,
                "rack %s viola la regla: ancho=%d, alto=%d"
                % (rid, rack.ancho, rack.alto),
            )

    def test_puertas_sobre_el_borde(self):
        """Toda puerta tiene x==0 o x==ancho_x-1 o y==0 o y==largo_y-1."""
        ax, ay = self.wh.ancho_x, self.wh.largo_y
        for pid, p in self.wh.puertas.items():
            en_borde = (p.x == 0) or (p.x == ax - 1) or (p.y == 0) or (p.y == ay - 1)
            self.assertTrue(
                en_borde,
                "puerta %s en (%d,%d) no está sobre el borde" % (pid, p.x, p.y),
            )

    def test_pasillos_implicitos_rellenados(self):
        """
        Después de cargar, ninguna celda del grid debe seguir VACIA.
        Todas las que no son rack/puerta/zona deben ser PASILLO AMBOS.
        """
        from src.core.cell import VACIA

        vacias = []
        for y in range(self.wh.largo_y):
            for x in range(self.wh.ancho_x):
                if self.wh.grid[y][x].tipo == VACIA:
                    vacias.append((x, y))

        self.assertEqual(
            vacias,
            [],
            "quedaron %d celdas VACIAS sin rellenar: %s" % (len(vacias), vacias[:10]),
        )


@unittest.skipUnless(WAREHOUSE_REAL_DISPONIBLE, MOTIVO_SKIP or "")
class TestIntegracionEscenarioGrande(unittest.TestCase):
    """Mismo chequeo básico pero sobre el escenario grande."""

    def setUp(self):
        if not Path(RUTA_GRANDE).exists():
            self.skipTest("No existe %s" % RUTA_GRANDE)
        self.wh, self.productos, self.pedidos, self.pickers, self.config = (
            cargar_escenario(RUTA_GRANDE)
        )

    def test_carga_sin_errores(self):
        self.assertGreater(len(self.wh.racks), 0)
        self.assertGreater(len(self.wh.pasillos), 0)
        self.assertGreater(len(self.productos), 0)

    def test_no_hay_celdas_vacias(self):
        from src.core.cell import VACIA

        for y in range(self.wh.largo_y):
            for x in range(self.wh.ancho_x):
                self.assertNotEqual(
                    self.wh.grid[y][x].tipo,
                    VACIA,
                    "celda (%d,%d) quedó VACIA" % (x, y),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
