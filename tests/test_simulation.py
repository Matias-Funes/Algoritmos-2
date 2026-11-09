import unittest

from main import _SimulationTk, _crear_waves
from src.algorithms.pathfinding import CacheDistancias
from src.core.graph_builder import construir_grafo
from src.core.inventory import GestorInventario, Producto
from src.core.order import Orden
from src.core.picker import Picker
from src.core.warehouse import Warehouse
from src.core.wave import Wave
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
        self.assertEqual(
            estado["pickers"][0]["productos_recogidos"], 5
        )
        self.assertEqual(estado["productos_despachados"], 5)
        self.assertEqual(len(estado["descargas"]), 3)
        self.assertEqual(producto.cantidad_disponible, 0)
        self.assertEqual(picker.carga_actual_kg, 0)
        self.assertEqual(tuple(picker.posicion_actual), (0, 0))

    def test_puntos_de_descarga_preservan_el_reingreso_a_futuras_waves(self):
        from src.core.graph_builder import Graph

        grafo = Graph()
        nodos = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        for nodo in nodos:
            grafo.add_node(nodo)
        grafo.add_edge((0, 0), (1, 0))
        grafo.add_edge((1, 0), (2, 0))
        grafo.add_edge((2, 0), (0, 0))
        grafo.add_edge((2, 0), (4, 0))
        grafo.add_edge((1, 0), (3, 0))
        picker = Picker("PK_01", (0, 0), 1.0)

        simulacion = Simulation(
            warehouse=None,
            pickers=[picker],
            productos=[],
            asignaciones={picker.id: []},
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={
                "SEGURA": [(2, 0)],
                "SIN_RETORNO": [(3, 0)],
            },
            pickers_con_trabajo_posterior={picker.id},
        )

        self.assertEqual(
            simulacion._puntos_despacho_reingreso[picker.id],
            {(2, 0)},
        )
        simulacion._estado_picker[picker.id] = "activo"
        simulacion.pickers[0].carga_actual_kg = 1.0
        self.assertTrue(
            simulacion._planificar_descarga_dinamica(simulacion.pickers[0])
        )
        self.assertEqual(
            simulacion._objetivos_dinamicos[picker.id]["punto"],
            (2, 0),
        )

    def test_progreso_acumulado_por_picker_y_turnos_en_la_flota(self):
        warehouse = Warehouse(8, 6)
        warehouse.rellenar_pasillos_implicitos()
        producto = Producto("P001", "Producto", "R1", (6, 4, 1), 2, 1.0)
        picker = Picker("PK_01", (0, 0), 1.0)
        inventario = GestorInventario()
        inventario.agregar_producto(producto)
        pedidos = [
            Orden(f"PED_{i}", 1, [("P001", 1)])
            for i in range(2)
        ]
        waves = []
        fases = []
        for indice, pedido in enumerate(pedidos, start=1):
            wave = Wave(f"WAVE_{indice:03d}", 1, 1, 10.0)
            wave.agregar_pedido(pedido, inventario)
            waves.append(wave)
            fases.append(
                {
                    "asignaciones": {picker.id: [pedido]},
                    "waves_ids": {picker.id: wave.id},
                }
            )

        grafo = construir_grafo(warehouse)
        simulacion = _SimulationTk(
            warehouse=warehouse,
            pickers=[picker],
            productos=[producto],
            fases=fases,
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={"ZONA_A": [(0, 0)]},
            waves=waves,
        )
        for _ in range(1000):
            if not simulacion.avanzar_paso():
                break
        else:
            self.fail("La simulación no terminó en el límite de pasos.")

        estado = simulacion.get_estado()
        estado_picker = estado["pickers"][0]
        self.assertEqual(estado["productos_recogidos"], 2)
        self.assertEqual(estado["productos_recogidos_wave_actual"], 1)
        self.assertEqual(estado["turno_actual"], 2)
        self.assertEqual(estado["turnos_totales"], 2)
        self.assertEqual(estado["waves_totales"], 2)
        self.assertEqual(estado_picker["productos_recogidos"], 2)
        self.assertEqual(estado_picker["productos_objetivo"], 2)
        self.assertEqual(estado_picker["productos_transportados"], 0)
        self.assertEqual(estado_picker["wave_actual"], "-")
        self.assertFalse(estado_picker["activo"])

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
        self.assertEqual(estado["productos_despachados"], 0)
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
                for anterior, nueva in zip(posiciones_anteriores, posiciones_nuevas)
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
                for (x1, y1), (x2, y2) in zip(ruta_recalculada, ruta_recalculada[1:])
            )
        )

    def test_retroceder_paso(self):
        """Prueba que el botón de atrás devuelve a los pickers a su posición anterior."""
        from pathlib import Path

        from main import construir_simulacion

        wh, sim = construir_simulacion(Path("data/scenarios/escenario_basico.json"))

        # Avanzamos 3 pasos
        sim.avanzar_paso()
        sim.avanzar_paso()
        sim.avanzar_paso()

        posicion_adelantada = sim.pickers[0].posicion_actual

        # Retrocedemos 1 paso
        sim.retroceder_paso()

        # La posición debería ser distinta a la de adelante
        self.assertNotEqual(sim.pickers[0].posicion_actual, posicion_adelantada)

    def test_ruta_pendiente_se_recorta_al_avanzar(self):
        simulacion, picker, producto = self.crear_simulacion()

        estado_inicial = simulacion.get_estado()
        ruta_inicial = estado_inicial["rutas"][0]
        self.assertGreater(
            len(ruta_inicial), 1, "La ruta inicial debe tener varios pasos"
        )

        # Avanzamos un paso
        simulacion.avanzar_paso()

        estado_paso_1 = simulacion.get_estado()
        ruta_paso_1 = estado_paso_1["rutas"][0]

        # La nueva ruta debe tener un paso menos que la anterior
        self.assertEqual(len(ruta_paso_1), len(ruta_inicial) - 1)

        # La nueva ruta debe empezar en la posición actual del picker
        self.assertEqual(ruta_paso_1[0], tuple(picker.posicion_actual))

    def test_planifica_varios_productos_con_una_sola_busqueda(self):
        warehouse = Warehouse(8, 6)
        warehouse.rellenar_pasillos_implicitos()
        productos = [
            Producto("P001", "Producto 1", "R1", (6, 4, 1), 1, 1.0),
            Producto("P002", "Producto 2", "R2", (7, 5, 1), 1, 1.0),
        ]
        picker = Picker("PK_01", (0, 0), 2.0)
        pedidos = [
            Orden("PED_01", 1, [("P001", 1)]),
            Orden("PED_02", 1, [("P002", 1)]),
        ]
        grafo = construir_grafo(warehouse)
        simulacion = Simulation(
            warehouse=warehouse,
            pickers=[picker],
            productos=productos,
            asignaciones={picker.id: pedidos},
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={"ZONA_A": [(0, 0)]},
        )
        picker_sim = simulacion.pickers[0]
        simulacion._tramos_dinamicos[picker_sim.id] = []
        simulacion._indices_ruta[picker_sim.id] = 0
        simulacion._objetivos_dinamicos[picker_sim.id] = None
        simulacion._rutas[picker_sim.id] = [
            tuple(picker_sim.posicion_actual)
        ]

        calcular_distancias = simulacion._calcular_distancias_con_picker
        camino_desde_busqueda = simulacion._camino_desde_busqueda
        cantidad_busquedas = 0
        cantidad_caminos_reconstruidos = 0

        def contar_busquedas(picker_actual, origen=None, destinos=None):
            nonlocal cantidad_busquedas
            cantidad_busquedas += 1
            return calcular_distancias(picker_actual, origen, destinos)

        def contar_caminos(picker_actual, destino, busqueda):
            nonlocal cantidad_caminos_reconstruidos
            cantidad_caminos_reconstruidos += 1
            return camino_desde_busqueda(
                picker_actual, destino, busqueda
            )

        simulacion._calcular_distancias_con_picker = contar_busquedas
        simulacion._camino_desde_busqueda = contar_caminos
        simulacion._planificar_picker_dinamico(picker_sim)

        self.assertEqual(cantidad_busquedas, 1)
        self.assertEqual(cantidad_caminos_reconstruidos, 1)
        self.assertEqual(
            simulacion._objetivos_dinamicos[picker_sim.id]["tipo"],
            "producto",
        )
        self.assertIn(
            simulacion._objetivos_dinamicos[picker_sim.id]["producto_id"],
            {"P001", "P002"},
        )

    def test_cuatro_pickers_aparecen_en_estado_y_rutas_pendientes(self):
        warehouse = Warehouse(8, 6)
        warehouse.rellenar_pasillos_implicitos()
        producto_1 = Producto("P001", "Producto 1", "R1", (6, 4, 1), 1, 1.0)
        producto_2 = Producto("P002", "Producto 2", "R2", (7, 5, 1), 1, 1.0)
        picker_1 = Picker("PK_01", (0, 0), 1.0)
        picker_2 = Picker("PK_02", (1, 1), 1.0)
        picker_3 = Picker("PK_03", (2, 2), 1.0)  # sin trabajo
        picker_4 = Picker("PK_04", (3, 3), 1.0)  # sin trabajo
        pedidos_1 = [Orden("PED_01", 1, [("P001", 1)])]
        pedidos_2 = [Orden("PED_02", 1, [("P002", 1)])]
        grafo = construir_grafo(warehouse)
        simulacion = Simulation(
            warehouse=warehouse,
            pickers=[picker_1, picker_2, picker_3, picker_4],
            productos=[producto_1, producto_2],
            asignaciones={
                picker_1.id: pedidos_1,
                picker_2.id: pedidos_2,
                picker_3.id: [],
                picker_4.id: [],
            },
            cache_distancias=CacheDistancias(grafo),
            puntos_despacho={"ZONA_A": [(0, 0)]},
        )

        estado_inicial = simulacion.get_estado()
        self.assertEqual(len(estado_inicial["pickers"]), 4)

        # Los inactivos no deben desaparecer del estado
        inactivos = [p for p in estado_inicial["pickers"] if not p["activo"]]
        self.assertEqual(len(inactivos), 2)
        self.assertEqual(inactivos[0]["id"], "PK_03")
        self.assertEqual(inactivos[1]["id"], "PK_04")

        # Validar que el camino pendiente se recorta al avanzar
        ruta_inicial = estado_inicial["rutas"][0]
        simulacion.avanzar_paso()
        estado_paso_1 = simulacion.get_estado()
        ruta_paso_1 = estado_paso_1["rutas"][0]

        self.assertEqual(len(ruta_paso_1), len(ruta_inicial) - 1)
        self.assertEqual(ruta_paso_1[0], tuple(picker_1.posicion_actual))


if __name__ == "__main__":
    unittest.main()
