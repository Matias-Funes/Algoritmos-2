"""Motor paso a paso para el movimiento y la recolección de pickers.

La clase mantiene el estado temporal de la simulación y coordina los
movimientos en sincronía. Puede ejecutar rutas ya preparadas o planificar
tramos dinámicos entre racks y zonas de despacho.
"""

from __future__ import annotations

import sys
import heapq
from math import floor
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.inventory import Producto
from src.core.picker import Picker


class Simulation:
    def __init__(
        self,
        warehouse: Any,
        pickers: list[Any],
        rutas: Any = None,
        productos: Any = None,
        pedidos: Any = None,
        inventario: Any = None,
        asignaciones: dict[str, Any] | None = None,
        cache_distancias: Any = None,
        puntos_despacho: dict[str, list[tuple[int, int]]] | None = None,
    ) -> None:
        self.warehouse = warehouse
        self.pickers = [
            self._crear_picker(picker) for picker in pickers
        ]
        self.paso_actual = 0
        self._rutas = {
            picker.id: self._obtener_ruta(
                rutas, picker, indice, len(self.pickers) == 1
            )
            for indice, picker in enumerate(self.pickers)
        }
        self._indices_ruta = {
            picker.id: (
                1
                if self._rutas[picker.id]
                and self._rutas[picker.id][0] == tuple(picker.posicion_actual)
                else 0
            )
            for picker in self.pickers
        }
        self._productos = self._indexar_productos(productos, inventario)
        self._demanda_por_picker: dict[str, dict[str, int]] = {}
        self._demanda_global: dict[str, int] = {}
        self._asignaciones_explicitas = asignaciones is not None
        self._cargar_demanda(pedidos, asignaciones)
        self._demanda_global_inicial = dict(self._demanda_global)
        self._demanda_por_picker_inicial = {
            picker_id: dict(demanda)
            for picker_id, demanda in self._demanda_por_picker.items()
        }
        self._total_productos = sum(self._demanda_global.values()) + sum(
            sum(demanda.values())
            for demanda in self._demanda_por_picker.values()
        )
        self._modo_dinamico = (
            cache_distancias is not None or puntos_despacho is not None
        )
        if self._modo_dinamico and (
            cache_distancias is None or puntos_despacho is None
        ):
            raise ValueError(
                "La navegación dinámica requiere caché de distancias y "
                "puntos de despacho."
            )
        self._cache_distancias = cache_distancias
        self._puntos_despacho = {
            zona_id: list(dict.fromkeys(tuple(punto) for punto in puntos))
            for zona_id, puntos in (puntos_despacho or {}).items()
        }
        self._ticks_bloqueado = {
            picker.id: 0 for picker in self.pickers
        }
        self.productos_recogidos: list[dict[str, Any]] = []
        self.productos_faltantes: list[dict[str, Any]] = []
        self.descargas: list[dict[str, Any]] = []
        self.distancia = 0
        self._en_ejecucion = False
        self._stock_inicial = {
            producto_id: self._valor(
                producto, "cantidad_disponible", default=None
            )
            for producto_id, producto in self._productos.items()
        }
        self._estado_inicial = {
            picker.id: {
                "posicion": tuple(picker.posicion_actual),
                "carga": picker.carga_actual_kg,
                "items": list(picker.items_transportados),
            }
            for picker in self.pickers
        }
        if self._modo_dinamico:
            if self._total_productos and not self._puntos_despacho:
                raise ValueError(
                    "La simulación necesita al menos un punto de despacho "
                    "accesible para recoger productos."
                )
            self._inicializar_navegacion_dinamica()
        else:
            self._recoger_en_posiciones_actuales()

    @staticmethod
    def _crear_picker(picker: Any) -> Any:
        if not isinstance(picker, dict):
            return picker
        ubicacion = picker["posicion_inicial"]
        if isinstance(ubicacion, dict):
            ubicacion = (ubicacion["x"], ubicacion["y"])
        
        # Lee la prioridad desde el JSON
        prioridad = picker.get("prioridad", 1)
        
        return Picker(
            picker.get("id", picker.get("picker_id")),
            tuple(ubicacion),
            picker["capacidad_carga_kg"],
            prioridad=prioridad
        )

    @staticmethod
    def _obtener_ruta(
        rutas: Any, picker: Any, indice: int, es_unico_picker: bool
    ) -> list[tuple[int, int]]:
        if rutas is None:
            ruta = []
        elif isinstance(rutas, dict):
            ruta = rutas.get(picker.id, rutas.get(indice, []))
        elif not rutas:
            ruta = []
        elif rutas and all(
            isinstance(punto, (tuple, list)) and len(punto) == 2
            for punto in rutas
        ):
            ruta = rutas if es_unico_picker or indice == 0 else []
        else:
            ruta = rutas[indice] if indice < len(rutas) else []

        resultado = []
        for punto in ruta:
            if not isinstance(punto, (tuple, list)) or len(punto) != 2:
                raise ValueError(f"Coordenada de ruta inválida: {punto!r}.")
            resultado.append((int(punto[0]), int(punto[1])))
        return resultado

    @staticmethod
    def _indexar_productos(productos: Any, inventario: Any) -> dict[str, Any]:
        if productos is None and inventario is not None:
            if hasattr(inventario, "todos_los_productos"):
                productos = inventario.todos_los_productos()
            elif isinstance(inventario, dict):
                productos = inventario
        if productos is None:
            return {}
        if hasattr(productos, "todos_los_productos"):
            productos = productos.todos_los_productos()
        if isinstance(productos, dict):
            elementos = []
            for producto_id, producto in productos.items():
                elementos.append(
                    producto
                    if not isinstance(producto, dict)
                    else Simulation._crear_producto(producto, producto_id)
                )
        else:
            elementos = [
                Simulation._crear_producto(producto)
                if isinstance(producto, dict)
                else producto
                for producto in productos
            ]
        return {
            str(Simulation._valor(producto, "producto_id", "id")): producto
            for producto in elementos
        }

    @staticmethod
    def _crear_producto(datos: dict[str, Any], producto_id: Any = None) -> Producto:
        ubicacion = datos["ubicacion"]
        if isinstance(ubicacion, dict):
            ubicacion = (
                ubicacion["x"],
                ubicacion["y"],
                ubicacion.get("z", 0),
            )
        return Producto(
            str(datos.get("producto_id", datos.get("id", producto_id))),
            datos.get("nombre", ""),
            datos.get("rack_id", ""),
            tuple(ubicacion),
            datos.get("cantidad_disponible", 0),
            datos.get("peso_kg", 0.0),
        )

    @staticmethod
    def _valor(objeto: Any, *nombres: str, default: Any = None) -> Any:
        for nombre in nombres:
            if isinstance(objeto, dict) and nombre in objeto:
                return objeto[nombre]
            if hasattr(objeto, nombre):
                return getattr(objeto, nombre)
        return default

    @staticmethod
    def _items_de_pedido(pedido: Any) -> list[tuple[str, int]]:
        items = Simulation._valor(pedido, "items", default=[])
        normalizados = []
        for item in items:
            if isinstance(item, dict):
                producto_id = item.get("producto_id", item.get("id"))
                cantidad = item.get("cantidad", 1)
            else:
                producto_id, cantidad = item
            if (
                producto_id is None
                or not isinstance(cantidad, int)
                or isinstance(cantidad, bool)
                or cantidad <= 0
            ):
                raise ValueError(f"Item de pedido inválido: {item!r}.")
            normalizados.append((str(producto_id), cantidad))
        return normalizados

    def _cargar_demanda(self, pedidos: Any, asignaciones: dict[str, Any] | None) -> None:
        if pedidos is not None and asignaciones is None:
            lista_pedidos = getattr(pedidos, "pedidos", pedidos)
            if isinstance(lista_pedidos, dict):
                lista_pedidos = list(lista_pedidos.values())
            for pedido in lista_pedidos:
                for producto_id, cantidad in self._items_de_pedido(pedido):
                    self._demanda_global[producto_id] = (
                        self._demanda_global.get(producto_id, 0) + cantidad
                    )

        if asignaciones is not None:
            for picker_id, asignados in asignaciones.items():
                pedidos_picker = getattr(asignados, "pedidos", asignados)
                if isinstance(pedidos_picker, dict):
                    pedidos_picker = list(pedidos_picker.values())
                demanda: dict[str, int] = {}
                for asignado in pedidos_picker:
                    if isinstance(asignado, dict) and (
                        "producto_id" in asignado or "id" in asignado
                    ):
                        pedido_items = self._items_de_pedido(
                            {"items": [asignado]}
                        )
                    elif isinstance(asignado, (tuple, list)) and len(asignado) == 2:
                        pedido_items = [(str(asignado[0]), asignado[1])]
                    else:
                        pedido_items = self._items_de_pedido(asignado)
                    for producto_id, cantidad in pedido_items:
                        demanda[producto_id] = demanda.get(producto_id, 0) + cantidad
                self._demanda_por_picker[str(picker_id)] = demanda

    def _celda_recoleccion(self, producto: Any) -> tuple[int, int]:
        ubicacion = self._valor(producto, "ubicacion")
        if isinstance(ubicacion, dict):
            x, y = int(ubicacion["x"]), int(ubicacion["y"])
        else:
            x, y = int(ubicacion[0]), int(ubicacion[1])

        if self.warehouse is None or not hasattr(self.warehouse, "grid"):
            return x, y
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < self.warehouse.ancho_x
                and 0 <= ny < self.warehouse.largo_y
                and self.warehouse.grid[ny][nx].tipo == "PASILLO"
            ):
                return nx, ny
        return x, y

    def _cantidad_pendiente(self, picker: Any, producto_id: str) -> int:
        if self._asignaciones_explicitas:
            return self._demanda_por_picker.get(picker.id, {}).get(producto_id, 0)
        return self._demanda_global.get(producto_id, 0)

    def _reducir_demanda(self, picker: Any, producto_id: str, cantidad: int) -> None:
        demanda = (
            self._demanda_por_picker.setdefault(picker.id, {})
            if self._asignaciones_explicitas
            else self._demanda_global
        )
        restante = demanda.get(producto_id, 0) - cantidad
        if restante > 0:
            demanda[producto_id] = restante
        else:
            demanda.pop(producto_id, None)

    def _recoger_en_posicion(self, picker: Any) -> None:
        posicion = tuple(picker.posicion_actual)
        for producto_id, producto in self._productos.items():
            cantidad = self._cantidad_pendiente(picker, producto_id)
            if not cantidad or self._celda_recoleccion(producto) != posicion:
                continue
            stock = self._valor(producto, "cantidad_disponible", default=None)
            if stock is not None and cantidad > stock:
                raise ValueError(
                    f"Stock insuficiente para '{producto_id}': "
                    f"disponible {stock}, pedido {cantidad}."
                )

            if hasattr(picker, "recoger"):
                picker.recoger(producto, cantidad)
            else:
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                picker.carga_actual_kg = getattr(picker, "carga_actual_kg", 0.0) + (
                    peso * cantidad
                )
            
            # --- NUEVA LÍNEA: Pausa para recolección ---
            picker.tiempo_recoleccion = 15
            
            if stock is not None:
                producto.cantidad_disponible -= cantidad
            self._reducir_demanda(picker, producto_id, cantidad)
            self.productos_recogidos.append(
                {
                    "picker_id": picker.id,
                    "producto_id": producto_id,
                    "cantidad": cantidad,
                }
            )

    def _recoger_en_posiciones_actuales(self) -> None:
        for picker in self.pickers:
            self._recoger_en_posicion(picker)

    def _inicializar_navegacion_dinamica(self) -> None:
        self._tramos_dinamicos: dict[str, list[tuple[int, int]]] = {
            picker.id: [] for picker in self.pickers
        }
        self._objetivos_dinamicos: dict[str, dict[str, Any] | None] = {
            picker.id: None for picker in self.pickers
        }
        self._estado_picker: dict[str, str] = {
            picker.id: "activo" for picker in self.pickers
        }
        self._ticks_bloqueado = {
            picker.id: 0 for picker in self.pickers
        }
        self._ticks_sin_movimiento = 0
        self._rutas = {
            picker.id: [tuple(picker.posicion_actual)]
            for picker in self.pickers
        }
        self._indices_ruta = {picker.id: 0 for picker in self.pickers}
        for picker in self.pickers:
            self._planificar_picker_dinamico(picker)

    def _celdas_recoleccion(self, producto: Any) -> list[tuple[int, int]]:
        ubicacion = self._valor(producto, "ubicacion")
        if isinstance(ubicacion, dict):
            x, y = int(ubicacion["x"]), int(ubicacion["y"])
        else:
            x, y = int(ubicacion[0]), int(ubicacion[1])

        if self.warehouse is None or not hasattr(self.warehouse, "grid"):
            return [(x, y)]

        puntos = []
        if self.warehouse.grid[y][x].es_transitable():
            puntos.append((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < self.warehouse.ancho_x
                and 0 <= ny < self.warehouse.largo_y
                and self.warehouse.grid[ny][nx].es_transitable()
            ):
                puntos.append((nx, ny))
        return list(dict.fromkeys(puntos))

    def _registrar_faltante(
        self,
        picker: Any,
        producto_id: str,
        cantidad: int,
        motivo: str,
    ) -> None:
        if cantidad <= 0:
            return
        self.productos_faltantes.append(
            {
                "picker_id": picker.id,
                "producto_id": producto_id,
                "cantidad": cantidad,
                "motivo": motivo,
            }
        )
        self._reducir_demanda(picker, producto_id, cantidad)

    def _ruta_mas_cercana(
        self,
        picker: Any,
        origen: tuple[int, int],
        destinos: list[tuple[int, int]],
    ) -> tuple[tuple[int, int], list[tuple[int, int]]] | None:
        mejor: tuple[float, tuple[int, int], list[tuple[int, int]]] | None = None
        for destino in destinos:
            ruta = self._camino_con_picker(picker, destino)
            if ruta is None:
                continue
            distancia, camino = ruta
            candidato = (distancia, destino, camino)
            if mejor is None or candidato[:2] < mejor[:2]:
                mejor = candidato
        if mejor is None:
            return None
        return mejor[1], mejor[2]

    def _camino_con_picker(
        self,
        picker: Any,
        destino: tuple[int, int],
    ) -> tuple[float, list[tuple[int, int]]] | None:
        origen = tuple(picker.posicion_actual)
        grafo = getattr(self._cache_distancias, "_grafo", None)
        if grafo is None:
            distancia = self._cache_distancias.distancia(origen, destino)
            camino = self._cache_distancias.camino(origen, destino)
            return (distancia, camino) if camino else None

        bloqueadas = {
            tuple(otro.posicion_actual)
            for otro in self.pickers
            if otro.id != picker.id
            and self._estado_picker.get(otro.id) != "terminado"
        }
        if destino in bloqueadas:
            return None

        distancias = {origen: 0.0}
        predecesores = {}
        cola = [(0.0, origen)]
        while cola:
            distancia_actual, actual = heapq.heappop(cola)
            if distancia_actual != distancias.get(actual):
                continue
            if actual == destino:
                break
            for vecino, peso in grafo.get_neighbors(actual).items():
                if vecino in bloqueadas:
                    continue
                nueva_distancia = distancia_actual + peso
                if nueva_distancia < distancias.get(vecino, float("inf")):
                    distancias[vecino] = nueva_distancia
                    predecesores[vecino] = actual
                    heapq.heappush(cola, (nueva_distancia, vecino))

        if destino not in distancias:
            return None
        camino = [destino]
        while camino[-1] != origen:
            camino.append(predecesores[camino[-1]])
        camino.reverse()
        return distancias[destino], camino

    def _establecer_tramo(
        self,
        picker: Any,
        camino: list[tuple[int, int]],
        objetivo: dict[str, Any],
    ) -> None:
        if any(
            abs(origen[0] - destino[0]) + abs(origen[1] - destino[1]) != 1
            for origen, destino in zip(camino, camino[1:])
        ):
            raise ValueError("Las rutas de los pickers no pueden tener diagonales.")
        self._objetivos_dinamicos[picker.id] = objetivo
        self._tramos_dinamicos[picker.id] = camino
        self._indices_ruta[picker.id] = 1
        self._rutas[picker.id].extend(camino[1:])

    @staticmethod
    def _orden_id_picker(picker_id: str) -> tuple[str, int, str]:
        prefijo, separador, sufijo = picker_id.rpartition("_")
        if separador and sufijo.isdigit():
            return prefijo, int(sufijo), picker_id
        return picker_id, -1, picker_id

    def _replanificar_picker_bloqueado(self, picker: Any) -> bool:
        objetivo = self._objetivos_dinamicos.get(picker.id)
        if objetivo is None:
            return False

        opciones: list[tuple[float, tuple[int, int], list[tuple[int, int]]]] = []
        if objetivo["tipo"] == "producto":
            producto = self._productos[objetivo["producto_id"]]
            for destino in self._celdas_recoleccion(producto):
                ruta = self._camino_con_picker(picker, destino)
                if ruta is not None:
                    distancia, camino = ruta
                    opciones.append((distancia, destino, camino))
        elif objetivo["tipo"] == "despacho":
            for zona_id, puntos in self._puntos_despacho.items():
                for destino in puntos:
                    ruta = self._camino_con_picker(picker, destino)
                    if ruta is None:
                        continue
                    distancia, camino = ruta
                    prioridad_zona = 0 if zona_id == objetivo["zona_id"] else 1
                    opciones.append(
                        (distancia + prioridad_zona * 1e-6, destino, camino)
                    )

        if not opciones:
            return False

        _, _, camino = min(opciones, key=lambda opcion: (opcion[0], opcion[1]))
        tramo_actual = self._tramos_dinamicos[picker.id]
        indice_actual = self._indices_ruta[picker.id]
        camino_pendiente = tramo_actual[max(indice_actual - 1, 0) :]
        if camino == camino_pendiente:
            return False

        self._rutas[picker.id] = [tuple(picker.posicion_actual)]
        self._establecer_tramo(picker, camino, objetivo)
        return True

    def _planificar_descarga_dinamica(self, picker: Any) -> bool:
        if not self._puntos_despacho:
            raise ValueError(
                f"El picker {picker.id} necesita descargar, pero no hay "
                "puntos de despacho configurados."
            )

        ocupadas = {
            tuple(otro.posicion_actual)
            for otro in self.pickers
            if otro.id != picker.id
            and self._estado_picker.get(otro.id) != "terminado"
        }
        opciones = []
        hay_punto_alcanzable = False
        puntos_ocupados = 0
        origen = tuple(picker.posicion_actual)
        for zona_id, puntos in self._puntos_despacho.items():
            for punto in puntos:
                if punto in ocupadas:
                    puntos_ocupados += 1
                    continue
                ruta = self._camino_con_picker(picker, punto)
                if ruta is None:
                    camino = self._cache_distancias.camino(origen, punto)
                    if not camino:
                        continue
                    ruta = (
                        self._cache_distancias.distancia(origen, punto),
                        camino,
                    )
                hay_punto_alcanzable = True
                distancia, camino = ruta
                opciones.append((distancia, zona_id, punto, camino))

        if not opciones:
            cantidad_puntos = sum(
                len(puntos) for puntos in self._puntos_despacho.values()
            )
            if cantidad_puntos and puntos_ocupados == cantidad_puntos:
                return False
            if not hay_punto_alcanzable:
                raise ValueError(
                    f"No hay una ruta desde {origen} hasta una zona de "
                    f"despacho para el picker {picker.id}."
                )
            return False

        _, zona_id, punto, camino = min(
            opciones, key=lambda opcion: (opcion[0], opcion[1], opcion[2])
        )
        self._establecer_tramo(
            picker,
            camino,
            {"tipo": "despacho", "zona_id": zona_id, "punto": punto},
        )
        return True

    def _planificar_picker_dinamico(self, picker: Any) -> None:
        if self._estado_picker[picker.id] == "terminado":
            return
        if self._indices_ruta[picker.id] < len(
            self._tramos_dinamicos[picker.id]
        ):
            return

        objetivo_anterior = self._objetivos_dinamicos[picker.id]
        if objetivo_anterior is not None:
            self._atender_objetivo_dinamico(picker, objetivo_anterior)
            self._objetivos_dinamicos[picker.id] = None
        self._tramos_dinamicos[picker.id] = []
        self._indices_ruta[picker.id] = 0

        while self._estado_picker[picker.id] != "terminado":
            demanda = (
                self._demanda_por_picker.get(picker.id, {})
                if self._asignaciones_explicitas
                else self._demanda_global
            )
            for producto_id, cantidad in list(demanda.items()):
                producto = self._productos.get(producto_id)
                if producto is None:
                    raise ValueError(
                        f"El pedido del picker {picker.id} referencia el "
                        f"producto inexistente '{producto_id}'."
                    )
                stock = self._valor(
                    producto, "cantidad_disponible", default=None
                )
                if stock is not None and stock <= 0:
                    self._registrar_faltante(
                        picker, producto_id, cantidad, "stock_agotado"
                    )

            demanda = (
                self._demanda_por_picker.get(picker.id, {})
                if self._asignaciones_explicitas
                else self._demanda_global
            )
            if not demanda:
                if picker.carga_actual_kg > 1e-9:
                    if self._planificar_descarga_dinamica(picker):
                        if len(self._tramos_dinamicos[picker.id]) == 1:
                            objetivo = self._objetivos_dinamicos[picker.id]
                            self._objetivos_dinamicos[picker.id] = None
                            self._atender_objetivo_dinamico(picker, objetivo)
                            continue
                    return
                self._estado_picker[picker.id] = "terminado"
                return

            capacidad_libre = (
                picker.capacidad_carga_kg - picker.carga_actual_kg
            )
            origen = tuple(picker.posicion_actual)
            opciones = []
            inalcanzables = []
            for producto_id, cantidad in demanda.items():
                producto = self._productos[producto_id]
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                if peso > 0:
                    unidades_posibles = floor(
                        (capacidad_libre + 1e-9) / peso
                    )
                    if unidades_posibles <= 0:
                        continue
                else:
                    unidades_posibles = cantidad

                puntos = self._celdas_recoleccion(producto)
                ruta = self._ruta_mas_cercana(picker, origen, puntos)
                if ruta is None:
                    puntos_alcanzables = [
                        (self._cache_distancias.distancia(origen, punto), punto)
                        for punto in puntos
                    ]
                    puntos_alcanzables = [
                        (distancia, punto)
                        for distancia, punto in puntos_alcanzables
                        if distancia != float("inf")
                    ]
                    if not puntos_alcanzables:
                        inalcanzables.append(producto_id)
                        continue
                    _, punto = min(puntos_alcanzables)
                    camino = self._cache_distancias.camino(origen, punto)
                    if not camino:
                        inalcanzables.append(producto_id)
                        continue
                    ruta = punto, camino
                punto, camino = ruta
                distancia = len(camino) - 1
                opciones.append((distancia, producto_id, camino))

            if opciones:
                _, producto_id, camino = min(
                    opciones, key=lambda opcion: (opcion[0], opcion[1])
                )
                objetivo = {"tipo": "producto", "producto_id": producto_id}
                if len(camino) == 1:
                    self._atender_objetivo_dinamico(picker, objetivo)
                    continue
                self._establecer_tramo(picker, camino, objetivo)
                return

            if picker.carga_actual_kg > 1e-9:
                if self._planificar_descarga_dinamica(picker):
                    camino = self._tramos_dinamicos[picker.id]
                    if len(camino) == 1:
                        objetivo = self._objetivos_dinamicos[picker.id]
                        self._objetivos_dinamicos[picker.id] = None
                        self._atender_objetivo_dinamico(picker, objetivo)
                        continue
                return

            for producto_id, cantidad in list(demanda.items()):
                producto = self._productos[producto_id]
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                motivo = (
                    "capacidad_picker"
                    if peso > picker.capacidad_carga_kg
                    else "sin_ruta"
                    if producto_id in inalcanzables
                    else "capacidad_picker"
                )
                self._registrar_faltante(
                    picker, producto_id, cantidad, motivo
                )

    def _atender_objetivo_dinamico(
        self,
        picker: Any,
        objetivo: dict[str, Any] | None,
    ) -> None:
        if objetivo is None:
            return
        if objetivo["tipo"] == "ceder":
            return
        if objetivo["tipo"] == "producto":
            self._recoger_objetivo_dinamico(
                picker, objetivo["producto_id"]
            )
            return

        items = picker.descargar()
        puerta_id = None
        if self.warehouse is not None:
            zona = self.warehouse.zonas.get(objetivo["zona_id"])
            puerta_id = zona.puerta_id if zona is not None else None
        self.descargas.append(
            {
                "picker_id": picker.id,
                "zona_id": objetivo["zona_id"],
                "puerta_id": puerta_id,
                "paso": self.paso_actual,
                "items": [
                    {"producto_id": producto_id, "cantidad": cantidad}
                    for producto_id, cantidad in items
                ],
            }
        )

    def _recoger_objetivo_dinamico(
        self,
        picker: Any,
        producto_id: str,
    ) -> None:
        producto = self._productos[producto_id]
        pendiente = self._cantidad_pendiente(picker, producto_id)
        if pendiente <= 0:
            return

        stock = self._valor(producto, "cantidad_disponible", default=None)
        disponible = pendiente if stock is None else min(pendiente, stock)
        peso = float(self._valor(producto, "peso_kg", default=0.0))
        capacidad_libre = max(
            picker.capacidad_carga_kg - picker.carga_actual_kg, 0.0
        )
        unidades_capacidad = (
            disponible
            if peso <= 0
            else floor((capacidad_libre + 1e-9) / peso)
        )
        cantidad = min(disponible, unidades_capacidad)
        if cantidad <= 0:
            return

        picker.recoger(producto, cantidad)
        
        # --- NUEVA LÍNEA: Pausa para recolección ---
        picker.tiempo_recoleccion = 15
        
        if stock is not None:
            producto.cantidad_disponible -= cantidad
        self._reducir_demanda(picker, producto_id, cantidad)
        self.productos_recogidos.append(
            {
                "picker_id": picker.id,
                "producto_id": producto_id,
                "cantidad": cantidad,
            }
        )

    def avanzar_paso(self) -> bool:
        propuestas: dict[str, tuple[int, int]] = {}
        if self._modo_dinamico:
            for picker in self.pickers:
                # --- NUEVA LÍNEA: No planificar si está recolectando ---
                if getattr(picker, "tiempo_recoleccion", 0) > 0:
                    continue
                self._planificar_picker_dinamico(picker)
                
        for picker in self.pickers:
            # --- NUEVA LÍNEA: Frenar y descontar tiempo ---
            if getattr(picker, "tiempo_recoleccion", 0) > 0:
                picker.tiempo_recoleccion -= 1
                continue
            # ------------------------------------------------
            
            if self._modo_dinamico:
                tramo = self._tramos_dinamicos[picker.id]
                indice = self._indices_ruta[picker.id]
                if indice < len(tramo):
                    propuestas[picker.id] = tramo[indice]
            else:
                ruta = self._rutas[picker.id]
                indice = self._indices_ruta[picker.id]
                if indice < len(ruta):
                    propuestas[picker.id] = ruta[indice]

        if not propuestas:
            if not self._modo_dinamico or all(
                estado == "terminado"
                for estado in self._estado_picker.values()
            ):
                self._en_ejecucion = False
                return False
            self.paso_actual += 1
            self._ticks_sin_movimiento += 1
            if self._ticks_sin_movimiento > max(10, len(self.pickers) * 10):
                raise RuntimeError(
                    "Los pickers no pueden avanzar: todos los puntos de "
                    "despacho alcanzables están ocupados."
                )
            self._en_ejecucion = True
            return True

        self.paso_actual += 1
        destinos: dict[tuple[int, int], list[Any]] = {}
        for picker in self.pickers:
            if picker.id in propuestas:
                destinos.setdefault(propuestas[picker.id], []).append(picker)

        aceptados: set[str] = set()
        bloqueos_por_picker: dict[str, set[str]] = {}
        for pickers_destino in destinos.values():
            # El ganador de la celda es el que tiene MAYOR prioridad.
            ganador = min(
                pickers_destino,
                key=lambda picker: (
                    -picker.prioridad, # Menor prioridad (ej: 1) se frena, mayor (ej: 5) avanza.
                    str(picker.id),
                ),
            )
            aceptados.add(ganador.id)
            for picker in pickers_destino:
                if picker.id != ganador.id:
                    bloqueos_por_picker.setdefault(picker.id, set()).add(
                        ganador.id
                    )

        if self._modo_dinamico:
            picker_por_zona: dict[str, str] = {}
            for picker in self.pickers:
                objetivo = self._objetivos_dinamicos[picker.id]
                if (
                    picker.id not in aceptados
                    or objetivo is None
                    or objetivo["tipo"] != "despacho"
                    or propuestas[picker.id] != objetivo["punto"]
                ):
                    continue
                zona_id = objetivo["zona_id"]
                if zona_id in picker_por_zona:
                    aceptados.remove(picker.id)
                    bloqueos_por_picker.setdefault(picker.id, set()).add(
                        picker_por_zona[zona_id]
                    )
                else:
                    picker_por_zona[zona_id] = picker.id

        cambio = True
        while cambio:
            cambio = False
            posiciones_ocupadas = {
                tuple(picker.posicion_actual): picker.id
                for picker in self.pickers
                if picker.id not in aceptados
                and (
                    not self._modo_dinamico
                    or self._estado_picker[picker.id] != "terminado"
                )
            }
            for picker in self.pickers:
                if picker.id not in aceptados:
                    continue
                ocupante = posiciones_ocupadas.get(propuestas[picker.id])
                if ocupante is not None:
                    bloqueos_por_picker.setdefault(picker.id, set()).add(
                        ocupante
                    )
                    aceptados.remove(picker.id)
                    cambio = True

        for indice, picker in enumerate(self.pickers):
            if picker.id not in aceptados:
                continue
            for otro in self.pickers[indice + 1 :]:
                if (
                    otro.id in aceptados
                    and propuestas[picker.id] == tuple(otro.posicion_actual)
                    and propuestas[otro.id] == tuple(picker.posicion_actual)
                ):
                    bloqueos_por_picker.setdefault(picker.id, set()).add(otro.id)
                    bloqueos_por_picker.setdefault(otro.id, set()).add(picker.id)
                    aceptados.remove(picker.id)
                    aceptados.remove(otro.id)

        for picker in self.pickers:
            if picker.id not in aceptados:
                continue
            destino = propuestas[picker.id]
            anterior = tuple(picker.posicion_actual)
            picker.mover_a(destino)
            self._indices_ruta[picker.id] += 1
            self.distancia += abs(destino[0] - anterior[0]) + abs(
                destino[1] - anterior[1]
            )
            if not self._modo_dinamico:
                self._recoger_en_posicion(picker)

        if self._modo_dinamico:
            for picker in self.pickers:
                bloqueadores = bloqueos_por_picker.get(picker.id, set())
                if not bloqueadores:
                    self._ticks_bloqueado[picker.id] = 0
                    continue
                self._ticks_bloqueado[picker.id] += 1
                espera = self._ticks_bloqueado[picker.id]
                es_picker_mayor = all(
                    self._orden_id_picker(picker.id)
                    > self._orden_id_picker(bloqueador_id)
                    for bloqueador_id in bloqueadores
                )
                if (
                    espera >= 2
                    and (espera - 2) % 5 == 0
                    and es_picker_mayor
                ):
                    self._replanificar_picker_bloqueado(picker)

            if aceptados:
                self._ticks_sin_movimiento = 0
            else:
                self._ticks_sin_movimiento += 1
                if self._ticks_sin_movimiento > max(10, len(self.pickers) * 10):
                    raise RuntimeError(
                        "Los pickers llevan más de un tick bloqueados. "
                        "No se encontró una ruta alternativa. Revisá la "
                        "circulación y los puntos de despacho."
                    )

            for picker in self.pickers:
                if (
                    picker.id not in aceptados
                    or self._indices_ruta[picker.id]
                    < len(self._tramos_dinamicos[picker.id])
                ):
                    continue
                objetivo = self._objetivos_dinamicos[picker.id]
                self._objetivos_dinamicos[picker.id] = None
                self._tramos_dinamicos[picker.id] = []
                self._indices_ruta[picker.id] = 0
                self._atender_objetivo_dinamico(picker, objetivo)

            for picker in self.pickers:
                self._planificar_picker_dinamico(picker)

        quedan_pasos = (
            any(estado != "terminado" for estado in self._estado_picker.values())
            if self._modo_dinamico
            else any(
                self._indices_ruta[picker.id] < len(self._rutas[picker.id])
                for picker in self.pickers
            )
        )
        self._en_ejecucion = quedan_pasos
        return quedan_pasos

    def get_estado(self) -> dict[str, Any]:
        return {
            "paso_actual": self.paso_actual,
            "pickers": [
                {
                    "id": picker.id,
                    "x": picker.posicion_actual[0],
                    "y": picker.posicion_actual[1],
                    "carga_actual_kg": picker.carga_actual_kg,
                    "items_transportados": [
                        {"producto_id": producto_id, "cantidad": cantidad}
                        for producto_id, cantidad in picker.items_transportados
                    ],
                    "productos_transportados": sum(
                        cantidad
                        for _, cantidad in picker.items_transportados
                    ),
                    "productos_objetivo": sum(
                        self._demanda_por_picker_inicial.get(
                            picker.id, {}
                        ).values()
                    )
                    if self._asignaciones_explicitas
                    else sum(self._demanda_global_inicial.values()),
                    "activo": (
                        not self._modo_dinamico
                        or self._estado_picker[picker.id] != "terminado"
                    ),
                    
                    # --- NUEVA LÍNEA: Informar a la UI si está recolectando ---
                    "recolectando": getattr(picker, "tiempo_recoleccion", 0) > 0
                }
                for picker in self.pickers
            ],
            "rutas": [list(self._rutas[picker.id]) for picker in self.pickers],
            "productos_recogidos": sum(
                item["cantidad"] for item in self.productos_recogidos
            ),
            "total_productos": self._total_productos,
            "distancia": self.distancia,
            
            # Le pasamos a la UI los pedidos que se están procesando actualmente
            "pedidos_actuales": (
                self._demanda_por_picker
                if self._asignaciones_explicitas
                else self._demanda_global
            ),
            
            "recolecciones": [dict(item) for item in self.productos_recogidos],
            "faltantes": [dict(item) for item in self.productos_faltantes],
            "productos_despachados": sum(
                item["cantidad"]
                for descarga in self.descargas
                for item in descarga["items"]
            ),
            "descargas": [
                {**descarga, "items": [dict(item) for item in descarga["items"]]}
                for descarga in self.descargas
            ],
        }

    def iniciar(self) -> None:
        self._en_ejecucion = True

    def pausar(self) -> None:
        self._en_ejecucion = False

    def continuar(self) -> None:
        """Reanuda la simulación desde donde se pausó."""
        self._en_ejecucion = True

    def resetear(self) -> None:
        for picker in self.pickers:
            inicial = self._estado_inicial[picker.id]
            picker.mover_a(inicial["posicion"])
            picker.items_transportados = list(inicial["items"])
            picker.carga_actual_kg = inicial["carga"]
            # --- NUEVA LÍNEA: Reiniciar la pausa ---
            picker.tiempo_recoleccion = 0 
        
        self._indices_ruta = {
            picker.id: (
                1
                if self._rutas[picker.id]
                and self._rutas[picker.id][0]
                == tuple(picker.posicion_actual)
                else 0
            )
            for picker in self.pickers
        }
        self.paso_actual = 0
        self.distancia = 0
        self.productos_recogidos.clear()
        self.productos_faltantes.clear()
        self.descargas.clear()
        self._en_ejecucion = False
        self._demanda_global = dict(self._demanda_global_inicial)
        self._demanda_por_picker = {
            picker_id: dict(demanda)
            for picker_id, demanda in self._demanda_por_picker_inicial.items()
        }
        for producto_id, stock in self._stock_inicial.items():
            if stock is not None:
                self._productos[producto_id].cantidad_disponible = stock
        if self._modo_dinamico:
            self._inicializar_navegacion_dinamica()
        else:
            self._recoger_en_posiciones_actuales()