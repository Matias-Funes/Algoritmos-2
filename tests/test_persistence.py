import json
import tempfile
import unittest
from pathlib import Path

from main import _crear_pedidos, _crear_pickers, _crear_productos
from src.io.persistence import crear_datos_escenario, guardar_escenario
from src.io.scenario_loader import cargar_escenario


class TestPersistenciaEscenario(unittest.TestCase):
    def setUp(self):
        ruta = Path("data/scenarios/escenario_basico.json")
        if not ruta.is_file():
            self.skipTest("No existe el escenario básico.")
        (
            self.warehouse,
            self.productos_raw,
            self.pedidos_raw,
            self.pickers_raw,
            self.configuracion,
        ) = cargar_escenario(str(ruta))

    def test_round_trip_de_datos_crudos_conserva_el_esquema_del_escenario(self):
        original = crear_datos_escenario(
            self.warehouse,
            self.productos_raw,
            self.pedidos_raw,
            self.pickers_raw,
            self.configuracion,
        )
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "nested" / "escenario.json"
            guardar_escenario(
                ruta,
                self.warehouse,
                self.productos_raw,
                self.pedidos_raw,
                self.pickers_raw,
                self.configuracion,
            )
            contenido_guardado = json.loads(ruta.read_text(encoding="utf-8"))
            warehouse, productos, pedidos, pickers, config = cargar_escenario(
                str(ruta)
            )

        self.assertEqual(contenido_guardado, original)
        self.assertEqual(warehouse.ancho_x, self.warehouse.ancho_x)
        self.assertEqual(warehouse.largo_y, self.warehouse.largo_y)
        self.assertEqual(len(warehouse.puertas), len(self.warehouse.puertas))
        self.assertEqual(len(warehouse.zonas), len(self.warehouse.zonas))
        self.assertEqual(productos, self.productos_raw)
        self.assertEqual(pedidos, self.pedidos_raw)
        self.assertEqual(pickers, self.pickers_raw)
        self.assertEqual(config, self.configuracion)

    def test_modelos_de_dominio_se_convierten_al_formato_del_loader(self):
        productos = _crear_productos(self.productos_raw)
        pedidos = _crear_pedidos(self.pedidos_raw)
        pickers = _crear_pickers(self.pickers_raw)

        datos = crear_datos_escenario(
            self.warehouse,
            productos,
            pedidos,
            pickers,
            self.configuracion,
        )
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "escenario-modelos.json"
            ruta.write_text(json.dumps(datos), encoding="utf-8")
            _, productos_cargados, pedidos_cargados, pickers_cargados, _ = (
                cargar_escenario(str(ruta))
            )

        self.assertEqual(
            productos_cargados[0]["ubicacion"],
            {
                "x": productos[0].ubicacion[0],
                "y": productos[0].ubicacion[1],
                "z": productos[0].ubicacion[2],
            },
        )
        self.assertEqual(
            pedidos_cargados[0]["id"], pedidos[0].orden_id
        )
        self.assertEqual(
            pedidos_cargados[0]["items"][0],
            {
                "producto_id": pedidos[0].items[0][0],
                "cantidad": pedidos[0].items[0][1],
            },
        )
        self.assertEqual(
            pickers_cargados[0]["posicion_inicial"],
            self.pickers_raw[0]["posicion_inicial"],
        )

    def test_no_modifica_los_registros_crudos_recibidos(self):
        productos_originales = json.loads(json.dumps(self.productos_raw))
        pedidos_originales = json.loads(json.dumps(self.pedidos_raw))
        pickers_originales = json.loads(json.dumps(self.pickers_raw))

        crear_datos_escenario(
            self.warehouse,
            self.productos_raw,
            self.pedidos_raw,
            self.pickers_raw,
            self.configuracion,
        )

        self.assertEqual(self.productos_raw, productos_originales)
        self.assertEqual(self.pedidos_raw, pedidos_originales)
        self.assertEqual(self.pickers_raw, pickers_originales)

    def test_guardar_escenario_no_incluye_estado_runtime_de_los_pickers(self):
        picker = _crear_pickers(self.pickers_raw)[0]
        picker.mover_a((picker.posicion_inicial[0] + 1, picker.posicion_inicial[1]))
        picker_raw_con_estado = picker.to_dict()

        datos = crear_datos_escenario(
            self.warehouse,
            self.productos_raw,
            self.pedidos_raw,
            [picker_raw_con_estado],
            self.configuracion,
        )

        self.assertEqual(
            datos["pickers"][0]["posicion_inicial"],
            {
                "x": picker.posicion_inicial[0],
                "y": picker.posicion_inicial[1],
            },
        )
        self.assertNotIn("posicion_actual", datos["pickers"][0])
        self.assertNotIn("carga_actual_kg", datos["pickers"][0])
        self.assertNotIn("items_transportados", datos["pickers"][0])


if __name__ == "__main__":
    unittest.main()
