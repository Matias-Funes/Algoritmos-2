import unittest

from main import _crear_waves
from src.algorithms.pathfinding import CacheDistancias
from src.core.graph_builder import construir_grafo
from src.core.inventory import GestorInventario, Producto
from src.core.order import Orden
from src.core.picker import Picker
from src.core.warehouse import Warehouse
from src.simulation.simulation import Simulation


class TestViajesDinamicos(unittest.TestCase):
    def crear_simulacion(self, stock=5, cantidad=5):
        warehouse = Warehouse(8, 6)
        warehouse.rellenar_pasillos_implicitos()
        producto = Producto("P001", "Producto", "R1", (6, 4, 1), stock, 2.0)
        picker = Picker("PK_01", (0, 0), 4.0)
        pedido = Orden("PED_01", 1, [("P001", cantidad)])
        grafo = construir_grafo(warehouse)
        simulacion = Simulation(
            warehouse=warehouse,
            pickers=[picker],
            productos=[producto],
            asignaciones={picker.id: [pedido]},
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={"ZONA_A": [(0, 0)]},
        )
        return simulacion, picker, producto

    def ejecutar_hasta_terminar(self, simulacion):
        for _ in range(500):
            if not simulacion.avanzar_paso():
                return
        self.fail("La simulación no terminó en el límite de pasos.")

    def test_wave_puede_superar_capacidad_y_se_completa_en_varios_viajes(self):
        inventario = GestorInventario()
        inventario.agregar_producto(
            Producto("P001", "Producto", "R1", (1, 1, 1), 5, 2.0)
        )
        picker = Picker("PK_01", (0, 0), 4.0)
        pedido = Orden("PED_01", 1, [("P001", 5)])

        waves, _, waves_por_picker = _crear_waves(
            [pedido],
            [picker],
            inventario,
            {"wave_max_pedidos": 3, "wave_max_productos": 10},
        )

        self.assertEqual(len(waves), 1)
        self.assertEqual(waves_por_picker[picker.id], waves)
        self.assertGreater(waves[0].peso_total(inventario), picker.capacidad_carga_kg)

        simulacion, picker, producto = self.crear_simulacion()
        estado_inicial = simulacion.get_estado()["pickers"][0]
        self.assertEqual(estado_inicial["productos_transportados"], 0)
        self.assertEqual(estado_inicial["productos_objetivo"], 5)
        self.assertEqual(estado_inicial["items_transportados"], [])
        self.ejecutar_hasta_terminar(simulacion)
        estado = simulacion.get_estado()

        self.assertEqual(estado["productos_recogidos"], 5)
        self.assertEqual(estado["productos_despachados"], 5)
        self.assertEqual(len(estado["descargas"]), 3)
        self.assertEqual(producto.cantidad_disponible, 0)
        self.assertEqual(picker.carga_actual_kg, 0)
        self.assertEqual(tuple(picker.posicion_actual), (0, 0))

    def test_stock_insuficiente_se_registra_y_se_entrega_lo_disponible(self):
        simulacion, picker, producto = self.crear_simulacion(stock=2, cantidad=5)

        self.ejecutar_hasta_terminar(simulacion)
        estado = simulacion.get_estado()

        self.assertEqual(estado["productos_recogidos"], 2)
        self.assertEqual(estado["productos_despachados"], 2)
        self.assertEqual(
            estado["faltantes"],
            [
                {
                    "picker_id": "PK_01",
                    "producto_id": "P001",
                    "cantidad": 3,
                    "motivo": "stock_agotado",
                }
            ],
        )
        self.assertEqual(producto.cantidad_disponible, 0)
        self.assertEqual(picker.carga_actual_kg, 0)

    def test_reset_restablece_stock_demanda_y_rutas_dinamicas(self):
        simulacion, picker, producto = self.crear_simulacion()
        self.ejecutar_hasta_terminar(simulacion)

        simulacion.resetear()

        estado = simulacion.get_estado()
        self.assertEqual(producto.cantidad_disponible, 5)
        self.assertEqual(tuple(picker.posicion_actual), (0, 0))
        self.assertEqual(picker.carga_actual_kg, 0)
        self.assertEqual(estado["productos_recogidos"], 0)
        self.assertEqual(estado["faltantes"], [])
        self.assertEqual(estado["descargas"], [])

    def test_despacho_compartido_espera_y_libera_su_acceso(self):
        warehouse = Warehouse(8, 6)
        warehouse.rellenar_pasillos_implicitos()
        producto_1 = Producto("P001", "Producto 1", "R1", (6, 4, 1), 1, 1.0)
        producto_2 = Producto("P002", "Producto 2", "R2", (7, 5, 1), 1, 1.0)
        picker_1 = Picker("PK_01", (0, 0), 1.0)
        picker_2 = Picker("PK_02", (7, 5), 1.0)
        pedidos_1 = [Orden("PED_01", 1, [("P001", 1)])]
        pedidos_2 = [Orden("PED_02", 1, [("P002", 1)])]
        grafo = construir_grafo(warehouse)
        simulacion = Simulation(
            warehouse=warehouse,
            pickers=[picker_1, picker_2],
            productos=[producto_1, producto_2],
            asignaciones={
                picker_1.id: pedidos_1,
                picker_2.id: pedidos_2,
            },
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={"ZONA_A": [(0, 0)]},
        )

        hubo_avance_simultaneo = False
        for _ in range(500):
            posiciones_anteriores = [
                tuple(picker.posicion_actual) for picker in simulacion.pickers
            ]
            quedan_pasos = simulacion.avanzar_paso()
            posiciones_nuevas = [
                tuple(picker.posicion_actual) for picker in simulacion.pickers
            ]
            if all(
                anterior != nueva
                for anterior, nueva in zip(
                    posiciones_anteriores, posiciones_nuevas
                )
            ):
                hubo_avance_simultaneo = True
            if not quedan_pasos:
                break
        else:
            self.fail("La simulación no terminó en el límite de pasos.")
        descargas = simulacion.get_estado()["descargas"]

        self.assertTrue(hubo_avance_simultaneo)
        self.assertEqual(len(descargas), 2)
        self.assertEqual(
            {descarga["picker_id"] for descarga in descargas},
            {picker_1.id, picker_2.id},
        )
        self.assertNotEqual(descargas[0]["paso"], descargas[1]["paso"])
        self.assertEqual(
            {picker["id"] for picker in simulacion.get_estado()["pickers"]},
            {picker_1.id, picker_2.id},
        )

    def test_colision_espera_un_tick_y_picker_de_id_mayor_recalcula(self):
        warehouse = Warehouse(3, 3)
        warehouse.rellenar_pasillos_implicitos()
        producto_1 = Producto("P001", "Producto 1", "R1", (2, 2, 1), 1, 1.0)
        producto_2 = Producto("P002", "Producto 2", "R2", (0, 0, 1), 1, 1.0)
        picker_menor = Picker("PK_01", (1, 0), 1.0)
        picker_mayor = Picker("PK_02", (0, 0), 1.0)
        grafo = construir_grafo(warehouse)
        simulacion = Simulation(
            warehouse=warehouse,
            pickers=[picker_menor, picker_mayor],
            productos=[producto_1, producto_2],
            asignaciones={picker_menor.id: [], picker_mayor.id: []},
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={"ZONA_A": [(2, 2)]},
        )
        simulacion._estado_picker[picker_menor.id] = "activo"
        simulacion._estado_picker[picker_mayor.id] = "activo"
        simulacion._objetivos_dinamicos = {
            picker_menor.id: {"tipo": "producto", "producto_id": "P002"},
            picker_mayor.id: {"tipo": "producto", "producto_id": "P001"},
        }
        simulacion._tramos_dinamicos = {
            picker_menor.id: [(1, 0), (0, 0)],
            picker_mayor.id: [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
        }
        simulacion._indices_ruta = {
            picker_menor.id: 1,
            picker_mayor.id: 1,
        }

        simulacion.avanzar_paso()
        self.assertEqual(
            tuple(picker_mayor.posicion_actual),
            (0, 0),
            "Los pickers deben esperar el primer tick de bloqueo.",
        )
        ruta_antes = list(simulacion._tramos_dinamicos[picker_mayor.id])

        simulacion.avanzar_paso()

        ruta_recalculada = simulacion._tramos_dinamicos[picker_mayor.id]
        self.assertNotEqual(ruta_recalculada, ruta_antes)
        self.assertNotIn((1, 0), ruta_recalculada[1:])
        self.assertEqual(
            simulacion._tramos_dinamicos[picker_menor.id],
            [(1, 0), (0, 0)],
            "El picker de ID menor conserva su ruta y cede el paso.",
        )
        self.assertTrue(
            all(
                abs(x1 - x2) + abs(y1 - y2) == 1
                for (x1, y1), (x2, y2) in zip(
                    ruta_recalculada, ruta_recalculada[1:]
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
