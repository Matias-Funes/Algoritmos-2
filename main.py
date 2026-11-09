"""Punto de entrada: abre la aplicación (menú, configuración y simulación)."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable

from src.algorithms.pathfinding import CacheDistancias
from src.controlador import Controlador
from src.core.graph_builder import construir_grafo
from src.core.inventory import GestorInventario, Producto
from src.core.order import Orden
from src.core.picker import Picker
from src.core.wave import Wave
from src.io.scenario_loader import cargar_escenario
from src.simulation.simulation import Simulation


def _crear_productos(datos_productos: list[dict[str, Any]]) -> list[Producto]:
    """Convierte los productos crudos del JSON en objetos del dominio."""
    productos = []
    for datos in datos_productos:
        ubicacion = datos["ubicacion"]
        if isinstance(ubicacion, dict):
            ubicacion = (
                ubicacion["x"],
                ubicacion["y"],
                ubicacion.get("z", 0),
            )
        productos.append(
            Producto(
                datos["id"],
                datos["nombre"],
                datos["rack_id"],
                tuple(ubicacion),
                datos["cantidad_disponible"],
                datos["peso_kg"],
            )
        )
    return productos


def _crear_pedidos(
    datos_pedidos: list[dict[str, Any]],
) -> list[Orden]:
    """Convierte los pedidos crudos a Orden con items (id, cantidad)."""
    return [
        Orden(
            orden_id=datos["id"],
            prioridad=datos["prioridad"],
            estado=datos.get("estado", "PENDIENTE"),
            items=[
                (item["producto_id"], item["cantidad"])
                for item in datos["items"]
            ],
        )
        for datos in datos_pedidos
    ]


def _crear_pickers(datos_pickers: list[dict[str, Any]]) -> list[Picker]:
    """Convierte posiciones x/y del escenario a los Picker del dominio."""
    pickers = []
    for datos in datos_pickers:
        posicion = datos["posicion_inicial"]
        if isinstance(posicion, dict):
            posicion = (posicion["x"], posicion["y"])
        pickers.append(
            Picker(
                picker_id=datos["id"],
                posicion_inicial=tuple(posicion),
                capacidad_carga_kg=datos["capacidad_carga_kg"],
                prioridad=datos.get("prioridad", 1),
            )
        )
    return pickers


def _validar_stock_pedidos(
    pedidos: list[Orden],
    inventario: GestorInventario,
) -> None:
    """Valida referencias y avisa cuando la demanda supera el stock inicial."""
    demanda_por_producto: dict[str, int] = {}
    for pedido in pedidos:
        for producto_id, cantidad in pedido.items:
            demanda_por_producto[producto_id] = (
                demanda_por_producto.get(producto_id, 0) + cantidad
            )

    for producto_id, demanda in demanda_por_producto.items():
        producto = inventario.obtener_producto(producto_id)
        if demanda > producto.cantidad_disponible:
            print(
                f"   Aviso: {producto_id}: se piden {demanda}, "
                f"hay {producto.cantidad_disponible}; se preparará lo "
                "disponible y se registrará el faltante."
            )


def _crear_waves(
    pedidos: list[Orden],
    pickers: list[Picker],
    inventario: GestorInventario,
    configuracion: dict[str, Any],
) -> tuple[list[Wave], dict[str, list[Orden]], dict[str, list[Wave]]]:
    """
    Asigna pedidos a waves individuales por picker usando un algoritmo Greedy general.
    Funciona para cualquier cantidad de pickers y pedidos.
    """
    max_pedidos = configuracion.get("wave_max_pedidos", len(pedidos) or 1)
    max_productos = configuracion.get("wave_max_productos", 100)

    if max_pedidos <= 0 or max_productos <= 0:
        raise ValueError("Los límites de wave deben ser enteros positivos.")
    if pedidos and not pickers:
        raise ValueError("No se pueden procesar pedidos sin pickers.")

    # 1. Ordenar pedidos por prioridad (mayor a menor)
    pedidos_ordenados = sorted(pedidos, key=lambda p: -p.prioridad)

    waves: list[Wave] = []
    pedidos_por_picker = {picker.id: [] for picker in pickers}
    waves_por_picker = {picker.id: [] for picker in pickers}
    carga_wave_actual = {picker.id: 0.0 for picker in pickers}
    wave_actual: dict[str, Wave] = {picker.id: None for picker in pickers}
    siguiente_wave_id = 1

    for pedido in pedidos_ordenados:
        peso_pedido = pedido.peso_total(inventario)
        asignado = False

        # 2. Filtrar pickers que puedan transportar el pedido (capacidad individual)
        candidatos = [
            p for p in pickers
            if p.capacidad_carga_kg >= peso_pedido
        ]

        if not candidatos:
            print(f"   Advertencia: El pedido {pedido.orden_id} pesa más que cualquier picker.")
            candidatos = pickers

        # 3. Ordenar candidatos por menor carga acumulada (Balanceo de carga)
        candidatos_ordenados = sorted(
            candidatos,
            key=lambda p: carga_wave_actual[p.id]
        )

        # 4. Intentar meter en la wave actual del picker
        for picker in candidatos_ordenados:
            wave = wave_actual[picker.id]
            if wave is not None and wave.puede_aceptar(pedido, inventario):
                wave.agregar_pedido(pedido, inventario)
                pedidos_por_picker[picker.id].append(pedido)
                carga_wave_actual[picker.id] += peso_pedido
                asignado = True
                break

        # 5. Si no entró en ninguna wave actual, crear una nueva wave
        if not asignado:
            # Elegir al picker con menos carga actual
            picker_elegido = min(candidatos, key=lambda p: carga_wave_actual[p.id])
            nueva_wave = Wave(
                wave_id=f"WAVE_{siguiente_wave_id:03d}",
                capacidad_max_pedidos=max_pedidos,
                capacidad_max_productos=max_productos,
                peso_max_kg=configuracion.get("wave_max_peso_kg", 100000.0)
            )
            siguiente_wave_id += 1

            if nueva_wave.agregar_pedido(pedido, inventario):
                wave_actual[picker_elegido.id] = nueva_wave
                waves_por_picker[picker_elegido.id].append(nueva_wave)
                pedidos_por_picker[picker_elegido.id].append(pedido)
                carga_wave_actual[picker_elegido.id] += peso_pedido
                waves.append(nueva_wave)
                asignado = True

        if not asignado:
            raise ValueError(
                f"El pedido {pedido.orden_id} excede los límites de "
                "pedidos/productos configurados para una wave."
            )

    return waves, pedidos_por_picker, waves_por_picker


def _crear_fases_simulacion(
    pickers: list[Picker],
    waves_por_picker: dict[str, list[Wave]],
) -> list[dict[str, Any]]:
    """Agrupa el trabajo de cada wave por turno para ejecutar pickers juntos."""
    fases = []
    cantidad_turnos = max(
        (len(waves_por_picker[picker.id]) for picker in pickers),
        default=0,
    )
    for indice_turno in range(cantidad_turnos):
        asignaciones = {}
        waves_ids = {}  # <--- NUEVO: Guarda el ID de la wave de cada picker
        for picker in pickers:
            waves_picker = waves_por_picker[picker.id]
            if indice_turno >= len(waves_picker):
                continue
            wave = waves_picker[indice_turno]
            asignaciones[picker.id] = wave.pedidos
            waves_ids[picker.id] = wave.id  # <--- NUEVO
        fases.append({"asignaciones": asignaciones, "waves_ids": waves_ids})

    return fases or [{"asignaciones": {}, "waves_ids": {}}]


def _obtener_puntos_despacho(
    warehouse: Any,
    grafo: Any,
) -> dict[str, list[tuple[int, int]]]:
    """Devuelve las celdas transitables de las zonas vinculadas a salida."""
    puntos_por_zona = {}
    for zona in warehouse.zonas.values():
        puerta = warehouse.puertas.get(zona.puerta_id)
        if puerta is None or puerta.tipo not in ("OUTBOUND", "AMBOS"):
            continue

        puntos = {
            (x, y)
            for x, y in zona.celdas()
            if (x, y) in grafo.adj
        }
        if puntos:
            puntos_por_zona[zona.id] = sorted(puntos)

    return puntos_por_zona


class _SimulationTk:
    """Coordina fases y presenta viajes dinámicos al bucle de Tk."""

    def __init__(
        self,
        warehouse: Any,
        pickers: list[Picker],
        productos: list[Producto],
        fases: list[dict[str, Any]],
        cache_distancias: CacheDistancias,
        puntos_despacho: dict[str, list[tuple[int, int]]],
        grafo: Any = None,
        inventario: Any = None,
        waves: list[Wave] | None = None,
        configuracion: dict[str, Any] | None = None,
        estrategia_recorrido: str = "Vecino más cercano (B)",
        intervalo_ms: int = 250,
    ) -> None:
        self.warehouse = warehouse
        self.pickers = pickers
        self.productos = productos
        self.fases = fases
        self.cache_distancias = cache_distancias
        self.puntos_despacho = puntos_despacho
        self.intervalo_ms = intervalo_ms
        self.grafo = grafo
        self.inventario = inventario
        self.waves = list(waves or [])
        self.configuracion = configuracion
        self.estrategia_recorrido = estrategia_recorrido
        self.fase_actual = 0
        self._root = None
        self._actualizar_interfaz: Callable[[], None] | None = None
        self._after_id = None
        self._en_ejecucion = False
        self._fase_completada = False
        self._productos_recogidos_acumulados = 0
        self._productos_recogidos_acumulados_por_picker = {
            picker.id: 0 for picker in pickers
        }
        self._productos_despachados_acumulados = 0
        self._distancia_acumulada = 0
        self._faltantes_acumulados: list[dict[str, Any]] = []
        self._descargas_acumuladas: list[dict[str, Any]] = []

        self._total_productos = sum(
            cantidad
            for fase in fases
            for pedidos_fase in fase["asignaciones"].values()
            for pedido in pedidos_fase
            for _, cantidad in pedido.items
        )
        self._productos_objetivo_por_picker = {picker.id: 0 for picker in pickers}
        for fase in fases:
            for picker_id, pedidos_picker in fase["asignaciones"].items():
                self._productos_objetivo_por_picker[picker_id] = (
                    self._productos_objetivo_por_picker.get(picker_id, 0)
                    + sum(
                        cantidad
                        for pedido in pedidos_picker
                        for _, cantidad in pedido.items
                    )
                )
        self._estado_inicial_pickers = {
            picker.id: {
                "posicion": tuple(picker.posicion_actual),
                "carga": picker.carga_actual_kg,
                "items": list(picker.items_transportados),
            }
            for picker in pickers
        }
        self._stock_inicial = {
            producto.producto_id: producto.cantidad_disponible
            for producto in productos
        }
        self._simulacion_actual = self._crear_simulacion_fase(0)
        self.historial_snapshots = []

    def _crear_simulacion_fase(self, indice: int) -> Simulation:
        """Crea un motor común que planifica el trabajo de toda la flota."""
        fase = self.fases[indice]
        es_ultima = (indice == len(self.fases) - 1)
        pickers_con_trabajo_posterior = {
            picker_id
            for fase_futura in self.fases[indice + 1 :]
            for picker_id, pedidos in fase_futura["asignaciones"].items()
            if pedidos
        }
        return Simulation(
            warehouse=self.warehouse,
            pickers=self.pickers,
            productos=self.productos,
            asignaciones=fase["asignaciones"],
            cache_distancias=self.cache_distancias,
            puntos_despacho=self.puntos_despacho,
            estrategia_recorrido=self.estrategia_recorrido,
            es_ultima_fase=es_ultima,
            pickers_con_trabajo_posterior=pickers_con_trabajo_posterior,
        )

    def vincular_interfaz(
        self, root: Any, actualizar_interfaz: Callable[[], None]
    ) -> None:
        """Registra la ventana que recibirá cada actualización de estado."""
        self._root = root
        self._actualizar_interfaz = actualizar_interfaz

    def get_estado(self) -> dict[str, Any]:
        """Devuelve el estado del turno activo y de toda la flota."""
        estado = self._simulacion_actual.get_estado()
        faltantes_actuales = estado["faltantes"]
        descargas_actuales = estado["descargas"]
        recogidos_en_fase = (
            0 if self._fase_completada else estado["productos_recogidos"]
        )
        productos_recogidos_fase = estado["productos_recogidos"]
        total_productos_fase = estado["total_productos"]
        estado["productos_recogidos"] = (
            self._productos_recogidos_acumulados + recogidos_en_fase
        )
        estado["total_productos_wave_actual"] = total_productos_fase
        estado["productos_recogidos_wave_actual"] = productos_recogidos_fase
        distancia_en_fase = (
            0 if self._fase_completada else estado["distancia"]
        )
        estado["distancia"] = self._distancia_acumulada + distancia_en_fase
        estado["total_productos"] = self._total_productos
        estado["terminada"] = self._fase_completada
        estado["turno_actual"] = self.fase_actual + 1
        estado["turnos_totales"] = len(self.fases)
        estado["waves_totales"] = len(self.waves)
        estado["faltantes"] = list(self._faltantes_acumulados)
        estado["descargas"] = list(self._descargas_acumuladas)
        if not self._fase_completada:
            estado["faltantes"].extend(faltantes_actuales)
            estado["descargas"].extend(descargas_actuales)
        estado["productos_despachados"] = (
            self._productos_despachados_acumulados
            + (
                0
                if self._fase_completada
                else estado["productos_despachados"]
            )
        )
        estado_pickers = {picker["id"]: picker for picker in estado["pickers"]}

        # Cada fase sincroniza una wave asignada por picker.
        waves_ids_fase = self.fases[self.fase_actual].get("waves_ids", {})

        estado["pickers"] = [
            {
                "id": picker.id,
                "x": picker.posicion_actual[0],
                "y": picker.posicion_actual[1],
                "carga_actual_kg": picker.carga_actual_kg,
                "capacidad_carga_kg": picker.capacidad_carga_kg,
                "wave_actual": (
                    waves_ids_fase.get(picker.id, "-")
                    if estado_pickers.get(picker.id, {}).get("activo", False)
                    else "-"
                ),
                "items_transportados": [
                    dict(item)
                    for item in estado_pickers.get(picker.id, {}).get(
                        "items_transportados", []
                    )
                ],
                "productos_transportados": estado_pickers.get(
                    picker.id, {}
                ).get("productos_transportados", 0),
                "productos_recogidos": (
                    self._productos_recogidos_acumulados_por_picker.get(
                        picker.id, 0
                    )
                    + (
                        0
                        if self._fase_completada
                        else estado_pickers.get(picker.id, {}).get(
                            "productos_recogidos", 0
                        )
                    )
                ),
                "productos_objetivo": self._productos_objetivo_por_picker.get(
                    picker.id, 0
                ),
                "activo": estado_pickers.get(picker.id, {}).get(
                    "activo", False
                ),
            }
            for picker in self.pickers
        ]
        return estado

    def avanzar_paso(self) -> bool:
        """Avanza el viaje actual o prepara el próximo al completar la wave."""
        if self._fase_completada:
            return False

        self.historial_snapshots.append(self.get_snapshot())

        if len(self.historial_snapshots) > 1000:
            self.historial_snapshots.pop(0)

        if self._simulacion_actual.avanzar_paso():
            return True

        estado_fase = self._simulacion_actual.get_estado()
        self._productos_recogidos_acumulados += estado_fase["productos_recogidos"]
        for picker_id, cantidad in estado_fase[
            "productos_recogidos_por_picker"
        ].items():
            self._productos_recogidos_acumulados_por_picker[picker_id] = (
                self._productos_recogidos_acumulados_por_picker.get(
                    picker_id, 0
                )
                + cantidad
            )
        self._productos_despachados_acumulados += estado_fase[
            "productos_despachados"
        ]
        self._distancia_acumulada += estado_fase["distancia"]
        self._faltantes_acumulados.extend(estado_fase["faltantes"])
        self._descargas_acumuladas.extend(estado_fase["descargas"])
        for faltante in estado_fase["faltantes"]:
            print(
                f"   Faltante {faltante['producto_id']}: "
                f"{faltante['cantidad']} unidades "
                f"({faltante['motivo']}, picker {faltante['picker_id']})"
            )
        self._fase_completada = True
        siguiente_fase = self.fase_actual + 1
        if siguiente_fase >= len(self.fases):
            self._en_ejecucion = False
            return False

        self.fase_actual = siguiente_fase
        self._simulacion_actual = self._crear_simulacion_fase(self.fase_actual)
        self._fase_completada = False
        return True

    def actualizar_velocidad(self, intervalo_ms: int) -> None:
        """Permite cambiar la velocidad en caliente mientras la simulación corre."""
        self.intervalo_ms = intervalo_ms

    def iniciar(self) -> None:
        """Inicia la animación programando ticks sin bloquear Tkinter."""
        if self._root is None or self._actualizar_interfaz is None:
            raise RuntimeError("La simulación debe vincularse a una ventana antes.")
        if self._en_ejecucion:
            return
        self._en_ejecucion = True
        self._programar_paso(0)

    def pausar(self) -> None:
        """Pausa la animación y cancela el callback pendiente, si existe."""
        self._en_ejecucion = False
        if self._after_id is not None and self._root is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    def resetear(self) -> None:
        """Restaura el estado inicial de todos los viajes y del inventario."""
        self.pausar()
        for picker in self.pickers:
            inicial = self._estado_inicial_pickers[picker.id]
            picker.mover_a(inicial["posicion"])
            picker.carga_actual_kg = inicial["carga"]
            picker.items_transportados = list(inicial["items"])
        for producto in self.productos:
            producto.cantidad_disponible = self._stock_inicial[
                producto.producto_id
            ]
        self.fase_actual = 0
        self._fase_completada = False
        self._productos_recogidos_acumulados = 0
        self._productos_recogidos_acumulados_por_picker = {
            picker.id: 0 for picker in self.pickers
        }
        self._productos_despachados_acumulados = 0
        self._distancia_acumulada = 0
        self._faltantes_acumulados.clear()
        self._descargas_acumuladas.clear()
        self._simulacion_actual = self._crear_simulacion_fase(0)
        self.historial_snapshots.clear()
        if self._actualizar_interfaz is not None:
            self._actualizar_interfaz()

    def _programar_paso(self, demora_ms: int) -> None:
        self._after_id = self._root.after(demora_ms, self._avanzar_automaticamente)

    def _avanzar_automaticamente(self) -> None:
        """Ejecuta un tick y vuelve a programarse solo mientras haya ruta."""
        self._after_id = None
        if not self._en_ejecucion:
            return

        quedan_pasos = self.avanzar_paso()
        if self._actualizar_interfaz is not None:
            self._actualizar_interfaz()

        if quedan_pasos and self._en_ejecucion:
            self._programar_paso(self.intervalo_ms)
        else:
            self._en_ejecucion = False

    def retroceder_paso(self) -> bool:
        """Revierte el estado al paso anterior usando el historial."""
        if not self.historial_snapshots:
            return False

        snapshot_anterior = self.historial_snapshots.pop()
        self.restaurar_snapshot(snapshot_anterior)
        self.pausar()
        return True

    def comparar_estrategias(self):
        if self.grafo is None or self.inventario is None or not self.waves:
            return {"por_wave": [], "totales": {},
                    "ganador_distancia": None, "ganador_tiempo": None,
                    "errores": []}
        from src.utils.benchmark import comparar_estrategias
        return comparar_estrategias(
            self.grafo, self.waves, self.warehouse, self.inventario
        )

    def get_snapshot(self) -> dict:
        """Devuelve un diccionario con el estado exacto para guardar."""
        return {
            "fase_actual": self.fase_actual,
            "paso_actual": self._simulacion_actual.paso_actual,
            "distancia_acumulada": self._distancia_acumulada,
            "productos_recogidos_acumulados": self._productos_recogidos_acumulados,
            "productos_recogidos_acumulados_por_picker": dict(
                self._productos_recogidos_acumulados_por_picker
            ),
            "faltantes_acumulados": self._faltantes_acumulados,
            "descargas_acumuladas": self._descargas_acumuladas,
            "pickers": [
                {
                    "id": p.id,
                    "posicion_actual": list(p.posicion_actual),
                    "carga_actual_kg": p.carga_actual_kg,
                    "items_transportados": list(p.items_transportados),
                } for p in self.pickers
            ],
            "stock_productos": {
                prod.producto_id: prod.cantidad_disponible for prod in self.productos
            },
            "distancia_fase_actual": self._simulacion_actual.distancia,
            "recogidos_fase_actual": list(self._simulacion_actual.productos_recogidos),
            "faltantes_fase_actual": list(self._simulacion_actual.productos_faltantes),
            "descargas_fase_actual": list(self._simulacion_actual.descargas),
        }

    def restaurar_snapshot(self, snapshot: dict):
        """Aplica una foto guardada para continuar la simulación."""
        self.fase_actual = snapshot["fase_actual"]
        self._distancia_acumulada = snapshot["distancia_acumulada"]
        self._productos_recogidos_acumulados = snapshot["productos_recogidos_acumulados"]
        self._faltantes_acumulados = snapshot["faltantes_acumulados"]
        self._descargas_acumuladas = snapshot["descargas_acumuladas"]
        recogidos_por_picker = snapshot.get(
            "productos_recogidos_acumulados_por_picker"
        )
        if recogidos_por_picker is None:
            recogidos_por_picker = {
                picker.id: 0 for picker in self.pickers
            }
            for descarga in self._descargas_acumuladas:
                picker_id = descarga["picker_id"]
                recogidos_por_picker[picker_id] = (
                    recogidos_por_picker.get(picker_id, 0)
                    + sum(item["cantidad"] for item in descarga["items"])
                )
        self._productos_recogidos_acumulados_por_picker = {
            picker.id: recogidos_por_picker.get(picker.id, 0)
            for picker in self.pickers
        }
        self._productos_despachados_acumulados = sum(
            item["cantidad"]
            for descarga in self._descargas_acumuladas
            for item in descarga["items"]
        )

        for prod in self.productos:
            if prod.producto_id in snapshot["stock_productos"]:
                prod.cantidad_disponible = snapshot["stock_productos"][prod.producto_id]

        estado_pickers = {p["id"]: p for p in snapshot["pickers"]}
        for picker in self.pickers:
            if picker.id in estado_pickers:
                data = estado_pickers[picker.id]
                picker.posicion_actual = tuple(data["posicion_actual"])
                picker.carga_actual_kg = data["carga_actual_kg"]
                picker.items_transportados = [tuple(item) for item in data["items_transportados"]]

        self._fase_completada = False
        self._simulacion_actual = self._crear_simulacion_fase(self.fase_actual)
        self._simulacion_actual.paso_actual = snapshot["paso_actual"]

        self._simulacion_actual.distancia = snapshot.get("distancia_fase_actual", 0)
        self._simulacion_actual.productos_recogidos = snapshot.get("recogidos_fase_actual", [])
        self._simulacion_actual.productos_faltantes = snapshot.get("faltantes_fase_actual", [])
        self._simulacion_actual.descargas = snapshot.get("descargas_fase_actual", [])
        self._simulacion_actual._cantidad_productos_recogidos = sum(
            item["cantidad"]
            for item in self._simulacion_actual.productos_recogidos
        )
        self._simulacion_actual._productos_recogidos_por_picker = {
            picker.id: 0 for picker in self.pickers
        }
        for item in self._simulacion_actual.productos_recogidos:
            picker_id = item["picker_id"]
            self._simulacion_actual._productos_recogidos_por_picker[
                picker_id
            ] = (
                self._simulacion_actual._productos_recogidos_por_picker.get(
                    picker_id, 0
                )
                + item["cantidad"]
            )
        self._simulacion_actual._cantidad_productos_despachados = sum(
            item["cantidad"]
            for descarga in self._simulacion_actual.descargas
            for item in descarga["items"]
        )

        # Descontamos la demanda de lo ya recogido
        picker_por_id = {p.id: p for p in self._simulacion_actual.pickers}
        for rec in snapshot.get("recogidos_fase_actual", []):
            picker = picker_por_id.get(rec["picker_id"])
            if picker is not None:
                self._simulacion_actual._reducir_demanda(
                    picker, rec["producto_id"], rec["cantidad"]
                )

def _limpiar_productos_inalcanzables(pedidos, inventario, warehouse, grafo, cache, puntos_despacho):
    """
    Busca productos cuyas celdas de acceso estén totalmente aisladas (sin ida o sin vuelta).
    Los elimina de los pedidos y del inventario.
    """
    productos_invalidos = set()
    advertencias = []

    # 1. Encontrar un nodo de despacho de referencia
    nodo_despacho = None
    for p in puntos_despacho.values():
        if p:
            nodo_despacho = p[0]
            break

    for prod in inventario.todos_los_productos():
        prod_id = prod.producto_id
        x, y = prod.ubicacion[0], prod.ubicacion[1]
        celdas_acceso = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < warehouse.ancho_x and 0 <= ny < warehouse.largo_y:
                if warehouse.grid[ny][nx].tipo == "PASILLO":
                    celdas_acceso.append((nx, ny))

        if not celdas_acceso:
            productos_invalidos.add(prod_id)
            continue

        # 2. Verificar conectividad real con el despacho (Ida y Vuelta)
        # Si el producto está en un callejón, d_vuelta será infinito y se descarta.
        es_alcanzable = False
        if nodo_despacho:
            for celda in celdas_acceso:
                d_ida = cache.distancia(nodo_despacho, celda)
                d_vuelta = cache.distancia(celda, nodo_despacho)
                if d_ida != float("inf") and d_vuelta != float("inf"):
                    es_alcanzable = True
                    break

        if not es_alcanzable:
            productos_invalidos.add(prod_id)
            advertencias.append(f"El producto {prod_id} está aislado o no tiene ruta de vuelta al despacho.")
            continue

    if not productos_invalidos:
        return pedidos, advertencias

    # Descontar del inventario
    for pid in productos_invalidos:
        prod = inventario.obtener_producto(pid)
        if prod:
            prod.cantidad_disponible = 0

    # Limpiar pedidos
    pedidos_limpios = []
    for pedido in pedidos:
        nuevos_items = []
        for prod_id, cant in pedido.items:
            if prod_id not in productos_invalidos:
                nuevos_items.append((prod_id, cant))
            else:
                advertencias.append(f"Pedido {pedido.orden_id}: quitado {prod_id} (inaccesible).")

        pedido.items = nuevos_items
        if pedido.items:
            pedidos_limpios.append(pedido)

    return pedidos_limpios, advertencias

def construir_simulacion(
    ruta_escenario: Path,
    modo_waves: str = "Wave Global (Flota)", # Se mantiene por compatibilidad con la UI
    estrategia_recorrido: str = "Vecino más cercano (B)"
) -> tuple[Any, _SimulationTk]:
    """Carga un escenario JSON y arma el warehouse y la simulación."""
    print("=== Wave Picking System ===")
    print(f"1. Cargando escenario: {ruta_escenario}")
    warehouse, productos_raw, pedidos_raw, pickers_raw, configuracion = (
        cargar_escenario(str(ruta_escenario))
    )

    print("2. Creando inventario, pedidos y pickers")
    productos = _crear_productos(productos_raw)
    inventario = GestorInventario()
    for producto in productos:
        inventario.agregar_producto(producto)
    pedidos = _crear_pedidos(pedidos_raw)
    pickers = _crear_pickers(pickers_raw)

    # ASIGNAR POSICIONES ALEATORIAS EN PASILLOS SIN SOLAPAMIENTO
    celdas_transitables = warehouse.celdas_transitables()
    if celdas_transitables:
        if len(pickers) > len(celdas_transitables):
            raise ValueError(
                f"Hay {len(pickers)} pickers y solo {len(celdas_transitables)} "
                "celdas transitables. No se pueden ubicar sin solaparse."
            )
        celdas_elegidas = random.sample(celdas_transitables, len(pickers))
        for picker, celda in zip(pickers, celdas_elegidas):
            nueva_pos = (celda.x, celda.y)
            picker.posicion_inicial = nueva_pos
            picker.posicion_actual = nueva_pos

    _validar_stock_pedidos(pedidos, inventario)

    print("3. Construyendo grafo de circulación")
    grafo = construir_grafo(warehouse)
    if grafo.node_count() == 0:
        raise ValueError("El almacén no contiene celdas transitables.")

    print("4. Preparando rutas dinámicas y zonas de despacho")
    cache = CacheDistancias(grafo)
    puntos_despacho = _obtener_puntos_despacho(warehouse, grafo)
    if pedidos and not puntos_despacho:
        raise ValueError(
            "No hay zonas de despacho accesibles asociadas a una puerta de salida."
        )

    # --- NUEVO: Limpieza de productos en callejones sin salida ---
    print("4.5 Validando accesibilidad de productos")
    pedidos, advertencias = _limpiar_productos_inalcanzables(
        pedidos, inventario, warehouse, grafo, cache, puntos_despacho
    )
    if advertencias:
        print("\n   [!] ADVERTENCIAS DE ACCESIBILIDAD:")
        for adv in advertencias[:15]: # Mostramos las primeras 15
            print(f"       - {adv}")
        if len(advertencias) > 15:
            print(f"       ... y {len(advertencias) - 15} advertencias más.")
    # -------------------------------------------------------------

    print("5. Generando waves (Algoritmo Greedy unificado para todos los pickers)")
    waves, _, waves_por_picker = _crear_waves(pedidos, pickers, inventario, configuracion)
    fases = _crear_fases_simulacion(pickers, waves_por_picker)
    print(f"   Waves generadas: {len(waves)}")

    print(
        f"6. Iniciando motor de simulación: {len(waves)} waves "
        f"en {len(fases)} fases de viaje"
    )

    if not fases:
        fases = [{"asignaciones": {}, "waves_ids": {}}]

    simulacion = _SimulationTk(
        warehouse=warehouse,
        pickers=pickers,
        productos=productos,
        fases=fases,
        cache_distancias=cache,
        puntos_despacho=puntos_despacho,
        grafo=grafo,
        inventario=inventario,
        waves=waves,
        configuracion=configuracion,
        estrategia_recorrido=estrategia_recorrido,
    )
    return warehouse, simulacion


def guardar_partida(ruta_json: Path, sim_tk: _SimulationTk):
    """Guarda el escenario base Y el estado actual de la simulación."""
    from src.io.persistence import crear_datos_escenario

    pedidos_actuales = []
    for wave in sim_tk.waves:
        for pedido in wave.pedidos:
            pedido_dict = {
                "id": pedido.orden_id,
                "prioridad": pedido.prioridad,
                "estado": "PENDIENTE",
                "items": [
                    {"producto_id": pid, "cantidad": cant}
                    for pid, cant in pedido.items
                ]
            }
            pedidos_actuales.append(pedido_dict)

    datos = crear_datos_escenario(
        sim_tk.warehouse,
        sim_tk.productos,
        pedidos_actuales,
        sim_tk.pickers,
        sim_tk.configuracion
    )

    datos["snapshot_simulacion"] = sim_tk.get_snapshot()

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def main() -> None:
    """Abre la aplicación empezando por el menú."""
    raiz_proyecto = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Wave Picking System")
    parser.add_argument(
        "escenario",
        nargs="?",
        help=(
            "Ruta opcional a un escenario JSON que aparece ya cargado en el "
            "menú. Si se omite, se elige con el botón 'Cargar JSON'."
        ),
    )
    argumentos = parser.parse_args()

    controlador = Controlador(
        constructor_simulacion=construir_simulacion,
        tamano_celda=16,
        carpeta_json=raiz_proyecto / "data" / "scenarios",
    )
    if argumentos.escenario:
        ruta_escenario = Path(argumentos.escenario)
        if not ruta_escenario.is_absolute():
            ruta_escenario = raiz_proyecto / ruta_escenario
        controlador.ruta_json = str(ruta_escenario)
    controlador.iniciar()


if __name__ == "__main__":
    main()
